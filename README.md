# Standalone AI Question-Generation Engine for Learn (ICSE Classes 8–12)

A standalone, modular Python engine (`question_quality_engine.py`) that reads educational PDFs or pre-extracted curriculum text and generates **curriculum-grounded, notation-accurate, and rubric-validated questions and answers** for **ICSE Classes 8, 9, 10, 11, and 12**.

> **Integration Boundary Notice:** This module is built independently of Learn's internal repository. It does not recreate Learn's UI, printing workflow, or internal database schema, and exposes a clean, documented Python API and JSON output contract ready to be connected to Learn as a question-generation layer.

---

## 1. Architecture Overview

The engine is divided into four decoupled components:

1. **Advanced PDF & Scientific Notation Extractor (`PDFExtractionEngine` in `question_quality_engine.py`)**
   - Accepts a local PDF file path (`extract_pdf_content`) or already-extracted text (`parse_extracted_text_input`).
   - Preserves chapter headings, section headings, paragraphs, bulleted/numbered lists, structured tables (`TableRecord`), and figure/diagram/map metadata (`FigureRecord`) linked to 1-indexed page numbers.
   - Reconstructs subscripts and superscripts from PDF `BT ... ET` text matrix vertical baseline offsets (`Tm` / `Td` / `Tf`) as well as LaTeX/ASCII scientific notation (`2H₂O(l) → 2H₂(g) + O₂(g)`, `CuSO₄(aq) ⇌ Cu²⁺(aq) + SO₄²⁻(aq)`, `V = I × R`, `H = I²Rt`, `d/dx(xⁿ) = nxⁿ⁻¹`).
   - Detects empty files, corrupt/unreadable PDFs, and image-only scanned PDFs (`ocr_required: True`), reporting clear OCR recommendations without silently treating an unread scan as valid text.
2. **Curriculum Source Analyzer (`SourceAnalyzer` in `question_quality_engine.py`)**
   - Segments long documents into context-preserving chapter/section chunks (`max_chunk_chars`).
   - Identifies and prioritizes learning points across definitions, chemical/mathematical formulas, quantitative numerical problems, causes & consequences, sequential processes, comparisons, and data tables.
   - Filters out non-curriculum publication metadata (ISBNs, reprint dates, copyright notices) so History & Civics questions never confuse textbook metadata with historical chronology.
3. **Modular AI Provider Adapter Layer (`provider_adapters.py`)**
   - Keeps provider-specific requests behind `AIProviderAdapter`.
   - Includes `GeminiProviderAdapter` (using `GEMINI_API_KEY` and JSON schema output constraints), `OpenAICompatibleProviderAdapter`, and `DeterministicSynthesisAdapter` (for deterministic offline unit testing and baseline benchmarking).
   - Enforces request timeouts (`AI_TIMEOUT_SECONDS`), bounded exponential backoff retries (`AI_MAX_RETRIES`), rate-limit handling, and strict credential redaction (`sanitize_secrets`).
4. **Configurable 7-Criterion Question-Quality Rubric & Deterministic Verifier (`QuestionQualityRubric`, `RubricConfig`, `DeterministicVerifier`)**
   - Scores every candidate question on a documented **1–5 scale** across 7 criteria (`curriculum_relevance`, `source_fidelity`, `clarity`, `educational_value`, `distinctness`, `answer_quality`, `grade_suitability`).
   - Independently verifies mathematical/physics numerical answers using Python's `ast` evaluator and checks chemical reaction equations for elemental atom conservation.
   - Rejects unsupported claims, invented page numbers, duplicate/near-duplicate questions, and questions that claim to interpret visual-only maps or diagrams whose contents were not extracted.

---

## 2. Installation & Configuration

### Python Environment
The standalone engine runs on **Python 3.10+** with zero mandatory third-party C extensions required, and optionally integrates with `pypdf` / `pdfplumber` when installed:

```bash
# Optional third-party extractors / SDKs
pip install -r requirements.txt
```

