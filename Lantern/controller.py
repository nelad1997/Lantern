

from typing import Dict, Optional, Any, List


from definitions import ActionType, UserEventType


from tree import add_child, set_current
from prompt_builder import build_prompt
from llm_client import call_llm

def decide_anchor(tree: Dict, user_text: Optional[str]) -> str:
    """
    Decide which node should serve as the anchor for the current action.

    At this stage, the anchor is always the current node.
    This function exists to allow future extension (e.g., paragraph-level anchors).

    Args:
        tree (Dict): The decision tree.
        user_text (Optional[str]): Optional user-provided text override.

    Returns:
        str: The node ID to be used as the anchor.
    """
    return tree["current"]


def build_focus(tree: Dict, anchor_id: str, user_text: Optional[str]) -> str:
    """
    Build the textual focus that the LLM should operate on.

    If the user provided explicit text, it takes precedence.
    Otherwise, use the summary stored in the anchor node.

    Args:
        tree (Dict): The decision tree.
        anchor_id (str): ID of the anchor node.
        user_text (Optional[str]): Optional user-provided text.

    Returns:
        str: The focus text for the LLM.
    """
    if user_text:
        return user_text.strip()
    return tree["nodes"][anchor_id]["summary"]


def parse_llm_options(llm_output: str) -> List[str]:
    """
    Parse an LLM response into a list of distinct options.

    This is intentionally simple for now and can be replaced
    with more structured parsing later.

    Args:
        llm_output (str): Raw text returned by the LLM.

    Returns:
        List[str]: Parsed options.
    """
    return [line.strip() for line in llm_output.split("\n") if line.strip()]


def handle_event(
    tree: Dict,
    event_type: UserEventType,
    event_context: Optional[Dict[str, Any]] = None
) -> Dict:
    """
    Main orchestration entry point for all user events.

    This function interprets the user event, coordinates all
    internal components (prompt building, LLM calls, tree updates),
    and returns a final, UI-ready result.

    Args:
        tree (Dict): The decision tree.
        event_type (UserEventType): Type of the user event.
        event_context (Optional[Dict[str, Any]]): Additional data for the event.

    Returns:
        Dict: A UI-ready result describing what should be displayed next.
    """
    event_context = event_context or {}

    if event_type == UserEventType.ACTION:
        return _handle_action(tree, event_context)

    if event_type == UserEventType.CHOOSE_OPTION:
        return _handle_choose_option(tree, event_context)

    raise ValueError("Unsupported UserEventType")


def _handle_action(tree: Dict, event_context: Dict[str, Any]) -> Dict:
    """
    Handle an ACTION event by orchestrating prompt creation,
    LLM invocation, and optional tree expansion.

    Args:
        tree (Dict): The decision tree.
        event_context (Dict[str, Any]): Must contain 'action' and may contain 'user_text'.

    Returns:
        Dict: UI-ready result (options list or critique text).
    """
    action = event_context.get("action")
    user_text = event_context.get("user_text")

    if not isinstance(action, ActionType):
        raise ValueError("Invalid or missing ActionType")

    anchor_id = decide_anchor(tree, user_text)
    focus = build_focus(tree, anchor_id, user_text)

    prompt = build_prompt(action, focus)
    llm_output = call_llm(prompt)

    # CRITIQUE does not create new branches
    if action == ActionType.CRITIQUE:
        return {
            "mode": "critique",
            "text": llm_output
        }

    # DIVERGE / REFINE create new child nodes
    options = parse_llm_options(llm_output)

    for option in options:
        add_child(tree, anchor_id, option)

    return {
        "mode": "options",
        "options": options
    }


def _handle_choose_option(tree: Dict, event_context: Dict[str, Any]) -> Dict:
    """
    Handle the user's selection of one of the previously generated options.

    Args:
        tree (Dict): The decision tree.
        event_context (Dict[str, Any]): Must contain 'option_index'.

    Returns:
        Dict: UI-ready result reflecting the updated current focus.
    """
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
