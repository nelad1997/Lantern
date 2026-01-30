import os
from enum import Enum

# --- ENVIRONMENT FLAGS ---
# Define strictly for Cloud/Local separation logic.
# Local runs will naturally be False. Cloud runs must set "STREAMLIT_CLOUD" = "1".
IS_CLOUD = bool(os.getenv("STREAMLIT_CLOUD"))

class ActionType(Enum):
    """
    High-level actions the user can invoke on the current focus.
    """
    DIVERGE = "diverge"
    REFINE = "refine"
    CRITIQUE = "critique"
    CLASSIFY = "classify"
    SEGMENT = "segment"


class UserEventType(Enum):
    """
    Types of user events coming from the UI.
    """
    ACTION = "action"          # User invoked an agent (diverge / refine / critique)
    CHOOSE_OPTION = "choose"   # User selected one of the generated options