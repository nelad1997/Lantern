from definitions import ActionType


def build_prompt(action: ActionType, focus: str, instructions: str = "") -> str:
    """
    Builds a prompt for the LLM based on the requested action.
    'focus' is the Input Text. 'instructions' are system constraints.
    """

    # -------------------------------------------------
    # DIVERGE — EXPLORE Mode (Thematic Perspectives)
    # -------------------------------------------------
    if action == ActionType.DIVERGE:
        # For Diverge, we keep the previous format for now (concatenated) 
        # as it works well with the "Perspectives" logic.
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
            "For each perspective:\n"
            "Title: <A SPECIFIC, UNIQUE name for this perspective. DO NOT USE 'Alternative Perspective'>\n"
            "Module: <The principle applied>\n"
            "Explanation: <How it applies (MAX 100 WORDS)>\n\n"
            "Rules:\n"
            "- Do NOT rewrite the author's text.\n"
            "- KEEP IT SHORT.\n"
            "- STRICT MAXIMUM: 3 options.\n"
            "- MANDATORY: Every Title MUST be distinct and directly describe the perspective's unique focus.\n"
            "- Use 'Title:' as the key even if the content is in another language.\n"
            "- Return ONLY the perspectives in the specified format.\n\n"

            f"Input & Principles:\n{focus}\n{instructions}"
        )

    # -------------------------------------------------
    # REFINE — POLISH Mode (Academic Editor)
    # -------------------------------------------------
    if action == ActionType.REFINE:
        return (
            "You are a meticulous academic editor. Your task is to identify specific "
            "improvements to the author's text for clarity, flow, and structure.\n"
            "MODE: REFINE (Granular Analysis)\n\n"

            "--- SYSTEM INSTRUCTIONS ---\n"
            f"{instructions}\n"
            "1. Identify clear, logical segments of the text that can be improved.\n"
            "2. For each improvement, provide the original segment, the replacement, and a brief academic reason.\n"
            "3. Keep the original meaning and core arguments intact.\n\n"

            "--- OUTPUT FORMAT (STRICT) ---\n"
            "Respond ONLY with a list of improvements in the following block format:\n\n"
            "Original: <The exact text segment from the input>\n"
            "Proposed: <The improved version of that segment>\n"
            "Type: <1-3 words describing the improvement type>\n"
            "Reason: <Provide a comprehensive, multi-faceted academic explanation.>\n\n"
            "Separate each improvement block with a double newline.\n\n"
            "Rules:\n"
            "- Do NOT include any introductory or concluding text.\n"
            "- Ensure 'Original' text matches the input EXACTLY for replacement logic.\n"
            "- Respond in the same language as the input text.\n\n"

            "--- INPUT TEXT TO REFINE ---\n"
            f"{focus}"
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
            "1. Context Awareness: Infer the theoretical or analytical lens. Critique how well it applies that lens.\n"
            "2. Apply Module 1 (Logical Rigor) and Module 5 (Ethics/Bibliography).\n"
            "3. Identify UP TO 3 distinct logical gaps, unsubstantiated claims, or hidden assumptions.\n"
            "4. If the text is already highly rigorous and NO improvements are necessary, return ONLY the string: NO_CRITIQUE_NEEDED\n\n"

            "Output Rules:\n"
            "- If there are critiques, provide UP TO 3 short and direct blocks.\n"
            "Output Format (STRICT) per block:\n"
            "Title: <Short unique title for the issue (MUST be distinct for each block)>\n"
            "Module: <The academic principle applied>\n"
            "Critique: <The concise critique content>\n"
            "- Separate blocks with a double newline.\n"
            "- Ensure each block identifies a DIFFERENT type of issue.\n"
            "- Respond in the same language as the input text.\n"
            "- STRICTLY NO introductory text. Start directly with 'Title:' or 'NO_CRITIQUE_NEEDED'.\n\n"
            f"Input & Principles:\n{focus}"
        )

    raise ValueError(f"Unsupported action type: {action}")