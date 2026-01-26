
import re
from typing import List

def parse_llm_options(llm_output: str) -> List[str]:
    # ניקוי פורמטים נפוצים של markdown
    clean_output = llm_output.replace("**Title:**", "Title:").replace("**Title**:", "Title:")
    clean_output = clean_output.replace("**Module:**", "Module:").replace("**Module**:", "Module:")
    clean_output = clean_output.replace("**Explanation:**", "Explanation:").replace("**Explanation**:", "Explanation:")
    clean_output = clean_output.replace("**Critique:**", "Critique:").replace("**Critique**:", "Critique:")

    # אם יש "Title:", ננסה לפצל לפי זה (כולל מספור לפני)
    if "Title:" in clean_output:
        # פיצול לפי התחלות של אפשרויות (Title: או מספר ואז Title:)
        candidates = re.split(r"(?=\n(?:\d+\.|\*|-)?\s*Title:|^(?:\d+\.|\*|-)?\s*Title:)", clean_output.strip())
        return [c.strip() for c in candidates if c.strip() and "Title:" in c]

    # fallback לשיטה הישנה של בלוקים
    blocks = clean_output.split("\n\n")
    return [block.strip() for block in blocks if len(block.strip()) > 20]

sample_output = """
1. Title: Theoretical Lens
Module: Synthesis
Explanation: This lens focuses on the theoretical aspects.

2. **Title:** Empirical Lens
Module: Data Analysis
Explanation: This lens focuses on the data.

3. Title: Interdisciplinary Lens
Module: Integration
Explanation: This lens integrates multiple fields.
"""

options = parse_llm_options(sample_output)
print(f"Found {len(options)} options.")
for i, opt in enumerate(options):
    print(f"--- Option {i+1} ---")
    print(opt)

# Test with no Title:
sample_no_title = "This is a long explanation of one option that should be caught by the fallback logic because it's longer than 20 characters."
options_no_title = parse_llm_options(sample_no_title)
print(f"\nFound {len(options_no_title)} options in fallback.")