### Environment Variables (`.env`)
Copy `.env.example` and configure:
```bash
export GEMINI_API_KEY="your_api_key_here"
export AI_PROVIDER="auto"            # "auto", "gemini", "openai_compatible", or "deterministic"
export AI_MODEL="gemini-3.8-flash"   # Configurable model name
export AI_TIMEOUT_SECONDS="25.0"     # Per-request timeout
export AI_MAX_RETRIES="2"            # Bounded retries with exponential backoff
```

---

## 3. Standalone Python API Usage

### Generating Questions from a Local PDF
```python
from question_quality_engine import generate_questions

result = generate_questions(
    pdf_path="fixtures/icse_sample_science_history.pdf",
    class_level=10,
    subject="Chemistry",
    question_count=5,
    options={
        "provider": "auto",
        "question_types": ["understanding", "why_how", "problem_solving", "interpretation", "comparison"],
        "rubric_config": {
            "min_criterion_score": 3,
            "min_source_fidelity": 4,
            "min_average_score": 3.6,
            "max_similarity_threshold": 0.55,
            "require_math_verification": True,
        },
    },
)

for q in result["questions"]:
    print(q["question_id"], q["question_type"], q["source_page"], q["quality_scores"]["average_score"])
    print("Q:", q["question"])
    print("A:", q["answer"])
```

### Passing Already-Extracted Text (Alternative Input Mode for Learn)
```python
result = generate_questions(
    extracted_text="--- Page 12 ---\nOhm's Law states that V = I × R at constant temperature...",
    class_level=10,
    subject="Physics",
    question_count=2,
)
```

---

## 4. Documented 7-Criterion Question-Quality Rubric (1–5 Scale)

| Criterion | Weight (Default) | Default Min | Score 1 (Reject) | Score 3 (Acceptable) | Score 5 (Exemplary) |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **`curriculum_relevance`** | `1.15` | `3` | Tests publication/ISBN metadata or lacks a learning point | Valid secondary fact from the passage | Directly targets a prioritized, syllabus-central learning point |
| **`source_fidelity`** | `1.35` | `4` | Hallucinates facts, invents page numbers, or claims to read an unextracted visual diagram | Partially paraphrased support (`>= 50%` containment) | Verbatim source evidence verified on exact `source_page` |
| **`clarity`** | `1.00` | `3` | Fragmented, ungrammatical, or ambiguous wording | Understandable wording with minor stiffness | Specific, unambiguous ICSE question with clear task verb |
| **`educational_value`** | `1.10` | `3` | Mechanical copy of source sentence (`> 85%` overlap) | Basic factual recall (Classes 8–10) | Conceptual explanation, comparison, table interpretation, or problem solving |
| **`distinctness`** | `1.00` | `3` | Duplicate or near-duplicate (`>= 75%` similarity) | Moderate thematic overlap (`40%–54%`) | Completely distinct learning point and cognitive skill |
| **`answer_quality`** | `1.25` | `3` | Factually wrong, fails math solver or chemical balance check | Correct core point but brief | Complete, notation-faithful model answer verified deterministically |
| **`grade_suitability`** | `1.15` | `3` | Severe mismatch for target ICSE class | Acceptable with minor phrasing adjustments | Calibrated to ICSE Classes 8–10 or Classes 11–12 depth |

---

## 5. Output Schema & Student Worksheet Separation

The engine returns both:
1. **`questions`**: Full validated records with `source_reference`, `quality_scores`, `validation_results`, `validation_status`, `review_status`, and `review_notes` for backend quality auditing.
2. **`student_worksheet`**: A clean student-facing worksheet payload containing only `question_id`, `question`, `answer`, `question_type`, `difficulty`, and `source_page` (free of internal diagnostic scores).

Each item in `result["questions"]` conforms to the validated JSON schema:

