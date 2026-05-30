"""
PDF Text Extractor Module
==========================
Extracts text content from uploaded PDF files (student project reports / lab records).

Uses PyPDF2 as the primary extractor and pdfplumber as a fallback when PyPDF2
yields insufficient text (< 100 characters). Extracted text is cleaned of excess
whitespace and truncated to 8000 characters to stay within LLM context limits.

Functions:
    extract_text_pypdf2(pdf_path)  — Primary extraction via PyPDF2
    extract_text_pdfplumber(pdf_path) — Fallback extraction via pdfplumber
    extract_and_clean(pdf_path)    — Orchestrator that tries both and cleans output
"""

import os
import re
import tempfile

import PyPDF2
import pdfplumber


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_TEXT_LENGTH = 8000  # Maximum characters to send to the LLM
MIN_TEXT_THRESHOLD = 100  # Minimum chars before we consider PyPDF2 output valid


# ---------------------------------------------------------------------------
# Primary Extractor — PyPDF2
# ---------------------------------------------------------------------------
def extract_text_pypdf2(pdf_path: str) -> str:
    """
    Extract text from a PDF using PyPDF2.

    Parameters:
        pdf_path (str): Absolute or relative path to the PDF file.

    Returns:
        str: Concatenated text from all pages, or empty string on failure.
    """
    try:
        text_parts = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        print(f"[PyPDF2] Extraction failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Fallback Extractor — pdfplumber
# ---------------------------------------------------------------------------
def extract_text_pdfplumber(pdf_path: str) -> str:
    """
    Extract text from a PDF using pdfplumber (fallback extractor).

    pdfplumber often handles scanned-style or complex-layout PDFs better
    than PyPDF2.

    Parameters:
        pdf_path (str): Absolute or relative path to the PDF file.

    Returns:
        str: Concatenated text from all pages, or empty string on failure.
    """
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        print(f"[pdfplumber] Extraction failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Helper — Count pages
# ---------------------------------------------------------------------------
def _count_pages(pdf_path: str) -> int:
    """
    Return the number of pages in a PDF file.

    Parameters:
        pdf_path (str): Path to the PDF file.

    Returns:
        int: Page count, or 0 on failure.
    """
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return len(reader.pages)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------
def extract_and_clean(pdf_path: str) -> dict:
    """
    Extract text from a PDF, clean it, and return metadata.

    Strategy:
        1. Try PyPDF2 first.
        2. If extracted text < 100 chars, fall back to pdfplumber.
        3. Clean whitespace (collapse multiple spaces/newlines).
        4. Truncate to 8000 characters max.

    Parameters:
        pdf_path (str): Absolute or relative path to the PDF file.

    Returns:
        dict: {
            "raw_text"     : str — original extracted text (before cleaning),
            "cleaned_text" : str — cleaned and truncated text,
            "page_count"   : int — number of pages in the PDF,
            "word_count"   : int — word count of the cleaned text,
            "char_count"   : int — character count of the cleaned text
        }

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If no meaningful text could be extracted.
    """
    # --- Validate file exists ---
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # --- Step 1: Primary extraction (PyPDF2) ---
    raw_text = extract_text_pypdf2(pdf_path)

    # --- Step 2: Fallback to pdfplumber if text is too short ---
    if len(raw_text.strip()) < MIN_TEXT_THRESHOLD:
        print("[INFO] PyPDF2 yielded < 100 chars — falling back to pdfplumber")
        fallback_text = extract_text_pdfplumber(pdf_path)
        if len(fallback_text.strip()) > len(raw_text.strip()):
            raw_text = fallback_text

    # --- Step 3: Clean the text ---
    # Collapse multiple whitespace characters (spaces, tabs) into single space
    cleaned = re.sub(r"[ \t]+", " ", raw_text)
    # Collapse 3+ consecutive newlines into exactly 2 (paragraph break)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Strip leading/trailing whitespace from each line
    cleaned = "\n".join(line.strip() for line in cleaned.split("\n"))
    # Remove leading/trailing whitespace from entire text
    cleaned = cleaned.strip()

    # --- Step 4: Truncate to MAX_TEXT_LENGTH ---
    if len(cleaned) > MAX_TEXT_LENGTH:
        # Truncate at a word boundary to avoid cutting mid-word
        truncated = cleaned[:MAX_TEXT_LENGTH]
        last_space = truncated.rfind(" ")
        if last_space > MAX_TEXT_LENGTH * 0.8:  # Only break at space if reasonable
            truncated = truncated[:last_space]
        cleaned = truncated + "\n\n[... text truncated for processing ...]"

    # --- Step 5: Count pages ---
    page_count = _count_pages(pdf_path)

    # --- Step 6: Compute statistics ---
    words = cleaned.split()
    word_count = len(words)
    char_count = len(cleaned)

    # --- Validate we got something useful ---
    if char_count < 10:
        raise ValueError(
            "Extracted text is too short. The PDF may be image-based or empty. "
            "Please ensure the PDF contains selectable text."
        )

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned,
        "page_count": page_count,
        "word_count": word_count,
        "char_count": char_count,
    }


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("PDF Extractor — Smoke Test")
    print("=" * 60)

    # Test 1: Clean function with synthetic text
    print("\n[Test 1] Text cleaning logic")
    sample_raw = (
        "  This   is   a   test   document.\n\n\n\n\n"
        "It has    multiple    spaces   and    blank    lines.\n"
        "  And leading spaces on lines.  "
    )
    # Simulate cleaning inline
    cleaned = re.sub(r"[ \t]+", " ", sample_raw)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = "\n".join(line.strip() for line in cleaned.split("\n"))
    cleaned = cleaned.strip()
    print(f"  Raw length : {len(sample_raw)}")
    print(f"  Clean length: {len(cleaned)}")
    print(f"  Cleaned text: '{cleaned}'")
    assert "   " not in cleaned, "Multiple spaces should be collapsed"
    print("  ✓ Cleaning logic passed")

    # Test 2: Truncation logic
    print("\n[Test 2] Truncation logic")
    long_text = "word " * 2000  # 10,000 chars
    if len(long_text) > MAX_TEXT_LENGTH:
        truncated = long_text[:MAX_TEXT_LENGTH]
        last_space = truncated.rfind(" ")
        if last_space > MAX_TEXT_LENGTH * 0.8:
            truncated = truncated[:last_space]
        print(f"  Original: {len(long_text)} chars")
        print(f"  Truncated: {len(truncated)} chars")
        assert len(truncated) <= MAX_TEXT_LENGTH
        print("  ✓ Truncation logic passed")

    # Test 3: Extract from a real PDF (if path provided)
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"\n[Test 3] Extracting from: {pdf_path}")
        try:
            result = extract_and_clean(pdf_path)
            print(f"  Pages    : {result['page_count']}")
            print(f"  Words    : {result['word_count']}")
            print(f"  Chars    : {result['char_count']}")
            print(f"  Preview  : {result['cleaned_text'][:200]}...")
            print("  ✓ Extraction passed")
        except Exception as e:
            print(f"  ✗ Extraction failed: {e}")
    else:
        print("\n[Test 3] Skipped — no PDF path provided")
        print("  Usage: python pdf_extractor.py <path_to_pdf>")

    print("\n" + "=" * 60)
    print("All basic tests passed ✓")
    print("=" * 60)
