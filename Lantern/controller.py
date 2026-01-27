import os
import re
import difflib
from typing import Dict, Optional, Any, List
from definitions import ActionType, UserEventType
from tree import add_child, navigate_to_node
from prompt_builder import build_prompt
from llm_client import call_llm


# --- פונקציות עזר לטעינה וניהול ---

def load_academic_principles() -> str:
    """טוען את מסמך העקרונות האקדמיים מהקובץ החיצוני."""
    filename = "academic_writing_principles.md"
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def generate_diff_html_legacy(old_text: str, new_text: str) -> str:
    """Legacy: Simple word-based diff (destroys paragraph structure)."""
    output = []
    matcher = difflib.SequenceMatcher(None, old_text.split(), new_text.split())

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            old_part = " ".join(old_text.split()[i1:i2])
            new_part = " ".join(new_text.split()[j1:j2])
            output.append(f'<span style="color:#ef4444; text-decoration:line-through;">{old_part}</span>')
            output.append(f'<span style="color:#10b981; font-weight:bold;">{new_part}</span>')
        elif tag == 'delete':
            deleted_part = " ".join(old_text.split()[i1:i2])
            output.append(f'<span style="color:#ef4444; text-decoration:line-through;">{deleted_part}</span>')
        elif tag == 'insert':
            added_part = " ".join(new_text.split()[j1:j2])
            output.append(f'<span style="color:#10b981; font-weight:bold;">{added_part}</span>')
        elif tag == 'equal':
            output.append(" ".join(old_text.split()[i1:i2]))

    return " ".join(output)


def _diff_paragraph_content(old_p: str, new_p: str) -> str:
    """Helper: Performs word-level diff on a single paragraph."""
    # Uses the legacy logic for internal paragraph content
    return generate_diff_html_legacy(old_p, new_p)


def generate_diff_html(old_text: str, new_text: str) -> str:
    """
    Inline diff that preserves paragraph structure (newlines).
    1. Replaces newlines with a unique token.
    2. Diffs as a single word stream.
    3. Reconstructs with <br> tags.
    """
    token = "__BR_TOKEN__"
    # Pad newlines with spaces to ensure they are treated as standalone tokens
    old_tokenized = old_text.replace('\n', f" {token} ")
    new_tokenized = new_text.replace('\n', f" {token} ")

    output = []
    # Split by whitespace
    old_words = old_tokenized.split()
    new_words = new_tokenized.split()

    matcher = difflib.SequenceMatcher(None, old_words, new_words)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            old_part = " ".join(old_words[i1:i2])
            new_part = " ".join(new_words[j1:j2])
            # Restore newlines inside the tags if any
            old_part = old_part.replace(token, "<br>")
            new_part = new_part.replace(token, "<br>")
            output.append(f'<span style="color:#ef4444; text-decoration:line-through;">{old_part}</span>')
            output.append(f'<span style="color:#10b981; font-weight:bold;">{new_part}</span>')
        elif tag == 'delete':
            deleted_part = " ".join(old_words[i1:i2])
            deleted_part = deleted_part.replace(token, "<br>")
            output.append(f'<span style="color:#ef4444; text-decoration:line-through;">{deleted_part}</span>')
        elif tag == 'insert':
            added_part = " ".join(new_words[j1:j2])
            added_part = added_part.replace(token, "<br>")
            output.append(f'<span style="color:#10b981; font-weight:bold;">{added_part}</span>')
        elif tag == 'equal':
            part = " ".join(old_words[i1:i2])
            part = part.replace(token, "<br>")
            output.append(part)

    # Join and cleanup extra spaces around <br> tags to prevent "floating" punctuation or gaps
    res = " ".join(output)
    res = res.replace(" <br> ", "<br>").replace("<br> ", "<br>").replace(" <br>", "<br>")
    return res


# --- הפונקציה שהייתה חסרה והוחזרה ---
def apply_fuzzy_replacement(full_text: str, target: str, replacement: str) -> Optional[str]:
    if not target or not full_text:
        return None
    if target in full_text:
        return full_text.replace(target, replacement, 1)

    matcher = difflib.SequenceMatcher(None, full_text, target)
    match = matcher.find_longest_match(0, len(full_text), 0, len(target))

    if match.size > len(target) * 0.8:
        start, end = match.a, match.a + match.size
        return full_text[:start] + replacement + full_text[end:]
    return None


# -------------------------------------


def decide_anchor(tree: Dict, user_text: Optional[str]) -> str:
    return tree["current"]


def build_focus(tree: Dict, anchor_id: str, user_text: Optional[str]) -> str:
    if user_text:
        return user_text.strip()
    return tree["nodes"][anchor_id]["summary"]


