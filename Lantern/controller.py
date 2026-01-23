import os
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


def generate_diff_html(old_text: str, new_text: str) -> str:
    """
    משווה בין שני טקסטים ויוצר HTML המציג שינויים:
    מילים שנמחקו - אדום עם קו חוצה.
    מילים שנוספו - ירוק מודגש.
    """
    output = []
    # פירוק למילים כדי להשוות ברמת המילה
    matcher = difflib.SequenceMatcher(None, old_text.split(), new_text.split())

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            # מילים שהוחלפו
            old_part = " ".join(old_text.split()[i1:i2])
            new_part = " ".join(new_text.split()[j1:j2])
            output.append(f'<span style="color:#ef4444; text-decoration:line-through;">{old_part}</span>')
            output.append(f'<span style="color:#10b981; font-weight:bold;">{new_part}</span>')
        elif tag == 'delete':
            # מילים שנמחקו
            deleted_part = " ".join(old_text.split()[i1:i2])
            output.append(f'<span style="color:#ef4444; text-decoration:line-through;">{deleted_part}</span>')
        elif tag == 'insert':
            # מילים שנוספו
            added_part = " ".join(new_text.split()[j1:j2])
            output.append(f'<span style="color:#10b981; font-weight:bold;">{added_part}</span>')
        elif tag == 'equal':
            # מילים ללא שינוי
            output.append(" ".join(old_text.split()[i1:i2]))

    return " ".join(output)


def decide_anchor(tree: Dict, user_text: Optional[str]) -> str:
    return tree["current"]


def build_focus(tree: Dict, anchor_id: str, user_text: Optional[str]) -> str:
    if user_text:
        return user_text.strip()
    return tree["nodes"][anchor_id]["summary"]


def parse_llm_options(llm_output: str) -> List[str]:
    """מפרק את פלט ה-LLM לאופציות נפרדות לפי שורות רווח."""
    blocks = llm_output.split("\n\n")
    return [block.strip() for block in blocks if block.strip()]


def apply_fuzzy_replacement(full_text: str, target: str, replacement: str) -> Optional[str]:
    """
    מנסה למצוא ולהחליף משפט בטקסט גם אם יש הבדלים קטנים (רווחים וכו').
    מחזיר את הטקסט החדש או None אם לא נמצאה התאמה מספקת.
    """
    if not target or not full_text:
        return None
        
    # ניסיון ראשון: התאמה מדויקת (הכי בטוח)
    if target in full_text:
        return full_text.replace(target, replacement, 1)
        
    # ניסיון שני: התאמה ללא רווחים
    # (זה מורכב ליישום ישיר על האינדקסים המקוריים, אז נשתמש ב-SequenceMatcher)
    
    # שימוש ב-SequenceMatcher למציאת הבלוק הכי דומה
    matcher = difflib.SequenceMatcher(None, full_text, target)
    match = matcher.find_longest_match(0, len(full_text), 0, len(target))
    
    # בדיקת איכות ההתאמה (האם מצאנו את רוב המשפט?)
    if match.size > len(target) * 0.8:  # 80% התאמה
        # החלפת הבלוק שנמצא
        start, end = match.a, match.a + match.size
        return full_text[:start] + replacement + full_text[end:]
        
    return None


# --- ניהול אירועים ראשי ---

def handle_event(
        tree: Dict,
        event_type: UserEventType,
        event_context: Optional[Dict[str, Any]] = None
) -> Dict:
    system_rules = load_academic_principles()
    event_context = event_context or {}

    if event_type == UserEventType.ACTION:
        return _handle_action(tree, event_context, system_rules)

    if event_type == UserEventType.CHOOSE_OPTION:
        return _handle_choose_option(tree, event_context)

    raise ValueError("Unsupported UserEventType")


# --- טיפול בפעולות ---

