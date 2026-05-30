"""
ARC AI2 Dataset Loader Module
===============================
Loads the ARC (AI2 Reasoning Challenge) dataset from HuggingFace for
few-shot prompting in the question generation pipeline.

The dataset is cached locally as JSON after first download to avoid
repeated HuggingFace calls. If HuggingFace is unreachable, hardcoded
fallback examples are returned.

Functions:
    load_arc_examples(n_examples, cache_path) — Load and cache ARC examples
    get_few_shot_examples(bloom_level)        — Format examples for prompt injection
"""

import json
import os
import random

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
# Resolve paths relative to the project root (one level up from modules/)
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_MODULE_DIR)
_DEFAULT_CACHE_PATH = os.path.join(_PROJECT_ROOT, "datasets", "arc_examples.json")


# ---------------------------------------------------------------------------
# Bloom level → question style mapping for few-shot formatting
# ---------------------------------------------------------------------------
_BLOOM_STYLE_MAP = {
    "BL2": {
        "label": "Understanding",
        "verbs": ["Describe", "Explain", "Summarize"],
        "prefix": "Explain the concept behind",
    },
    "BL3": {
        "label": "Application",
        "verbs": ["Apply", "Demonstrate", "Solve", "Use"],
        "prefix": "How would you apply",
    },
    "BL4": {
        "label": "Analysis",
        "verbs": ["Compare", "Differentiate", "Examine"],
        "prefix": "Analyze and compare",
    },
    "BL5": {
        "label": "Evaluation",
        "verbs": ["Justify", "Assess", "Critique", "Argue"],
        "prefix": "Evaluate and justify",
    },
}


# ---------------------------------------------------------------------------
# Hardcoded fallback examples (used when HuggingFace is unreachable)
# ---------------------------------------------------------------------------
def _get_fallback_examples() -> list:
    """
    Return hardcoded fallback ARC-style example questions.

    These are used when the HuggingFace dataset cannot be downloaded.
    Covers various science topics to provide diverse few-shot examples.

    Returns:
        list[dict]: List of example question dicts with keys:
            question, choices, answer_key, answer_text
    """
    return [
        {
            "question": "Which property of a mineral can be determined just by looking at it?",
            "choices": ["luster", "hardness", "weight", "streak"],
            "answer_key": "A",
            "answer_text": "luster",
        },
        {
            "question": "A student wants to know if a rock isite orite. What test should the student perform?",
            "choices": [
                "ite isite to vinegar",
                "Ite is harder than ite",
                "ite has a higher density than ite",
                "Ite reacts differently to acid",
            ],
            "answer_key": "D",
            "answer_text": "Ite reacts differently to acid",
        },
        {
            "question": "Which of the following is a characteristic of all living organisms?",
            "choices": [
                "They produce their own food",
                "They respond to stimuli",
                "They have a backbone",
                "They live on land",
            ],
            "answer_key": "B",
            "answer_text": "They respond to stimuli",
        },
        {
            "question": "What is the main function of the root system in plants?",
            "choices": [
                "Photosynthesis",
                "Reproduction",
                "Absorption of water and minerals",
                "Gas exchange",
            ],
            "answer_key": "C",
            "answer_text": "Absorption of water and minerals",
        },
        {
            "question": "Which force keeps the planets in orbit around the Sun?",
            "choices": [
                "Magnetic force",
                "Gravitational force",
                "Frictional force",
                "Nuclear force",
            ],
            "answer_key": "B",
            "answer_text": "Gravitational force",
        },
        {
            "question": "What happens to water when it is heated to 100°C at sea level?",
            "choices": [
                "It freezes",
                "It evaporates slowly",
                "It boils",
                "It condenses",
            ],
            "answer_key": "C",
            "answer_text": "It boils",
        },
        {
            "question": "Which type of energy transformation occurs in a solar panel?",
            "choices": [
                "Chemical to thermal",
                "Light to electrical",
                "Electrical to mechanical",
                "Thermal to chemical",
            ],
            "answer_key": "B",
            "answer_text": "Light to electrical",
        },
        {
            "question": "An object is accelerating. What must be true?",
            "choices": [
                "Its speed is constant",
                "A net force is acting on it",
                "It is moving in a straight line",
                "No friction is present",
            ],
            "answer_key": "B",
            "answer_text": "A net force is acting on it",
        },
        {
            "question": "Which layer of Earth's atmosphere contains the ozone layer?",
            "choices": [
                "Troposphere",
                "Stratosphere",
                "Mesosphere",
                "Thermosphere",
            ],
            "answer_key": "B",
            "answer_text": "Stratosphere",
        },
        {
            "question": "What is the primary reason for seasons on Earth?",
            "choices": [
                "Distance from the Sun",
                "Tilt of Earth's axis",
                "Speed of Earth's rotation",
                "Shape of Earth's orbit",
            ],
            "answer_key": "B",
            "answer_text": "Tilt of Earth's axis",
        },
        {
            "question": "Which process converts glucose into energy in cells?",
            "choices": [
                "Photosynthesis",
                "Cellular respiration",
                "Fermentation",
                "Osmosis",
            ],
            "answer_key": "B",
            "answer_text": "Cellular respiration",
        },
        {
            "question": "What property of waves determines their pitch?",
            "choices": ["Amplitude", "Frequency", "Wavelength", "Speed"],
            "answer_key": "B",
            "answer_text": "Frequency",
        },
        {
            "question": "Which of these is an example of a chemical change?",
            "choices": [
                "Ice melting",
                "Wood burning",
                "Water evaporating",
                "Glass breaking",
            ],
            "answer_key": "B",
            "answer_text": "Wood burning",
        },
        {
            "question": "In a food web, what role do decomposers play?",
            "choices": [
                "They produce energy from sunlight",
                "They break down dead organisms and recycle nutrients",
                "They are the top predators",
                "They convert CO2 into oxygen",
            ],
            "answer_key": "B",
            "answer_text": "They break down dead organisms and recycle nutrients",
        },
        {
            "question": "Which element is most abundant in Earth's atmosphere?",
            "choices": ["Oxygen", "Nitrogen", "Carbon dioxide", "Argon"],
            "answer_key": "B",
            "answer_text": "Nitrogen",
        },
    ]


