from definitions import ActionType


def build_prompt(action: ActionType, focus: str) -> str:
    """
    Build a prompt for the LLM based on the requested action and focus text.

    Args:
        action (ActionType):
            The type of action to perform (DIVERGE, REFINE, CRITIQUE).
        focus (str):
            The text or summary that the action should be applied to.

    Returns:
        str:
            A prompt string to send to the LLM.
    """
    if action == ActionType.DIVERGE:
        return (
            "You are an academic writing assistant.\n"
            "Given the following text, suggest several distinct directions "
            "the argument could be developed further.\n"
            "Output a plain list of options, separated by newlines, with no numbering.\n\n"
            f"Text:\n{focus}"
        )

    if action == ActionType.REFINE:
        return (
            "You are an academic writing assistant.\n"
            "Improve and refine the following text while preserving its meaning.\n\n"
            f"Text:\n{focus}"
        )

    if action == ActionType.CRITIQUE:
        return (
            "You are an academic writing assistant.\n"
            "Provide constructive critique of the following text, "
            "focusing on clarity, structure, and argumentation.\n\n"
            f"Text:\n{focus}"
        )

    raise ValueError("Unsupported action type")



