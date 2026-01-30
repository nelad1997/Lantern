import os
import re
import difflib
from typing import Dict, Optional, Any, List
from definitions import ActionType, UserEventType
from tree import add_child, navigate_to_node
from prompt_builder import build_prompt
from llm_client import call_llm
import logging

logger = logging.getLogger(__name__)


# --- פונקציות עזר לטעינה וניהול ---

def load_academic_principles(action: Optional[ActionType] = None) -> str:
    """טוען את מסמך העקרונות האקדמיים ומסנן לפי הפעולה הנדרשת."""
    filename = "academic_writing_principles"
    if not os.path.exists(filename):
        filename = "academic_writing_principles.md"
        
    if not os.path.exists(filename):
        return ""
        
    with open(filename, "r", encoding="utf-8") as f:
        full_text = f.read().strip()
        
    if not action:
        return full_text
        
    # Mapping modules to actions to save tokens
    # Action -> Module Keywords
    mapping = {
        ActionType.DIVERGE: ["Module 4", "Module 5", "Synthesis", "Partner Behaviors", "VII"],
        ActionType.CRITIQUE: ["Module 1", "Module 5", "Devil's Advocate", "Ethics", "VII"],
        ActionType.REFINE: ["Module 2", "Module 3", "Old-to-New", "Nominalization", "VI"],
        ActionType.SEGMENT: ["Module 2.1", "Module 2.2", "Section-Level", "Architecture"],
    }
    
    relevant_keywords = mapping.get(action, [])
    if not relevant_keywords:
        return full_text
        
    # Split by headers (##) and filter
    sections = re.split(r"(?=^##)", full_text, flags=re.MULTILINE)
    filtered = [sections[0]] # Keep Intro/Phase 0 usually
    
    for section in sections[1:]:
        if any(kw.lower() in section.lower() for kw in relevant_keywords):
            filtered.append(section)
            
    return "\n\n".join(filtered)


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
def apply_fuzzy_replacement(full_html: str, target: str, replacement: str) -> Optional[str]:
    """
    Improved HTML-aware replacement. Handles tags and entities (like &nbsp;) correctly.
    """
    if not target or not full_html:
        return None
        
    # 1. Lex HTML into Tokens: (Type, Content, HTML_Index)
    # Type: 0=Text, 1=Tag, 2=Entity
    tokens = []
    i = 0
    while i < len(full_html):
        if full_html[i] == '<':
            # Tag
            end = full_html.find('>', i)
            if end != -1:
                tokens.append((1, full_html[i:end+1], i))
                i = end + 1
                continue
        elif full_html[i] == '&':
            # Entity?
            end = full_html.find(';', i)
            if end != -1 and end - i < 10:
                tokens.append((2, full_html[i:end+1], i))
                i = end + 1
                continue
        
        # Plain text
        tokens.append((0, full_html[i], i))
        i += 1

    # 2. Build plain text and map plain indices back to Token Index
    plain_text = ""
    plain_to_token_map = [] # list of token_idx
    
    for idx, (type, content, start_idx) in enumerate(tokens):
        if type == 0: # Text char
            plain_text += content
            plain_to_token_map.append(idx)
        elif type == 2: # Entity
            # Map common entities to space/char
            if content == "&nbsp;":
                plain_text += " "
            elif content == "&lt;":
                plain_text += "<"
            elif content == "&gt;":
                plain_text += ">"
            elif content == "&amp;":
                plain_text += "&"
            else:
                plain_text += " " # Fallback
            plain_to_token_map.append(idx)
        elif type == 1: # Tag
            # Map block tags to newlines to match prompt extraction
            tag_name = re.search(r"^</?([a-z1-6]+)", content.lower())
            if tag_name:
                name = tag_name.group(1)
                if name in ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "br"]:
                    plain_text += "\n"
                    plain_to_token_map.append(idx)

    # 3. Robust Search in plain_text
    # 3.1 Clean and Normalize target (the text AI wants to replace)
    clean_target = re.sub(r"\[P\s*\d+\]", "", target, flags=re.IGNORECASE).strip()
    
    # 3.2 Build a "Normalized" version of plain_text WITH an index map
    # This maps each character in the 'clean' string back to its index in the 'original' plain_text
    clean_plain = ""
    index_map = [] # index_map[i] = index in plain_text
    
    def is_significant(c):
        # We ignore most punctuation and whitespace for the "comparison" string
        return c.isalnum() or c in " @#$%^&*()_+=[]{}|\\/" # keep some "structural" chars but skip dashes/quotes/dots

    for i, char in enumerate(plain_text):
        c_norm = char.lower()
        # Standardize problematic chars
        if c_norm in ['–', '—', '\u2013', '\u2014']: c_norm = '-'
        if c_norm in ['"', '"', '"', '"']: c_norm = '"'
        if c_norm in ["'", "'", "'", "'"]: c_norm = "'"
        
        # LENIENT: Treat all whitespace as space
        if c_norm.isspace(): c_norm = ' '

        if is_significant(c_norm):
            clean_plain += c_norm
            index_map.append(i)
        elif not clean_plain or clean_plain[-1] != " ":
            # Keep a single space to separate words
            clean_plain += " "
            index_map.append(i)

    # Normalize target the same way
    target_clean = ""
    for char in clean_target:
        c_norm = char.lower()
        if c_norm in ['–', '—', '\u2013', '\u2014']: c_norm = '-'
        if c_norm.isspace(): c_norm = ' '
        
        if is_significant(c_norm):
            target_clean += c_norm
        elif not target_clean or target_clean[-1] != " ":
            target_clean += " "
    
    target_clean = target_clean.strip()
    if not target_clean: return None

    # 3.3 Find the match in the clean string
    matcher = difflib.SequenceMatcher(None, clean_plain, target_clean)
    match = matcher.find_longest_match(0, len(clean_plain), 0, len(target_clean))
    
    if match.size > len(target_clean) * 0.4:
        # Success! Map back to original indices
        start_idx = index_map[match.a]
        # For the end index, we take the original index of the characters in the match
        end_clean_idx = min(len(index_map) - 1, match.a + (match.size - 1))
        # We want to cover the length of the 'original' target, 
        # but the AI might have provided slightly more/less text.
        # We'll use the mapped end index but ensure it captures roughly the right range.
        end_idx_orig = index_map[end_clean_idx]
        match_len = (end_idx_orig - start_idx) + 1
    else:
        # Fallback to a simpler but broader search if mapping failed
        pos = plain_text.lower().replace('–', '-').find(clean_target.lower().replace('–', '-'))
        if pos != -1:
            start_idx = pos
            match_len = len(clean_target)
        else:
            return None

    # 4. Find the HTML range by checking the token map
    try:
        # Start token
        start_token_idx = plain_to_token_map[start_idx]
        html_start = tokens[start_token_idx][2]
        
        # End token. Handle potential index wrap
        end_idx_clamped = min(len(plain_to_token_map) - 1, start_idx + match_len - 1)
        end_token_idx = plain_to_token_map[end_idx_clamped]
        last_token = tokens[end_token_idx]
        html_end = last_token[2] + len(last_token[1])
        
        return full_html[:html_start] + replacement + full_html[html_end:]
    except:
        return None