# ---------------------------------------------------------------------------
# Load & cache ARC examples from HuggingFace
# ---------------------------------------------------------------------------
def load_arc_examples(
    n_examples: int = 50, cache_path: str = None
) -> list:
    """
    Load ARC-Challenge examples from HuggingFace, caching locally as JSON.

    Strategy:
        1. Check if cache file exists → load from cache.
        2. If no cache → download from HuggingFace, process, save to cache.
        3. If HuggingFace is unreachable → return hardcoded fallback examples.

    Parameters:
        n_examples (int): Number of examples to load (default 50).
        cache_path (str): Path to the cache JSON file. Defaults to
                          datasets/arc_examples.json relative to project root.

    Returns:
        list[dict]: List of dicts with keys:
            question (str), choices (list[str]), answer_key (str), answer_text (str)
    """
    if cache_path is None:
        cache_path = _DEFAULT_CACHE_PATH

    # --- Step 1: Check cache ---
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            if isinstance(cached_data, list) and len(cached_data) > 0:
                print(f"[Dataset] Loaded {len(cached_data)} examples from cache")
                return cached_data[:n_examples]
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Dataset] Cache read failed: {e} — will re-download")

    # --- Step 2: Try HuggingFace download ---
    try:
        from datasets import load_dataset
        from dotenv import load_dotenv

        load_dotenv()

        print("[Dataset] Downloading ARC-Challenge from HuggingFace...")

        # Use HF_TOKEN from .env if available for authenticated access
        # (faster downloads, higher rate limits). Falls back to unauthenticated.
        hf_token = os.getenv("HF_TOKEN")
        if hf_token and not hf_token.startswith("hf_your"):
            print("[Dataset] Using authenticated HuggingFace access")
            dataset = load_dataset(
                "allenai/ai2_arc", "ARC-Challenge", split="test",
                token=hf_token
            )
        else:
            print("[Dataset] Using unauthenticated access (set HF_TOKEN in .env for faster downloads)")
            dataset = load_dataset("allenai/ai2_arc", "ARC-Challenge", split="test")

        examples = []
        for i, item in enumerate(dataset):
            if i >= n_examples:
                break

            # ARC dataset structure: question, choices (dict with text/label), answerKey
            choices_text = item["choices"]["text"]
            choices_labels = item["choices"]["label"]
            answer_key = item["answerKey"]

            # Find the answer text by matching the answer key to the label
            answer_text = ""
            for label, text in zip(choices_labels, choices_text):
                if label == answer_key:
                    answer_text = text
                    break

            examples.append(
                {
                    "question": item["question"],
                    "choices": choices_text,
                    "answer_key": answer_key,
                    "answer_text": answer_text,
                }
            )

        # --- Save to cache ---
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(examples, f, indent=2, ensure_ascii=False)
        print(f"[Dataset] Cached {len(examples)} examples to {cache_path}")

        return examples

    except Exception as e:
        print(f"[Dataset] HuggingFace download failed: {e}")
        print("[Dataset] Using hardcoded fallback examples")
        return _get_fallback_examples()