def _handle_action(tree: Dict, event_context: Dict[str, Any], system_rules: str) -> Dict:
    action = event_context.get("action")
    user_text = event_context.get("user_text")
    pinned_context = event_context.get("pinned_context", [])
    banned_ids = event_context.get("banned_ideas", [])

    if not isinstance(action, ActionType):
        raise ValueError("Invalid or missing ActionType")

    anchor_id = decide_anchor(tree, user_text)
    base_focus = build_focus(tree, anchor_id, user_text)

    # 1. בניית ה-Constraints
    constraints = []
    if system_rules:
        constraints.append(
            "### ACADEMIC WRITING PRINCIPLES ###\n" + system_rules +
            "\nNOTE: Apply rigor to analytical sections; favor clarity for introductions."
        )

    if pinned_context:
        # Extract text from both old (string) and new (dict) pinned items
        pinned_texts = [item["text"] if isinstance(item, dict) else item for item in pinned_context]
        constraints.append(f"Pinned context:\n- " + "\n- ".join(pinned_texts))

    if banned_ids:
        banned_texts = [tree["nodes"][bid]["summary"] for bid in banned_ids if bid in tree["nodes"]]
        if banned_texts:
            constraints.append(f"Do NOT suggest:\n- " + "\n- ".join(banned_texts))

    knowledge_base = event_context.get("knowledge_base", {})
    if knowledge_base:
        kb_text = "\n\n".join([f"--- FILE: {name} ---\n{content}" for name, content in knowledge_base.items()])
        constraints.append(f"### REFERENCE KNOWLEDGE BASE ###\nUse the following reference material to improve your suggestions and critique:\n{kb_text}")

    # --- Stronger Deduplication (Check existing siblings) ---
    if action == ActionType.DIVERGE:
        current_node = tree["nodes"][anchor_id]
        
        # Prevent AI from suggesting the topic itself as a sub-path
        topic_context = current_node["summary"]
        
        existing_children_ids = current_node.get("children", [])
        existing_summaries = [tree["nodes"][cid]["summary"] for cid in existing_children_ids if cid in tree["nodes"]]
        
        # Add Current Topic context to existing summaries to ban them
        banned_suggestions = existing_summaries + [topic_context]
        
        if banned_suggestions:
             constraints.append(f"ALREADY EXPLORED / CURRENT TOPIC (Do not repeat these):\n- " + "\n- ".join(banned_suggestions))

    constraints.append("IMPORTANT: Respond in the same language as the input text.")

    # --- Handle Empty Draft (Fresh Start) ---
    is_fresh_start = False
    if not base_focus or base_focus.strip() == "":
        is_fresh_start = True
        base_focus = "[NEW PROJECT: NO TEXT DRAFT YET]"
        constraints.append("The user has just started. Suggest 3 distinct academic perspectives or research directions to begin the inquiry.")

    # 2. שליחה ל-LLM
    full_focus_text = base_focus + ("\n\n[SYSTEM CONSTRAINTS]:\n" + "\n".join(constraints) if constraints else "")
    prompt = build_prompt(action, full_focus_text)
    llm_output = call_llm(prompt)

    # 3. עיבוד תוצאה לפי סוג פעולה (הפרדה לשינויים ויזואליים)

    if action == ActionType.CRITIQUE:
        options = parse_llm_options(llm_output)
        # Create nodes immediately for critiques
        critique_nodes = []
        for opt in options:
            if opt.strip() == "NO_CRITIQUE_NEEDED":
                 critique_nodes.append({"id": None, "text": opt})
                 continue
                 
            # Extract title for summary
            summary = opt
            if "Title:" in opt:
                try:
                    parts = opt.replace("Title:", "").split("Critique:", 1)
                    title = parts[0].strip(" *")
                    summary = title
                except:
                    pass
            
            # Add child node
            cid = add_child(tree, anchor_id, opt, node_type="ai_critique", metadata={"label": summary, "idea_text": opt})
            critique_nodes.append({"id": cid, "text": opt})
            
        return {"mode": "critique", "items": critique_nodes}

    if action == ActionType.REFINE:
        refined_text = llm_output.strip()
        # יצירת ה-Diff הויזואלי
        diff_html = generate_diff_html(base_focus, refined_text)

        return {
            "mode": "refine",
            "refined_text": refined_text, 
            "diff_html": diff_html
        }

    if action == ActionType.DIVERGE:
        options = parse_llm_options(llm_output)
        for option in options:
            # Parse Title for cleaner graph label, but keep full text for Pinning
            label = None
            if "Title:" in option:
                try:
                    parts = option.split("Explanation:", 1)[0]
                    label = parts.replace("Title:", "").strip(" *")
                except:
                   pass
            
            # Store full idea text for Pinning Context (Critical Fix)
            meta = {"idea_text": option}
            if label:
                meta["label"] = label
                
            add_child(tree, anchor_id, option, metadata=meta)
            
        return {"mode": "options", "options": options}

    return {"status": "error", "message": "Unknown action"}


def _handle_choose_option(tree: Dict, event_context: Dict[str, Any]) -> Dict:
    option_index = event_context.get("option_index")
    current_id = tree["current"]
    children = tree["nodes"][current_id]["children"]
    chosen_child_id = children[option_index]
    navigate_to_node(tree, chosen_child_id)
    return {"mode": "continue", "current_text": tree["nodes"][chosen_child_id]["summary"]}