# -------------------------------------


def decide_anchor(tree: Dict, user_text: Optional[str]) -> str:
    return tree["current"]


def build_focus(tree: Dict, anchor_id: str, user_text: Optional[str]) -> str:
    node = tree["nodes"].get(anchor_id)
    node_summary = node.get("summary", "") if node else ""
    
    # If we have a specific user focus (paragraph), we combine it with the node's intent
    if user_text:
        clean_text = user_text.strip()
        if node and node.get("type") != "root":
            # Include the current node's idea as context for the expansion
            node_label = node.get("metadata", {}).get("label", "Current Perspective")
            return f"FOCUS PARAGRAPH:\n{clean_text}\n\nCURRENT PERSPECTIVE/IDEA:\n{node_label}: {node_summary}"
        return clean_text
    
    return node_summary


def parse_llm_options(llm_output: str) -> List[str]:
    """
    Robustly splits LLM output into separate options/perspectives.
    Handles various markers like "Title:", " שדה:", bullets, and paragraph markers [P1].
    """
    if not llm_output:
        return []
        
    # 1. Clean common markdown bolding to simplify matching
    clean_text = re.sub(r"\*\*(Title|Module|Explanation|Critique|שם|מחלקה|הסבר|ביקורת|כותרת)\*\*:", r"\1:", llm_output, flags=re.IGNORECASE)
    
    # 2. Split using lookahead. 
    # This identifies the start of an option (Title/שם/כותרת) optionally preceded by bullets or [PX].
    # We look for a newline followed by the marker.
    split_pattern = r"(?=\n\s*(?:(?:\[P\d+\]|(?:\d+[\.)])|[*•\-])[ \t]*)*(?:Title|שם|כותרת):)"
    blocks = re.split(split_pattern, clean_text.strip(), flags=re.IGNORECASE)
    
    # 3. Filter and clean
    results = []
    primary_keys = ["Title", "שם", "כותרת", "Critique", "ביקורת"] # Added critique keys for safety
    for b in blocks:
        b = b.strip()
        # Ensure the block contains at least one of our recognition markers
        if len(b) > 10 and any(k.lower() + ":" in b.lower() for k in primary_keys):
            results.append(b)
            
    # 4. Fallback if split failed to find anything structured
    if not results:
        # Fallback to double newline split
        results = [b.strip() for b in clean_text.split("\n\n") if len(b.strip()) > 20]
        
    return results


