"""Synthetic test fixtures.

SAMPLE_PDF_PARAGRAPHS is a short, made-up curriculum page written for automated tests only. It is NOT the
curriculum PDF the methodology was tested against, and results on it say nothing about lesson quality.
SAMPLE_LESSON is a hand-written lesson grounded in that synthetic PDF, used to exercise rendering and checks.
"""

import pymupdf

SAMPLE_PDF_PAGES = [
    [
        "Chapter 9: Perimeter and Area",
        "9.1 Area of a Triangle. The area of a figure is the amount of surface it covers. Area is measured in "
        "square units such as square centimetres (cm²).",
        "Any side of a triangle can be taken as its base. The height is the perpendicular distance from the "
        "opposite vertex to the base.",
        "The area of a triangle is half the product of its base and its height. "
        "Area of a triangle = 1/2 × base × height.",
        "Example 1: Find the area of a triangle with base 8 cm and height 5 cm. Solution: Area = 1/2 × base × "
        "height = 1/2 × 8 × 5 = 20 cm².",
        "Example 2: The area of a triangle is 24 cm² and its base is 6 cm. Find its height. Solution: "
        "24 = 1/2 × 6 × height, so 24 = 3 × height and height = 24 ÷ 3 = 8 cm.",
        "A triangle is half of a rectangle with the same base and height. That is why we take half of base × height.",
    ],
    [
        "Remember: the base and the height must be in the same unit. Area is always written in square units.",
        "Exercise 9.1: 1. Find the area of a triangle with base 10 cm and height 6 cm. 2. Find the area of a "
        "triangle with base 12 m and height 7 m. 3. A triangle has area 18 cm² and base 6 cm. Find its height.",
    ],
]