def parse_llm_options(llm_output: str) -> List[str]:
    """
    מפרק את פלט ה-LLM לאופציות בצורה רובוסטית.
    """
    # ניקוי פורמטים נפוצים של markdown
    clean_output = llm_output.replace("**Title:**", "Title:").replace("**Title**:", "Title:")
    clean_output = clean_output.replace("**Module:**", "Module:").replace("**Module**:", "Module:")
    clean_output = clean_output.replace("**Explanation:**", "Explanation:").replace("**Explanation**:", "Explanation:")
    clean_output = clean_output.replace("**Critique:**", "Critique:").replace("**Critique**:", "Critique:")

    # אם יש "Title:", ננסה לפצל לפי זה (כולל מספור לפני)
    if "Title:" in clean_output:
        # פיצול לפי התחלות של אפשרויות (Title: או מספר ואז Title:)
        candidates = re.split(r"(?=\n(?:\d+\.|\*|-)?\s*Title:|^(?:\d+\.|\*|-)?\s*Title:)", clean_output.strip())
        return [c.strip() for c in candidates if c.strip() and "Title:" in c]

    # fallback לשיטה הישנה של בלוקים
    blocks = clean_output.split("\n\n")
    return [block.strip() for block in blocks if len(block.strip()) > 20]


# --- ניהול אירועים ראשי ---

def handle_event(tree: Dict, event_type: UserEventType, event_context: Optional[Dict[str, Any]] = None) -> Dict:
    system_rules = load_academic_principles()
    event_context = event_context or {}

    if event_type == UserEventType.ACTION:
        return _handle_action(tree, event_context, system_rules)

    if event_type == UserEventType.CHOOSE_OPTION:
        return _handle_choose_option(tree, event_context)

    raise ValueError("Unsupported UserEventType")