# --- ניהול אירועים ראשי ---

def handle_event(tree: Dict, event_type: UserEventType, event_context: Optional[Dict[str, Any]] = None) -> Dict:
    event_context = event_context or {}
    action = event_context.get("action")
    
    logger.info(f"🎮 EVENT: Type={event_type.name} | Action={action.name if action else 'None'}")
    
    system_rules = load_academic_principles(action)

    if event_type == UserEventType.ACTION:
        return _handle_action(tree, event_context, system_rules)

    if event_type == UserEventType.CHOOSE_OPTION:
        return _handle_choose_option(tree, event_context)

    raise ValueError("Unsupported UserEventType")


def _handle_action(tree: Dict, event_context: Dict[str, Any], system_rules: str) -> Dict:
    action = event_context.get("action")
    user_text = event_context.get("user_text")
    pinned_context = event_context.get("pinned_context", [])

    logger.info(f"🛠️ HANDLING ACTION: {action.name} | Text Length: {len(user_text) if user_text else 0}")

    if not isinstance(action, ActionType):
        raise ValueError("Invalid or missing ActionType")

    anchor_id = event_context.get("anchor_id") or decide_anchor(tree, user_text)
    base_focus = build_focus(tree, anchor_id, user_text)

    # בניית Constraints
    constraints = []
    # NOTE: We do NOT append 'system_rules' here anymore because they are passed 
    # as the 'system_instruction' argument to the LLM client, preventing duplication.

    if pinned_context:
        # Only send pinned items for DIVERGE to save tokens. 
        # For Refine/Critique, the local draft is usually sufficient.
        if action == ActionType.DIVERGE:
            pinned_texts = [item["text"] if isinstance(item, dict) else item for item in pinned_context]
            constraints.append(f"Pinned context (Reference only):\n- " + "\n- ".join(pinned_texts))

    if action == ActionType.DIVERGE:
        current_node = tree["nodes"][anchor_id]
        existing_summaries = [tree["nodes"][cid]["summary"] for cid in current_node.get("children", []) if
                              cid in tree["nodes"]]
        if existing_summaries:
            constraints.append(f"ALREADY EXPLORED (Do not repeat):\n- " + "\n- ".join(existing_summaries))

    knowledge_base = event_context.get("knowledge_base", {})
    if knowledge_base and action == ActionType.DIVERGE:
        # Only send KB for DIVERGE (Expanding new ideas). 
        # Refine/Critique usually don't need the whole KB.
        kb_text = "\n\n".join([f"--- FILE: {name} ---\n{content}" for name, content in knowledge_base.items()])
        constraints.append(f"### REFERENCE KNOWLEDGE BASE ###\n{kb_text}")

    focus_ctx = event_context.get("focus_context", {})
    focus_mode = focus_ctx.get("mode", "Whole Document")
    
    final_user_text = user_text
    if focus_mode == "Whole Document" and user_text:
        # Check for logical paragraphs provided by the UI state
        logical_paras = event_context.get("logical_paragraphs", [])
        if logical_paras:
             # Construct the prompt text using the logical structure
             marked_paras = []
             for i, p in enumerate(logical_paras):
                 if p.strip():
                     marked_paras.append(f"[P{i+1}] {p.strip()}")
             final_user_text = "\n\n".join(marked_paras)
        else:
             # Fallback to simple split (with a bit more robustness)
             paras = [p.strip() for p in user_text.split("\n") if p.strip()]
             marked_paras = [f"[P{i+1}] {p}" for i, p in enumerate(paras)]
             final_user_text = "\n\n".join(marked_paras)
        
        constraints.append(
            "MANDATORY CITATION RULE:\n"
            "The user is analyzing the WHOLE DOCUMENT. Every response (Title/Type) MUST start with "
            "the corresponding paragraph number in brackets, e.g., '[P1] Title' or '[P4] Improvement'. "
            "Use the [PX] markers provided in the input text to identify the paragraph number."
        )
    elif focus_mode == "Specific Paragraph" and user_text:
        # Explicitly tell the AI WHICH paragraph it is analyzing
        p_idx = focus_ctx.get("block_idx", 1)
        final_user_text = f"[P{p_idx}] {user_text}"
        constraints.append(
            f"FOCUS RULE:\n"
            f"You are focusing SPECIALLY on Paragraph {p_idx}. "
            f"Use the marker [P{p_idx}] in your response (Title/Type) to identify this focus."
        )

    constraints.append("CRITICAL: Respond in the same language as the input text (e.g., if input is Hebrew, response MUST be Hebrew).")

    # שליחה ל-LLM
    constraints_str = "\n".join(constraints) if constraints else ""
    
    # FINAL PROMPT CONSTRUCTION:
    # We use final_user_text which has the correct paragraph markers ([PX]).
    # We also prepend any node-level perspective context from base_focus if it exists and differs from the user text.
    if base_focus and base_focus.strip() != user_text.strip():
        # This adds the "Current Perspective/Idea" context to the prompt
        prompt_focus = f"{base_focus}\n\nANALYSIS TARGET (DRAFT):\n{final_user_text}"
    else:
        prompt_focus = final_user_text

    prompt = build_prompt(action, prompt_focus, instructions=constraints_str)
    
    logger.info(f"🧠 CONTROLLER: Calling AI for action={action.name} | Focus={focus_mode}")
    
    # We leverage the 'system_instruction' parameter to optimize prompt size and stay within quota
    from definitions import IS_CLOUD
    try:
        llm_output = call_llm(prompt, system_instruction=system_rules)
    except Exception as e:
        if IS_CLOUD:
            logger.error(f"☁️ CLOUD LLM FAILURE: {e}")
            # Evaluate if we should return a UI error representation instead of crashing
            return {"status": "error", "message": "The AI service is temporarily unavailable. Please try again."}
        else:
            # Local: Fail hard to show traceback
            raise e
    
    logger.info(f"📥 CONTROLLER: AI response received ({len(llm_output)} chars)")

    if action == ActionType.DIVERGE:
        options = parse_llm_options(llm_output)
        # HARD LIMIT: Never process more than 3 options
        options = options[:3]
        final_options = []

        for option in options:
            title = "Alternative Perspective"
            module = "Analysis"
            explanation = option

            try:
                # ניקוי כותרות שדה בצורה גמישה
                clean_opt = option
                
                # regex חכם יותר שתופס וריאציות כולל כותרת
                title_match = re.search(r"(?:Title|שם|נושא|כותרת):\s*(.*?)(?:\n|Module:|מחלקה:|Explanation:|הסבר:|$)", clean_opt, re.IGNORECASE)
                module_match = re.search(r"(?:Module|מחלקה|עקרון):\s*(.*?)(?:\n|Explanation:|הסבר:|$)", clean_opt, re.IGNORECASE)
                # Explanation/Critique as synonyms
                exp_match = re.search(r"(?:Explanation|Critique|הסבר|ביקורת):\s*(.*)", clean_opt, re.DOTALL | re.IGNORECASE)

                if title_match: 
                    title = title_match.group(1).strip(" *")
                    # Standarize [PX] in title if present
                    para_match = re.search(r"(\[P\s*\d+\])", title, re.IGNORECASE)
                    if para_match:
                        marker = para_match.group(1).upper().replace(" ", "")
                        # Normalize: Move marker to front
                        title = re.sub(r"\[P\s*\d+\]", "", title, flags=re.IGNORECASE).strip()
                        title = f"{marker} {title}"
                if module_match: module = module_match.group(1).strip()
                if exp_match: explanation = exp_match.group(1).strip()
                else:
                    # אם לא מצאנו Explanation רשמי, ניקח את הכל אחרי ה-Module או ה-Title
                    explanation = re.sub(r"^(?:Title|Module).*?\n", "", clean_opt, flags=re.MULTILINE | re.IGNORECASE).strip()
            except Exception as e:
                logger.warning(f"⚠️ PARSING ERROR: Failed to parse AI option. Error: {e}")

            if not explanation or len(explanation) < 5: continue

            # Determine scope label
            scope_label = "Whole Document" if focus_mode == "Whole Document" else f"Paragraph {focus_ctx.get('block_idx', 1)}"
            
            # If marker found in title (even in Whole Document mode), update scope for better UI badge
            para_match_final = re.search(r"(\[P\s*\d+\])", title, re.IGNORECASE)
            if para_match_final:
                marker = para_match_final.group(1).upper().replace(" ", "")
                p_num = marker.strip("[]P").strip()
                scope_label = f"Paragraph {p_num}"

            meta = {
                "label": title,
                "module": module,
                "explanation": explanation,
                "scope": scope_label
            }
            # הוספה לעץ
            add_child(tree, anchor_id, explanation, metadata=meta)
            final_options.append(option)

        return {"mode": "options", "options": final_options}

    if action == ActionType.CRITIQUE:
        options = parse_llm_options(llm_output)
        # HARD LIMIT: Never process more than 3 options
        options = options[:3]
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

                if title_match: 
                    title = title_match.group(1).strip(" *")
                    # Standarize [PX] in title if present
                    para_match = re.search(r"(\[P\s*\d+\])", title, re.IGNORECASE)
                    if para_match:
                        marker = para_match.group(1).upper().replace(" ", "")
                        # Normalize: Move marker to front
                        title = re.sub(r"\[P\s*\d+\]", "", title, flags=re.IGNORECASE).strip()
                        title = f"{marker} {title}"
                
                if module_match: module = module_match.group(1).strip()
                if body_match: body = body_match.group(1).strip()

            except:
                pass

            # Determine scope label
            scope_label = "Whole Document" if focus_mode == "Whole Document" else f"Paragraph {focus_ctx.get('block_idx', 1)}"
            
            # If marker found in title (even in Whole Document mode), update scope for better UI badge
            para_match_final = re.search(r"(\[P\s*\d+\])", title, re.IGNORECASE)
            if para_match_final:
                marker = para_match_final.group(1).upper().replace(" ", "")
                p_num = marker.strip("[]P").strip()
                scope_label = f"Paragraph {p_num}"

            # החזרת אובייקט נתונים ללא הוספה לעץ
            critique_items.append({
                "title": title,
                "module": module,
                "text": body,
                "scope": scope_label
            })

        return {"mode": "critique", "items": critique_items}

    if action == ActionType.REFINE:
        suggestions = []
        # Support various field labels (English/Hebrew) and optional para markers
        # Improved regex to handle start of string and flexible markers
        # Using lookahead to find next Original block without consuming it
        blocks = re.split(r"(?im)^(?=\s*(?:\[P\d+\]\s*)?(?:Original|מקור):)", llm_output.strip())
        
        for i, block in enumerate(blocks):
            if not block.strip(): continue
            try:
                # 1. Standardize field names for easier lookups (bold/hebrew -> plain english)
                clean_block = re.sub(r"\*\*(Original|Proposed|Reason|Type|מקור|מוצע|הסבר|נימוק|סוג)\*\*:", r"\1:", block, flags=re.IGNORECASE)
                clean_block = re.sub(r"(?:מקור|מוצע|הסבר|נימוק|סוג):", lambda m: {"מקור": "Original:", "מוצע": "Proposed:", "הסבר": "Reason:", "נימוק": "Reason:", "סוג": "Type:"}.get(m.group(0)[:-1], m.group(0)), clean_block, flags=re.IGNORECASE)
                
                # 2. Extract using non-greedy match until the next field header
                # This pattern ensures we capture multiple lines.
                fields = ["Original", "Proposed", "Type", "Reason"]
                found_fields = {}
                for f in fields:
                    # Search for field name followed by text until another field name or end
                    field_pat = rf"{f}:\s*(.*?)(?=\n\s*(?:{'|'.join(fields)}):|$)"
                    m = re.search(field_pat, clean_block, re.DOTALL | re.IGNORECASE)
                    if m:
                        found_fields[f] = m.group(1).strip()
                
                if "Original" in found_fields and "Proposed" in found_fields:
                    # Globally strip any [PX] markers
                    orig_raw = found_fields["Original"]
                    prop_raw = found_fields["Proposed"]
                    orig_clean = re.sub(r"\[P\s*\d+\]", "", orig_raw, flags=re.IGNORECASE).strip()
                    prop_clean = re.sub(r"\[P\s*\d+\]", "", prop_raw, flags=re.IGNORECASE).strip()
                    
                    # Fix: Strip leading/trailing ellipsis that the AI might add as context
                    orig_clean = re.sub(r"^\s*(?:\.\.\.|…)\s*|\s*(?:\.\.\.|…)\s*$", "", orig_clean).strip()
                    prop_clean = re.sub(r"^\s*(?:\.\.\.|…)\s*|\s*(?:\.\.\.|…)\s*$", "", prop_clean).strip()
                    
                    # Determine scope label
                    focus_ctx = event_context.get("focus_context", {})
                    focus_mode = focus_ctx.get("mode", "Whole Document")
                    scope_label = "Whole Document" if focus_mode == "Whole Document" else f"Paragraph {focus_ctx.get('block_idx', 1)}"
                    
                    suggestion_type = found_fields.get("Type", "Improvement")
                    # Remove any existing [PX] from type to avoid doubles
                    suggestion_type = re.sub(r"\[P\s*\d+\]", "", suggestion_type, flags=re.IGNORECASE).strip()
                    
                    # Ensure [PX] is in the type if in Whole Document mode
                    if focus_mode == "Whole Document":
                        # Search for marker in the whole block (AI might put it in Type or Reason)
                        para_match = re.search(r"(\[P\s*\d+\])", block, re.IGNORECASE)
                        if para_match:
                            marker = para_match.group(1).upper().replace(" ", "")
                            suggestion_type = f"{marker} {suggestion_type}"
                            # Also update scope label for the badge
                            p_num = marker.strip("[]P")
                            scope_label = f"Paragraph {p_num}"
                    
                    suggestions.append({
                        "id": f"refine_{i}_{os.urandom(2).hex()}",
                        "original": orig_clean,
                        "proposed": prop_clean,
                        "type": suggestion_type,
                        "reason": found_fields.get("Reason", "General improvement"),
                        "status": "pending",
                        "scope": scope_label
                    })
            except:
                continue

        # Fallback for plain text refinements
        if not suggestions:
             return {"mode": "refine_legacy", "refined_text": llm_output.strip(), "diff_html": generate_diff_html(base_focus, llm_output.strip())}

        return {"mode": "refine_suggestions", "items": suggestions}

    if action == ActionType.SEGMENT:
        # Robustly split by "Block X:" markers
        blocks = re.split(r"\n?\s*Block\s*\d+:\s*", llm_output.strip(), flags=re.IGNORECASE)
        # Filter out empty blocks
        paras = []
        for b in blocks:
            b_clean = b.strip()
            if b_clean:
                # MANDATORY: Strip any [P1], Block 1, or manual numbering the AI might have added anyway
                b_clean = re.sub(r"^(?:\[P\s*\d+\]|Block\s*\d+:?|\d+[\.)]|[*•\-])\s*", "", b_clean, flags=re.IGNORECASE).strip()
                # Repeat once to catch "[P1] [P1]" or similar
                b_clean = re.sub(r"^(?:\[P\s*\d+\]|Block\s*\d+:?|\d+[\.)]|[*•\-])\s*", "", b_clean, flags=re.IGNORECASE).strip()
                paras.append(b_clean)
        
        # FALLBACK: If no blocks were found but output exists, use simple paragraph splitting
        if not paras and llm_output.strip():
            paras = [p.strip() for p in llm_output.split("\n\n") if p.strip()]
            
        return {"mode": "segmentation", "paragraphs": paras}

    return {"status": "error", "message": "Unknown action"}


def _handle_choose_option(tree: Dict, event_context: Dict[str, Any]) -> Dict:
    option_index = event_context.get("option_index")
    current_id = tree["current"]
    children = tree["nodes"][current_id]["children"]
    chosen_child_id = children[option_index]
    navigate_to_node(tree, chosen_child_id)
    return {"mode": "continue", "current_text": tree["nodes"][chosen_child_id]["summary"]}