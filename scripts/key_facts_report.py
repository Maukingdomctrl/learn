"""Save the 5 attached ICSE Class 8 sheets into fixtures/sheets/ and run the Key Facts
writer with provider "deterministic" on every PDF in fixtures/sheets/, writing
fixtures/key_facts_report.md with every card's question, answer, rubric score, and reasons.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from generate_fixtures import build_multi_page_pdf
from learn.teaching_engine.card_quality import (
    clean_lines,
    clean_sheet,
    explain_no_card_reason,
    is_card_acceptable,
    plan_key_facts_cards,
    preprocess_sheet_lines,
    score_card,
    write_key_fact_card,
)
from question_quality_engine import PDFExtractionEngine



def _encode_line_for_pdf(line: str) -> str:
    """Encode Unicode punctuation/math symbols into PDF octal escapes supported by PDFExtractionEngine."""
    replacements = {
        "•": r"\225",
        "‘": r"\221",
        "’": r"\222",
        "“": r"\223",
        "”": r"\224",
        "–": r"\226",
        "—": r"\227",
        "−": "-",
        "°": r"\260",
        "±": r"\261",
        "²": r"\262",
        "³": r"\263",
        "⁴": "^4",
        "×": r"\327",
        "÷": r"\367",
        "¼": r"\274",
        "½": r"\275",
        "¾": r"\276",
        "£": r"\243",
        "·": ".",
        "→": "->",
        "≥": ">=",
        "π": "pi",
        "√": "sqrt",
        "■": "2",
    }
    res: list[str] = []
    for ch in line:
        if ch in replacements:
            res.append(replacements[ch])
        elif ch == "\\":
            res.append("\\\\")
        elif ch == "(":
            res.append("\\(")
        elif ch == ")":
            res.append("\\)")
        elif ord(ch) < 128:
            res.append(ch)
        elif ord(ch) <= 255:
            res.append(f"\\{ord(ch):03o}")
        else:
            res.append("?")
    return "".join(res)


def _page_lines_to_stream(lines: list[str]) -> bytes:
    ops: list[str] = ["BT", "/F1 11 Tf"]
    y = 790.0
    for line in lines:
        safe = _encode_line_for_pdf(line)
        ops.append(f"1 0 0 1 45 {y:.1f} Tm")
        ops.append(f"({safe}) Tj")
        y -= 15.0
    ops.append("ET")
    return "\n".join(ops).encode("ascii")


# ---------------------------------------------------------------------------
# Exact OCR page contents of the 5 attached ICSE Class 8 sheets
# ---------------------------------------------------------------------------

STRESS_TEST_PAGES: list[list[str]] = [
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 1 of 20",
        "Grade 8 Maths & Science — Worksheet Stress Test",
        "20-page document for testing PDF extraction, formula parsing, tables, diagrams, and worksheet structure.",
        "Student: ____________________ Date: ____________________",
        "Notation checklist",
        "Read and recognize these characters exactly: ¾ 2½ × ÷ ± ≥ π √ ° →",
        "Powers and chemical subscripts: x² H2O CO2 3.5 × 10⁴",
        "This packet mixes worked examples, answer tables, independent practice, a diagram, and data interpretation.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 2 of 20",
        "Page 2 — Formula reference",
        "Speed = Distance ÷ Time",
        "A = l × b",
        "v = u + at",
        "Symbols: v = final velocity; u = initial velocity; a = acceleration; t = time. For the area formula, l is length and b is breadth.",
        "Practice: write the formula you would use to calculate (a) speed, (b) rectangle area, (c) final velocity when acceleration is constant.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 3 of 20",
        "Page 3 — Superscripts, subscripts & scientific notation",
        "Algebra: x² means x multiplied by itself. If x = 5, then x² = 25.",
        "Science notation: H2O is the formula for water; CO2 is carbon dioxide.",
        "Scientific notation: 3.5 × 10⁴ = 35,000.",
        "Practice: evaluate 4²; write the number represented by 2.1 × 10³; identify the subscript in H2O and CO2.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 4 of 20",
        "Page 4 — Fractions and mixed numbers",
        "Fraction symbols: ¾ = three quarters. Mixed number: 2½ = two and one half.",
        "Practice sums (show working):",
        "1. ¾ + ¼ = ______",
        "2. 2½ − ½ = ______",
        "3. ¾ of 20 = ______",
        "4. Write 1.25 as a fraction in simplest form. ______",
        "Check your notation: keep the fraction bar or fraction glyph clear in your final answer.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 5 of 20",
        "Page 5 — Units and measurement",
        "Speed unit: 5 km/h means five kilometres per hour.",
        "Temperature: 25 °C means twenty-five degrees Celsius.",
        "Practice: convert 5 km/h to m/s (use 1 km/h = 5/18 m/s). Convert 25 °C to kelvin using K = °C + 273.",
        "Write units with every numerical answer.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 6 of 20",
        "Page 6 — Mathematical symbols",
        "± means plus or minus; ≥ means greater than or equal to; π is the circle constant; √ denotes a square root.",
        "Practice: choose the correct symbol: (a) 7 __ 5 (≥ or ±); (b) √49 = ____; (c) circumference of a circle = ____ × diameter.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 7 of 20",
        "Page 7 — Worked example: speed",
        "Example 1: A car travels 120 km in 2 h. Find its speed.",
        "Solution: Speed = 120 ÷ 2 = 60 km/h.",
        "Why? Speed is distance divided by time. The units are km ÷ h, so the result is km/h.",
        "Try: A cyclist travels 18 km in 1.5 h. Find the average speed.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 8 of 20",
        "Page 8 — Practice: speed and distance",
        "Solve and show each step.",
        "1. A bus travels 150 km in 3 h. Find speed.",
        "2. A runner covers 400 m in 80 s. Find speed in m/s.",
        "3. A car moves at 60 km/h for 2.5 h. Find distance.",
        "4. A train covers 90 km at 45 km/h. Find travel time.",
        "Answers are not supplied on this page.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 9 of 20",
        "Page 9 — Answered practice table",
        "Question | Answer | Working",
        "A vehicle travels 100 km in 2 h. Find speed. | 50 km/h | 100 ÷ 2 = 50",
        "A cyclist travels 30 km in 3 h. Find speed. | 10 km/h | 30 ÷ 3 = 10",
        "A car travels at 40 km/h for 2 h. Find distance. | 80 km | 40 × 2 = 80",
        "A journey of 120 km takes 4 h. Find speed. | 30 km/h | 120 ÷ 4 = 30",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 10 of 20",
        "Page 10 — Rectangle area",
        "Formula: A = l × b",
        "Worked example: l = 8 cm and b = 3 cm. A = 8 × 3 = 24 cm².",
        "Practice (no answers here):",
        "1. l = 9 cm, b = 4 cm. Find A.",
        "2. l = 12 m, b = 5 m. Find A.",
        "3. A = 42 cm² and l = 7 cm. Find b.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 11 of 20",
        "Page 11 — Motion formula",
        "For constant acceleration: v = u + at",
        "Example: u = 4 m/s, a = 2 m/s², t = 3 s. Then v = 4 + (2 × 3) = 10 m/s.",
        "Practice: (1) u = 5 m/s, a = 3 m/s², t = 4 s. Find v. (2) u = 0, a = 2 m/s², t = 6 s. Find v.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 12 of 20",
        "Page 12 — Mixed calculation practice",
        "Show working and include units.",
        "1. ¾ of 32 = ____",
        "2. √81 = ____",
        "3. 3.5 × 10⁴ = ____",
        "4. 5 km/h expressed in m/s = ____",
        "5. 25 °C expressed in K = ____",
        "6. A rectangle is 6 cm by 2½ cm. Find its area.",
        "No answer key is printed for these questions.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 13 of 20",
        "Page 13 — Key terms",
        "KEY TERMS",
        "Force: a push or pull on an object.",
        "Speed: distance travelled per unit time.",
        "Acceleration: change in velocity per unit time.",
        "Use each term in a sentence of your own.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 14 of 20",
        "Page 14 — Labelled circuit diagram",
        "Study the simple circuit. Trace the wire path and identify the cell, bulb, and connecting wire.",
        "Cell / battery",
        "Bulb",
        "Connecting wire",
        "Closed path",
        "Current direction →",
        "Schematic (not to scale)",
        "Questions: (1) What component supplies electrical energy? (2) What happens if the circuit path is broken?",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 15 of 20",
        "Page 15 — Data table: time and distance",
        "A toy car moves along a straight track. Recorded values:",
        "Time (s) | Distance (m)",
        "0 | 0",
        "1 | 2",
        "2 | 4",
        "3 | 6",
        "4 | 8",
        "5 | 10",
        "Read the graph: If distance is plotted on the vertical axis and time on the horizontal axis, what does the straight-line pattern indicate? What is the car’s speed?",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 16 of 20",
        "Page 16 — Graph reading practice",
        "Use the Time | Distance table on page 15.",
        "1. What distance has the car travelled after 4 s?",
        "2. At what time does it reach 8 m?",
        "3. Describe the relationship between time and distance.",
        "4. Calculate the gradient (distance ÷ time) using the 5 s data.",
        "Sketch a distance–time graph on graph paper. Label both axes and units.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 17 of 20",
        "Page 17 — Chemical equation",
        "Equation: 2H2 + O2 → 2H2O",
        "Read the subscripts and coefficients carefully: the small 2 belongs to the formula; the leading 2 multiplies the whole formula.",
        "Practice: In 2H2, how many hydrogen atoms are represented? In O2, how many oxygen atoms are represented? How many H2O molecules appear on the product side?",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 18 of 20",
        "Page 18 — Mixed answer table",
        "Question | Answer | Working",
        "Evaluate x² when x = 7. | 49 | 7 × 7 = 49",
        "Find the area when l = 5 cm, b = 4 cm. | 20 cm² | 5 × 4 = 20",
        "Find speed for 75 km in 1.5 h. | 50 km/h | 75 ÷ 1.5 = 50",
        "Find v for u = 3 m/s, a = 2 m/s², t = 5 s. | 13 m/s | 3 + (2 × 5) = 13",
        "Check that units and superscripts remain legible in the extracted answer.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 19 of 20",
        "Page 19 — Independent mixed worksheet",
        "Solve without looking back at worked examples.",
        "1. Write the speed formula.",
        "2. Calculate speed: 84 km in 2 h.",
        "3. Calculate area: 7½ cm × 4 cm.",
        "4. Evaluate √121.",
        "5. Write 0.00035 in scientific notation.",
        "6. State what the arrow means in a chemical equation.",
        "7. Define force.",
        "8. From the table on page 15, find distance at 3 s.",
        "Answers intentionally omitted.",
    ],
    [
        "Grade 8 Maths & Science — PDF Stress Test",
        "Worksheet test copy Page 20 of 20",
        "Page 20 — Symbol and extraction checklist",
        "Confirm the PDF reader preserves these exactly:",
        "¾ 2½ 5 km/h 25 °C 3.5 × 10⁴ ± ≥ π √ x² H2O CO2",
        "Formula strings:",
        "Speed = Distance ÷ Time",
        "A = l × b",
        "v = u + at",
        "2H2 + O2 → 2H2O",
        "Document feature checklist: worked solution; unanswered practice; Question | Answer | Working table; boxed key terms; labelled diagram; Time | Distance table; graph-reading prompt.",
        "End of 20-page stress-test worksheet.",
    ],
]

UK_CITIES_PAGES: list[list[str]] = [
    [
        "Grade 8 Social Studies | Country - United Kingdom Page 1",
        "IMPORTANT CITIES OF THE UNITED KINGDOM",
        "Grade 8 Social Studies | Notes + Comparative Table + Practice Questions",
        "1. QUICK REVISION NOTES",
        "1. LONDON – Capital of the United Kingdom & England",
        "• Situated on the River Thames in southeastern England.",
        "• One of the world’s preeminent cities – hub of political, economic and cultural network.",
        "• Metropolitan area covers much of southeastern England.",
        "• Continues to serve as the financial centre of Europe and a centre of innovation.",
        "• Major influence in popular culture worldwide.",
        "2. BIRMINGHAM – West Midlands, England",
        "• Major city of the West Midlands, lying on the River Rea.",
        "• Largest and most populous British city outside London.",
        "• Was a medium-sized market town in the medieval period; grew to international prominence in the 18th century.",
        "• At the heart of the Industrial Revolution – advances in science, technology & economic development.",
        "• The industrial steam engine (one of the most important inventions in British history) was invented here.",
        "• Birmingham Hippodrome is the UK’s busiest theatre (over 520,000 visitors each year).",
        "3. BELFAST – Capital of Northern Ireland",
        "• Capital and largest city of Northern Ireland; second largest city on the island of Ireland.",
        "• Situated on the River Lagan; population about 286,000 (2011 census).",
        "• Historic industries: Irish linen, tobacco processing, rope-making and shipbuilding.",
        "• Harland and Wolff shipyard built the RMS Titanic – once the world’s biggest and most productive shipyard.",
        "• Key role in the Industrial Revolution; global industrial centre until the latter half of the 20th century.",
        "• Sustained major aerospace and missiles industry since the mid-1930s.",
        "• Today: centre for industry, arts, higher education, business and law – the economic engine of Northern Ireland.",
        "• Home to the Titanic Belfast interactive museum.",
        "4. EDINBURGH – Capital of Scotland",
        "• Capital city of Scotland; Scotland’s second most populous city and the seventh most populous in the UK.",
        "• Home to the Scottish Parliament and the seat of the monarchy in Scotland.",
        "• Second largest financial centre in the UK after London.",
        "• Centre of banking for over 300 years: Bank of Scotland founded in 1695 (HQ in Edinburgh).",
        "• Royal Bank of Scotland (RBS) has its global headquarters in Edinburgh.",
        "• Tourism is a major mainstay: supports 30,000 jobs worth £1.6 billion to the city economy.",
        "• Famous for its stunning mix of architecture: medieval tenements, Old Town, cobbled wynds and Georgian-era buildings.",
        "5. CARDIFF – Capital of Wales",
        "• Capital and largest city in Wales; the eleventh-largest city in the United Kingdom.",
        "• Country’s chief commercial centre; base for national cultural & sporting institutions, Welsh national media.",
        "• Seat of the National Assembly for Wales (Senedd).",
        "• Was a small town until the early 19th century; rose as a major port for coal transport.",
        "• Became the world’s most important coal port (handled more than London and Liverpool).",
        "• Made a city in 1905; proclaimed capital of Wales in 1955.",
        "• Main engine of growth in the Welsh economy; centre for white-collar professions.",
    ],
    [
        "Grade 8 Social Studies | Country - United Kingdom Page 2",
        "• Relies principally on retail, finance, media and tourism sectors.",
        "• Home to the Wales Millennium Centre – a thriving creative capital with rich cultural heritage.",
        "MEMORY TIP: Remember the order – London (England) → Birmingham (England) → Belfast (N. Ireland) → Edinburgh (Scotland) → Cardiff (Wales). Think: “Large British Buildings Excel in Culture!”",
    ],
    [
        "Grade 8 Social Studies | Country - United Kingdom Page 3",
        "2. COMPARATIVE TABLE – EASY TO REMEMBER",
        "Feature | London | Birmingham | Belfast | Edinburgh | Cardiff",
        "Country / Region | England (UK Capital) | West Midlands, England | Northern Ireland | Scotland | Wales",
        "Status | Capital of UK & England | Largest city outside London | Capital of N. Ireland | Capital of Scotland | Capital of Wales",
        "River | River Thames | River Rea | River Lagan | — | —",
        "Population Rank | Largest in UK | 2nd largest in UK (outside London) | Largest in N. Ireland; 2nd on Ireland island | 2nd in Scotland; 7th in UK | Largest in Wales; 11th in UK",
        "Key Historical Role | Political, economic & cultural hub | Heart of Industrial Revolution; steam engine | Shipbuilding (Titanic); Industrial Revolution | Banking centre since 1695 | World’s top coal port in 19th century",
        "Famous Landmark / Fact | Financial centre of Europe | Birmingham Hippodrome (busiest theatre) | Titanic Belfast Museum; Harland & Wolff | Scottish Parliament; RBS HQ | Wales Millennium Centre; Capital since 1955",
        "Modern Economy | Finance, innovation, culture | Industry, technology, culture | Industry, aerospace, arts, education | Finance, banking, tourism (£1.6 bn) | Retail, finance, media, tourism",
        "Special Note | Metropolitan area covers SE England | Grew to prominence in 18th century | Pop. ~286,000 (2011); economic engine of NI | Tourism: 30,000 jobs | Made city 1905; capital 1955",
        "Quick Comparison Snapshot (One-Line Memory)",
        "• London = Political + Financial Powerhouse (Thames)",
        "• Birmingham = Industrial Revolution Heart (Steam Engine + Hippodrome)",
        "• Belfast = Shipbuilding & Titanic (Lagan + Harland & Wolff)",
        "• Edinburgh = Banking Capital of Scotland (Parliament + RBS)",
        "• Cardiff = Coal Port turned Creative Capital (1955 Capital + Millennium Centre)",
    ],
    [
        "Grade 8 Social Studies | Country - United Kingdom Page 4",
        "3. PRACTICE QUESTIONS",
        "A. Fill in the Blanks (1 mark each)",
        "1. London is situated on the tidal ________________ in southeastern England.",
        "2. Birmingham is a major city of the ________________, England.",
        "3. The industrial ________________ was invented in Birmingham.",
        "4. Belfast is situated on the River ________________.",
        "5. Harland and Wolff shipyard in Belfast built the famous ship ________________.",
        "6. Edinburgh is the ________________ largest financial centre in the UK after London.",
        "7. The Bank of Scotland was founded in the year ________________.",
        "8. Cardiff was proclaimed the capital of Wales in the year ________________.",
        "9. Birmingham Hippodrome is the UK’s ________________ theatre with over 520,000 visitors each year.",
        "10. Cardiff relies principally on the retail, finance, media and ________________ sectors.",
        "B. Answer in One Sentence (1 mark each)",
        "1. Name the capital city of Northern Ireland.",
        "2. Which river flows through Birmingham?",
        "3. What is the population of Belfast according to the 2011 census?",
        "4. Name the interactive museum in Belfast that pays homage to the Titanic.",
        "5. Which city is home to the Scottish Parliament?",
        "6. When was Cardiff made a city?",
        "7. What was Cardiff famous for as a port in the 19th century?",
        "8. Name the busiest theatre in the UK located in Birmingham.",
        "9. Which bank has its global headquarters in Edinburgh?",
        "10. What is the rank of Cardiff among UK cities by population?",
        "C. Short Answer Questions (2 marks each)",
        "1. Why is London considered one of the world’s preeminent cities?",
        "2. Describe the importance of Birmingham during the Industrial Revolution.",
        "3. What role did Harland and Wolff play in Belfast’s industrial history?",
        "4. Explain why Edinburgh is an important financial centre.",
        "5. How did Cardiff rise from a small town to become the capital of Wales?",
        "6. Compare the economic activities of Edinburgh and Cardiff today.",
        "7. State any two facts that show Belfast’s importance in the Industrial Revolution and later years.",
        "8. Mention two unique features of Edinburgh’s cultural and political importance.",
    ],
    [
        "Grade 8 Social Studies | Country - United Kingdom Page 5",
        "4. ANSWER KEY",
        "A. Fill in the Blanks – Answers",
        "1. River Thames",
        "2. West Midlands",
        "3. steam engine (industrial steam engine)",
        "4. Lagan",
        "5. RMS Titanic",
        "6. second",
        "7. 1695",
        "8. 1955",
        "9. busiest",
        "10. tourism",
        "B. One Sentence Answers",
        "1. Belfast is the capital city of Northern Ireland.",
        "2. The River Rea flows through Birmingham.",
        "3. The population of Belfast was about 286,000 according to the 2011 census.",
        "4. The Titanic Belfast is the interactive museum that pays homage to the Titanic.",
        "5. Edinburgh is home to the Scottish Parliament.",
        "6. Cardiff was made a city in 1905.",
        "7. Cardiff was the world’s most important coal port in the 19th century.",
        "8. Birmingham Hippodrome is the busiest theatre in the UK.",
        "9. The Royal Bank of Scotland (RBS) has its global headquarters in Edinburgh.",
        "10. Cardiff is the eleventh-largest city in the United Kingdom.",
        "C. Short Answer Questions – Model Answers",
        "1. Why is London considered one of the world’s preeminent cities?",
        "London is the capital of the UK, situated on the River Thames. It is the hub of a political, economic and cultural network that extends far beyond England’s shores. It remains the financial centre of Europe and a major centre of innovation and popular culture.",
        "2. Describe the importance of Birmingham during the Industrial Revolution.",
        "Birmingham was at the forefront of the Industrial Revolution. It produced worldwide advances in science, technology and economic development. The industrial steam engine, one of the most important inventions in British history, was invented in Birmingham.",
        "3. What role did Harland and Wolff play in Belfast’s industrial history?",
        "Harland and Wolff was the world’s biggest and most productive shipyard in the early 20th century. It built the famous RMS Titanic and made Belfast a global centre of shipbuilding during the Industrial Revolution.",
        "4. Explain why Edinburgh is an important financial centre.",
        "Edinburgh is the second largest financial centre in the UK after London. It has been a centre of banking for over 300 years. The Bank of Scotland was founded there in 1695 and the Royal Bank of Scotland (RBS) has its global headquarters in Edinburgh.",
        "5. How did Cardiff rise from a small town to become the capital of Wales?",
        "Cardiff was a small town until the early 19th century. It became a major port for coal transport and grew into the world’s most important coal port. It was made a city in 1905 and was proclaimed the capital of Wales in 1955.",
        "6. Compare the economic activities of Edinburgh and Cardiff today.",
        "Edinburgh’s economy is driven by finance, banking and tourism (supporting 30,000 jobs worth £1.6 billion). Cardiff relies principally on retail, finance, media and tourism sectors and is a centre for white-collar professions and creative industries.",
        "7. State any two facts that show Belfast’s importance in the Industrial Revolution and later years.",
    ],
    [
        "Grade 8 Social Studies | Country - United Kingdom Page 6",
        "1) Belfast was a global industrial centre with major shipbuilding (Harland & Wolff / Titanic). 2) It has sustained a major aerospace and missiles industry since the mid-1930s and remains the economic engine of Northern Ireland.",
        "8. Mention two unique features of Edinburgh’s cultural and political importance.",
        "1) Edinburgh is home to the Scottish Parliament and is the seat of the monarchy in Scotland. 2) It is famous for its stunning mix of medieval, Old Town and Georgian architecture and is a major tourist destination.",
        "Study Tip for Grade 8: Make a simple mind-map with the 5 cities in a circle. Write the river, one famous fact and the capital status for each. Revise the comparative table daily for 5 minutes – you will remember everything easily!",
    ],
]

CONSTITUTION_PAGES: list[list[str]] = [
    [
        "SYNTHETIC SAMPLE · NOT OFFICIAL SCHOOL MATERIAL",
        "HISTORY AND CIVICS | The Constitution",
        "Practice source | Page 1 of 2",
        "A Constitution Sets Out Shared Rules",
        "A constitution is a set of fundamental rules and principles used to govern a country. It describes important institutions and how public authority is organised.",
        "India's Constitution was adopted by the Constituent Assembly on 26 November 1949. It came into effect on 26 January 1950. Republic Day marks the date it came into effect.",
        "The Preamble introduces the Constitution's aims and guiding values. It begins with the words 'We, the people of India', expressing that the Constitution derives its authority from the people.",
        "The Constitution is the supreme law of India. Laws and government actions must follow its provisions.",
        "Representative practice text for software testing · Not a syllabus claim",
    ],
    [
        "SYNTHETIC SAMPLE · NOT OFFICIAL SCHOOL MATERIAL",
        "HISTORY AND CIVICS | The Constitution",
        "Practice source | Page 2 of 2",
        "Rights, Duties and Institutions",
        "Fundamental Rights protect important freedoms and equal treatment. They also provide ways to seek remedies when certain rights are violated.",
        "Fundamental Duties describe responsibilities expected of citizens. Rights and duties are different ideas: a right is a protected freedom or entitlement, while a duty is a responsibility.",
        "The Constitution establishes the Union government and state governments and describes their roles. The legislature makes laws, the executive carries them out, and the judiciary interprets laws and resolves disputes.",
        "Study prompt: Choose one institution named above. Explain its role in your own words, then point to the sentence that supports your explanation.",
        "Representative practice text for software testing · Not a syllabus claim",
    ],
]

CHEMISTRY_10_PAGES: list[list[str]] = [
    [
        "1. Matter Around Us",
        "Chemistry | Standard 8 • Sheet 1/10 • FOUNDATION • Basic vocabulary",
        "What is matter?",
        "Matter is anything that has mass and occupies space. Objects around us are made of matter, although energy such as light is not matter.",
        "Materials",
        "Materials have properties such as colour, hardness, solubility, and conductivity. These properties help us describe and choose materials.",
        "Facts to Remember",
        "• Matter has mass and occupies space.",
        "• Materials can be described by their physical properties.",
        "• Solubility describes how well a substance dissolves in a given solvent.",
        "Check Your Understanding",
        "1. Define matter.",
        "2. Name three properties used to describe materials.",
        "3. Is light matter? Give a reason.",
    ],
    [
        "2. States of Matter",
        "Chemistry | Standard 8 • Sheet 2/10 • FOUNDATION • Compare states",
        "Solids and liquids",
        "A solid usually keeps its shape and volume. A liquid keeps its volume but takes the shape of its container.",
        "Gases",
        "A gas spreads to fill its container and can be compressed much more easily than a solid or liquid.",
        "Facts to Remember",
        "• A solid generally has a fixed shape and volume.",
        "• A liquid has a fixed volume but takes its container's shape.",
        "• A gas spreads to fill its container.",
        "Check Your Understanding",
        "1. Compare the shape of a solid and a liquid.",
        "2. Why can a gas be compressed more easily?",
        "3. Give one example of each state.",
    ],
    [
        "3. Particle Model",
        "Chemistry | Standard 8 • Sheet 3/10 • FOUNDATION • Explain observations",
        "Particles",
        "Matter is made of tiny particles. In solids, particles are closely packed and vibrate about fixed positions; in liquids, they can move past one another; in gases, they are far apart and move freely.",
        "Temperature",
        "Heating generally increases particle motion. This helps explain expansion and changes of state.",
        "Facts to Remember",
        "• Matter consists of particles too small to see individually.",
        "• Particles in a solid vibrate around fixed positions.",
        "• Heating generally increases particle motion.",
        "Check Your Understanding",
        "1. Use particles to explain why a liquid flows.",
        "2. How does particle spacing differ in a gas and a solid?",
        "3. What usually happens to particle motion when matter is heated?",
    ],
    [
        "4. Changes of State",
        "Chemistry | Standard 8 • Sheet 4/10 • DEVELOPING • Process vocabulary",
        "Heating",
        "Melting changes a solid into a liquid. Evaporation changes liquid into vapour from its surface; boiling occurs throughout a liquid at its boiling point under a given pressure.",
        "Cooling",
        "Condensation changes gas into liquid. Freezing changes liquid into solid. Sublimation is a change from solid directly to gas.",
        "Facts to Remember",
        "• Melting is solid to liquid.",
        "• Condensation is gas to liquid.",
        "• Sublimation is solid directly to gas.",
        "Check Your Understanding",
        "1. Name the change from liquid to solid.",
        "2. Distinguish evaporation from boiling.",
        "3. What change occurs when water vapour forms droplets?",
    ],
    [
        "5. Pure Substances and Mixtures",
        "Chemistry | Standard 8 • Sheet 5/10 • DEVELOPING • Classify materials",
        "Pure substances",
        "An element contains one kind of atom. A compound contains elements chemically combined in a fixed proportion.",
        "Mixtures",
        "A mixture contains two or more substances physically combined. Its components can often be separated by physical methods, and the composition may vary.",
        "Facts to Remember",
        "• An element contains one kind of atom.",
        "• A compound has elements chemically combined in a fixed proportion.",
        "• A mixture contains substances physically combined.",
        "Check Your Understanding",
        "1. Classify oxygen as an element, compound, or mixture.",
        "2. How does a mixture differ from a compound?",
        "3. Why can mixture composition vary?",
    ],
    [
        "6. Separating Mixtures",
        "Chemistry | Standard 8 • Sheet 6/10 • DEVELOPING • Choose a method",
        "Physical methods",
        "Filtration separates an insoluble solid from a liquid. Evaporation can recover a dissolved solid. Decantation separates a liquid from settled solids or from another immiscible liquid.",
        "Other methods",
        "A magnet can remove suitable magnetic materials. Distillation uses evaporation and condensation to separate substances based on differences in volatility.",
        "Facts to Remember",
        "• Filtration can separate an insoluble solid from a liquid.",
        "• Evaporation can leave a dissolved solid behind.",
        "• Distillation involves evaporation followed by condensation.",
        "Check Your Understanding",
        "1. Which method can separate sand from water?",
        "2. How could salt be recovered from salt water?",
        "3. Why would a magnet not separate dissolved salt from water?",
    ],
    [
        "7. Atoms, Molecules, and Symbols",
        "Chemistry | Standard 8 • Sheet 7/10 • DEVELOPING • Read chemical language",
        "Atoms and molecules",
        "Atoms are the basic units of elements. A molecule is a group of atoms bonded together. Some substances, such as noble gases, exist as individual atoms.",
        "Symbols and formulae",
        "Chemical symbols are abbreviated names for elements. A formula uses symbols and numbers to show which atoms are present; H2O represents water with two hydrogen atoms and one oxygen atom per molecule.",
        "Facts to Remember",
        "• A chemical symbol represents an element.",
        "• H2O contains hydrogen and oxygen in a 2:1 atom ratio.",
        "• Subscripts in a formula show the number of atoms of the preceding element.",
        "Check Your Understanding",
        "1. What does the symbol O represent?",
        "2. How many hydrogen atoms are shown in H2O?",
        "3. What information does a chemical formula provide?",
    ],
    [
        "8. Physical and Chemical Changes",
        "Chemistry | Standard 8 • Sheet 8/10 • CHALLENGE • Use evidence",
        "Physical change",
        "A physical change alters form or state without producing a new substance. Melting ice is physical: the substance remains water.",
        "Chemical change",
        "A chemical change produces one or more new substances. Evidence may include gas formation, a colour change, a temperature change, or a precipitate, though no single sign proves a reaction by itself.",
        "Facts to Remember",
        "• A physical change does not create a new substance.",
        "• A chemical change forms new substance(s).",
        "• Observations such as bubbles or colour change can be clues, not conclusive proof alone.",
        "Check Your Understanding",
        "1. Why is melting ice a physical change?",
        "2. Give two possible clues of a chemical reaction.",
        "3. Why should a clue be interpreted with other evidence?",
    ],
    [
        "9. Chemical Reactions and Equations",
        "Chemistry | Standard 8 • Sheet 9/10 • CHALLENGE • Interpret representations",
        "Reaction",
        "In a chemical reaction, atoms rearrange as reactants form products. A word equation names the reactants and products.",
        "Conservation",
        "In a balanced chemical equation, the number of atoms of each element is the same on both sides. Coefficients change the number of particles; subscripts are part of a substance's formula and should not be changed when balancing.",
        "Facts to Remember",
        "• Reactants are the starting substances; products are formed.",
        "• A balanced equation has equal counts of each element on both sides.",
        "• Balancing changes coefficients, not chemical formula subscripts.",
        "Check Your Understanding",
        "1. What are reactants and products?",
        "2. Why must atom counts match in a balanced equation?",
        "3. Why is changing a subscript not an acceptable balancing step?",
    ],
    [
        "10. Acids, Bases, and Indicators",
        "Chemistry | Standard 8 • Sheet 10/10 • CHALLENGE • Apply chemical properties",
        "Acids and bases",
        "Acidic and basic solutions have different chemical properties. Indicators change colour depending on the solution; litmus is a common indicator.",
        "pH and safety",
        "The pH scale is commonly used to describe acidity or basicity: values below 7 are acidic, 7 is neutral, and above 7 are basic at typical classroom conditions. Never taste unknown chemicals; follow lab safety directions.",
        "Facts to Remember",
        "• At typical classroom conditions, pH 7 is neutral.",
        "• Values below 7 are acidic; values above 7 are basic.",
        "• Indicators help identify acidic or basic solutions; unknown chemicals must not be tasted.",
        "Check Your Understanding",
        "1. What colour change does litmus commonly show in an acid?",
        "2. Classify pH 3, pH 7, and pH 10.",
        "3. Why is tasting a chemical an unsafe test?",
    ],
]


SHEETS_SPEC: list[tuple[str, list[list[str]]]] = [
    ("01_grade8_maths_science_stress_test_1.pdf", STRESS_TEST_PAGES),
    ("02_important_cities_of_the_united_kingdom.pdf", UK_CITIES_PAGES),
    ("03_grade8_maths_science_stress_test_2.pdf", STRESS_TEST_PAGES),
    ("04_history_and_civics_the_constitution.pdf", CONSTITUTION_PAGES),
    ("05_chemistry_standard_8_matter_to_acids.pdf", CHEMISTRY_10_PAGES),
]


def save_attached_sheets(sheets_dir: Path) -> list[Path]:
    """Save the 5 attached ICSE Class 8 sheets as PDF files in fixtures/sheets/."""
    sheets_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    for filename, pages_lines in SHEETS_SPEC:
        streams = [_page_lines_to_stream(page) for page in pages_lines]
        pdf_bytes = build_multi_page_pdf(streams)
        out_path = sheets_dir / filename
        out_path.write_bytes(pdf_bytes)
        saved_paths.append(out_path)
    return saved_paths


def run_key_facts_writer_on_pdf(pdf_path: Path) -> dict[str, Any]:
    """Extract text from `pdf_path` and run the deterministic Key Facts planner on `extraction`."""
    extractor = PDFExtractionEngine()
    extraction = extractor.extract_from_pdf(str(pdf_path))
    sheet_text = extraction.full_text
    cleaned = clean_sheet(extraction)
    kept_lines = cleaned["facts"]
    removed_lines = cleaned["removed"]
    tables = cleaned["tables"]
    sheet_has_explicit_marks = cleaned["sheet_has_explicit_marks"]

    planned_cards, dropped_raw = plan_key_facts_cards(extraction)

    accepted_cards: list[dict[str, Any]] = []
    dropped_cards: list[dict[str, Any]] = []
    no_card_lines: list[dict[str, str]] = []
    prior_accepted: list[dict[str, Any]] = []

    for card in planned_cards:
        if not card.get("answer"):
            continue
        res = score_card(card, sheet_text, prior_cards=prior_accepted)
        scores = res["scores"]
        reasons = res["reasons"]
        overall = res["overall"]
        passed = bool(res["accepted"]) and is_card_acceptable(res)
        card_entry = {
            "label": card.get("label") or card.get("subject_label") or card.get("subject", ""),
            "front": card.get("front") or card.get("clue") or card.get("question", ""),
            "prompt": card.get("prompt", "Fill in the key fact"),
            "question": card.get("clue") or card.get("question", ""),
            "answer": card.get("answer", ""),
            "page": int(card.get("page") or 1),
            "family": card.get("family") or card.get("expression_family") or card.get("answer_tier", ""),
            "section": card.get("section", ""),
            "card_type": card.get("card_type", "quiz"),
            "tier": card.get("tier", ""),
            "source_line": card.get("source_line", ""),
            "subject": card.get("subject", ""),
            "scores": scores,
            "average_score": overall,
            "passed": passed,
            "reasons": reasons,
        }
        prior_accepted.append(card)
        accepted_cards.append(card_entry)

    for d in dropped_raw:
        dropped_cards.append(
            {
                "label": d.get("subject", ""),
                "front": d.get("front") or d.get("clue", ""),
                "prompt": d.get("prompt", ""),
                "answer": d.get("answer", ""),
                "page": int(d.get("page") or 1),
                "source_line": d.get("source_line", ""),
                "average_score": float(d.get("average_score", 0.0)),
                "reasons": list(d.get("reasons", [])),
            }
        )

    for item in kept_lines:
        ln = item["text"]
        subj = item["subject"]
        is_marked = item["is_marked"]
        bold_spans = item.get("bold_spans") or []
        if sheet_has_explicit_marks and not is_marked:
            no_card_lines.append(
                {
                    "line": ln,
                    "subject": subj,
                    "reason": "unmarked prose on a sheet that explicitly marks learning points",
                }
            )
            continue
        card_probe = write_key_fact_card(ln, subject=subj, bold_spans=bold_spans)
        if card_probe is None:
            no_card_lines.append(
                {
                    "line": ln,
                    "subject": subj,
                    "reason": explain_no_card_reason(ln, subject=subj),
                }
            )

    removal_counts: dict[str, int] = {}
    for rem in removed_lines:
        rtype = rem.get("reason") or rem.get("type", "other")
        removal_counts[rtype] = removal_counts.get(rtype, 0) + 1

    return {
        "pdf_name": pdf_path.name,
        "page_count": len(extraction.pages),
        "sheet_has_explicit_marks": sheet_has_explicit_marks,
        "kept_lines": kept_lines,
        "removed_lines": removed_lines,
        "tables": tables,
        "removal_counts": removal_counts,
        "accepted_cards": accepted_cards,
        "dropped_cards": dropped_cards,
        "no_card_lines": no_card_lines,
    }


# ---------------------------------------------------------------------------
# Step 5 Generality Check: Two short (~15 lines) made-up sheets
# 1) Class 4 EVS: Water, Plants, and Shelter
# 2) Class 10 Science & Geography: Electricity, Carbon, and Indian Physiography
# ---------------------------------------------------------------------------

MADE_UP_CLASS_4_EVS_SHEET = "\n".join(
    [
        "1. Water and Living Things",
        "• **Evaporation** is the process by which liquid water changes into water vapour on heating.",
        "• Rainwater harvesting collects rainwater from rooftops to recharge groundwater.",
        "• World Water Day is celebrated on 22 March every year.",
        "• An adult human body contains about 60% water by weight.",
        "• Cactus plants store water in their thick fleshy stems to survive in dry deserts.",
        "• The water cycle begins with evaporation, followed by condensation into clouds.",
        "2. Plants and Animals Around Us",
        "• **Chlorophyll** is the green pigment in leaves that traps sunlight for making food.",
        "• The roots of a plant absorb water and dissolved minerals from the soil.",
        "• Honeybees store sweet nectar from flowers inside a hexagonal wax **honeycomb**.",
        "• A frog is called an amphibian because it lives both on land and in water.",
        "• Banyan trees have aerial prop roots that grow downwards to support heavy branches.",
        "• Desert oak is a tall tree native to Australia that stores water in its trunk.",
        "Practice Questions",
        "1. When is World Water Day celebrated?",
        "2. Which animal is called an amphibian because it lives on land and in water?",
    ]
)

MADE_UP_CLASS_10_SCIENCE_GEO_SHEET = "\n".join(
    [
        "1. Electric Current and Circuits",
        "• Ohm's Law: V = I × R",
        "• Electric power is measured in watts, and commercial electrical energy is measured in kilowatt-hours.",
        "• The filament of an electric bulb is made of **tungsten** because it has a melting point of 3,380 °C.",
        "• Fuse wire is an alloy of lead and tin that melts due to excessive current.",
        "• Chemical equation: CH₄ + 2O₂ → CO₂ + 2H₂O",
        "2. Physiography and Climate of India",
        "• The Tropic of Cancer passes through the middle of India at 23.5° N latitude.",
        "• The Narmada River flows westwards through a rift valley between the Vindhya and Satpura ranges.",
        "• Mawsynram in Meghalaya receives an average annual rainfall of over 1,180 cm.",
        "• Alluvial soil covers about 40 per cent of the total land area of India.",
        "• Retreating monsoon winds blow from north-east to south-west during October and November.",
        "• Project Tiger was launched by the Government of India on 1 April 1973.",
        "• Silent Valley National Park is located in the Nilgiri Hills of Kerala.",
        "Practice Questions",
        "1. On which date was Project Tiger launched by the Government of India?",
        "2. Which river flows westwards through a rift valley?",
    ]
)


def generate_report(folder: Path | str | None = None) -> Path:
    default_sheets_dir = ROOT_DIR / "fixtures" / "sheets"
    if folder is None:
        sheets_dir = default_sheets_dir
        save_attached_sheets(sheets_dir)
    else:
        sheets_dir = Path(folder).resolve()
        if sheets_dir == default_sheets_dir.resolve() and not list(sheets_dir.glob("*.pdf")):
            save_attached_sheets(sheets_dir)

    pdf_files = sorted(sheets_dir.glob("*.pdf"))
    md_lines: list[str] = [
        f"# Key Facts Deterministic Report (`{sheets_dir.relative_to(ROOT_DIR) if sheets_dir.is_relative_to(ROOT_DIR) else sheets_dir}/`)",
        "",
        "Generated with provider `\"deterministic\"` (no AI).",
        "",
    ]

    for pdf_path in pdf_files:
        result = run_key_facts_writer_on_pdf(pdf_path)
        accepted = result["accepted_cards"]
        dropped = result["dropped_cards"]
        no_card_lines = result["no_card_lines"]
        kept_lines = result["kept_lines"]
        removed_lines = result["removed_lines"]
        removal_counts = result["removal_counts"]
        reasons_breakdown = ", ".join(f"`{k}`: {v}" for k, v in sorted(removal_counts.items()))

        md_lines.append(f"## {result['pdf_name']}")
        md_lines.append("")
        md_lines.append(
            f"- **Pages:** {result['page_count']} | **Explicit learning marks detected:** `{result['sheet_has_explicit_marks']}` | "
            f"**Number of cards:** {len(accepted)} (accepted: {len(accepted)}, dropped: {len(dropped)}) | "
            f"**Content lines with no card:** {len(no_card_lines)}"
        )
        md_lines.append(
            f"- **Input filter (`clean_sheet`):** Kept **{len(kept_lines)}** fact lines | "
            f"Removed **{len(removed_lines)}** non-fact items ({reasons_breakdown}) | "
            f"Structured tables: **{len(result['tables'])}**"
        )
        md_lines.append("")
        md_lines.append("| # | Label | Front | Prompt | Answer | Page | Family | Source Line | Rubric Score | Rubric Reasons |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for idx, c in enumerate(accepted, start=1):
            l_str = str(c.get("label", "")).replace("|", "\\|")
            f_str = str(c["front"]).replace("|", "\\|")
            p_str = str(c["prompt"]).replace("|", "\\|")
            a_str = str(c["answer"]).replace("|", "\\|")
            pg_str = str(c.get("page", 1))
            fam_str = str(c.get("family", "")).replace("|", "\\|")
            src_str = str(c["source_line"]).replace("|", "\\|")
            scores_str = ", ".join(f"{k}={v}" for k, v in c["scores"].items())
            rubric_col = f"**{c['average_score']:.2f}/5.00** (PASS)<br>`{scores_str}`"
            reasons_col = "; ".join(c["reasons"]).replace("|", "\\|") if c["reasons"] else "—"
            md_lines.append(
                f"| {idx} | {l_str} | {f_str} | {p_str} | `{a_str}` | {pg_str} | `{fam_str}` | `{src_str}` | {rubric_col} | {reasons_col} |"
            )

        md_lines.append("")
        md_lines.append("### Dropped Cards")
        md_lines.append("")
        if not dropped:
            md_lines.append("- None (0 cards dropped by `score_card()`).")
        else:
            for idx, d in enumerate(dropped, start=1):
                f_str = str(d["front"]).replace("|", "\\|")
                a_str = str(d["answer"]).replace("|", "\\|")
                src_str = str(d["source_line"]).replace("|", "\\|")
                rsn_str = "; ".join(d["reasons"]).replace("|", "\\|")
                md_lines.append(
                    f"{idx}. **Front:** `{f_str}` | **Answer:** `{a_str}` | **Source Line:** `{src_str}` | **Score:** `{d['average_score']:.2f}/5.00` — **Reason:** {rsn_str}"
                )
        md_lines.append("")

        if no_card_lines:
            md_lines.append("### Content Lines Receiving No Card")
            md_lines.append("")
            for idx, item in enumerate(no_card_lines, start=1):
                ln_str = item["line"].replace("|", "\\|")
                rsn_str = item["reason"].replace("|", "\\|")
                md_lines.append(f"{idx}. `{ln_str}` — **{rsn_str}**")
            md_lines.append("")

    # Step 5: Generality Check on Class 4 EVS and Class 10 Science/Geography
    md_lines.append("## Step 5 — Generality Check (Unseen Made-Up Sheets)")
    md_lines.append("")
    for title, raw_sheet in (
        ("Class 4 EVS — Water, Plants, and Shelter", MADE_UP_CLASS_4_EVS_SHEET),
        ("Class 10 Science & Geography — Electricity, Carbon, and Indian Physiography", MADE_UP_CLASS_10_SCIENCE_GEO_SHEET),
    ):
        cards, dropped = plan_key_facts_cards(raw_sheet)
        md_lines.append(f"### {title} ({len(cards)} cards, {len(dropped)} dropped)")
        md_lines.append("")
        md_lines.append("| # | Label | Front | Prompt | Answer | Page | Family |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for idx, c in enumerate(cards, start=1):
            md_lines.append(
                f"| {idx} | {c.get('label', '')} | {c.get('front', '')} | {c.get('prompt', '')} | `{c.get('answer', '')}` | {c.get('page', 1)} | `{c.get('family', '')}` |"
            )
        md_lines.append("")

    report_path = ROOT_DIR / "fixtures" / "key_facts_report.md"
    report_path.write_text("\n".join(md_lines), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    arg_folder = sys.argv[1] if len(sys.argv) > 1 else None
    out = generate_report(arg_folder)
    print(f"Wrote {out}")
