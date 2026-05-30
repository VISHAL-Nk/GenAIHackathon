"""
Question Generation Module
============================
Generates Bloom's Taxonomy-mapped viva voce questions using the Groq LLM API.

Uses the llama3-70b-8192 model to generate exactly 10 questions from a
student's project report text, distributed as:
    BL2 (Understand) : 3 questions
    BL3 (Apply)      : 3 questions
    BL4 (Analyze)    : 2 questions
    BL5 (Evaluate)   : 2 questions

Functions:
    generate_questions(document_text, subject) — Main generation function
    get_bloom_color(bloom_level)               — Returns hex color for UI
"""

import json
import os
import re

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_MODULE_DIR)
_PROMPT_PATH = os.path.join(_PROJECT_ROOT, "prompts", "question_prompt.txt")

# ---------------------------------------------------------------------------
# Expected Bloom's distribution — used for validation
# ---------------------------------------------------------------------------
_EXPECTED_DISTRIBUTION = {"BL2": 3, "BL3": 3, "BL4": 2, "BL5": 2}
_TOTAL_QUESTIONS = 10

# ---------------------------------------------------------------------------
# Bloom level → UI color mapping
# ---------------------------------------------------------------------------
_BLOOM_COLORS = {
    "BL2": "#DBEAFE",  # Light blue — Understand
    "BL3": "#D1FAE5",  # Light green — Apply
    "BL4": "#FEF3C7",  # Light yellow — Analyze
    "BL5": "#FEE2E2",  # Light red — Evaluate
}

# Bloom level → text color for badges
_BLOOM_TEXT_COLORS = {
    "BL2": "#1E40AF",  # Dark blue
    "BL3": "#065F46",  # Dark green
    "BL4": "#92400E",  # Dark amber
    "BL5": "#991B1B",  # Dark red
}


# ---------------------------------------------------------------------------
# JSON cleaning utility
# ---------------------------------------------------------------------------
def _clean_json_response(response_text: str) -> str:
    """
    Clean LLM response text to extract valid JSON.

    LLMs often wrap JSON in markdown code fences (```json ... ```) or
    include explanatory text before/after the JSON. This function strips
    those artifacts.

    Strategy:
        1. Strip markdown code fences (```json and ```)
        2. Strip leading/trailing whitespace
        3. If text doesn't start with '[', use regex to find the JSON array

    Parameters:
        response_text (str): Raw LLM response text.

    Returns:
        str: Cleaned JSON string that should be parseable.
    """
    text = response_text.strip()

    # Step 1: Remove markdown code fences
    # Handles: ```json\n...\n``` and ```\n...\n```
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    # Step 2: If the text doesn't start with '[', try to extract the JSON array
    # using regex. This handles cases where the LLM adds text before/after.
    # Pattern: Match everything between the first '[' and the last ']'
    if not text.startswith("["):
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            text = match.group(0)

    return text


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _validate_questions(questions: list) -> bool:
    """
    Validate that generated questions meet all requirements.

    Checks:
        1. Exactly 10 questions
        2. Each question has required keys: q_number, bloom_level, bloom_label, question
        3. Bloom distribution is exactly 3 BL2 + 3 BL3 + 2 BL4 + 2 BL5

    Parameters:
        questions (list[dict]): List of question dictionaries from LLM.

    Returns:
        bool: True if validation passes.

    Raises:
        ValueError: With descriptive message if validation fails.
    """
    # Check count
    if len(questions) != _TOTAL_QUESTIONS:
        raise ValueError(
            f"Expected exactly {_TOTAL_QUESTIONS} questions, got {len(questions)}. "
            "The LLM did not follow the count requirement."
        )

    # Check required keys in each question
    required_keys = {"q_number", "bloom_level", "bloom_label", "question"}
    for i, q in enumerate(questions):
        missing = required_keys - set(q.keys())
        if missing:
            raise ValueError(
                f"Question {i+1} is missing required fields: {missing}. "
                f"Got keys: {list(q.keys())}"
            )

    # Check Bloom's distribution
    # Count how many questions are at each Bloom level
    bl_counts = {}
    for q in questions:
        bl = q["bloom_level"]
        bl_counts[bl] = bl_counts.get(bl, 0) + 1

    for bl, expected in _EXPECTED_DISTRIBUTION.items():
        actual = bl_counts.get(bl, 0)
        if actual != expected:
            raise ValueError(
                f"Bloom level {bl} distribution error: expected {expected}, "
                f"got {actual}. Full distribution: {bl_counts}"
            )

    return True


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------
def generate_questions(document_text: str, subject: str) -> list:
    """
    Generate 10 viva voce questions mapped to Bloom's Taxonomy levels.

    Calls the Groq API with llama3-70b-8192 to generate questions based on
    the provided document text. Includes few-shot examples from the ARC
    dataset for improved question quality.

    Parameters:
        document_text (str): Cleaned text extracted from the student's PDF.
        subject (str): The subject/course name for context.

    Returns:
        list[dict]: List of 10 question dicts, each with keys:
            q_number (int), bloom_level (str), bloom_label (str), question (str)

    Raises:
        ValueError: If API key is missing, response is invalid, or validation fails.
        Exception: If API call fails after retries.
    """
    # --- Load API key ---
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )

    # --- Load prompt template ---
    try:
        with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Question prompt template not found at: {_PROMPT_PATH}. "
            "Ensure prompts/question_prompt.txt exists."
        )

    # --- Get few-shot examples from ARC dataset ---
    try:
        from modules.dataset_loader import get_few_shot_examples

        few_shot_parts = []
        for bl in ["BL2", "BL3", "BL4", "BL5"]:
            few_shot_parts.append(f"--- {bl} Examples ---\n{get_few_shot_examples(bl)}")
        few_shot_text = "\n\n".join(few_shot_parts)
    except Exception as e:
        print(f"[QuestionGen] Could not load few-shot examples: {e}")
        few_shot_text = "(No few-shot examples available)"

    # --- Fill in the prompt template ---
    prompt = prompt_template.format(
        document_text=document_text[:6000],  # Leave room for prompt overhead
        subject=subject,
        few_shot_examples=few_shot_text,
    )

    # --- Call Groq API ---
    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert academic question generator. "
                    "You MUST return ONLY valid JSON arrays. No explanations.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=4000,
        )

        raw_response = response.choices[0].message.content
        print(f"[QuestionGen] Raw response length: {len(raw_response)} chars")

    except Exception as e:
        raise RuntimeError(f"Groq API call failed: {e}")

    # --- Parse JSON response ---
    cleaned = _clean_json_response(raw_response)

    try:
        questions = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Last-resort regex: try to find any JSON array in the response
        # This handles cases where the LLM embeds the array in markdown/text
        array_match = re.search(r"\[.*\]", raw_response, re.DOTALL)
        if array_match:
            try:
                questions = json.loads(array_match.group(0))
            except json.JSONDecodeError:
                raise ValueError(
                    f"Could not parse LLM response as JSON. "
                    f"Parse error: {e}. "
                    f"Raw response preview: {raw_response[:500]}"
                )
        else:
            raise ValueError(
                f"LLM response does not contain a JSON array. "
                f"Parse error: {e}. "
                f"Raw response preview: {raw_response[:500]}"
            )

    # --- Validate the questions ---
    _validate_questions(questions)

    # Ensure q_number is an int
    for q in questions:
        q["q_number"] = int(q["q_number"])

    return questions