def make_sample_pdf(path: str, pages=None) -> str:
    doc = pymupdf.open()
    for paragraphs in pages or SAMPLE_PDF_PAGES:
        page = doc.new_page(width=595, height=842)
        y = 60
        for para in paragraphs:
            rect = pymupdf.Rect(60, y, 535, y + 120)
            page.insert_textbox(rect, para, fontsize=11, fontname="helv")
            y += 30 + 14 * (len(para) // 80 + 1)
    doc.save(path)
    return path


def make_scanned_pdf(path: str) -> str:
    """A page with no text layer (an image only), to exercise the OCR path."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 100), False)
    pix.clear_with(200)
    page.insert_image(pymupdf.Rect(60, 60, 260, 160), pixmap=pix)
    doc.save(path)
    return path


SAMPLE_LESSON = {
    "standard": 7,
    "title": "Area of a Triangle",
    "scope_line": "Today: how to find the area of a triangle from its base and height",
    "concepts": [{"name": "Area of a triangle", "source_unit_ids": ["SRC-P1-U3"]}],
    "core_claims": [
        {
            "text": "Area is the amount of surface a figure covers, measured in square units.",
            "source_unit_ids": ["SRC-P1-U1"],
        },
        {
            "text": "Any side can be the base; the height is the perpendicular distance from the opposite vertex.",
            "source_unit_ids": ["SRC-P1-U2"],
        },
        {"text": "Area of a triangle = 1/2 x base x height.", "source_unit_ids": ["SRC-P1-U3"]},
        {"text": "A triangle is half of a rectangle with the same base and height.", "source_unit_ids": ["SRC-P1-U6"]},
    ],
    "terms": [
        {"term": "base", "definition": "the side of the triangle we measure from", "source_unit_ids": ["SRC-P1-U2"]},
        {
            "term": "height",
            "definition": "the perpendicular distance from the opposite vertex to the base",
            "source_unit_ids": ["SRC-P1-U2"],
        },
    ],
    "stages": [
        {
            "stage": "Discover",
            "activity_type": "CHOOSE",
            "hook": "A boat's sail is a triangle with base 8 m and height 5 m. How much cloth covers it?",
            "instruction": "Circle the answer you predict.",
            "body_text": "Area is the surface a shape covers. We measure it in square units, like cm². Any "
            "side of a triangle can be its base. The height is the straight-up distance from "
            "the opposite vertex (corner) to the base, meeting it at a right angle. A triangle "
            "is half of a rectangle with the same base and height. So the rule is: area of a "
            "triangle = 1/2 × base × height.",
            "worked_example": [
                "Find the area of a triangle with base 8 cm and height 5 cm.",
                "Area = 1/2 × base × height",
                "= 1/2 × 8 × 5",
                "= 20 cm²",
            ],
            "visuals": [
                {
                    "kind": "shape",
                    "caption": "The triangle in the worked example",
                    "purpose": "See that the height is perpendicular to the base, from the opposite vertex.",
                    "shape": "triangle",
                    "base": 8,
                    "height": 5,
                    "unit": "cm",
                    "source_unit_ids": ["SRC-P1-U2", "SRC-P1-U4"],
                }
            ],
            "items": [
                {"number": 1, "prompt": "How much cloth covers the sail?", "options": ["13 m²", "20 m²", "40 m²"]},
                {
                    "number": 2,
                    "prompt": "In the worked example, which measurement is the height?",
                    "options": ["8 cm", "5 cm", "20 cm²"],
                },
            ],
        },
        {
            "stage": "Reinforce",
            "activity_type": "FILL_IN",
            "instruction": "Fill each blank with a word from the word bank.",
            "body_text": "Use each word at most once. Some words are not needed.",
            "word_bank": ["base", "height", "half", "square", "unit", "double"],
            "example": {"prompt": "Area is measured in ____ units.", "answer": "square"},
            "items": [
                {"number": 3, "prompt": "The ____ meets the base at a right angle."},
                {"number": 4, "prompt": "To find the area, we take ____ of base × height."},
                {"number": 5, "prompt": "Any side of a triangle can be used as its ____."},
                {
                    "number": 6,
                    "prompt": "This triangle has area 24 cm² and base 6 cm. Write its height on the diagram.",
                    "visual": {
                        "kind": "shape",
                        "caption": "",
                        "purpose": "Use the rule backwards to complete a partly labelled triangle.",
                        "shape": "triangle",
                        "base": 6,
                        "height": 8,
                        "unit": "cm",
                        "source_unit_ids": ["SRC-P1-U5"],
                    },
                    "hidden": ["height"],
                },
            ],
        },
        {
            "stage": "Vary",
            "activity_type": "SPOT_MISTAKE",
            "instruction": "Circle the wrong step. Write the correct step on the lines.",
            "body_text": "Remember: the base and the height must be in the same unit.",
            "hint_pointer": "Stuck? Look at the worked example on Page 1.",
            "items": [
                {
                    "number": 7,
                    "prompt": "Find Ravi's mistake.",
                    "peer_work": {
                        "intro": "Ravi found the area of a triangle with base 10 cm and height 6 cm:",
                        "steps": ["Area = 1/2 × base × height", "= 1/2 × 10 × 6", "= 60 cm²"],
                        "mistake_step": 3,
                    },
                },
                {
                    "number": 8,
                    "prompt": "Find Meena's mistake.",
                    "peer_work": {
                        "intro": "Meena found the height of a triangle with area 24 cm² and base 6 cm:",
                        "steps": ["24 = 1/2 × 6 × height", "24 = 3 × height", "height = 24 × 3 = 72 cm"],
                        "mistake_step": 3,
                    },
                },
                {
                    "number": 9,
                    "prompt": "Find Arjun's mistake.",
                    "peer_work": {
                        "intro": "Arjun found the area of a triangle with base 9 cm and height 4 cm:",
                        "steps": ["Area = 1/2 × base × height", "= 1/2 × 9 × 4", "= 18 cm"],
                        "mistake_step": 3,
                    },
                },
            ],
        },
        {
            "stage": "Apply",
            "activity_type": "SOLVE",
            "instruction": "Solve each problem. Show your working in the box.",
            "hint_pointer": "Stuck? Use the rule in the box on Page 1.",
            "items": [
                {
                    "number": 10,
                    "prompt": "Find the area of a triangular garden bed: base 12 m, height 7 m.",
                    "unit": "m²",
                },
                {
                    "number": 11,
                    "prompt": "A triangular tile has area 18 cm² and base 6 cm. Find its height.",
                    "unit": "cm",
                },
            ],
        },
        {
            "stage": "Recall",
            "activity_type": "SHORT_ANSWER",
            "instruction": "Answer from memory.",
            "items": [
                {
                    "number": 12,
                    "prompt": "Write the rule for the area of a triangle in your own words.",
                    "keywords": ["base", "height"],
                }
            ],
        },
    ],
    "answer_key": {
        "entries": [
            {
                "item_number": 1,
                "answer": "20 m²",
                "reason": "1/2 × 8 × 5 = 20, so 20 square metres.",
                "calculation": "0.5*8*5",
                "source_unit_ids": ["SRC-P1-U3"],
            },
            {
                "item_number": 2,
                "answer": "5 cm",
                "reason": "The example gives height 5 cm.",
                "source_unit_ids": ["SRC-P1-U4"],
            },
            {
                "item_number": 3,
                "answer": "height",
                "reason": "The height is perpendicular to the base.",
                "source_unit_ids": ["SRC-P1-U2"],
            },
            {
                "item_number": 4,
                "answer": "half",
                "reason": "Area is half the product of base and height.",
                "source_unit_ids": ["SRC-P1-U3"],
            },
            {
                "item_number": 5,
                "answer": "base",
                "reason": "Any side can be taken as the base.",
                "source_unit_ids": ["SRC-P1-U2"],
            },
            {
                "item_number": 6,
                "answer": "8",
                "reason": "24 = 1/2 × 6 × height = 3 × height, so height = 8 cm.",
                "calculation": "24/(0.5*6)",
                "source_unit_ids": ["SRC-P1-U5"],
            },
            {
                "item_number": 7,
                "answer": "= 30 cm²",
                "reason": "Half of 10 × 6 is 30, not 60.",
                "calculation": "0.5*10*6",
                "source_unit_ids": ["SRC-P1-U3"],
            },
            {
                "item_number": 8,
                "answer": "8 cm, because height = 24 ÷ 3",
                "reason": "If 24 = 3 × height, divide 24 by 3.",
                "calculation": "24/3",
                "source_unit_ids": ["SRC-P1-U5"],
            },
            {
                "item_number": 9,
                "answer": "= 18 cm²",
                "reason": "Area is written in square units, so cm², not cm.",
                "calculation": "0.5*9*4",
                "source_unit_ids": ["SRC-P1-U1", "SRC-P1-U3"],
            },
            {
                "item_number": 10,
                "answer": "42 m²",
                "reason": "1/2 × 12 × 7 = 42.",
                "calculation": "0.5*12*7",
                "source_unit_ids": ["SRC-P1-U3", "SRC-P2-U2"],
            },
            {
                "item_number": 11,
                "answer": "6 cm",
                "reason": "18 = 1/2 × 6 × height = 3 × height, so height = 6.",
                "calculation": "18/(0.5*6)",
                "source_unit_ids": ["SRC-P1-U5", "SRC-P2-U2"],
            },
            {
                "item_number": 12,
                "answer": "The area is half of base times height.",
                "accepted_alternatives": ["Must say: half (1/2), base, height, multiplied"],
                "reason": "This is the rule for the area of a triangle.",
                "source_unit_ids": ["SRC-P1-U3"],
            },
        ],
        "scope_covered": "Area of a triangle = 1/2 × base × height: finding an area and finding a missing height.",
        "not_covered": "Perimeter and other shapes in Chapter 9.",
        "source_issues": [],
        "shortened_lesson_note": None,
    },
}

SAMPLE_PLAN = {
    "concept": "Area of a triangle",
    "learning_steps": [
        {
            "title": "Base and height",
            "idea": "Any side can be the base; the height is the perpendicular distance from the opposite vertex.",
            "source_unit_ids": ["SRC-P1-U2"],
        },
        {
            "title": "Half of a rectangle",
            "idea": "A triangle is half of a rectangle with the same base and height, so area = 1/2 × base × height.",
            "source_unit_ids": ["SRC-P1-U6", "SRC-P1-U3"],
        },
        {
            "title": "Finding a missing height",
            "idea": "When the area and base are known, the same rule gives the height.",
            "source_unit_ids": ["SRC-P1-U5"],
        },
    ],
    "misconception": {
        "wrong_idea": "Area of a triangle = base × height (forgetting to halve).",
        "correct_idea": "The area of a triangle is half of base × height.",
        "source_unit_ids": ["SRC-P1-U3", "SRC-P1-U6"],
    },
    "worked_example": {
        "problem": "Find the area of a triangle with base 8 cm and height 5 cm.",
        "steps": ["Area = 1/2 × base × height", "= 1/2 × 8 × 5", "= 20 cm²"],
        "answer": "20 cm²",
        "calculation": "0.5*8*5",
        "source_unit_ids": ["SRC-P1-U4"],
    },
    "visual_type": "shape",
    "visual_purpose": "See that the height is perpendicular to the base, from the opposite vertex.",
}
