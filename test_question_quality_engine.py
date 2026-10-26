"""
Automated Unit & Validation Test Suite for `question_quality_engine.py` and `provider_adapters.py`.

Covers all required validation scenarios without requiring live network AI API calls:
1. PDF text, table, figure, and coordinate-aware subscript/superscript extraction
2. Empty, missing, or corrupt/unreadable PDFs
3. Image-only scanned PDFs and explicit OCR requirement warnings
4. Page and section association (and unpaginated text null-page preservation)
5. Scientific, chemical, and mathematical notation preservation
6. Structured-output parsing and schema validation
7. Missing or malformed fields rejection
8. Duplicate and near-duplicate question detection
9. Source-evidence verification, publication-date trap filtering, and unread diagram protection
10. AI Provider timeout, HTTP 429 rate-limit backoff retries, and secret redaction
11. Valid JSON serialization of all returned structures
12. Deterministic numerical solver & chemical equation stoichiometry verification
13. Configurable 7-criterion Question-Quality Rubric thresholds & ICSE Class 8–12 adaptation
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
import urllib.request

from generate_fixtures import generate_all_fixtures
from provider_adapters import (
    GeminiProviderAdapter,
    ProviderConfig,
    ProviderError,
    sanitize_secrets,
)
from question_quality_engine import (
    DeterministicVerifier,
    PDFExtractionEngine,
    QuestionQualityRubric,
    RubricConfig,
    SourceAnalyzer,
    analyze_source_material,
    compare_provider_runs,
    evaluate_question_set,
    extract_pdf_content,
    generate_evaluation_comparison_report,
    generate_questions,
    parse_extracted_text_input,
    validate_output_schema,
)


class TestQuestionQualityEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        generate_all_fixtures()
        cls.sample_pdf = Path("fixtures/icse_sample_science_history.pdf")
        cls.image_only_pdf = Path("fixtures/image_only_scan.pdf")

    # ------------------------------------------------------------------------
    # 1. PDF Text, Table, Figure & Coordinate Notation Extraction
    # ------------------------------------------------------------------------
    def test_01_pdf_text_and_structure_extraction(self) -> None:
        res = extract_pdf_content(self.sample_pdf)
        self.assertEqual(res.extraction_status, "ok")
        self.assertFalse(res.ocr_required)
        self.assertEqual(res.page_count, 3)

        # Page 1 headings, tables, and figures
        p1 = res.pages[0]
        self.assertEqual(p1.page_number, 1)
        self.assertTrue(any("ELECTROLYSIS" in h for h in p1.headings))
        self.assertGreaterEqual(len(p1.tables), 1)
        tbl1 = p1.tables[0]
        self.assertEqual(tbl1.page_number, 1)
        self.assertIn("Electrolyte", tbl1.headers)
        self.assertGreaterEqual(len(tbl1.rows), 2)

        # Verify coordinate-positioned subscript/superscript line from PDF stream
        self.assertIn("CuSO₄", p1.text)
        self.assertIn("Cu²⁺", p1.text)
        self.assertIn("SO₄²⁻", p1.text)

        # Verify Page 2 visual map figure detection
        p2 = res.pages[1]
        self.assertEqual(p2.page_number, 2)
        self.assertGreaterEqual(len(p2.figures), 1)
        self.assertTrue(any(f.is_visual_only for f in p2.figures))

    # ------------------------------------------------------------------------
    # 2. Empty or Unreadable PDFs
    # ------------------------------------------------------------------------
    def test_02_empty_and_unreadable_pdfs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_pdf = Path(tmpdir) / "empty.pdf"
            empty_pdf.write_bytes(b"")
            res_empty = extract_pdf_content(empty_pdf)
            self.assertEqual(res_empty.extraction_status, "empty")
            self.assertEqual(res_empty.page_count, 0)

            corrupt_pdf = Path(tmpdir) / "corrupt.pdf"
            corrupt_pdf.write_bytes(b"NOT_A_VALID_PDF_BINARY_HEADER")
            res_corrupt = extract_pdf_content(corrupt_pdf)
            self.assertEqual(res_corrupt.extraction_status, "unreadable")
            self.assertTrue(any("Invalid PDF header" in w for w in res_corrupt.warnings))

            missing_res = extract_pdf_content(Path(tmpdir) / "nonexistent.pdf")
            self.assertEqual(missing_res.extraction_status, "unreadable")

    # ------------------------------------------------------------------------
    # 3. Image-Only PDFs & OCR Requirement Reporting
    # ------------------------------------------------------------------------
    def test_03_image_only_pdf_and_ocr_warnings(self) -> None:
        res = extract_pdf_content(self.image_only_pdf)
        self.assertEqual(res.extraction_status, "ocr_required")
        self.assertTrue(res.ocr_required)
        self.assertIn("OCR", res.ocr_recommendation)

        # Running generate_questions on an image-only PDF must not silently fabricate questions
        gen = generate_questions(
            pdf_path=self.image_only_pdf,
            class_level=10,
            subject="Biology",
            question_count=4,
        )
        self.assertEqual(gen["status"], "ocr_required")
        self.assertEqual(len(gen["questions"]), 0)
        self.assertTrue(any("OCR" in w for w in gen["metadata"]["warnings"]))

    # ------------------------------------------------------------------------
    # 4. Page & Section Association + Extracted Text Input Mode
    # ------------------------------------------------------------------------
    def test_04_page_association_and_extracted_text_input(self) -> None:
        # Unpaginated text must preserve source_page = None (never invent page numbers)
        unpaginated_text = (
            "CHAPTER 4: TRANSPIRATION IN PLANTS\n"
            "Transpiration is defined as the loss of water in the form of water vapour from the aerial parts of a living plant.\n"
            "Lenticular transpiration occurs through minute openings called lenticels on the bark of woody stems, whereas cuticular transpiration takes place directly through the waxy cuticle."
        )
        out = generate_questions(
            extracted_text=unpaginated_text,
            class_level=10,
            subject="Biology",
            question_count=2,
            options={"provider": "deterministic"},
        )
        self.assertEqual(out["status"], "ok")
        self.assertEqual(len(out["questions"]), 2)
        for q in out["questions"]:
            self.assertIsNone(q["source_page"])

        # Paginated text markers `--- Page 7 ---` must associate with page 7
        paginated_text = (
            "--- Page 7 ---\n"
            "Archimedes' Principle states that when a body is immersed wholly or partially in a liquid at rest, it experiences an upthrust equal to the weight of the liquid displaced."
        )
        out_paged = generate_questions(
            extracted_text=paginated_text,
            class_level=9,
            subject="Physics",
            question_count=1,
            options={"provider": "deterministic"},
        )
        self.assertEqual(out_paged["questions"][0]["source_page"], 7)

    # ------------------------------------------------------------------------
    # 5. Scientific & Mathematical Notation Preservation
    # ------------------------------------------------------------------------
    def test_05_scientific_and_mathematical_notation_preservation(self) -> None:
        engine = PDFExtractionEngine()
        raw = (
            "Reaction: 2H2O(l) -> 2H2(g) + O2(g) and CuSO4(aq) <=> Cu^{2+}(aq) + SO4^{2-}(aq). "
            "Calculus: d/dx(x^n) = nx^{n-1} and acceleration g = 9.8 m/s^2."
        )
        norm = engine.normalize_scientific_notation(raw)
        self.assertIn("2H₂O(l) → 2H₂(g) + O₂(g)", norm)
        self.assertIn("CuSO₄(aq) ⇌ Cu²⁺(aq) + SO₄²⁻(aq)", norm)
        self.assertIn("nxⁿ⁻¹", norm)
        self.assertIn("m/s²", norm)

        items = engine.extract_notation_items(norm, page_number=1)
        kinds = {item.kind for item in items}
        self.assertIn("chemical_equation", kinds)
        self.assertIn("chemical_formula", kinds)
        self.assertIn("unit_quantity", kinds)

    # ------------------------------------------------------------------------
    # 6 & 7. Structured-Output Parsing & Malformed Field Rejection
    # ------------------------------------------------------------------------
    def test_06_schema_validation_and_malformed_fields(self) -> None:
        valid_rec = {
            "question_id": "q_01",
            "question": "What is Ohm's Law?",
            "answer": "Ohm's Law states that V = I × R at constant temperature.",
            "question_type": "recall",
            "difficulty": "easy",
            "learning_point": "Define Ohm's Law",
            "source_evidence": "Ohm's Law states that V = I × R.",
            "source_page": 1,
            "quality_scores": {"average_score": 4.5},
            "validation_status": "accepted",
            "review_notes": [],
        }
        self.assertEqual(validate_output_schema(valid_rec)["question_id"], "q_01")

        # Missing required field
        broken_rec = dict(valid_rec)
        del broken_rec["source_evidence"]
        with self.assertRaises(ValueError):
            validate_output_schema(broken_rec)

        # Invalid source_page type
        bad_page = dict(valid_rec, source_page="page_one")
        with self.assertRaises(ValueError):
            validate_output_schema(bad_page)

    # ------------------------------------------------------------------------
    # 8. Duplicate & Near-Duplicate Question Detection
    # ------------------------------------------------------------------------
    def test_07_duplicate_and_near_duplicate_detection(self) -> None:
        ext = extract_pdf_content(self.sample_pdf)
        rubric = QuestionQualityRubric(RubricConfig(max_similarity_threshold=0.55))

        q1 = {
            "question_id": "q_01",
            "question": "Define electrolysis as described in the chapter on electrical energy.",
            "answer": "Electrolysis is the chemical decomposition of an ionic compound in fused or aqueous state by direct electric current.",
            "question_type": "understanding",
            "difficulty": "easy",
            "learning_point": "Define electrolysis of ionic compounds",
            "source_evidence": "Electrolysis is defined as the chemical decomposition of an ionic compound (electrolyte) in fused or aqueous state by the passage of direct electric current.",
            "source_page": 1,
        }
        q2_near_dup = {
            "question_id": "q_02",
            "question": "What is meant by electrolysis according to the section on electrical energy?",
            "answer": "It is the chemical decomposition of an electrolyte by direct electric current.",
            "question_type": "recall",
            "difficulty": "easy",
            "learning_point": "Define electrolysis of ionic compounds",
            "source_evidence": "Electrolysis is defined as the chemical decomposition of an ionic compound (electrolyte) in fused or aqueous state by the passage of direct electric current.",
            "source_page": 1,
        }

        accepted, all_eval = rubric.evaluate_and_filter_set(
            [q1, q2_near_dup],
            extraction=ext,
            class_level=10,
            subject="Chemistry",
        )
        self.assertEqual(len(accepted), 1)
        self.assertEqual(all_eval[1]["validation_status"], "rejected")
        self.assertLessEqual(all_eval[1]["quality_scores"]["distinctness"], 2)

    # ------------------------------------------------------------------------
    # 9. Source Evidence Grounding, Metadata Date Trap & Unread Diagram Protection
    # ------------------------------------------------------------------------
    def test_08_source_evidence_metadata_trap_and_unread_diagram(self) -> None:
        ext = extract_pdf_content(self.sample_pdf)
        rubric = QuestionQualityRubric()

        # Case A: Fabricated / unsupported source evidence
        hallucinated = {
            "question_id": "q_bad_ev",
            "question": "Why did Napoleon invade Russia in 1812?",
            "answer": "Because Russia withdrew from the Continental System.",
            "question_type": "why_how",
            "difficulty": "medium",
            "learning_point": "Napoleonic Wars",
            "source_evidence": "Napoleon crossed the Niemen River in June 1812.",
            "source_page": 2,
        }
        scored_h = rubric.score_single_question(hallucinated, extraction=ext, class_level=10, subject="History")
        self.assertEqual(scored_h["validation_status"], "rejected")
        self.assertEqual(scored_h["quality_scores"]["source_fidelity"], 1)

        # Case B: Textbook publication / reprint date confused with historical date
        metadata_trap = {
            "question_id": "q_meta_date",
            "question": "What important historical event occurred in 2025 according to the textbook?",
            "answer": "The book was reprinted in 2025 by Curriculum Press Pvt Ltd.",
            "question_type": "recall",
            "difficulty": "easy",
            "learning_point": "Publication date of the textbook",
            "source_evidence": "First Published in 2022, Reprinted in 2025 by Curriculum Press Pvt Ltd. ISBN: 978-81-99999-01-2.",
            "source_page": 2,
        }
        scored_m = rubric.score_single_question(metadata_trap, extraction=ext, class_level=10, subject="History")
        self.assertEqual(scored_m["validation_status"], "rejected")
        self.assertEqual(scored_m["quality_scores"]["curriculum_relevance"], 1)

        # Case C: Claiming to read an unextracted visual map/diagram
        unread_map_q = {
            "question_id": "q_map_hallucination",
            "question": "Looking at the figure in Map 2.1, what is the exact isohyet contour line value drawn over Nagpur?",
            "answer": "The contour line drawn on the map over Nagpur reads 1125 mm.",
            "question_type": "interpretation",
            "difficulty": "hard",
            "learning_point": "Read contour lines on Map 2.1",
            "source_evidence": "Map 2.1: Isohyetal Distribution of Annual Rainfall Across the Indian Subcontinent",
            "source_page": 2,
        }
        scored_map = rubric.score_single_question(unread_map_q, extraction=ext, class_level=10, subject="Geography")
        self.assertEqual(scored_map["validation_status"], "rejected")
        self.assertEqual(scored_map["quality_scores"]["source_fidelity"], 1)

    # ------------------------------------------------------------------------
    # 10. Provider Timeout, Rate-Limit Retry & Secret Redaction
    # ------------------------------------------------------------------------
    def test_09_provider_timeout_retry_and_secret_sanitization(self) -> None:
        fake_secret = "AIzaSySecretKeyForTesting987654321"
        sanitized = sanitize_secrets(f"Request failed for url https://example.com?key={fake_secret}")
        self.assertNotIn(fake_secret, sanitized)
        self.assertIn("[REDACTED", sanitized)

        # Simulate 1 transient HTTP 429 rate-limit error followed by a valid JSON response
        call_count = 0

        def flaky_sender(req: urllib.request.Request, timeout: float) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", hdrs=None, fp=None)  # type: ignore
            mock_gemini_resp = {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        [
                                            {
                                                "question": "What is Ohm's Law?",
                                                "answer": "Potential difference V = I × R at constant temperature.",
                                                "question_type": "recall",
                                                "difficulty": "easy",
                                                "learning_point": "Ohm's Law relationship",
                                                "source_evidence": "Ohm's Law states that V = I * R.",
                                                "source_page": 1,
                                            }
                                        ]
                                    )
                                }
                            ]
                        }
                    }
                ]
            }
            return json.dumps(mock_gemini_resp).encode("utf-8")

        adapter = GeminiProviderAdapter(
            ProviderConfig(provider="gemini", model="gemini-3.8-flash", timeout_seconds=5.0, max_retries=2, backoff_base_seconds=0.01),
            api_key=fake_secret,
            http_sender=flaky_sender,
            sleep_fn=lambda _: None,
        )
        cands = adapter.generate_candidates(
            learning_points=[{"id": "lp_1", "topic": "Physics", "summary": "Ohm's Law", "source_evidence": "V = I * R", "source_page": 1}],
            class_level=10,
            subject="Physics",
            question_count=1,
            planned_types=["recall"],
        )
        self.assertEqual(call_count, 2)
        self.assertEqual(len(cands), 1)

        # Simulate persistent timeout exceeding max_retries
        def always_timeout(req: urllib.request.Request, timeout: float) -> bytes:
            raise TimeoutError(f"Timed out connecting with key={fake_secret}")

        failing_adapter = GeminiProviderAdapter(
            ProviderConfig(provider="gemini", model="gemini-3.8-flash", timeout_seconds=1.0, max_retries=1, backoff_base_seconds=0.01),
            api_key=fake_secret,
            http_sender=always_timeout,
            sleep_fn=lambda _: None,
        )
        with self.assertRaises(ProviderError) as ctx:
            failing_adapter.generate_candidates(
                learning_points=[{"id": "lp_1", "topic": "Physics", "summary": "Ohm's Law", "source_evidence": "V = I * R", "source_page": 1}],
                class_level=10,
                subject="Physics",
                question_count=1,
                planned_types=["recall"],
            )
        self.assertEqual(ctx.exception.attempts, 2)
        self.assertNotIn(fake_secret, str(ctx.exception))

    # ------------------------------------------------------------------------
    # 11 & 12. Deterministic Numerical & Chemical Verification + JSON Serialization
    # ------------------------------------------------------------------------
    def test_10_deterministic_math_and_chemical_verification(self) -> None:
        # Balanced chemical equation check
        bal_ok = DeterministicVerifier.check_chemical_equation_balance("2H₂O(l) → 2H₂(g) + O₂(g)")
        self.assertTrue(bal_ok["balanced"])
        self.assertEqual(bal_ok["lhs_atoms"], {"H": 4, "O": 2})

        # Unbalanced chemical equation check
        bal_bad = DeterministicVerifier.check_chemical_equation_balance("H₂O(l) → 2H₂(g) + O₂(g)")
        self.assertFalse(bal_bad["balanced"])

        # Numerical verification catches wrong LLM calculation
        wrong_math = DeterministicVerifier.verify_numerical_answer(
            "Calculate V when I = 2.5 A and R = 12 Ω.",
            "Using V = I × R, V = 2.5 × 12 = 35 V.",
            {"formula": "I * R", "variables": {"I": 2.5, "R": 12.0}, "expected_value": 30.0},
        )
        self.assertFalse(wrong_math["verified"])

        # Numerical verification passes accurate calculation
        right_math = DeterministicVerifier.verify_numerical_answer(
            "Calculate V when I = 2.5 A and R = 12 Ω.",
            "Using V = I × R, V = 2.5 × 12 = 30 V.",
            {"formula": "I * R", "variables": {"I": 2.5, "R": 12.0}, "expected_value": 30.0},
        )
        self.assertTrue(right_math["verified"])

    # ------------------------------------------------------------------------
    # 13. End-to-End Grade Adaptation (Class 8–10 vs Class 11–12) & Rubric Config
    # ------------------------------------------------------------------------
    def test_11_end_to_end_generation_and_rubric_configuration(self) -> None:
        res_10 = generate_questions(
            pdf_path=self.sample_pdf,
            class_level=10,
            subject="Chemistry & Physics",
            question_count=5,
            options={"provider": "deterministic"},
        )
        self.assertEqual(res_10["status"], "ok")
        self.assertEqual(len(res_10["questions"]), 5)
        self.assertGreaterEqual(res_10["evaluation"]["valid_source_evidence_pct"], 80.0)

        # Ensure full output is strictly JSON serializable
        serialized = json.dumps(res_10, ensure_ascii=False)
        self.assertGreater(len(serialized), 500)

        # Test stricter custom RubricConfig threshold filtering
        strict_res = generate_questions(
            pdf_path=self.sample_pdf,
            class_level=12,
            subject="Mathematics",
            question_count=4,
            options={
                "provider": "deterministic",
                "rubric_config": {
                    "min_criterion_score": 4,
                    "min_average_score": 4.2,
                },
            },
        )
        for q in strict_res["questions"]:
            self.assertGreaterEqual(q["quality_scores"]["average_score"], 4.2)

    # ------------------------------------------------------------------------
    # 14. Regression Fixture: "The Making of the Indian Constitution — History & Civics | Standard 8"
    # ------------------------------------------------------------------------
    def test_12_indian_constitution_pdf_extraction_and_generation(self) -> None:
        constitution_pdf = Path("public/assets/aistudio/indian_constitution_history_lesson_0b1adbb9.pdf")
        if not constitution_pdf.exists():
            self.skipTest("Attached Indian Constitution PDF not present in workspace.")

        ext = extract_pdf_content(constitution_pdf)
        self.assertEqual(ext.extraction_status, "ok")
        self.assertFalse(ext.ocr_required)
        self.assertEqual(ext.page_count, 1)
        self.assertIn("The Making of the Indian Constitution", ext.full_text)
        self.assertIn("Dr. B. R. Ambedkar", ext.full_text)
        self.assertIn("26 November 1949", ext.full_text)
        self.assertIn("26 January 1950", ext.full_text)

        gen = generate_questions(
            pdf_path=constitution_pdf,
            class_level=8,
            subject="History & Civics",
            question_count=6,
            options={"provider": "deterministic"},
        )
        self.assertEqual(gen["status"], "ok")
        self.assertEqual(len(gen["questions"]), 6)
        self.assertEqual(gen["evaluation"]["valid_source_evidence_pct"], 100.0)
        self.assertGreaterEqual(gen["evaluation"]["distinct_question_types"], 5)

        # Verify all 8 core facts from the lesson are covered across the generated question-answer set
        combined_qa = " ".join(f"{q['question']} {q['answer']}" for q in gen["questions"])
        self.assertIn("15 August 1947", combined_qa)
        self.assertIn("powers of the government", combined_qa.lower().replace("powers of government", "powers of the government"))
        self.assertIn("9 December 1946", combined_qa)
        self.assertIn("Dr. Rajendra Prasad", combined_qa)
        self.assertIn("permanent President", combined_qa)
        self.assertIn("Dr. B. R. Ambedkar", combined_qa)
        self.assertIn("Drafting Committee", combined_qa)
        self.assertIn("26 November 1949", combined_qa)
        self.assertIn("26 January 1950", combined_qa)
        for ideal in ("justice", "liberty", "equality", "fraternity"):
            self.assertIn(ideal, combined_qa.lower())

        # Verify explicit distinction between adoption (26 November 1949) and commencement (26 January 1950)
        adoption_vs_commencement = [
            q for q in gen["questions"]
            if "26 November 1949" in q["question"] and "26 January 1950" in q["question"]
        ]
        self.assertGreaterEqual(len(adoption_vs_commencement), 1)
        self.assertIn("adopted", adoption_vs_commencement[0]["answer"].lower())
        self.assertIn("effect", adoption_vs_commencement[0]["answer"].lower())

        # Verify ZERO outside historical details not present in the one-page lesson PDF
        forbidden_outside_phrases = (
            "british rule",
            "three years",
            "299 members",
            "cabinet mission",
            "jawaharlal nehru",
            "objectives resolution",
            "mountbatten",
        )
        for phrase in forbidden_outside_phrases:
            self.assertNotIn(phrase, combined_qa.lower(), f"Outside historical phrase '{phrase}' leaked into output!")

        # Verify every item has structured source_reference, validation_results, and clean student_worksheet
        self.assertIn("student_worksheet", gen)
        self.assertEqual(gen["student_worksheet"]["total_questions"], 6)
        for ws_item in gen["student_worksheet"]["questions"]:
            self.assertNotIn("quality_scores", ws_item)
            self.assertNotIn("validation_results", ws_item)

        for q in gen["questions"]:
            self.assertEqual(q["source_page"], 1)
            self.assertIn(q["validation_status"], ("accepted", "revised"))
            self.assertEqual(q["review_status"], "accepted")
            self.assertTrue(q["validation_results"]["source_grounding_pass"])
            self.assertTrue(q["validation_results"]["answer_support_pass"])
            self.assertTrue(q["validation_results"]["answer_alignment_pass"])
            self.assertTrue(q["validation_results"]["clarity_pass"])
            self.assertEqual(q["validation_results"]["ungrounded_claims"], [])
            self.assertIsInstance(q["source_reference"], dict)
            self.assertEqual(q["source_reference"]["page_number"], 1)
            self.assertTrue(q["source_reference"]["supporting_text"])

    # ------------------------------------------------------------------------
    # 15. Science Passage with Formulas and Chemical Equations
    # ------------------------------------------------------------------------
    def test_13_science_passage_with_formulas_and_equations(self) -> None:
        sci_passage = (
            "CHAPTER 5: OHM'S LAW AND WATER ELECTROLYSIS\n"
            "Ohm's Law states that the potential difference V across the ends of a metallic conductor is directly proportional "
            "to the current I flowing through it, provided temperature remains constant: V = I * R.\n"
            "During the electrolysis of acidified water using platinum electrodes, water decomposes according to the balanced "
            "chemical equation 2H2O(l) -> 2H2(g) + O2(g)."
        )
        gen = generate_questions(
            extracted_text=sci_passage,
            class_level=10,
            subject="Physics & Chemistry",
            question_count=2,
            options={"provider": "deterministic"},
        )
        self.assertEqual(gen["status"], "ok")
        self.assertEqual(len(gen["questions"]), 2)
        combined = " ".join(q["question"] + " " + q["answer"] for q in gen["questions"])
        self.assertIn("V = I × R", combined)
        self.assertTrue(any(q["validation_results"]["answer_support_pass"] for q in gen["questions"]))

    # ------------------------------------------------------------------------
    # 16. Passage with Dates and Named People
    # ------------------------------------------------------------------------
    def test_14_passage_with_dates_and_named_people(self) -> None:
        history_passage = (
            "CHAPTER 2: THE REVOLT OF 1857\n"
            "The Doctrine of Lapse was an annexation policy applied by Lord Dalhousie, which stated that if an Indian ruler "
            "of a dependent state died without a natural male heir, the kingdom would lapse to the British East India Company.\n"
            "First, on 29 March 1857 at Barrackpore, Mangal Pandey defied British officers; second, on 10 May 1857, sepoys "
            "at Meerut broke into open revolt and marched to Delhi; subsequently, Bahadur Shah Zafar was proclaimed Emperor."
        )
        gen = generate_questions(
            extracted_text=history_passage,
            class_level=10,
            subject="History & Civics",
            question_count=2,
            options={"provider": "deterministic"},
        )
        self.assertEqual(gen["status"], "ok")
        self.assertEqual(len(gen["questions"]), 2)
        combined = " ".join(q["question"] + " " + q["answer"] for q in gen["questions"])
        self.assertIn("Lord Dalhousie", combined)
        self.assertIn("1857", combined)
        for q in gen["questions"]:
            self.assertTrue(q["validation_results"]["source_grounding_pass"])
            self.assertTrue(q["validation_results"]["answer_support_pass"])

    # ------------------------------------------------------------------------
    # 17. Short Passage Insufficient for Requested Question Count
    # ------------------------------------------------------------------------
    def test_15_short_passage_insufficient_for_requested_count(self) -> None:
        short_passage = (
            " Boyle's Law states that at constant temperature, the volume of a fixed mass of dry gas is inversely "
            "proportional to its pressure."
        )
        gen = generate_questions(
            extracted_text=short_passage,
            class_level=9,
            subject="Chemistry",
            question_count=5,
            options={"provider": "deterministic"},
        )
        self.assertEqual(gen["status"], "partial")
        self.assertEqual(len(gen["questions"]), 1)
        self.assertTrue(any("only supports 1" in w for w in gen["metadata"]["warnings"]))
        self.assertTrue(gen["questions"][0]["validation_results"]["source_grounding_pass"])

    # ------------------------------------------------------------------------
    # 18. Malformed or Incomplete Extracted Text
    # ------------------------------------------------------------------------
    def test_16_malformed_or_incomplete_extracted_text(self) -> None:
        malformed_text = "   ... ??? ###   \n  ISBN: 978-81-0000-000-1  \n  Reprint 2025-26 "
        gen = generate_questions(
            extracted_text=malformed_text,
            class_level=8,
            subject="History",
            question_count=3,
            options={"provider": "deterministic"},
        )
        self.assertIn(gen["status"], ("empty_source", "empty"))
        self.assertEqual(len(gen["questions"]), 0)

    # ------------------------------------------------------------------------
    # 19. Deliberate Unsupported-Answer & Outside-Knowledge Rejection Test
    # ------------------------------------------------------------------------
    def test_17_unsupported_answer_and_outside_knowledge_rejection(self) -> None:
        constitution_text = (
            "The Making of the Indian Constitution\n"
            "When India became independent on 15 August 1947, it needed fundamental rules to govern the country.\n"
            "The Constituent Assembly was formed to prepare India's Constitution. The Assembly first met on 9 December 1946. "
            "Dr. Rajendra Prasad was elected its permanent President. Dr. B. R. Ambedkar chaired the Drafting Committee.\n"
            "The Constituent Assembly adopted the Constitution on 26 November 1949. It came into effect on 26 January 1950, when India became a republic."
        )
        ext = parse_extracted_text_input(constitution_text)
        rubric = QuestionQualityRubric()

        # Candidate 1: Plausible outside fact ("299 members", "Jawaharlal Nehru", "1948") not in PDF
        outside_fact_cand = {
            "question_id": "q_outside_1",
            "question": "How many members signed the Constitution after Jawaharlal Nehru moved the Objectives Resolution?",
            "answer": "The Constituent Assembly had 299 members who completed the draft in 1948 after Jawaharlal Nehru moved the Objectives Resolution.",
            "question_type": "recall",
            "difficulty": "medium",
            "learning_point": "Membership of the Constituent Assembly",
            "source_evidence": "The Constituent Assembly was formed to prepare India's Constitution.",
            "source_page": None,
        }
        scored_1 = rubric.score_single_question(
            outside_fact_cand, extraction=ext, class_level=8, subject="History & Civics", allow_external_knowledge=False
        )
        self.assertEqual(scored_1["validation_status"], "rejected")
        self.assertEqual(scored_1["review_status"], "rejected")
        self.assertFalse(scored_1["validation_results"]["source_grounding_pass"])
        self.assertFalse(scored_1["validation_results"]["answer_support_pass"])
        self.assertGreater(len(scored_1["validation_results"]["ungrounded_claims"]), 0)

        # Candidate 2: Question is grounded in the PDF, but the answer sneaks in outside knowledge ("from British rule", "nearly three years")
        outside_answer_cand = {
            "question_id": "q_outside_2",
            "question": "When was the Constitution of India adopted and when did it come into effect?",
            "answer": "After gaining freedom from British rule and working for nearly three years and eleven months, the Constitution was adopted on 26 November 1949 and came into effect on 26 January 1950.",
            "question_type": "recall",
            "difficulty": "easy",
            "learning_point": "Adoption and commencement dates of the Constitution",
            "source_evidence": "The Constituent Assembly adopted the Constitution on 26 November 1949. It came into effect on 26 January 1950, when India became a republic.",
            "source_page": None,
        }
        scored_2 = rubric.score_single_question(
            outside_answer_cand, extraction=ext, class_level=8, subject="History & Civics", allow_external_knowledge=False
        )
        self.assertEqual(scored_2["validation_status"], "rejected")
        self.assertFalse(scored_2["validation_results"]["answer_support_pass"])
        self.assertTrue(any("British" in c for c in scored_2["validation_results"]["ungrounded_claims"]))

    # ------------------------------------------------------------------------
    # 20. Question-Answer Mismatch Detection Test
    # ------------------------------------------------------------------------
    def test_18_question_answer_mismatch_detection(self) -> None:
        constitution_text = (
            "The Constituent Assembly was formed to prepare India's Constitution. The Assembly first met on 9 December 1946. "
            "Dr. Rajendra Prasad was elected its permanent President. Dr. B. R. Ambedkar chaired the Drafting Committee, which prepared the draft Constitution. "
            "The Constituent Assembly adopted the Constitution on 26 November 1949. It came into effect on 26 January 1950, when India became a republic."
        )
        ext = parse_extracted_text_input(constitution_text)
        rubric = QuestionQualityRubric()

        # Case A: Question asks "When", answer gives a person's role without a date
        when_mismatch = {
            "question_id": "q_mismatch_when",
            "question": "When did the Constituent Assembly hold its first meeting?",
            "answer": "Dr. Rajendra Prasad was elected its permanent President and Dr. B. R. Ambedkar chaired the Drafting Committee.",
            "question_type": "recall",
            "difficulty": "easy",
            "learning_point": "First meeting of the Constituent Assembly",
            "source_evidence": "The Assembly first met on 9 December 1946. Dr. Rajendra Prasad was elected its permanent President.",
            "source_page": None,
        }
        scored_when = rubric.score_single_question(when_mismatch, extraction=ext, class_level=8, subject="History & Civics")
        self.assertEqual(scored_when["validation_status"], "rejected")
        self.assertFalse(scored_when["validation_results"]["answer_alignment_pass"])

        # Case B: Question asks about Dr. B. R. Ambedkar, answer only talks about 26 January 1950
        entity_mismatch = {
            "question_id": "q_mismatch_entity",
            "question": "What role did Dr. B. R. Ambedkar play in preparing the Constitution?",
            "answer": "The Constituent Assembly adopted the Constitution on 26 November 1949 and it came into effect on 26 January 1950.",
            "question_type": "recall",
            "difficulty": "easy",
            "learning_point": "Role of Dr. B. R. Ambedkar",
            "source_evidence": "Dr. B. R. Ambedkar chaired the Drafting Committee, which prepared the draft Constitution.",
            "source_page": None,
        }
        scored_entity = rubric.score_single_question(entity_mismatch, extraction=ext, class_level=8, subject="History & Civics")
        self.assertEqual(scored_entity["validation_status"], "rejected")
        self.assertFalse(scored_entity["validation_results"]["answer_alignment_pass"])

    # ------------------------------------------------------------------------
    # 21. Complex Textbook PDF Extraction & Before-vs-After Evaluation Report
    # ------------------------------------------------------------------------
    def test_19_complex_textbook_pdf_and_evaluation_comparison_report(self) -> None:
        report = generate_evaluation_comparison_report()
        self.assertEqual(report["after_fine_tuning"]["strict_pdf_grounding_pass_pct"], 100.0)
        self.assertEqual(report["after_fine_tuning"]["outside_knowledge_leak_count"], 0)
        self.assertGreater(
            report["after_fine_tuning"]["acceptance_rate_pct"],
            report["before_fine_tuning"]["acceptance_rate_pct"],
        )

        # Verify complex InDesign PDF 1.6 textbook extraction if present in workspace
        hees102_pdf = Path("public/assets/aistudio/hees102_e95194ff.pdf")
        if hees102_pdf.exists():
            ext_book = extract_pdf_content(hees102_pdf)
            self.assertEqual(ext_book.extraction_status, "ok")
            self.assertGreater(ext_book.page_count, 10)
            self.assertIn("Maratha", ext_book.full_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