```json
{
  "question_id": "q_01",
  "question": "Arrange the key milestones in the making of the Indian Constitution in chronological order from 9 December 1946 to 26 January 1950, stating what happened on each date.",
  "answer": "In chronological order: (1) 9 December 1946 — the Constituent Assembly held its first meeting; (2) 15 August 1947 — India became independent; (3) 26 November 1949 — the Constitution of India was adopted; and (4) 26 January 1950 — the Constitution came into effect, when India became a republic.",
  "question_type": "sequence",
  "difficulty": "medium",
  "learning_point": "Arrange the chronological milestones in the making of the Indian Constitution from 9 December 1946 to 26 January 1950",
  "source_evidence": "When India became independent on 15 August 1947, it needed fundamental rules to govern the country. The Assembly first met on 9 December 1946. The Constituent Assembly adopted the Constitution on 26 November 1949. It came into effect on 26 January 1950, when India became a republic.",
  "source_page": 1,
  "source_reference": {
    "page_number": 1,
    "paragraph_id": "p1_syn_sequence",
    "char_span": [92, 1348],
    "supporting_text": "When India became independent on 15 August 1947, it needed fundamental rules to govern the country. The Assembly first met on 9 December 1946. The Constituent Assembly adopted the Constitution on 26 November 1949. It came into effect on 26 January 1950, when India became a republic."
  },
  "quality_scores": {
    "curriculum_relevance": 5,
    "source_fidelity": 5,
    "clarity": 5,
    "educational_value": 5,
    "distinctness": 5,
    "answer_quality": 5,
    "grade_suitability": 5,
    "average_score": 5.0
  },
  "validation_results": {
    "source_grounding_pass": true,
    "answer_support_pass": true,
    "answer_alignment_pass": true,
    "clarity_pass": true,
    "specificity_pass": true,
    "non_duplication_pass": true,
    "completeness_pass": true,
    "ungrounded_claims": []
  },
  "validation_status": "accepted",
  "review_status": "accepted",
  "review_notes": [
    "Passed all 7 rubric criteria, strict PDF grounding, and question-answer alignment checks."
  ]
}
```

---

## 6. Running Automated Tests & Evaluation Comparison

```bash
# Run all 19 deterministic unit & regression tests
python3 -m unittest discover -s . -p "test_*.py" -v

# Generate before-vs-after evaluation comparison report
python3 question_quality_engine.py evaluate-comparison --output fixtures/evaluation_comparison_report.json
```

---

## 7. Extraction Limitations & Future Learn Integration Guide

### Known Extraction Limitations
1. **Scanned / Image-Only PDFs**: The engine detects image-only pages (`extraction_status: "ocr_required"`) and halts rather than guessing text. When integrating with scanned school books, configure an external OCR stage (e.g., Tesseract or Google Cloud Vision/Document AI) and pass its output into `generate_questions(extracted_text=...)`.
2. **Visual-Only Diagrams & Maps**: Embedded vector/bitmap diagrams without textual labels are flagged with `is_visual_only: True`. The engine intentionally blocks questions that claim to read internal visual contours or unlabeled arrows from such figures.
3. **Complex Multi-Line LaTeX Matrices**: Single-line equations, chemical stoichiometry, subscripts/superscripts, derivatives, and integrals are preserved; deeply nested 2D matrices spanning multiple vertical PDF lines may flatten into linear rows.

### Information Needed Later to Connect to Learn
To connect `question_quality_engine.py` into Learn's production pipeline later, only a thin adapter mapping will be needed once the following details from Learn are provided:
- **Learn's Input Convention**: Whether Learn passes a file path (`pdf_path`) or its own pre-extracted page/section text structure (`extracted_text`).
- **Learn's Output Question Schema**: Field-name mapping from our documented record (`question_id`, `question`, `answer`, `question_type`, `difficulty`, `learning_point`, `source_evidence`, `source_page`, `source_reference`, `quality_scores`, `validation_results`, `validation_status`, `review_status`, `review_notes`) or `student_worksheet` to Learn's database/ORM models.
- **Learn's Review Queue Workflow**: How records with `review_status == "repaired"` or `"rejected"` should be surfaced or logged in Learn's teacher review UI.