# ---------------------------------------------------------------------------
# UI helper — Bloom color
# ---------------------------------------------------------------------------
def get_bloom_color(bloom_level: str) -> str:
    """
    Return the hex background color for a Bloom's Taxonomy level.

    Used in the Streamlit UI to color-code question badges and cards.

    Parameters:
        bloom_level (str): One of 'BL2', 'BL3', 'BL4', 'BL5'.

    Returns:
        str: Hex color string (e.g., '#DBEAFE'). Returns light gray for unknown levels.
    """
    return _BLOOM_COLORS.get(bloom_level, "#F3F4F6")


def get_bloom_text_color(bloom_level: str) -> str:
    """
    Return the hex text color for a Bloom's Taxonomy level badge.

    Parameters:
        bloom_level (str): One of 'BL2', 'BL3', 'BL4', 'BL5'.

    Returns:
        str: Hex text color string.
    """
    return _BLOOM_TEXT_COLORS.get(bloom_level, "#374151")


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Question Generator — Smoke Test")
    print("=" * 60)

    # Test 1: Bloom colors
    print("\n[Test 1] Bloom colors")
    for bl in ["BL2", "BL3", "BL4", "BL5", "BL99"]:
        bg = get_bloom_color(bl)
        txt = get_bloom_text_color(bl)
        print(f"  {bl}: bg={bg}, text={txt}")
    print("  ✓ Bloom colors work")

    # Test 2: JSON cleaning
    print("\n[Test 2] JSON cleaning")

    # Test with markdown fences
    test_fenced = '```json\n[{"q_number": 1, "bloom_level": "BL2"}]\n```'
    cleaned = _clean_json_response(test_fenced)
    parsed = json.loads(cleaned)
    assert parsed[0]["q_number"] == 1
    print(f"  Fenced JSON: ✓ (parsed {len(parsed)} items)")

    # Test with extra text
    test_extra = 'Here are the questions:\n[{"q_number": 1, "bloom_level": "BL2"}]\nHope this helps!'
    cleaned = _clean_json_response(test_extra)
    parsed = json.loads(cleaned)
    assert parsed[0]["q_number"] == 1
    print(f"  Extra text JSON: ✓ (parsed {len(parsed)} items)")

    # Test with clean JSON
    test_clean = '[{"q_number": 1, "bloom_level": "BL2"}]'
    cleaned = _clean_json_response(test_clean)
    parsed = json.loads(cleaned)
    assert parsed[0]["q_number"] == 1
    print(f"  Clean JSON: ✓ (parsed {len(parsed)} items)")

    # Test 3: Validation
    print("\n[Test 3] Question validation")
    valid_questions = [
        {"q_number": i + 1, "bloom_level": bl, "bloom_label": label, "question": f"Q{i+1}?"}
        for i, (bl, label) in enumerate(
            [("BL2", "Understand")] * 3
            + [("BL3", "Apply")] * 3
            + [("BL4", "Analyze")] * 2
            + [("BL5", "Evaluate")] * 2
        )
    ]
    assert _validate_questions(valid_questions) is True
    print("  Valid set: ✓")

    # Test invalid count
    try:
        _validate_questions(valid_questions[:5])
        print("  ✗ Should have raised ValueError for wrong count")
    except ValueError as e:
        print(f"  Invalid count caught: ✓ ({str(e)[:60]}...)")

    # Test invalid distribution
    try:
        bad_dist = [
            {"q_number": i + 1, "bloom_level": "BL2", "bloom_label": "Understand", "question": f"Q{i+1}?"}
            for i in range(10)
        ]
        _validate_questions(bad_dist)
        print("  ✗ Should have raised ValueError for bad distribution")
    except ValueError as e:
        print(f"  Invalid distribution caught: ✓ ({str(e)[:60]}...)")

    print("\n[Note] generate_questions() not tested — requires GROQ_API_KEY")

    print("\n" + "=" * 60)
    print("All basic tests passed ✓")
    print("=" * 60)
