from enum import Enum

class ActionType(Enum):
    """
    High-level actions the user can invoke on the current focus.
    """
    DIVERGE = "diverge"
    REFINE = "refine"
    CRITIQUE = "critique"
    CLASSIFY = "classify"


class UserEventType(Enum):
    """
    Types of user events coming from the UI.
    """
    ACTION = "action"          # User invoked an agent (diverge / refine / critique)
    CHOOSE_OPTION = "choose"   # User selected one of the generated options