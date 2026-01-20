from definitions import ActionType


def build_prompt(action: ActionType, focus: str) -> str:
    """
    Builds a prompt for the LLM based on the requested action.
    The 'focus' variable contains both the user's draft and the
    Academic Writing Principles injected by the controller.
    """

    # -------------------------------------------------
    # DIVERGE — EXPLORE Mode (Thematic Perspectives)
    # -------------------------------------------------
    if action == ActionType.DIVERGE:
        return (
            "You are a world-class academic mentor. Your task is to suggest "
            "new directions to develop the author's argument.\n"
            "MODE: EXPLORE (Thematic Divergence)\n\n"

            "INSTRUCTIONS:\n"
            "1. Apply Module 4 (Synthesis) from the principles below.\n"
            "2. Internal Process: Brainstorm 6 distinct academic perspectives "
            "(e.g., theoretical, empirical, interdisciplinary, or counter-argumentative).\n"
            "3. Evaluation: Score each based on intellectual rigor and novelty.\n"
            "4. Selection: Select the TOP 3 winners to present to the user.\n\n"

            "Output Format (STRICT):\n"
            "For each of the 3 selected perspectives:\n"
            "Title: <A short, academic name for the lens>\n"
            "Explanation: <A substantive paragraph explaining how this lens "
            "further develops the argument, following academic standards>\n\n"

            "Rules:\n"
            "- Do NOT rewrite the author's text.\n"
            "- Ensure the 3 options vary significantly in their analytical nature.\n"
            "- Respond in the same language as the input text.\n"
            "- Do NOT include any introductory, concluding, or meta text.\n"
            "- Do NOT explain what you are about to do.\n"
            "- Return ONLY the 3 perspectives in the specified format.\n\n"

            f"Input & Principles:\n{focus}"
        )

    # -------------------------------------------------
    # REFINE — POLISH Mode (Academic Editor)
    # -------------------------------------------------
    if action == ActionType.CRITIQUE:
        return (
            "You are a rigorous academic peer reviewer. Your goal is to identify "
            "weaknesses in the text to help the author make the argument bulletproof.\n"
            "MODE: CHALLENGE (Devil’s Advocate)\n\n"

            "INSTRUCTIONS:\n"
            "1. Apply Module 1 (Logical Rigor) and Module 5 (Ethics/Bibliography) "
            "from the principles below.\n"
            "2. Identify 3 major logical gaps, unsubstantiated claims, or hidden assumptions.\n"
            "3. Check for 'Hasty Generalizations' and 'False Causation'.\n\n"

            "Output Rules:\n"
            "- Provide a plain list of 3 short, sharp, and direct critiques.\n"
            "- Be critical but constructive.\n"
            "- Do NOT suggest specific rewrites, only point out the flaws.\n"
            "- Respond in the same language as the input text.\n"
            "- Do NOT include any introductory, concluding, or meta text.\n"
            "- Do NOT explain what you are doing or why.\n"
            "- Return ONLY the list of critiques.\n\n"

            f"Input & Principles:\n{focus}"
        )

    # -------------------------------------------------
    # CRITIQUE — CHALLENGE Mode (Peer Reviewer)
    # -------------------------------------------------
    if action == ActionType.CRITIQUE:
        return (
            "You are a rigorous academic peer reviewer. Your goal is to identify "
            "weaknesses in the text to help the author make the argument bulletproof.\n"
            "MODE: CHALLENGE (Devil’s Advocate)\n\n"

            "INSTRUCTIONS:\n"
            "1. Apply Module 1 (Logical Rigor) and Module 5 (Ethics/Bibliography) "
            "from the principles below.\n"
            "2. Identify 3 major logical gaps, unsubstantiated claims, or hidden assumptions.\n"
            "3. Check for 'Hasty Generalizations' and 'False Causation'.\n\n"

            "Output Rules:\n"
            "- Provide a plain list of 3 short, sharp, and direct critiques.\n"
            "- Be critical but constructive.\n"
            "- Do NOT suggest specific rewrites, only point out the flaws.\n"
            "- Respond in the same language as the input text.\n\n"
            f"Input & Principles:\n{focus}"
        )

    raise ValueError(f"Unsupported action type: {action}")