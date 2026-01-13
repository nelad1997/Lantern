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
            "You are a world-class academic mentor and editor. "
            "Your goal is to push the writer's thinking into new, profound territories.\n\n"
        
            "Step 1: Brainstorm 6 distinct directions to develop the argument below. "
            "Ensure they vary significantly in nature (e.g., one theoretical, one empirical, "
            "one counter-argumentative, one interdisciplinary).\n"
        
            "Step 2: internal evaluation. Score each option based on:\n"
            "- Intellectual rigor (avoid generic suggestions)\n"
            "- Novelty (surprising but relevant angles)\n"
            "- Distinctness (make sure they don't overlap)\n\n"
        
            "Step 3: Select the TOP 3 winners.\n\n"
        
            "Output Rules:\n"
            "- Output ONLY the final 3 options.\n"
            "- Format as a plain list separated by newlines.\n"
            "- No numbering, no labels, no intro text.\n\n"
            "IMPORTANT: Respond in the same language as the input text."
        
            f"Text:\n{focus}"
        )

    if action == ActionType.REFINE:
        return (
            "You are a meticulous academic copyeditor. "
            "Your task is to polish the following text, similar to a high-end grammar and style checker.\n\n"
        
            "Guidelines:\n"
            "1. Correct all grammar, spelling, syntax, and punctuation errors.\n"
            "2. Enhance clarity and conciseness (remove fluff).\n"
            "3. Elevate vocabulary to be precise and academic, but strictly preserve the original meaning and the author's voice.\n"
            "4. Do NOT add new ideas or change the argument.\n\n"
        
            "Output ONLY the corrected text, with no introductory or concluding remarks.\n\n"
            "IMPORTANT: Respond in the same language as the input text."
            f"Text:\n{focus}"
        )

    if action == ActionType.CRITIQUE:
        return (
            "You are a critical academic peer reviewer known for rigorous scrutiny. "
            "Your goal is to challenge the following text to make it bulletproof.\n\n"
        
            "Analyze the text and identify 3 major weaknesses from the following categories:\n"
            "1. Logical Gaps: Are there jumps in reasoning?\n"
            "2. Unsubstantiated Claims: Is the author generalizing without evidence?\n"
            "3. Hidden Assumptions: What is the author taking for granted?\n"
            "4. Missing Perspectives: What counter-arguments are ignored?\n\n"
        
            "Output Rules:\n"
            "- Provide a bulleted list of 3 short, sharp critiques.\n"
            "- Be direct and tough but constructive.\n"
            "- Do not rewrite the text, just point out the flaws.\n\n"
            "IMPORTANT: Respond in the same language as the input text."
        
            f"Text:\n{focus}"
        )

    raise ValueError("Unsupported action type")



