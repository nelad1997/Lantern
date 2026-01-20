import os
import difflib
from typing import Dict, Optional, Any, List, Tuple
from definitions import ActionType, UserEventType
from tree import add_child, set_current, update_node_metadata
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
    """יוצר HTML המציג שינויים ויזואליים בין הטקסט המקורי למלוטש."""
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


def parse_llm_structured_output(llm_output: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    מפרק פלט מורכב הכולל אופציונלית סיכום שורש ואת נתיבי ההמשך.
    פורמט מצופה:
    ROOT_SUMMARY | [סיכום של הטקסט המקורי]
    Title | One-liner | Content
    """
    lines = llm_output.strip().split("\n")
    root_summary = None
    parsed_options = []

    for line in lines:
        if not line.strip():
            continue

        if "|" in line:
            parts = [p.strip() for p in line.split("|")]

            # זיהוי שורת סיכום השורש
            if parts[0] == "ROOT_SUMMARY" and len(parts) >= 2:
                root_summary = parts[1]
            # זיהוי נתיבי הסתעפות (Title | One-liner | Content)
            elif len(parts) >= 3:
                parsed_options.append({
                    "title": parts[0],
                    "one_liner": parts[1],
                    "content": parts[2]
                })
    return root_summary, parsed_options


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

    if action == "SAVE_METADATA":
        node_id = event_context.get("node_id")
        key = event_context.get("metadata_key")
        val = event_context.get("metadata_value")
        update_node_metadata(tree, node_id, key, val)
        return {"status": "success"}

    anchor_id = tree["current"]
    base_focus = user_text.strip() if user_text else tree["nodes"][anchor_id]["summary"]

    # בניית ה-Constraints
    constraints = []
    if system_rules:
        constraints.append("### ACADEMIC WRITING PRINCIPLES ###\n" + system_rules)
    if pinned_context:
        constraints.append("Pinned context:\n- " + "\n- ".join(pinned_context))
    if banned_ids:
        banned_texts = [tree["nodes"][bid]["summary"] for bid in banned_ids if bid in tree["nodes"]]
        constraints.append("Do NOT suggest:\n- " + "\n- ".join(banned_texts))

    full_focus_text = base_focus + ("\n\n[SYSTEM CONSTRAINTS]:\n" + "\n".join(constraints) if constraints else "")
    prompt = build_prompt(action, full_focus_text)
    llm_output = call_llm(prompt)

    # עיבוד תוצאה לפי אפיון Lantern

    if action == ActionType.DIVERGE:
        # שימוש במפרק החדש שמחלץ גם את סיכום השורש
        root_summary, structured_options = parse_llm_structured_output(llm_output)

        # עדכון סיכום השורש אם אנחנו בצומת ה-Root והתקבל סיכום
        if root_summary and tree["nodes"][anchor_id].get("type") == "root":
            update_node_metadata(tree, anchor_id, "one_liner", root_summary)

        for opt in structured_options:
            add_child(
                tree,
                anchor_id,
                summary=opt["title"],
                node_type="ai_diverge",
                metadata={
                    "one_liner": opt["one_liner"],
                    "full_content": opt["content"],
                    "critiques": []
                }
            )
        return {"mode": "options", "options": [o["title"] for o in structured_options]}

    if action == ActionType.CRITIQUE:
        options = [block.strip() for block in llm_output.split("\n") if block.strip()]
        return {"mode": "critique", "items": options}

    if action == ActionType.REFINE:
        refined_text = llm_output.strip()
        diff_html = generate_diff_html(base_focus, refined_text)
        node = tree["nodes"][anchor_id]
        node["summary"] = refined_text
        node.setdefault("metadata", {})["html"] = f"<p>{refined_text}</p>"
        return {"mode": "refine", "options": [refined_text], "diff_html": diff_html}

    return {"status": "error", "message": "Unknown action"}


def _handle_choose_option(tree: Dict, event_context: Dict[str, Any]) -> Dict:
    option_index = event_context.get("option_index")
    current_id = tree["current"]
    children = tree["nodes"][current_id]["children"]
    chosen_child_id = children[option_index]
    set_current(tree, chosen_child_id)
    return {"mode": "continue", "current_text": tree["nodes"][chosen_child_id]["summary"]}