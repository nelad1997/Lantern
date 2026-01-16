

from typing import Dict, Optional, Any, List
from definitions import ActionType, UserEventType
from tree import add_child, set_current
from prompt_builder import build_prompt
from llm_client import call_llm


def decide_anchor(tree: Dict, user_text: Optional[str]) -> str:
    return tree["current"]


def build_focus(tree: Dict, anchor_id: str, user_text: Optional[str]) -> str:
    if user_text:
        return user_text.strip()
    return tree["nodes"][anchor_id]["summary"]


def parse_llm_options(llm_output: str) -> List[str]:
    return [line.strip() for line in llm_output.split("\n") if line.strip()]


def handle_event(
        tree: Dict,
        event_type: UserEventType,
        event_context: Optional[Dict[str, Any]] = None
) -> Dict:
    event_context = event_context or {}

    if event_type == UserEventType.ACTION:
        return _handle_action(tree, event_context)

    if event_type == UserEventType.CHOOSE_OPTION:
        return _handle_choose_option(tree, event_context)

    raise ValueError("Unsupported UserEventType")


def _handle_action(tree: Dict, event_context: Dict[str, Any]) -> Dict:
    """
    Handle an ACTION event with support for Context, Blocklist, and Language.
    """
    action = event_context.get("action")
    user_text = event_context.get("user_text")

    # שליפת נתונים מה-App (רשימות הקשר וחסימות)
    pinned_context = event_context.get("pinned_context", [])  # רשימת מחרוזות
    banned_ids = event_context.get("banned_ideas", [])  # רשימת IDs

    if not isinstance(action, ActionType):
        raise ValueError("Invalid or missing ActionType")

    anchor_id = decide_anchor(tree, user_text)
    base_focus = build_focus(tree, anchor_id, user_text)

    # --- 1. בניית הוראות נוספות (Constraints) ---
    constraints = []

    # הוספת הקשר (Pinned Ideas)
    if pinned_context:
        context_str = "\n- ".join(pinned_context)
        constraints.append(f"Consider the following pinned context/ideas:\n- {context_str}")

    # הוספת חסימות (Banned Ideas)
    # אנחנו צריכים להמיר את ה-IDs לטקסט כדי שה-LLM ידע ממה להימנע
    if banned_ids:
        banned_texts = []
        for bid in banned_ids:
            if bid in tree["nodes"]:
                banned_texts.append(tree["nodes"][bid]["summary"])
            # אם הרעיון נמחק מהעץ אבל קיים ב-banned, נתעלם ממנו או נטפל אחרת

        if banned_texts:
            banned_str = "\n- ".join(banned_texts)
            constraints.append(f"Do NOT suggest the following ideas again:\n- {banned_str}")

    # --- 2. הוראת שפה (Language Instruction) ---
    constraints.append("IMPORTANT: Respond in the same language as the input text.")

    # --- 3. הרכבת הפוקוס הסופי ---
    # משרשרים את האילוצים לטקסט המקורי שנשלח ל-Builder
    full_focus_text = base_focus
    if constraints:
        full_focus_text += "\n\n[SYSTEM INSTRUCTIONS]:\n" + "\n".join(constraints)

    # יצירת הפרומפט וקריאה ל-LLM
    prompt = build_prompt(action, full_focus_text)
    llm_output = call_llm(prompt)
    options = parse_llm_options(llm_output)

    if action == ActionType.CRITIQUE:
        return {
            "mode": "critique",
            "items": options } # מחזירים רשימה של הערות, לא טקסט אחד ארוך

    # DIVERGE / REFINE create new child nodes


    for option in options:
        # אופציונלי: כאן אפשר היה לסנן שוב אם ה-LLM בטעות החזיר רעיון חסום
        add_child(tree, anchor_id, option)

    return {
        "mode": "options",
        "options": options
    }


def _handle_choose_option(tree: Dict, event_context: Dict[str, Any]) -> Dict:
    option_index = event_context.get("option_index")

    if option_index is None:
        raise ValueError("option_index is required")

    current_id = tree["current"]
    children = tree["nodes"][current_id]["children"]

    if option_index < 0 or option_index >= len(children):
        raise IndexError("Invalid option index")

    chosen_child_id = children[option_index]
    set_current(tree, chosen_child_id)

    return {
        "mode": "continue",
        "current_text": tree["nodes"][chosen_child_id]["summary"]
    }
