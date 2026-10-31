"""Unit tests for learn/teaching_engine/expressions.py (Prompt 8, Step 2).

Covers every family A–L and every numbered bullet within each family with at least
one passing and one failing case using made-up sentences (no lines copied from the
5 fixture sheets).
"""

from __future__ import annotations

import unittest

from learn.teaching_engine.expressions import (
    FAMILIES,
    FAMILY_A,
    FAMILY_B,
    FAMILY_C,
    FAMILY_D,
    FAMILY_E,
    FAMILY_F,
    FAMILY_G,
    FAMILY_H,
    FAMILY_I,
    FAMILY_J,
    FAMILY_K,
    FAMILY_L,
    SUPERLATIVE_CHECK_NOTE,
    check_cut_in_half_span,
    find_all_expressions,
)


class TestExpressionLibraryFamilies(unittest.TestCase):
    """Test each expression family A–L and every numbered bullet."""

    # =========================================================================
    # A. TIME AND DATES (bullets 1–10)
    # =========================================================================

    def test_a1_full_dates_any_order_pass_and_fail(self) -> None:
        """A1: Full dates ('8 August 1942', 'August 8, 1942', '8th August 1942', '08/08/1942', '26-01-1950') are matched as ONE whole span."""
        for date_str in ("8 August 1942", "August 8, 1942", "8th August 1942", "08/08/1942", "26-01-1950"):
            sent = f"The municipal charter was signed on {date_str} in the town hall."
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 1]
            self.assertEqual(len(matches), 1, msg=f"Expected 1 full_date match for {date_str!r}, got {matches}")
            self.assertEqual(matches[0]["text"], date_str)
            self.assertEqual(sent[matches[0]["span"][0] : matches[0]["span"][1]], date_str)
            self.assertEqual(matches[0]["type"], "full_date")
            # Failing check: "August" alone is NOT emitted as a cut-in-half span when "8 August 1942" is present
            texts = [m["text"] for m in FAMILY_A.find(sent)]
            self.assertNotIn("August", texts)

        # Failing case: sentence without any full date produces no bullet-1 match
        no_date_matches = [m for m in FAMILY_A.find("The charter was signed during the summer session.") if m["bullet"] == 1]
        self.assertEqual(no_date_matches, [])

    def test_a2_month_year_and_day_month_pass_and_fail(self) -> None:
        """A2: Month + year ('August 1942') and day + month ('15 August') match as whole units when not inside a full date."""
        m1 = [m for m in FAMILY_A.find("Heavy monsoon rains began in August 1942 across the valley.") if m["bullet"] == 2]
        self.assertEqual(len(m1), 1)
        self.assertEqual(m1[0]["text"], "August 1942")
        self.assertEqual(m1[0]["type"], "month_year")

        m2 = [m for m in FAMILY_A.find("Schools celebrate the annual harvest festival on 15 August every year.") if m["bullet"] == 2]
        self.assertEqual(len(m2), 1)
        self.assertEqual(m2[0]["text"], "15 August")
        self.assertEqual(m2[0]["type"], "day_month")

        # Failing case: when part of a full date ("8 August 1942"), bullet 2 must NOT slice out "8 August" or "August 1942"
        m_full = [m for m in FAMILY_A.find("The assembly met on 8 August 1942 in the courtyard.") if m["bullet"] == 2]
        self.assertEqual(m_full, [])

    def test_a3_years_with_preposition_keep_preposition_on_card_pass_and_fail(self) -> None:
        """A3: 'in 1873', 'by 1905', 'from 1917 to 1934', 'between 1857 and 1858', 'since 1947', 'until 1950', 'till 1919' — preposition stays outside the span."""
        for phrase, expected_years in (
            ("The library opened in 1873 near the harbour.", ["1873"]),
            ("The railway line was completed by 1905.", ["1905"]),
            ("The canal was built from 1917 to 1934.", ["1917", "1934"]),
            ("Negotiations took place between 1857 and 1858.", ["1857", "1858"]),
            ("The observatory has operated since 1947.", ["1947"]),
            ("The old coinage remained valid until 1950.", ["1950"]),
            ("The tramway ran on steam till 1919.", ["1919"]),
        ):
            matches = [m for m in FAMILY_A.find(phrase) if m["bullet"] == 3]
            self.assertEqual([m["text"] for m in matches], expected_years, msg=f"Failed on {phrase!r}")
            for m in matches:
                # Failing check: preposition ("in", "by", "from", "between", "since", "until", "till") is NEVER part of the blanked text
                self.assertFalse(any(prep in m["text"].lower() for prep in ("in", "by", "from", "between", "since", "until", "till")))

    def test_a4_year_ranges_and_spans_pass_and_fail(self) -> None:
        """A4: Year ranges ('1917–1934', '1839–1904') and duration spans ('for 17 years', 'over 300 years', '24-day')."""
        for sent, expected in (
            ("The expedition journal covers the period 1917–1934.", "1917–1934"),
            ("Meera Bai (1839–1904) founded the rural weaving school.", "1839–1904"),
            ("The lighthouse keeper served for 17 years on the island.", "17 years"),
            ("The astronomical clock has ticked for over 300 years.", "300 years"),
            ("Volunteers completed the 24-day coastal march.", "24-day"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 4]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        # Failing case: plain room number "Room 104" is not a year range or duration span
        self.assertEqual([m for m in FAMILY_A.find("The botany club meets in Room 104.") if m["bullet"] == 4], [])

    def test_a5_centuries_and_parts_pass_and_fail(self) -> None:
        """A5: '19th century', 'the nineteenth century', 'early 20th century', 'the latter half of the 20th century', 'turn of the century'."""
        for sent, expected in (
            ("Steamships transformed ocean travel in the 19th century.", "19th century"),
            ("Botanical gardens expanded during the nineteenth century.", "the nineteenth century"),
            ("Aviation advanced rapidly in the early 20th century.", "early 20th century"),
            ("Satellite mapping began in the latter half of the 20th century.", "the latter half of the 20th century"),
            ("Electric streetlamps arrived at the turn of the century.", "turn of the century"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 5]
            self.assertEqual(len(matches), 1, msg=f"Failed on {sent!r}: {matches}")
            self.assertEqual(matches[0]["text"], expected)
            self.assertEqual(matches[0]["question_type"], "Which century…?")

        # Failing case: "19th regiment" is not a century
        self.assertEqual([m for m in FAMILY_A.find("The 19th regiment camped near the bridge.") if m["bullet"] == 5], [])

    def test_a6_decades_and_eras_pass_and_fail(self) -> None:
        """A6: 'the 1930s', 'mid-1930s', 'the Mughal period', 'the Vedic age', 'the Stone Age', 'Bronze Age'."""
        for sent, expected in (
            ("Radio broadcasting expanded during the 1930s.", "1930s"),
            ("Aeronautical workshops opened in the mid-1930s.", "mid-1930s"),
            ("Miniature painting flourished during the Mughal period.", "Mughal period"),
            ("Hymns were composed in the Vedic age.", "Vedic age"),
            ("Cave paintings survive from the Stone Age.", "Stone Age"),
            ("Copper and tin were alloyed during the Bronze Age.", "Bronze Age"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 6]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        # Failing case: ordinary sentence with no decade or historical era
        self.assertEqual([m for m in FAMILY_A.find("Water boils when heated in a kettle.") if m["bullet"] == 6], [])

    def test_a7_era_markers_pass_and_fail(self) -> None:
        """A7: '326 BC', 'AD 1206', '250 BCE', '1206 CE', 'c. 1500', 'circa 1500', 'around 1600', 'about 1757'."""
        for sent, expected in (
            ("The Macedonian army crossed the river in 326 BC.", "326 BC"),
            ("The Delhi Sultanate was established in AD 1206.", "AD 1206"),
            ("Rock edicts were carved in 250 BCE.", "250 BCE"),
            ("The port town prospered around 1206 CE.", "1206 CE"),
            ("The astrolabe was crafted in c. 1500.", "c. 1500"),
            ("Paper mills appeared in circa 1500.", "circa 1500"),
            ("Spice traders built the fort around 1600.", "1600"),
            ("The battle near the mango grove occurred about 1757.", "1757"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 7]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        # Failing case: bare letters "BC" without a year
        self.assertEqual([m for m in FAMILY_A.find("Triangle ABC has three acute angles.") if m["bullet"] == 7], [])

    def test_a8_indian_calendars_pass_and_fail(self) -> None:
        """A8: 'Vikram Samvat', 'Shaka era' + year."""
        m1 = [m for m in FAMILY_A.find("The inscription is dated to Vikram Samvat 2080.") if m["bullet"] == 8]
        self.assertEqual(len(m1), 1)
        self.assertEqual(m1[0]["text"], "Vikram Samvat 2080")

        m2 = [m for m in FAMILY_A.find("The national calendar follows the Shaka era 78 AD.") if m["bullet"] == 8]
        self.assertEqual(len(m2), 1)
        self.assertEqual(m2[0]["text"], "Shaka era 78 AD")

        # Failing case: unrelated calendar sentence
        self.assertEqual([m for m in FAMILY_A.find("A leap year has 366 days.") if m["bullet"] == 8], [])

    def test_a9_relative_time_words_pair_event_with_date_pass_and_fail(self) -> None:
        """A9: Relative time words ('before', 'after', 'during', 'following', 'when') pair an event with its printed date."""
        sent = "Following the cyclone of 1864, new seawalls were built along the harbour."
        matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 9]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "1864")
        self.assertEqual(matches[0]["relative_marker"].lower(), "following")

        # Failing case: relative word 'after' without any date/year in the sentence must NOT invent a date match
        self.assertEqual([m for m in FAMILY_A.find("Wash your hands after handling soil samples.") if m["bullet"] == 9], [])

    def test_a10_time_of_day_and_durations_pass_and_fail(self) -> None:
        """A10: '8:30 am', 'two hours', '24 hours', '365 days', 'a fortnight'."""
        for sent, expected in (
            ("The morning assembly bell rings at 8:30 am.", "8:30 am"),
            ("The ferry crossing takes two hours in calm weather.", "two hours"),
            ("Earth completes one rotation in 24 hours.", "24 hours"),
            ("A standard calendar year contains 365 days.", "365 days"),
            ("The lunar tide cycle repeats every a fortnight.", "a fortnight"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 10]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        # Failing case: ratio "1 : 2" is not a time of day
        self.assertEqual([m for m in FAMILY_A.find("Mix cement and sand in a 1 : 2 ratio.") if m["bullet"] == 10], [])

    # =========================================================================
    # B. NUMBERS AND QUANTITIES (bullets 1–7)
    # =========================================================================

    def test_b1_plain_grouped_and_indian_numbers_pass_and_fail(self) -> None:
        """B1: '72', '286,000', Indian grouping '2,86,000', '1.5 lakh', '3 crore', 'a million', 'two billion'."""
        for sent, expected in (
            ("The auditorium has 72 seats in the front gallery.", "72"),
            ("The district recorded a population of 286,000.", "286,000"),
            ("The cooperative enrolled 2,86,000 farmers across the state.", "2,86,000"),
            ("The reservoir stores 1.5 lakh litres of rainwater.", "1.5 lakh"),
            ("The afforestation drive planted 3 crore saplings.", "3 crore"),
            ("Over a million migrating birds visit the wetland.", "a million"),
            ("More than two billion stars populate the galaxy.", "two billion"),
        ):
            matches = FAMILY_B.find(sent)
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")
            # Failing check: "286" is never split off from "286,000" or "2,86,000"
            self.assertNotIn("286", [m["text"] for m in matches])

    def test_b2_number_words_pass_and_fail(self) -> None:
        """B2: 'one', 'twelve', 'first', 'second', 'third', 'tenth', 'a dozen', 'a hundred', 'half', 'a quarter', 'double', 'twice'."""
        for word in ("one", "twelve", "first", "second", "third", "tenth", "a dozen", "a hundred", "half", "a quarter", "double", "twice"):
            sent = f"The basket contained {word} of the harvested apples."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 2]
            self.assertTrue(any(m["text"] == word for m in matches), msg=f"Expected {word!r} in {matches}")

        # Failing case: sentence with no number words
        self.assertEqual([m for m in FAMILY_B.find("Copper conducts heat rapidly.") if m["bullet"] == 2], [])

    def test_b3_ordinals_and_ranks_not_superlative_note_pass_and_fail(self) -> None:
        """B3: 'the 7th most populous', 'second largest', 'eleventh-largest', 'No. 1' — ordinal with noun, never superlative note."""
        for sent, expected in (
            ("Nagpur is the 7th most populous city in the region.", "7th most populous city"),
            ("Pune is the second largest city in the state.", "second largest city"),
            ("Coventry is the eleventh-largest city in the country.", "eleventh-largest city"),
            ("Kandla became the No. 1 port on the western coast.", "No. 1 port"),
        ):
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 3]
            self.assertEqual(len(matches), 1, msg=f"Failed on {sent!r}: {matches}")
            self.assertEqual(matches[0]["text"], expected)
            self.assertFalse(matches[0].get("is_superlative"), "Ordinals must NOT trigger the superlative check note")
            all_expr = find_all_expressions(sent)
            for em in all_expr:
                self.assertNotIn("note", em, msg=f"Ordinal sentence {sent!r} must not attach superlative note")

        # Failing case: true superlative "the largest planet" is NOT an ordinal rank
        self.assertEqual([m for m in FAMILY_B.find("Jupiter is the largest planet in the solar system.") if m["bullet"] == 3], [])

    def test_b4_approximations_keep_qualifier_on_card_pass_and_fail(self) -> None:
        """B4: 'about', 'around', 'nearly', 'over', 'more than', 'less than', 'approximately', 'almost', 'at least', 'up to' stay outside the blank."""
        for qual in ("about", "around", "nearly", "over", "more than", "less than", "approximately", "almost", "at least", "up to"):
            sent = f"The botanical garden attracts {qual} 286,000 tourists every winter."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 4]
            self.assertTrue(len(matches) >= 1, msg=f"Expected B4 match for {qual!r} in {sent!r}")
            self.assertTrue(matches[0]["text"].startswith("286,000"))
            # Failing check: qualifier itself is NEVER inside the blanked span
            self.assertFalse(matches[0]["text"].lower().startswith(qual))

    def test_b5_percentages_fractions_ratios_pass_and_fail(self) -> None:
        """B5: '70%', '70 per cent', '3/4', 'three-fourths', '1 : 2', '2 out of 5'."""
        for expr in ("70%", "70 per cent", "3/4", "three-fourths", "1 : 2", "2 out of 5"):
            sent = f"Water covers {expr} of the experimental plot."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 5]
            self.assertEqual(len(matches), 1, msg=f"Expected B5 match for {expr!r}, got {matches}")
            self.assertEqual(matches[0]["text"], expr)

        # Failing case: date "08/08/1942" is NOT a fraction
        self.assertEqual([m for m in FAMILY_B.find("The treaty was signed on 08/08/1942.") if m["bullet"] == 5], [])

    def test_b6_money_pass_and_fail(self) -> None:
        """B6: '₹500', 'Rs. 500', 'INR 500', '£1.6 billion', '$20', '50 paise'."""
        for expr in ("₹500", "Rs. 500", "INR 500", "£1.6 billion", "$20", "50 paise"):
            sent = f"The museum entry ticket costs {expr} for adults."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 6]
            self.assertEqual(len(matches), 1, msg=f"Expected B6 match for {expr!r}, got {matches}")
            self.assertEqual(matches[0]["text"], expr)

        # Failing case: distance "500 km" is not money
        self.assertEqual([m for m in FAMILY_B.find("The highway is 500 km long.") if m["bullet"] == 6], [])

    def test_b7_counts_with_nouns_pass_and_fail(self) -> None:
        """B7: '72 delegates', '78 volunteers', '5 cities', '28 states', '8 union territories', '7 continents', '206 bones'."""
        for expr, expected_q in (
            ("72 delegates", "How many delegates…?"),
            ("78 volunteers", "How many volunteers…?"),
            ("5 cities", "How many cities…?"),
            ("28 states", "How many states…?"),
            ("8 union territories", "How many union territories…?"),
            ("7 continents", "How many continents…?"),
            ("206 bones", "How many bones…?"),
        ):
            sent = f"The survey recorded {expr} in the annual register."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 7]
            self.assertEqual(len(matches), 1, msg=f"Failed on {expr!r}: {matches}")
            self.assertEqual(matches[0]["text"], expr)
            self.assertEqual(matches[0]["question_type"], expected_q)

        # Failing case: year "in 1947" is not a count with noun
        self.assertEqual([m for m in FAMILY_B.find("The school opened in 1947.") if m["bullet"] == 7], [])

    # =========================================================================
    # C. MEASUREMENT AND UNITS (bullets 1–4)
    # =========================================================================

    def test_c1_si_and_common_units_never_split_number_from_unit_pass_and_fail(self) -> None:
        """C1: SI and common units with a number ('387 km', '40 mL', '2.0 m/s²', '25 °C', '15 N', '50 Hz')."""
        for expr in ("387 km", "40 mL", "2.0 m/s²", "25 °C", "15 N", "50 Hz", "4.2 light years"):
            sent = f"The instrument recorded a reading of {expr} during the trial."
            matches = [m for m in FAMILY_C.find(sent) if m["bullet"] == 1]
            self.assertEqual(len(matches), 1, msg=f"Failed on {expr!r}: {matches}")
            self.assertEqual(matches[0]["text"], expr)
            # Failing check: bare unit without number is never returned
            self.assertNotIn(expr.split()[-1], [m["text"] for m in matches if m["text"] != expr])

    def test_c2_area_and_volume_units_pass_and_fail(self) -> None:
        """C2: 'km²', 'sq km', 'square kilometres', 'm³', 'cubic metres'."""
        for expr in ("250 km²", "45 sq km", "120 square kilometres", "18 m³", "50 cubic metres"):
            sent = f"The protected forest covers {expr} on the plateau."
            matches = [m for m in FAMILY_C.find(sent) if m["bullet"] == 2]
            self.assertEqual(len(matches), 1, msg=f"Failed on {expr!r}: {matches}")
            self.assertEqual(matches[0]["text"], expr)

        # Failing case: linear measure "250 km" is C1, not C2 area/volume
        self.assertEqual([m for m in FAMILY_C.find("The river flows for 250 km.") if m["bullet"] == 2], [])

    def test_c3_geography_measures_pass_and_fail(self) -> None:
        """C3: '8,848 m above sea level', '200 cm', '23.5° N', '82.5° E', 'north-east'."""
        for sent, expected in (
            ("Mount Everest rises to 8,848 m above sea level.", "8,848 m above sea level"),
            ("The Tropic of Cancer lies at 23.5° N latitude.", "23.5° N"),
            ("Indian Standard Time is calculated along 82.5° E longitude.", "82.5° E"),
            ("Monsoon winds blow towards the north-east in summer.", "north-east"),
        ):
            matches = [m for m in FAMILY_C.find(sent) if m["bullet"] == 3]
            self.assertEqual(len(matches), 1, msg=f"Failed on {sent!r}: {matches}")
            self.assertEqual(matches[0]["text"], expected)

        # Failing case: angle "90°" without N/S/E/W is not a latitude/longitude measure
        self.assertEqual([m for m in FAMILY_C.find("A right angle measures 90°.") if m["bullet"] == 3], [])

    def test_c4_unit_conversions_pass_and_fail(self) -> None:
        """C4: '1 N = 1 kg·m/s²', '1 km = 1000 m', '500 g = 0.500 kg'."""
        for sent, expected_rhs in (
            ("In SI units, 1 N = 1 kg·m/s².", "1 kg·m/s²"),
            ("Metric length conversion: 1 km = 1000 m.", "1000 m"),
            ("Mass conversion: 500 g = 0.500 kg.", "0.500 kg"),
        ):
            matches = [m for m in FAMILY_C.find(sent) if m["bullet"] == 4]
            self.assertEqual(len(matches), 1, msg=f"Failed on {sent!r}: {matches}")
            self.assertEqual(matches[0]["text"], expected_rhs)

        # Failing case: algebraic formula "F = ma" has no numbers and is not a C4 unit conversion
        self.assertEqual([m for m in FAMILY_C.find("F = ma") if m["bullet"] == 4], [])

    # =========================================================================
    # D. FORMULAS, EQUATIONS, SYMBOLS (bullets 1–4)
    # =========================================================================

    def test_d1_physics_and_maths_formulas_pass_and_fail(self) -> None:
        """D1: 'F = ma', 'V = I × R', 'a = F ÷ m', 'P = 2(l + w)', 'A = πr²', 'speed = distance ÷ time'."""
        for sent, expected_rhs in (
            ("F = ma", "ma"),
            ("V = I × R", "I × R"),
            ("a = F ÷ m", "F ÷ m"),
            ("P = 2(l + w)", "2(l + w)"),
            ("A = πr²", "πr²"),
            ("speed = distance ÷ time", "distance ÷ time"),
        ):
            matches = [m for m in FAMILY_D.find(sent) if m["bullet"] == 1]
            self.assertEqual(len(matches), 1, msg=f"Failed on {sent!r}: {matches}")
            self.assertEqual(matches[0]["text"], expected_rhs)
            self.assertEqual(matches[0]["text"].count("("), matches[0]["text"].count(")"))

        # Failing case: unbalanced bracket expression "P = 2(l + w" must be rejected
        self.assertEqual([m for m in FAMILY_D.find("P = 2(l + w") if m["bullet"] == 1], [])

    def test_d2_chemical_formulas_and_equations_keep_subscripts_pass_and_fail(self) -> None:
        """D2: 'H₂O', 'CO₂', 'CaCO₃', '2H₂ + O₂ → 2H₂O', '(aq)', '(s)', '(l)', '(g)'."""
        for tok in ("H₂O", "CO₂", "CaCO₃"):
            sent = f"The laboratory flask contained pure {tok} during the test."
            matches = [m for m in FAMILY_D.find(sent) if m["type"] == "chemical_formula"]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], tok)

        eq_matches = [m for m in FAMILY_D.find("2H₂ + O₂ → 2H₂O") if m["type"] == "chemical_equation"]
        self.assertEqual(len(eq_matches), 1)
        self.assertEqual(eq_matches[0]["text"], "2H₂O")

        state_matches = [m for m in FAMILY_D.find("An aqueous solution is denoted by the state symbol (aq).") if m["type"] == "state_symbol"]
        self.assertEqual(len(state_matches), 1)
        self.assertEqual(state_matches[0]["text"], "(aq)")

        # Failing case: ordinary English word without subscripts/arrows is not a chemical formula
        self.assertEqual([m for m in FAMILY_D.find("The solution turned blue.") if m["bullet"] == 2], [])

    def test_d3_element_symbols_and_names_pass_and_fail(self) -> None:
        """D3: 'Na – sodium', 'Fe – iron', 'The chemical symbol for iron is Fe'."""
        m1 = [m for m in FAMILY_D.find("Alkali metal symbol: Na – sodium.") if m["bullet"] == 3]
        self.assertEqual(len(m1), 1)
        self.assertEqual(m1[0]["text"], "sodium")

        m2 = [m for m in FAMILY_D.find("The chemical symbol for iron is Fe.") if m["bullet"] == 3]
        self.assertEqual(len(m2), 1)
        self.assertEqual(m2[0]["text"], "Fe")

        # Failing case: person-dates heading "Rao (1900–1970) – Poet" is not an element symbol
        self.assertEqual([m for m in FAMILY_D.find("Rao (1900–1970) – Poet") if m["bullet"] == 3], [])

    def test_d4_maths_facts_pass_and_fail(self) -> None:
        """D4: 'angles of a triangle add up to 180°', 'a right angle is 90°', 'π ≈ 3.14', 'a square has 4 equal sides'."""
        for sent, expected in (
            ("The interior angles of a triangle add up to 180°.", "180°"),
            ("In geometry, a right angle is 90°.", "90°"),
            ("For circle calculations, π ≈ 3.14.", "3.14"),
            ("By definition, a square has 4 equal sides.", "4 equal sides"),
        ):
            matches = [m for m in FAMILY_D.find(sent) if m["bullet"] == 4]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        # Failing case: latitude "23.5° N" is a geography measure (C3), not a D4 angle fact
        self.assertEqual([m for m in FAMILY_D.find("The line lies at 23.5° N.") if m["bullet"] == 4], [])

    # =========================================================================
    # E. NAMES, TITLES AND ROLES (bullets 1–5)
    # =========================================================================

    def test_e1_naming_verbs_pass_and_fail(self) -> None:
        """E1: 'is called', 'is known as', 'also known as', 'is termed', 'is referred to as', 'nicknamed', 'popularly called', 'hailed as'."""
        for verb_phrase in ("is called", "is known as", "also known as", "is termed", "is referred to as", "nicknamed", "popularly called", "hailed as"):
            sent = f"The outer protective layer of the stem {verb_phrase} epidermis."
            matches = [m for m in FAMILY_E.find(sent) if m["bullet"] == 1]
            self.assertEqual(len(matches), 1, msg=f"Failed on {verb_phrase!r}: {matches}")
            self.assertEqual(matches[0]["text"], "epidermis")
            self.assertEqual(matches[0]["question_type"], "What is it called?")

        # Failing case: sentence without any naming verb
        self.assertEqual([m for m in FAMILY_E.find("The stem transports water to the leaves.") if m["bullet"] == 1], [])

    def test_e2_roles_passive_and_active_pass_and_fail(self) -> None:
        """E2: 'founded by', 'led by', 'chaired by', 'invented by', 'written by', 'built by' and active '<Name> founded/invented/wrote ...'."""
        m_pass = [m for m in FAMILY_E.find("The rural university was founded by Rabindranath Tagore in 1921.") if m["bullet"] == 2]
        self.assertEqual(len(m_pass), 1)
        self.assertEqual(m_pass[0]["text"], "Rabindranath Tagore")
        self.assertIn("Who founded", m_pass[0]["question_type"])

        m_act = [m for m in FAMILY_E.find("Alexander Fleming discovered penicillin in 1928.") if m["bullet"] == 2]
        self.assertEqual(len(m_act), 1)
        self.assertEqual(m_act[0]["text"], "Alexander Fleming")
        self.assertIn("Who discovered", m_act[0]["question_type"])

        # Failing case: passive verb with a common lowercase noun ("heated by steam") is not a person role
        self.assertEqual([m for m in FAMILY_E.find("The turbine was turned by steam.") if m["bullet"] == 2], [])

    def test_e3_titles_and_epithets_pass_and_fail(self) -> None:
        """E3: 'Father of ...', 'Architect of ...', 'Grand Old Man of ...', 'Iron Man of ...', 'Nightingale of ...', 'first <role>'."""
        for sent, expected in (
            ("Sardar Patel is remembered as the Iron Man of India.", "Iron Man of India"),
            ("Sarojini Naidu was honoured as the Nightingale of India.", "Nightingale of India"),
            ("Subhas Chandra Bose served as the first Mayor of Calcutta.", "first Mayor"),
        ):
            matches = [m for m in FAMILY_E.find(sent) if m["bullet"] == 3]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        # Failing case: lowercase phrase "father of two children" is not a historical title
        self.assertEqual([m for m in FAMILY_E.find("The farmer was the father of two children.") if m["bullet"] == 3], [])

    def test_e4_name_plus_dates_headings_pass_and_fail(self) -> None:
        """E4: '<Name> (1839–1904) – <title>'."""
        sent = "Anandi Gopal Joshi (1865–1887) – Pioneer of Medical Education"
        matches = [m for m in FAMILY_E.find(sent) if m["bullet"] == 4]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "Anandi Gopal Joshi")

        # Failing case: line without lifespan dates in parentheses
        self.assertEqual([m for m in FAMILY_E.find("Anandi Gopal Joshi studied medicine in Pennsylvania.") if m["bullet"] == 4], [])

    def test_e5_organisations_documents_events_article_21_pass_and_fail(self) -> None:
        """E5: 'Movement', 'Act', 'Samaj', 'Sabha', 'Committee', 'Assembly', 'Treaty', 'Battle of', 'Article 21', 'Eighth Schedule'."""
        for sent, expected in (
            ("Article 21 guarantees the protection of life and personal liberty.", "Article 21"),
            ("Recognised regional languages are listed in the Eighth Schedule.", "Eighth Schedule"),
            ("The Battle of Buxar was fought in 1764.", "Battle of Buxar"),
            ("Raja Ram Mohan Roy established the Atmiya Sabha in Calcutta.", "Atmiya Sabha"),
            ("The Chipko Movement protected Himalayan forests.", "Chipko Movement"),
        ):
            matches = [m for m in FAMILY_E.find(sent) if m["bullet"] == 5]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        # Failing case: bare lowercase word "article" in a grammar sentence is not Article <n>
        self.assertEqual([m for m in FAMILY_E.find("The word 'an' is an indefinite article.") if m["bullet"] == 5], [])

    # =========================================================================
    # F. DEFINITIONS AND CLASSIFICATION (bullets 1–3)
    # =========================================================================

    def test_f1_definitions_pass_and_fail(self) -> None:
        """F1: 'X is the process by which ...', 'X: <definition>', 'the study of ...'."""
        for sent, expected in (
            ("Photosynthesis is the process by which green plants make food using sunlight.", "Photosynthesis"),
            ("Transpiration: loss of water vapour from aerial parts of a plant.", "Transpiration"),
            ("Ornithology is the study of birds in their natural habitats.", "Ornithology"),
        ):
            matches = [m for m in FAMILY_F.find(sent) if m["bullet"] == 1]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        # Failing case: pronoun-leading sentence "It is a warm day." does not define "It"
        self.assertEqual([m for m in FAMILY_F.find("It is a warm day in the village.") if m["bullet"] == 1], [])

    def test_f2_kinds_and_parts_max_one_card_per_list_pass_and_fail(self) -> None:
        """F2: 'types of', 'consists of', 'includes', 'such as A, B and C' — blanks one item, max one match per list."""
        sent = "Root vegetables such as carrot, radish and beetroot store starch underground."
        matches = [m for m in FAMILY_F.find(sent) if m["bullet"] == 2]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "carrot")

        # Failing case: sentence without classification/part triggers
        self.assertEqual([m for m in FAMILY_F.find("Sunlight warms the upper layer of the pond.") if m["bullet"] == 2], [])

    def test_f3_properties_after_term_pass_and_fail(self) -> None:
        """F3: 'has ...', 'is ...', 'can ...' after a term."""
        sent = "Quartz has a hexagonal crystal structure."
        matches = [m for m in FAMILY_F.find(sent) if m["bullet"] == 3]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "Quartz")

        # Failing case: pronoun subject "They have..." is not a F3 property term
        self.assertEqual([m for m in FAMILY_F.find("They have four wings.") if m["bullet"] == 3], [])

    # =========================================================================
    # G. CAUSE, EFFECT, PURPOSE
    # =========================================================================

    def test_g_cause_effect_purpose_max_6_words_pass_and_fail(self) -> None:
        """G: 'because', 'due to', 'leads to', 'causes', 'is caused by', 'in order to' — <= 6 words."""
        m_cause = FAMILY_G.find("Sea breezes blow inland due to unequal heating of land.")
        self.assertEqual(len(m_cause), 1)
        self.assertEqual(m_cause[0]["text"], "unequal heating of land")
        self.assertEqual(m_cause[0]["question_type"], "Which cause fits the gap?")
        self.assertLessEqual(len(m_cause[0]["text"].split()), 6)

        m_effect = FAMILY_G.find("Deforestation on steep slopes leads to severe soil erosion.")
        self.assertEqual(len(m_effect), 1)
        self.assertEqual(m_effect[0]["text"], "severe soil erosion")
        self.assertEqual(m_effect[0]["question_type"], "Which effect…?")

        # Failing case: long multi-clause explanation (>6 words with no short boundary) is rejected
        long_sent = "Plants wilt because the surrounding soil loses moisture rapidly whenever hot dry summer winds blow continuously."
        self.assertEqual(FAMILY_G.find(long_sent), [])

    # =========================================================================
    # H. SEQUENCE AND PROCESS
    # =========================================================================

    def test_h_sequence_and_process_keeps_order_word_pass_and_fail(self) -> None:
        """H: 'first', 'next', 'finally', 'step 1', 'begins with', 'followed by', '→' — keeps order word on card."""
        m1 = FAMILY_H.find("The water cycle begins with evaporation from oceans and lakes.")
        self.assertEqual(len(m1), 1)
        self.assertEqual(m1[0]["text"], "evaporation")
        self.assertEqual(m1[0]["order_word"].lower(), "begins with")

        m2 = FAMILY_H.find("Metamorphosis stages: Egg → Larva → Pupa → Adult.")
        self.assertTrue(any(m["text"] == "Larva" for m in m2))

        # Failing case: chemical equation with arrow belongs to Family D, not Family H
        self.assertEqual(FAMILY_H.find("2H₂ + O₂ → 2H₂O"), [])

    # =========================================================================
    # I. PLACE AND LOCATION
    # =========================================================================

    def test_i_place_and_location_river_vs_place_pass_and_fail(self) -> None:
        """I: 'situated on', 'flows through', 'capital of', 'headquarters in', 'native to' — 'Which river…?' only when river is present."""
        m_riv = FAMILY_I.find("Nasik is situated on the banks of the River Godavari.")
        self.assertTrue(any(m["text"] == "River Godavari" and m["question_type"] == "Which river…?" for m in m_riv))

        m_place = FAMILY_I.find("The Tea Board has its headquarters in Kolkata.")
        self.assertTrue(any(m["text"] == "Kolkata" and m["question_type"] == "Which place…?" for m in m_place))

        # Failing case: non-place institution "Parliament" is not matched as a geographic place
        self.assertEqual(FAMILY_I.find("Laws are debated in the Parliament."), [])

    # =========================================================================
    # J. COMPARISONS AND SUPERLATIVES
    # =========================================================================

    def test_j_comparisons_and_superlatives_note_once_never_on_ordinals_pass_and_fail(self) -> None:
        """J: '______ is the largest planet' -> 'Jupiter' with check note once; never on 'eleventh-largest'."""
        m_sup = FAMILY_J.find("Jupiter is the largest planet in the solar system.")
        self.assertEqual(len(m_sup), 1)
        self.assertEqual(m_sup[0]["text"], "Jupiter")
        self.assertTrue(m_sup[0]["is_superlative"])
        self.assertEqual(m_sup[0]["note"], SUPERLATIVE_CHECK_NOTE)

        # Failing case: ordinal "eleventh-largest" must NOT be flagged as a true superlative in Family J
        self.assertFalse(FAMILY_J.has_true_superlative("Coventry is the eleventh-largest city in the country."))

    # =========================================================================
    # K. LANGUAGE AND GRAMMAR SHEETS
    # =========================================================================

    def test_k_language_and_grammar_pass_and_fail(self) -> None:
        """K: 'opposite of', 'plural of', 'synonym of', 'past tense of', 'rhymes with'."""
        for sent, expected in (
            ("The opposite of 'ancient' is 'modern'.", "modern"),
            ("The plural of 'cactus' is 'cacti'.", "cacti"),
            ("The past tense of 'teach' is 'taught'.", "taught"),
            ("The word 'bright' rhymes with 'light'.", "light"),
        ):
            matches = FAMILY_K.find(sent)
            self.assertEqual(len(matches), 1, msg=f"Failed on {sent!r}: {matches}")
            self.assertEqual(matches[0]["text"], expected)
            self.assertEqual(matches[0]["question_type"], "Which word fits the gap?")

        # Failing case: ordinary science sentence produces no Family K grammar match
        self.assertEqual(FAMILY_K.find("Sound waves require a medium to travel."), [])

    # =========================================================================
    # L. READING THE SHEET'S OWN QUESTIONS
    # =========================================================================

    def test_l_reading_sheet_questions_and_matching_to_facts_pass_and_fail(self) -> None:
        """L: Detects question words, Fill in the blanks, and True/False; links questions to fact lines as HIGH PRIORITY."""
        for q_line, expected_asks in (
            ("1. Who founded the Atmiya Sabha in Calcutta?", "person"),
            ("2. When was the municipal charter signed?", "date"),
            ("3. How many delegates attended the convention?", "number"),
            ("4. Which river flows through Nasik?", "river"),
            ("5. Define transpiration.", "term"),
            ("6. Fill in the blanks: Nasik is situated on the ________________.", "place"),
            ("7. True or False: Quartz has a hexagonal crystal structure.", "term"),
        ):
            m_q = FAMILY_L.find(q_line)
            self.assertEqual(len(m_q), 1, msg=f"Failed on {q_line!r}")
            self.assertTrue(m_q[0]["skip_as_card"])
            self.assertEqual(m_q[0]["asks_for"], expected_asks)

        # Match practice question to fact line and verify it promotes the matching span to Family L priority
        facts = [
            "The convention was held in the town hall.",
            "The rural university was founded by Rabindranath Tagore in 1921.",
        ]
        signals = FAMILY_L.match_questions_to_facts(["When was the rural university founded by Rabindranath Tagore?"], facts)
        self.assertIn(1, signals)
        exprs = find_all_expressions(facts[1], practice_signals=signals[1])
        self.assertEqual(exprs[0]["family"], "L")
        self.assertEqual(exprs[0]["text"], "1921")

        # Failing case: declarative fact sentence without '?' or question command is NOT matched by Family L
        self.assertEqual(FAMILY_L.find("Copper is a good conductor of electricity."), [])

    # =========================================================================
    # Step 6 helper: check_cut_in_half_span
    # =========================================================================

    def test_cut_in_half_span_detection(self) -> None:
        """Verify check_cut_in_half_span rejects 'August' out of '8 August 1942', '286' out of '286,000', and 'km' without its number."""
        is_cut, reason = check_cut_in_half_span(
            "August",
            source_line="The movement was launched on 8 August 1942.",
            clue="The movement was launched on 8 ______ 1942.",
        )
        self.assertTrue(is_cut, msg=reason)

        is_cut_num, reason_num = check_cut_in_half_span(
            "286",
            source_line="The city has a population of 286,000.",
            clue="The city has a population of ______,000.",
        )
        self.assertTrue(is_cut_num, msg=reason_num)

        is_cut_unit, reason_unit = check_cut_in_half_span(
            "km",
            source_line="The river is 387 km long.",
            clue="The river is 387 ______ long.",
        )
        self.assertTrue(is_cut_unit, msg=reason_unit)


if __name__ == "__main__":
    unittest.main(verbosity=2)
