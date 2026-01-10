from enum import Enum
from typing import Dict, Optional
from tree import (
    set_current,
    add_child,)


class ActionType(Enum):
    DIVERGE = "diverge"
    REFINE = "refine"
    CRITIQUE = "critique"

class UserEventType(Enum):
    ACTION = "action"          # diverge / refine / critique
    CHOOSE_OPTION = "choose"   # choose one of generated options


def decide_anchor(tree: Dict, user_text: Optional[str]) -> str:
    """
    Decide which node should be the anchor for the current action.
    For now, always use the current node.
    """
    return tree["current"]

def prepare_llm_input(
    tree: Dict,
    action: ActionType,
    user_text: Optional[str] = None
) -> Dict:
    anchor_id = decide_anchor(tree, user_text)
    anchor_node = tree["nodes"][anchor_id]

    focus_text = user_text.strip() if user_text else anchor_node["summary"]

    return {
        "focus": focus_text,
        "action": action.value,
        "anchor_node_id": anchor_id
    }


def handle_action_event(
    tree: Dict,
    action: ActionType,
    user_text: Optional[str] = None
) -> Dict:
    payload = prepare_llm_input(tree, action, user_text)

    if action in {ActionType.DIVERGE, ActionType.REFINE}:
        return {
            "type": "llm_call",
            "payload": payload,
            "creates_nodes": True
        }

    if action == ActionType.CRITIQUE:
        return {
            "type": "llm_call",
            "payload": payload,
            "creates_nodes": False
        }

    raise ValueError("Unsupported action type")


def handle_choose_option(tree: Dict, option_index: int) -> Dict:
    current_id = tree["current"]
    children = tree["nodes"][current_id]["children"]

    if not children:
        raise ValueError("No options available")

    if option_index < 0 or option_index >= len(children):
        raise IndexError("Invalid option index")

    chosen_child_id = children[option_index]
    set_current(tree, chosen_child_id)

    return {
        "type": "navigate",
        "payload": None,
        "creates_nodes": False }


