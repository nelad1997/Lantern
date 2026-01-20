from definitions import ActionType


def build_prompt(action: ActionType, focus: str) -> str:
    """
    בונה פרומפט עבור ה-LLM המבוסס על סוג הסוכן.
    המשתנה focus מכיל את הטקסט של המשתמש ואת העקרונות האקדמיים (Principles).
    """

    # -------------------------------------------------
    # DIVERGE — IDEA EXPANDER (Module 4: Synthesis)
    # -------------------------------------------------
    if action == ActionType.DIVERGE:
        return (
            "You are a world-class academic mentor. Suggest 3 new directions to develop the argument.\n"
            "MODE: EXPLORE (Thematic Divergence)\n\n"

            "INSTRUCTIONS:\n"
            "1. Apply Module 4 (Synthesis) from the principles below to guide your brainstorming.\n"
            "2. Generate 3 distinct academic perspectives (e.g., theoretical, social, or empirical).\n"
            "3. Ensure the options vary significantly and avoid incremental changes.\n"
            "4. DO NOT include introductory or meta text (e.g., 'Here are 3 ideas').\n"
            "5. Return ONLY the 3 perspectives, separated by a newline.\n\n"
            "6. For each option, provide: a Title (3 words), a One-liner (10 words max), and the Full Content.\n"
            "7. Format: Title | One-liner | Content\n"

            "LANGUAGE RULE: Respond STRICTLY in the same language as the 'Input Text' below. "
            "If the input is Hebrew, the response MUST be Hebrew.\n\n"

            f"Input & Principles:\n{focus}"
        )

    # -------------------------------------------------
    # CRITIQUE — DEVIL'S ADVOCATE (Module 1 & 5: Rigor/Ethics)
    # -------------------------------------------------
    if action == ActionType.CRITIQUE:
        return (
            "You are a rigorous academic peer reviewer. Identify weaknesses to make the argument bulletproof.\n"
            "MODE: CHALLENGE (Devil’s Advocate)\n\n"

            "INSTRUCTIONS:\n"
            "1. Apply Module 1 (Logical Rigor) and Module 5 (Ethics/Bibliography) from the principles below.\n"
            "2. Identify 3 major logical gaps, unsubstantiated claims, or hidden assumptions.\n"
            "3. Provide a plain list of 3 short, sharp, and direct critiques.\n"
            "4. DO NOT suggest rewrites, only point out flaws.\n\n"

            "LANGUAGE RULE: Respond STRICTLY in the same language as the 'Input Text' below.\n\n"

            f"Input & Principles:\n{focus}"
        )

    # -------------------------------------------------
    # REFINE — POLISHER (Academic Clarity & Style)
    # -------------------------------------------------
    if action == ActionType.REFINE:
        return (
            "You are a professional academic editor. Improve the clarity and flow of the text.\n"
            "MODE: REFINE (Academic Polisher)\n\n"

            "INSTRUCTIONS:\n"
            "1. Rewrite the text to be more precise, coherent, and academically rigorous.\n"
            "2. Maintain the original meaning while improving the writing style.\n"
            "3. Return ONLY the improved text, no explanations or meta-talk.\n\n"

            "LANGUAGE RULE: Respond STRICTLY in the same language as the 'Input Text' below.\n\n"

            f"Input & Principles:\n{focus}"
        )

    raise ValueError(f"Unsupported action type: {action}")