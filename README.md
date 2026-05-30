# 🎓 Automated Viva Voce Question Generator & Evaluator

> **Problem Statement: PS-E7** — GenAI Hackathon 2024

An AI-powered Streamlit web application that automates viva voce examinations by generating Bloom's Taxonomy-mapped questions from student project reports and evaluating answers using LLMs.

---

## 📸 Screenshots

> *Screenshots will be added after the first run*

| Stage | Description |
|-------|-------------|
| Upload | PDF upload with extraction stats |
| Info | Student information form |
| Questions | 10 Bloom's-mapped questions review |
| Evaluation | One-by-one answering with live AI scoring |
| Results | Final scores, grades, and DOCX download |

---

## ✨ Features

- 📄 **PDF Upload & Extraction** — Upload project reports/lab records; text extracted via PyPDF2 with pdfplumber fallback
- 🤖 **AI Question Generation** — 10 viva questions mapped to Bloom's Taxonomy (BL2-BL5) using Groq LLM
- ✍️ **Interactive Examination** — Answer questions one-by-one with immediate AI feedback
- 📊 **Smart Scoring** — 0-5 score per question with detailed justification
- 📄 **Professional DOCX** — Color-coded score sheet with bloom-wise breakdown
- 📚 **ARC Dataset Integration** — Few-shot examples from HuggingFace ARC AI2 for better question quality
- 🎨 **Premium UI** — Dark sidebar, gradient headers, bloom badges, animated progress

---

## 🛠️ Tech Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Frontend | Streamlit | 1.35.0 |
| LLM API | Groq (llama3-70b-8192) | 0.9.0 |
| PDF Extraction | PyPDF2 + pdfplumber | 3.0.1 / 0.11.0 |
| Document Generation | python-docx | 1.1.2 |
| Dataset | HuggingFace Datasets | 2.20.0 |
| LangChain | langchain + langchain-groq | 0.2.6 / 0.1.6 |
| Data Processing | Pandas | 2.2.2 |
| Environment | python-dotenv | 1.0.1 |

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.10 or higher
- A free Groq API key ([Get one here](https://console.groq.com))

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd viva_generator

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your Groq API key:
# GROQ_API_KEY=gsk_your_actual_key_here

# 5. Run the application
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## 📖 How to Use

### Step 1: Upload PDF 📄
- Click "Choose a PDF file" to upload your project report
- The system extracts text and shows page count, word count, and a preview
- Click **"Proceed to Student Info"**

### Step 2: Fill Student Info 📝
- Enter your name, student ID, subject, department, faculty name, and report title
- Click **"Generate Viva Questions"** — AI generates 10 questions (15-30 seconds)

### Step 3: Review Questions ❓
- Review all 10 questions with their Bloom's Taxonomy levels
- See distribution: 3 BL2, 3 BL3, 2 BL4, 2 BL5
- Optionally **"Regenerate Questions"** or click **"Start Answering"**

### Step 4: Answer Questions ✍️
- Answer each question one-by-one in the text area
- Click **"Save & Submit Answer"** for AI evaluation (2-5 seconds)
- See immediate score (0-5) and justification
- Use **"Skip"** to skip a question (scores 0) or **"Previous"** to go back

### Step 5: View Results 📊
- See total score, percentage, grade, and pass/fail status
- Bloom-wise breakdown (BL2/15, BL3/15, BL4/10, BL5/10)
- Click **"Generate & Download DOCX"** for the official score sheet

---

## 📁 Folder Structure

```
viva_generator/
├── app.py                    # Main Streamlit application (5-stage UI)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── README.md                 # This file
├── modules/
│   ├── __init__.py           # Package initialization
│   ├── pdf_extractor.py      # PDF text extraction (PyPDF2 + pdfplumber)
│   ├── question_gen.py       # LLM question generation (Bloom's mapped)
│   ├── evaluator.py          # LLM answer evaluation (0-5 scoring)
│   ├── docx_generator.py     # Professional DOCX score sheet generation
│   └── dataset_loader.py     # ARC AI2 dataset loader + few-shot formatter
├── prompts/
│   ├── question_prompt.txt   # Question generation system prompt
│   └── eval_prompt.txt       # Answer evaluation system prompt
├── datasets/
│   └── arc_examples.json     # Cached ARC examples (auto-generated)
├── sample_reports/
│   └── .gitkeep              # Place sample PDFs here
├── outputs/
│   └── score_sheets/         # Generated DOCX score sheets
│       └── .gitkeep
└── docs/
    ├── ARCHITECTURE.md       # System architecture documentation
    └── API_REFERENCE.md      # API documentation for all modules
```

---

## 📚 Bloom's Taxonomy Mapping

| Code | Level | Questions | Verbs |
|------|-------|-----------|-------|
| BL2 | Understand | 3 | Describe, Explain, Summarize |
| BL3 | Apply | 3 | Demonstrate, Solve, Apply, Use |
| BL4 | Analyze | 2 | Compare, Differentiate, Examine |
| BL5 | Evaluate | 2 | Justify, Assess, Critique, Argue |

**Total: 10 questions per examination**

---

## 📊 ARC AI2 Dataset Integration

The application uses the **ARC (AI2 Reasoning Challenge)** dataset from HuggingFace for **few-shot prompting**:

- **Dataset**: `ai2_arc`, `ARC-Challenge` split
- **Purpose**: Provides example questions to improve LLM question quality
- **Usage**: 3-5 examples are injected directly into the prompt (NOT a vector DB)
- **Caching**: Downloaded once, cached locally as `datasets/arc_examples.json`
- **Fallback**: 15 hardcoded examples used when HuggingFace is unreachable

---

## 📈 Grading Scale

| Percentage | Grade |
|-----------|-------|
| ≥ 90% | O (Outstanding) |
| ≥ 80% | A+ (Excellent) |
| ≥ 70% | A (Very Good) |
| ≥ 60% | B+ (Good) |
| ≥ 50% | B (Average) |
| ≥ 40% | C (Pass) |
| < 40% | F (Fail) |

**Scoring**: Each question is scored 0-5. Total maximum = 50.

---

## 🔧 Troubleshooting

### PDF shows "text too short" error
- The PDF may be image-based (scanned). This app requires text-selectable PDFs.
- Try re-saving the PDF from the original document application.

### Groq API rate limit error
- The free tier has rate limits. Wait 30-60 seconds and try again.
- Consider breaking your session into smaller batches.

### JSON parse error during question generation
- The LLM occasionally returns malformed JSON. Click **"Regenerate Questions"**.
- The system has multiple fallback parsers, but extreme cases may still fail.

### Questions don't match the document
- Ensure the PDF contains substantial text (100+ words).
- The system truncates text to 8000 characters — longer documents may lose content.

### DOCX download not working
- Check that the `outputs/score_sheets/` directory exists and is writable.
- Try the "Generate & Download" button again.

---

## 🏆 Team & Attribution

> Built for the **GenAI Hackathon 2024**
> Problem Statement: **PS-E7 — Automated Viva Voce Question Generator & Evaluator**

---

*Powered by Groq LLM, HuggingFace Datasets, and Streamlit*
