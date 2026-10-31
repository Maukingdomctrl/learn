"""
Generates genuine curriculum PDF fixtures, image-only scan PDF fixtures,
text passage fixtures, and sample structured JSON output in `fixtures/`.
"""

from __future__ import annotations

import json
from pathlib import Path
import zlib

from question_quality_engine import (
    generate_evaluation_comparison_report,
    generate_questions,
)


def _escape_pdf_literal(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def build_multi_page_pdf(pages_streams: list[bytes], include_image_on_pages: set[int] | None = None) -> bytes:
    """
    Construct a valid PDF 1.4 binary document with FlateDecode compressed content streams,
    Helvetica font resource, and optional `/Subtype /Image` XObjects.
    """
    img_pages = include_image_on_pages or set()
    objects: list[bytes] = []

    def add_obj(body: bytes) -> int:
        obj_id = len(objects) + 1
        objects.append(body)
        return obj_id

    # Object 1: Catalog (placeholder updated after Pages is created)
    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    # Object 2: Pages root (placeholder updated after pages are added)
    add_obj(b"<< /Type /Pages /Kids [] /Count 0 >>")
    # Object 3: Font
    font_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")

    # Optional 1x1 grayscale Image XObject for testing image/figure/OCR detection
    img_raw = zlib.compress(b"\xff")
    img_obj_id = add_obj(
        f"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode /Length {len(img_raw)} >>\nstream\n".encode("ascii")
        + img_raw
        + b"\nendstream"
    )

    page_obj_ids: list[int] = []
    for idx, raw_stream in enumerate(pages_streams):
        comp = zlib.compress(raw_stream)
        content_id = add_obj(
            f"<< /Filter /FlateDecode /Length {len(comp)} >>\nstream\n".encode("ascii")
            + comp
            + b"\nendstream"
        )
        if (idx + 1) in img_pages:
            res_dict = f"<< /Font << /F1 {font_id} 0 R >> /XObject << /Im1 {img_obj_id} 0 R >> >>"
        else:
            res_dict = f"<< /Font << /F1 {font_id} 0 R >> >>"

        page_id = add_obj(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources {res_dict} /Contents {content_id} 0 R >>".encode("ascii")
        )
        page_obj_ids.append(page_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"<< /Type /Pages /Kids [ {kids_str} ] /Count {len(page_obj_ids)} >>".encode("ascii")

    # Assemble PDF with xref table
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = [0]
    for idx, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("ascii"))
        out.extend(body)
        out.extend(b"\nendobj\n")

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


def _lines_to_pdf_stream(lines: list[str], *, include_sub_sup_demo: bool = False) -> bytes:
    """
    Convert lines of text into a PDF `BT ... ET` stream.
    When `include_sub_sup_demo=True`, also emits a coordinate-positioned chemical formula
    using explicit vertical baseline shifts (`Td` dy=-2.5 and dy=+2.5 with smaller `Tf`)
    so the coordinate-aware subscript/superscript reconstruction is exercised on real PDF ops.
    """
    ops: list[str] = ["BT", "/F1 11 Tf"]
    y = 790.0
    for line in lines:
        safe = _escape_pdf_literal(line)
        ops.append(f"1 0 0 1 45 {y:.1f} Tm")
        ops.append(f"({safe}) Tj")
        y -= 16.0

    if include_sub_sup_demo:
        # Emit a line with real PDF baseline shifts: "Coordinate Ion Check: SO" + sub "4" + sup "2-"
        ops.append(f"1 0 0 1 45 {y:.1f} Tm")
        ops.append("/F1 11 Tf (Coordinate Ion Check: CuSO) Tj")
        ops.append("/F1 8 Tf 95 -2.5 Td (4) Tj")
        ops.append("/F1 11 Tf 12 2.5 Td ( dissociates into Cu) Tj")
        ops.append("/F1 8 Tf 85 3.0 Td (2+) Tj")
        ops.append("/F1 11 Tf 15 -3.0 Td ( and SO) Tj")
        ops.append("/F1 8 Tf 35 -2.5 Td (4) Tj")
        ops.append("/F1 8 Tf 6 5.5 Td (2-) Tj")

    ops.append("ET")
    return "\n".join(ops).encode("latin-1", errors="ignore")


def generate_all_fixtures() -> None:
    fixtures_dir = Path("fixtures")
    fixtures_dir.mkdir(exist_ok=True)

    # Page 1: ICSE Class 10 Chemistry & Physics
    page1_lines = [
        "CHAPTER 1: ELECTROLYSIS AND ELECTRICAL ENERGY",
        "",
        "Electrolysis is defined as the chemical decomposition of an ionic compound (electrolyte) in fused or aqueous state by the passage of direct electric current.",
        "During the electrolysis of acidified water using platinum electrodes, water decomposes according to the balanced chemical equation 2H2O(l) -> 2H2(g) + O2(g).",
        "In aqueous copper(II) sulphate solution, CuSO4(aq) <=> Cu^{2+}(aq) + SO4^{2-}(aq), where positively charged Cu^{2+} cations migrate to the cathode and gain electrons.",
        "",
        "Table 1.1: Comparison of Strong and Weak Electrolytes",
        "| Electrolyte | Degree of Dissociation | Major Conducting Particles | Electrical Conductivity |",
        "| --- | --- | --- | --- |",
        "| Dilute H2SO4(aq) | Complete (nearly 100%) | Free mobile ions (H+ and SO4^{2-}) | High conductivity |",
        "| Acetic Acid CH3COOH(aq) | Partial (< 5%) | Mostly unionized molecules and few ions | Low conductivity |",
        "",
        "Ohm's Law states that the potential difference V across the ends of a metallic conductor is directly proportional to the current I flowing through it, provided temperature remains constant: V = I * R.",
        "Joule's Law of Heating states that the heat energy H produced in a resistor of resistance R carrying current I for time t is given by the equation H = I^2Rt.",
        "Fig. 1.1: Hoffman Voltameter apparatus for electrolysis of acidified water (Labels: Anode, Cathode, Graduated collecting limbs)",
    ]

    # Page 2: ICSE Class 10 History & Geography
    page2_lines = [
        "CHAPTER 2: THE FIRST WAR OF INDEPENDENCE (1857) AND INDIAN MONSOON",
        "",
        "The Doctrine of Lapse was an annexation policy applied by Lord Dalhousie, which stated that if an Indian ruler of a dependent state died without a natural male heir, the kingdom would lapse to the British East India Company.",
        "The immediate cause of the Revolt of 1857 was the introduction of the Enfield rifle, whose cartridges were greased with beef and pork fat that soldiers had to bite off before loading.",
        "First, on 29 March 1857 at Barrackpore, Mangal Pandey defied British officers; second, on 10 May 1857, sepoys at Meerut broke into open revolt and marched to Delhi; subsequently, Bahadur Shah Zafar was proclaimed Emperor.",
        "Whereas the Early Nationalists relied on constitutional petitions, prayers, and memoranda, in contrast the Assertive Nationalists advocated Swadeshi, Boycott, and National Education.",
        "",
        "Table 2.1: Comparison of Arabian Sea Branch and Bay of Bengal Branch",
        "| Monsoon Branch | Primary Windward Barrier | Relative Moisture Content | Major Rainfall Region |",
        "| --- | --- | --- | --- |",
        "| Arabian Sea Branch | Western Ghats | Very high moisture | Western Coastal Plains and Mumbai |",
        "| Bay of Bengal Branch | Garo-Khasi-Jaintia Hills | Moderate-high channeled moisture | Mawsynram, Cherrapunji, and Ganga Plains |",
        "",
        "Map 2.1: Isohyetal Distribution of Annual Rainfall Across the Indian Subcontinent",
        "First Published in 2022, Reprinted in 2025 by Curriculum Press Pvt Ltd. ISBN: 978-81-99999-01-2. Copyright (c) 2025 All rights reserved.",
    ]

    # Page 3: ICSE Class 12 Mathematics & Biology
    page3_lines = [
        "CHAPTER 3: DIFFERENTIAL CALCULUS AND CELLULAR RESPIRATION",
        "",
        "The Fundamental Power Rule of Differentiation states that for any real exponent n, the derivative of f(x) = x^n with respect to x is given by d/dx(x^n) = nx^{n-1}.",
        "Aerobic cellular respiration is the catabolic process by which glucose is completely oxidized in the presence of oxygen according to C6H12O6 + 6O2 -> 6CO2 + 6H2O + 38ATP.",
        "The Bohr Effect refers to the physiological phenomenon whereby an increase in carbon dioxide partial pressure (pCO2) and hydrogen ion concentration (lower pH) decreases the oxygen affinity of hemoglobin, shifting the oxygen dissociation curve to the right.",
        "Consequently, actively respiring tissues with elevated CO2 and lower pH trigger enhanced unloading of O2 from oxyhemoglobin (HbO2) to meet metabolic demand.",
    ]

    pdf_bytes = build_multi_page_pdf(
        [
            _lines_to_pdf_stream(page1_lines, include_sub_sup_demo=True),
            _lines_to_pdf_stream(page2_lines),
            _lines_to_pdf_stream(page3_lines),
        ],
        include_image_on_pages={1, 2},
    )
    sample_pdf_path = fixtures_dir / "icse_sample_science_history.pdf"
    sample_pdf_path.write_bytes(pdf_bytes)

    # Fixture 2: Image-only scanned PDF (contains `/Im1 Do` image operator and 0 text)
    image_only_stream = b"q 500 0 0 700 45 70 cm /Im1 Do Q"
    image_only_pdf = build_multi_page_pdf([image_only_stream, image_only_stream], include_image_on_pages={1, 2})
    (fixtures_dir / "image_only_scan.pdf").write_bytes(image_only_pdf)

    # Fixture 3: Representative text passages JSON
    text_passages = {
        "description": "Representative ICSE Classes 8-12 curriculum passages for evaluation and testing.",
        "passages": [
            {
                "id": "icse_10_chemistry_electrolysis",
                "class_level": 10,
                "subject": "Chemistry",
                "title": "Electrolysis and Ohm's Law (Class 10)",
                "text": "\n".join(page1_lines),
            },
            {
                "id": "icse_10_history_geography",
                "class_level": 10,
                "subject": "History & Civics",
                "title": "First War of Independence 1857 & Indian Monsoon (Class 10)",
                "text": "\n".join(page2_lines),
            },
            {
                "id": "icse_12_math_biology",
                "class_level": 12,
                "subject": "Mathematics",
                "title": "Differential Calculus & Cellular Respiration (Class 12)",
                "text": "\n".join(page3_lines),
            },
        ],
    }
    (fixtures_dir / "icse_text_passages.json").write_text(
        json.dumps(text_passages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Fixture 4: Generate sample validated output from the real sample PDF
    sample_output = generate_questions(
        pdf_path=sample_pdf_path,
        class_level=10,
        subject="Chemistry & Physics",
        question_count=6,
        options={"provider": "deterministic", "include_rejected": True},
    )
    (fixtures_dir / "sample_output.json").write_text(
        json.dumps(sample_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Fixture 5: Generate validated questions from the attached ICSE Class 8 History & Civics PDF
    constitution_pdf_path = Path("public/assets/aistudio/indian_constitution_history_lesson_0b1adbb9.pdf")
    if constitution_pdf_path.exists():
        constitution_output = generate_questions(
            pdf_path=constitution_pdf_path,
            class_level=8,
            subject="History & Civics",
            question_count=7,
            options={"provider": "deterministic", "include_rejected": True},
        )
        (fixtures_dir / "indian_constitution_output.json").write_text(
            json.dumps(constitution_output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Fixture 6: Generate before-vs-after evaluation comparison report
    comparison_report = generate_evaluation_comparison_report()
    (fixtures_dir / "evaluation_comparison_report.json").write_text(
        json.dumps(comparison_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    generate_all_fixtures()
    print("Generated all fixtures in fixtures/ successfully.")