# ---------------------------------------------------------------------------
# Format few-shot examples for a given Bloom's level
# ---------------------------------------------------------------------------
def get_few_shot_examples(bloom_level: str) -> str:
    """
    Return 3 formatted example questions for injection into LLM prompts.

    Selects examples from the cached ARC dataset and formats them in a
    style appropriate for the specified Bloom's Taxonomy level.

    Parameters:
        bloom_level (str): One of 'BL2', 'BL3', 'BL4', 'BL5'.

    Returns:
        str: Formatted string containing 3 example Q&A pairs, ready for
             prompt injection. Returns fallback examples if loading fails.
    """
    # Get Bloom style info
    style = _BLOOM_STYLE_MAP.get(bloom_level, _BLOOM_STYLE_MAP["BL2"])

    try:
        examples = load_arc_examples()
    except Exception:
        examples = _get_fallback_examples()

    # Select 3 random examples (use deterministic seed based on bloom level
    # so the same level always gets the same examples within a session)
    rng = random.Random(hash(bloom_level))
    selected = rng.sample(examples, min(3, len(examples)))

    # Format the examples for prompt injection
    formatted_parts = []
    for i, ex in enumerate(selected, 1):
        # Rephrase the ARC question in the style of the Bloom level
        verb = style["verbs"][i % len(style["verbs"])]
        formatted_parts.append(
            f"Example {i} ({style['label']} — {verb}):\n"
            f"Q: {ex['question']}\n"
            f"A: {ex['answer_text']}\n"
        )

    return "\n".join(formatted_parts)


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Dataset Loader — Smoke Test")
    print("=" * 60)

    # Test 1: Fallback examples
    print("\n[Test 1] Hardcoded fallback examples")
    fallback = _get_fallback_examples()
    print(f"  Count: {len(fallback)}")
    assert len(fallback) >= 15, "Should have at least 15 fallback examples"
    for ex in fallback[:3]:
        assert "question" in ex and "choices" in ex and "answer_key" in ex
    print("  ✓ Fallback examples valid")

    # Test 2: Load ARC examples (will use cache or fallback)
    print("\n[Test 2] load_arc_examples()")
    examples = load_arc_examples(n_examples=10)
    print(f"  Loaded: {len(examples)} examples")
    if examples:
        print(f"  First Q: {examples[0]['question'][:80]}...")
    print("  ✓ Loading works")

    # Test 3: Few-shot examples for each Bloom level
    print("\n[Test 3] get_few_shot_examples()")
    for bl in ["BL2", "BL3", "BL4", "BL5"]:
        fs = get_few_shot_examples(bl)
        print(f"\n  --- {bl} ---")
        print(f"  {fs[:150]}...")
        assert len(fs) > 50, f"Few-shot string for {bl} is too short"
    print("\n  ✓ Few-shot formatting works")

    print("\n" + "=" * 60)
    print("All tests passed ✓")
    print("=" * 60)