def _handle_action(tree: Dict, event_context: Dict[str, Any], system_rules: str) -> Dict:
    action = event_context.get("action")
    user_text = event_context.get("user_text")
    pinned_context = event_context.get("pinned_context", [])

    if not isinstance(action, ActionType):
        raise ValueError("Invalid or missing ActionType")

    anchor_id = decide_anchor(tree, user_text)
    base_focus = build_focus(tree, anchor_id, user_text)

    # בניית Constraints
    constraints = []
    if system_rules:
        constraints.append("### ACADEMIC WRITING PRINCIPLES ###\n" + system_rules)

    if pinned_context:
        pinned_texts = [item["text"] if isinstance(item, dict) else item for item in pinned_context]
        constraints.append(f"Pinned context:\n- " + "\n- ".join(pinned_texts))

    if action == ActionType.DIVERGE:
        current_node = tree["nodes"][anchor_id]
        existing_summaries = [tree["nodes"][cid]["summary"] for cid in current_node.get("children", []) if
                              cid in tree["nodes"]]
        if existing_summaries:
            constraints.append(f"ALREADY EXPLORED (Do not repeat):\n- " + "\n- ".join(existing_summaries))

    knowledge_base = event_context.get("knowledge_base", {})
    if knowledge_base:
        kb_text = "\n\n".join([f"--- FILE: {name} ---\n{content}" for name, content in knowledge_base.items()])
        constraints.append(f"### REFERENCE KNOWLEDGE BASE ###\n{kb_text}")

    constraints.append("IMPORTANT: Respond in the same language as the input text.")

    # שליחה ל-LLM
    constraints_str = "\n".join(constraints) if constraints else ""
    prompt = build_prompt(action, base_focus, instructions=constraints_str)
    llm_output = call_llm(prompt)

    # --- DIVERGE (הרחבה) - כן נכנס לעץ ---
    if action == ActionType.DIVERGE:
        options = parse_llm_options(llm_output)
        final_options = []

        for option in options:
            title = "Alternative Perspective"
            module = "Analysis"
            explanation = option

            try:
                # ניקוי כותרות שדה בצורה גמישה
                clean_opt = option
                
                # regex חכם יותר שתופס וריאציות
                title_match = re.search(r"(?:Title|שם|נושא):\s*(.*?)(?:\n|Module:|מחלקה:|Explanation:|הסבר:|$)", clean_opt, re.IGNORECASE)
                module_match = re.search(r"(?:Module|מחלקה|עקרון):\s*(.*?)(?:\n|Explanation:|הסבר:|$)", clean_opt, re.IGNORECASE)
                # Explanation/Critique as synonyms
                exp_match = re.search(r"(?:Explanation|Critique|הסבר|ביקורת):\s*(.*)", clean_opt, re.DOTALL | re.IGNORECASE)

                if title_match: title = title_match.group(1).strip(" *")
                if module_match: module = module_match.group(1).strip()
                if exp_match: explanation = exp_match.group(1).strip()
                else:
                    # אם לא מצאנו Explanation רשמי, ניקח את הכל אחרי ה-Module או ה-Title
                    explanation = re.sub(r"^(?:Title|Module).*?\n", "", clean_opt, flags=re.MULTILINE | re.IGNORECASE).strip()
            except:
                pass

            if not explanation or len(explanation) < 5: continue

            # Determine scope label
            focus_ctx = event_context.get("focus_context", {})
            focus_mode = focus_ctx.get("mode", "Whole document")
            scope_label = "Whole Document" if focus_mode == "Whole document" else f"Paragraph {focus_ctx.get('block_idx', 1)}"

            meta = {
                "label": title,
                "module": module,
                "explanation": explanation,
                "idea_text": option,
                "scope": scope_label,
                "source_context": event_context.get("user_text", "")
            }
            # הוספה לעץ
            add_child(tree, anchor_id, explanation, metadata=meta)
            final_options.append(option)

        return {"mode": "options", "options": final_options}

    # --- CRITIQUE (ביקורת) - לא נכנס לעץ ---
    if action == ActionType.CRITIQUE:
        options = parse_llm_options(llm_output)
        critique_items = []

        for opt in options:
            if "NO_CRITIQUE_NEEDED" in opt: continue

            title = "Critique"
            module = "Review"
            body = opt

            try:
                clean_opt = opt.replace("**Title:**", "Title:").replace("**Module:**", "Module:").replace(
                    "**Critique:**", "Critique:")

                title_match = re.search(r"Title:\s*(.*?)(?=\n|Module:|Critique:|$)", clean_opt, re.IGNORECASE)
                module_match = re.search(r"Module:\s*(.*?)(?=\n|Critique:|$)", clean_opt, re.IGNORECASE)
                body_match = re.search(r"Critique:\s*(.*)", clean_opt, re.DOTALL | re.IGNORECASE)

                if title_match: title = title_match.group(1).strip(" *")
                if module_match: module = module_match.group(1).strip()
                if body_match: body = body_match.group(1).strip()

            except:
                pass

            # Determine scope label
            focus_ctx = event_context.get("focus_context", {})
            focus_mode = focus_ctx.get("mode", "Whole document")
            scope_label = "Whole Document" if focus_mode == "Whole document" else f"Paragraph {focus_ctx.get('block_idx', 1)}"

            # החזרת אובייקט נתונים ללא הוספה לעץ
            critique_items.append({
                "title": title,
                "module": module,
                "text": body,
                "raw_text": opt,
                "scope": scope_label
            })

        return {"mode": "critique", "items": critique_items}

    if action == ActionType.REFINE:
        suggestions = []
        # Support various field labels (English/Hebrew) and markdown bolding
        blocks = re.split(r"(?=\n\s*(?:Original|מקור):|^s*(?:Original|מקור):)", llm_output.strip())
        
        for i, block in enumerate(blocks):
            if not block.strip(): continue
            try:
                # Clean up bolding and common field labels
                clean_block = block.replace("**Original:**", "Original:").replace("**Proposed:**", "Proposed:").replace("**Reason:**", "Reason:").replace("**Type:**", "Type:")
                clean_block = clean_block.replace("**מקור:**", "Original:").replace("**מוצע:**", "Proposed:").replace("**הסבר:**", "Reason:").replace("**סוג:**", "Type:")
                
                orig_match = re.search(r"Original:\s*(.*?)(?:\n|Proposed:|Reason:|Type:|$)", clean_block, re.DOTALL | re.IGNORECASE)
                prop_match = re.search(r"Proposed:\s*(.*?)(?:\n|Reason:|Type:|$)", clean_block, re.DOTALL | re.IGNORECASE)
                type_match = re.search(r"Type:\s*(.*?)(?:\n|Reason:|$)", clean_block, re.DOTALL | re.IGNORECASE)
                reason_match = re.search(r"Reason:\s*(.*)", clean_block, re.DOTALL | re.IGNORECASE)
                
                if orig_match and prop_match:
                    # Determine scope label
                    focus_ctx = event_context.get("focus_context", {})
                    focus_mode = focus_ctx.get("mode", "Whole document")
                    scope_label = "Whole Document" if focus_mode == "Whole document" else f"Paragraph {focus_ctx.get('block_idx', 1)}"
                    
                    suggestions.append({
                        "id": f"refine_{i}_{os.urandom(2).hex()}",
                        "original": orig_match.group(1).strip(),
                        "proposed": prop_match.group(1).strip(),
                        "type": type_match.group(1).strip() if type_match else "Improvement",
                        "reason": reason_match.group(1).strip() if reason_match else "General improvement",
                        "status": "pending",
                        "scope": scope_label
                    })
            except:
                continue

        # Fallback for plain text refinements (if the LLM ignored formatting rules)
        if not suggestions:
             return {"mode": "refine_legacy", "refined_text": llm_output.strip(), "diff_html": generate_diff_html(base_focus, llm_output.strip())}

        return {"mode": "refine_suggestions", "items": suggestions}

    return {"status": "error", "message": "Unknown action"}


def _handle_choose_option(tree: Dict, event_context: Dict[str, Any]) -> Dict:
    option_index = event_context.get("option_index")
    current_id = tree["current"]
    children = tree["nodes"][current_id]["children"]
    chosen_child_id = children[option_index]
    navigate_to_node(tree, chosen_child_id)
    return {"mode": "continue", "current_text": tree["nodes"][chosen_child_id]["summary"]}