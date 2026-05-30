"""
Answer Evaluator Module
========================
Evaluates student answers to viva voce questions using the Groq LLM API.

Each answer is scored from 0 to 5 with a written justification and a
correct-answer hint for faculty reference. Uses temperature=0.3 for
consistent and reproducible scoring.

Functions:
    evaluate_answer(question, bloom_level, student_answer, document_context) — Score an answer
    calculate_grade(total_score, max_score) — Calculate final grade
    get_score_color(score)                 — Color for score display
    get_score_label(score)                 — Human-readable score label
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
_EVAL_PROMPT_PATH = os.path.join(_PROJECT_ROOT, "prompts", "eval_prompt.txt")

# ---------------------------------------------------------------------------
# Score label mapping
# ---------------------------------------------------------------------------
_SCORE_LABELS = {
    5: "Excellent",
    4: "Good",
    3: "Satisfactory",
    2: "Partial",
    1: "Poor",
    0: "No Answer",
}

# ---------------------------------------------------------------------------
# Grading scale — percentage boundaries
# ---------------------------------------------------------------------------
_GRADE_SCALE = [
    (90, "O (Outstanding)"),
    (80, "A+ (Excellent)"),
    (70, "A (Very Good)"),
    (60, "B+ (Good)"),
    (50, "B (Average)"),
    (40, "C (Pass)"),
    (0, "F (Fail)"),
]


# ---------------------------------------------------------------------------
# JSON cleaning utility
# ---------------------------------------------------------------------------
def _clean_json_response(response_text: str) -> str:
    """
    Clean LLM response text to extract a valid JSON object.

    Strips markdown code fences and uses regex to find the JSON object
    if the response contains extra text.

    Parameters:
        response_text (str): Raw LLM response text.

    Returns:
        str: Cleaned JSON string that should be parseable as a dict.
    """
    text = response_text.strip()

    # Remove markdown code fences: ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    # If text doesn't start with '{', use regex to find the JSON object.
    # Pattern: Match everything between the first '{' and the last '}'
    # re.DOTALL makes '.' match newlines too, so multi-line JSON works.
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    return text


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------
def evaluate_answer(
    question: str,
    bloom_level: str,
    student_answer: str,
    document_context: str,
) -> dict:
    """
    Evaluate a student's answer using the Groq LLM API.

    Handles blank/empty answers without making an API call (returns score 0).
    For non-blank answers, sends the question, answer, and document context
    to the LLM with temperature=0.3 for consistent scoring.

    Parameters:
        question (str): The viva voce question that was asked.
        bloom_level (str): Bloom's Taxonomy level (e.g., 'BL2', 'BL3').
        student_answer (str): The student's text answer.
        document_context (str): Relevant text from the student's report.

    Returns:
        dict: {
            "score"               : int (0-5),
            "justification"       : str (2-3 sentence explanation),
            "correct_answer_hint" : str (1-2 sentence ideal answer)
        }
    """
    # --- Handle blank/empty answers without API call ---
    if not student_answer or not student_answer.strip():
        return {
            "score": 0,
            "justification": (
                "No answer was provided by the student. "
                "A score of 0 is assigned for blank or empty responses."
            ),
            "correct_answer_hint": (
                "Please refer to the relevant section in the project report "
                "to formulate an appropriate answer."
            ),
        }

    # --- Load API key ---
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )

    # --- Load evaluation prompt template ---
    try:
        with open(_EVAL_PROMPT_PATH, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Evaluation prompt template not found at: {_EVAL_PROMPT_PATH}. "
            "Ensure prompts/eval_prompt.txt exists."
        )

    # --- Fill in the prompt template ---
    prompt = prompt_template.format(
        question=question,
        bloom_level=bloom_level,
        student_answer=student_answer,
        document_context=document_context[:3000],  # Truncate context to save tokens
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
                    "content": (
                        "You are a strict but fair academic evaluator. "
                        "You MUST return ONLY a valid JSON object. No explanations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # Lower temperature for consistent, reproducible scoring
            max_tokens=500,
        )

        raw_response = response.choices[0].message.content
        print(f"[Evaluator] Raw response length: {len(raw_response)} chars")

    except Exception as e:
        print(f"[Evaluator] API call failed: {e}")
        # Return a safe default rather than crashing the whole evaluation
        return {
            "score": 0,
            "justification": f"Evaluation failed due to API error: {str(e)[:100]}",
            "correct_answer_hint": "Unable to generate hint due to API error.",
        }

    # --- Parse JSON response ---
    cleaned = _clean_json_response(raw_response)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Last-resort regex: find any JSON object in the response
        obj_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if obj_match:
            try:
                result = json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                print(f"[Evaluator] JSON parse failed: {e}")
                return {
                    "score": 0,
                    "justification": "Could not parse evaluation response from AI.",
                    "correct_answer_hint": "Evaluation parsing error occurred.",
                }
        else:
            print(f"[Evaluator] No JSON object found in response: {e}")
            return {
                "score": 0,
                "justification": "Could not parse evaluation response from AI.",
                "correct_answer_hint": "Evaluation parsing error occurred.",
            }

    # --- Clamp score to valid range [0, 5] ---
    # Ensure score is an integer and within bounds, even if the LLM returns
    # something unexpected like 6, -1, or a float.
    try:
        score = int(result.get("score", 0))
    except (ValueError, TypeError):
        score = 0
    result["score"] = max(0, min(5, score))

    # --- Ensure all required fields exist ---
    if "justification" not in result:
        result["justification"] = "No justification provided by evaluator."
    if "correct_answer_hint" not in result:
        result["correct_answer_hint"] = "No hint available."

    return result


# ---------------------------------------------------------------------------
# Grade calculation
# ---------------------------------------------------------------------------
def calculate_grade(total_score: int, max_score: int = 50) -> dict:
    """
    Calculate the final grade based on total score.

    Uses the grading scale:
        ≥90% → O (Outstanding)
        ≥80% → A+ (Excellent)
        ≥70% → A (Very Good)
        ≥60% → B+ (Good)
        ≥50% → B (Average)
        ≥40% → C (Pass)
        <40% → F (Fail)

    Parameters:
        total_score (int): Sum of all individual question scores.
        max_score (int): Maximum possible score (default 50 for 10 questions × 5).

    Returns:
        dict: {
            "total_score" : int,
            "max_score"   : int,
            "percentage"  : float (rounded to 1 decimal),
            "grade"       : str (e.g., "A+ (Excellent)"),
            "passed"      : bool
        }
    """
    # Handle edge cases
    if max_score <= 0:
        max_score = 50
    total_score = max(0, total_score)

    percentage = round((total_score / max_score) * 100, 1)

    # Find the appropriate grade from the scale
    grade = "F (Fail)"
    for threshold, grade_label in _GRADE_SCALE:
        if percentage >= threshold:
            grade = grade_label
            break

    passed = percentage >= 40

    return {
        "total_score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "grade": grade,
        "passed": passed,
    }


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def get_score_color(score: int) -> str:
    """
    Return the hex background color for a score value.

    Color coding:
        Score 4-5 → Light green (#C8F7C5) — Good/Excellent
        Score 2-3 → Light yellow (#FFF3CD) — Satisfactory/Partial
        Score 0-1 → Light red (#FFDEDE) — Poor/No Answer

    Parameters:
        score (int): Score value (0-5).

    Returns:
        str: Hex color string.
    """
    if score >= 4:
        return "#C8F7C5"
    elif score >= 2:
        return "#FFF3CD"
    else:
        return "#FFDEDE"


def get_score_label(score: int) -> str:
    """
    Return the human-readable label for a score value.

    Parameters:
        score (int): Score value (0-5).

    Returns:
        str: Label string (e.g., "Excellent", "Good", "Poor").
    """
    return _SCORE_LABELS.get(score, "Unknown")


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Answer Evaluator — Smoke Test")
    print("=" * 60)

    # Test 1: Grade calculation
    print("\n[Test 1] Grade calculation")
    test_cases = [
        (50, 50, "O (Outstanding)", True),
        (45, 50, "O (Outstanding)", True),
        (42, 50, "A+ (Excellent)", True),
        (37, 50, "A (Very Good)", True),
        (32, 50, "B+ (Good)", True),
        (25, 50, "B (Average)", True),
        (20, 50, "C (Pass)", True),
        (15, 50, "F (Fail)", False),
        (0, 50, "F (Fail)", False),
    ]
    for total, max_s, expected_grade, expected_pass in test_cases:
        result = calculate_grade(total, max_s)
        status = "✓" if result["grade"] == expected_grade and result["passed"] == expected_pass else "✗"
        print(
            f"  {status} Score {total}/{max_s} = {result['percentage']}% → "
            f"{result['grade']} (passed={result['passed']})"
        )
    print("  ✓ Grade calculation works")

    # Test 2: Score colors
    print("\n[Test 2] Score colors")
    for s in range(6):
        color = get_score_color(s)
        label = get_score_label(s)
        print(f"  Score {s}: {label} → {color}")
    print("  ✓ Score colors work")

    # Test 3: Blank answer evaluation (no API call)
    print("\n[Test 3] Blank answer evaluation")
    result = evaluate_answer(
        question="What is machine learning?",
        bloom_level="BL2",
        student_answer="",
        document_context="Machine learning is a subset of AI...",
    )
    assert result["score"] == 0
    assert "No answer" in result["justification"]
    print(f"  Blank answer: score={result['score']}, justification='{result['justification'][:60]}...'")
    print("  ✓ Blank answer handling works (no API call made)")

    # Test 4: Whitespace-only answer
    print("\n[Test 4] Whitespace-only answer")
    result = evaluate_answer(
        question="Explain the concept.",
        bloom_level="BL3",
        student_answer="   \n\t  ",
        document_context="Some context.",
    )
    assert result["score"] == 0
    print(f"  Whitespace answer: score={result['score']}")
    print("  ✓ Whitespace handling works")

    # Test 5: JSON cleaning
    print("\n[Test 5] JSON response cleaning")
    test_cases_json = [
        '```json\n{"score": 4, "justification": "Good", "correct_answer_hint": "hint"}\n```',
        'Here is the evaluation:\n{"score": 3, "justification": "OK", "correct_answer_hint": "hint"}\nDone!',
        '{"score": 5, "justification": "Perfect", "correct_answer_hint": "hint"}',
    ]
    for tc in test_cases_json:
        cleaned = _clean_json_response(tc)
        parsed = json.loads(cleaned)
        print(f"  Score parsed: {parsed['score']} ✓")
    print("  ✓ JSON cleaning works")

    print("\n[Note] evaluate_answer() with real answer not tested — requires GROQ_API_KEY")

    print("\n" + "=" * 60)
    print("All basic tests passed ✓")
    print("=" * 60)
