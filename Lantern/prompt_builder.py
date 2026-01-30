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
            
            "--- CONTEXT & CONSTRAINTS ---\n"
            f"{instructions}\n\n"

            "INSTRUCTIONS:\n"
            "1. Apply Module 4 (Synthesis) from the principles below.\n"
            "2. Internal Process: Brainstorm 6 distinct academic perspectives "
            "(e.g., theoretical, empirical, interdisciplinary, or counter-argumentative).\n"
            "3. Evaluation: Score each based on intellectual rigor and novelty.\n"
            "4. Selection: Select the TOP 3 winners to present to the user.\n\n"

            "Output Format (STRICT):\n"
            "For each perspective:\n"
            "Title: <[PX] A SPECIFIC, UNIQUE name for this perspective>\n"
            "Module: <The principle applied>\n"
            "Explanation: <How it applies (MAX 100 WORDS)>\n\n"
            "Rules:\n"
            "- MANDATORY CITATIONS: EVERY perspective MUST explicitly identify its relevant paragraph using the [PX] markers provided in the input (e.g., START the Title with '[P1]').\n"
            "- Do NOT rewrite the author's text.\n"
            "- KEEP IT SHORT.\n"
            "- STRICT MAXIMUM: 3 options.\n"
            "- Use 'Title:' as the key even if the content is in another language.\n"
            "- Return ONLY the perspectives in the specified format.\n\n"

            f"Input:\n{focus}"
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
            "Type: <[PX] Category, e.g., [P1] Clarity>\n"
            "Reason: <Provide a comprehensive academic explanation.>\n\n"
            "Separate each improvement block with a double newline.\n\n"
            "Rules:\n"
            "- Do NOT include any introductory or concluding text.\n"
            "- Ensure 'Original' text matches the input EXACTLY for replacement logic.\n"
            "- CITATIONS: EVERY block MUST include the [PX] marker from the input text in the 'Type' field.\n"
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

            "--- CONTEXT & CONSTRAINTS ---\n"
            f"{instructions}\n\n"

            "INSTRUCTIONS:\n"
            "1. Context Awareness: Infer the theoretical or analytical lens. Critique how well it applies that lens.\n"
            "2. Apply Module 1 (Logical Rigor) and Module 5 (Ethics/Bibliography).\n"
            "3. Identify UP TO 3 distinct logical gaps, unsubstantiated claims, or hidden assumptions.\n"
            "4. If the text is already highly rigorous and NO improvements are necessary, return ONLY the string: NO_CRITIQUE_NEEDED\n\n"

            "Output Rules:\n"
            "- If there are critiques, provide UP TO 3 short and direct blocks.\n"
            "- MANDATORY CITATIONS: If a critique focuses on a specific section, START the Title with the corresponding [PX] marker (e.g., '[P1] Hidden Assumption').\n"
            "Output Format (STRICT) per block:\n"
            "Title: <[PX] Short unique title for the issue>\n"
            "Module: <The academic principle applied>\n"
            "Critique: <The concise critique content>\n"
            "- Separate blocks with a double newline.\n"
            "- Ensure each block identifies a DIFFERENT type of issue.\n"
            "- Respond in the same language as the input text.\n"
            "- STRICTLY NO introductory text. Start directly with 'Title:' or 'NO_CRITIQUE_NEEDED'.\n\n"
            f"Input text:\n{focus}"
        )

    # -------------------------------------------------
    # SEGMENT — STRUCTURE Mode (Logical Paragraphs)
    # -------------------------------------------------
    if action == ActionType.SEGMENT:
        return (
            "You are a linguistic analyst. Your goal is to regroup the provided text into its core 'Logical Paragraphs' (Argument Units).\n"
            "MODE: SEGMENT (Logical Argument Analysis)\n\n"
            f"{instructions}\n\n"
            "--- OPERATIONAL DEFINITION ---\n"
            "A logical paragraph is a single, complete unit of argument: one central claim + its supporting explanations, reasons, or examples.\n\n"
            "--- SEGMENTATION RULES ---\n"
            "1. SKIP HEADERS: If the text contains a main title or sub-headers, SKIP them. Do NOT include them as blocks.\n"
            "2. LOGICAL ARGUMENT UNITS: Every distinct argumentative point, claim, or reasoning block should be its own unit.\n"
            "3. NO PARAPHRASING: Keep the text exactly as provided. Do not summarize or change wording.\n\n"
            "--- OUTPUT FORMAT (STRICT) ---\n"
            "Respond ONLY with a list of argumentative blocks in this exact format:\n\n"
            "Block 1:\n"
            "[Full exact text of the first logical argument unit]\n\n"
            "Block 2:\n"
            "[Full exact text of the second logical argument unit]\n\n"
            "CRITICAL: Do NOT include '[P1]', '[P2]', or ANY markers inside the block text. Only use the 'Block X:' header.\n\n"
            "--- INPUT TEXT ---\n"
            f"{focus}"
        )

    raise ValueError(f"Unsupported action type: {action}")