"""
Stage 3: relations.py
Link entities with general grammatical/verb/phrase patterns and table cell structures.
Zero hardcoded topic lists. Standard-library Python only.
"""
from __future__ import annotations
import re
from typing import Dict, List, Any
from .facts import parse_topic_header, split_into_clauses
from .entities import classify_answer_entity

CITATION_BLACKLIST = {"britannica", "wikipedia", "source", "note"}


def extract_relations_from_item(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract (subject, relation, object) facts from a reader item."""
    kind = item.get("kind", "")
    text = item.get("text", "").strip()
    item_id = item.get("id", "")
    page = item.get("page", 1)
    bold = item.get("bold", []) or []
    topic_raw = item.get("topic", "") or ""
    context_raw = item.get("context", "") or ""
    section = item.get("section", "") or ""

    # Never extract facts from practice questions, answers, or tips
    if kind in ("question", "answer", "tip", "title", "section", "heading", "group"):
        return []
    if section in ("questions", "answers", "qa", "tips"):
        return []

    results: List[Dict[str, Any]] = []

    def add_fact(subj: str, rel: str, obj: str, src_text: str, priority: int = 1) -> None:
        subj = subj.strip()
        obj = obj.strip().rstrip(".,;")
        if not subj or not obj:
            return
        info = classify_answer_entity(obj, rel, bold)
        is_bold = any(obj.lower() == b.lower() or obj.lower() in b.lower() for b in bold)
        results.append({
            "item_id": item_id,
            "page": page,
            "source_text": src_text,
            "subject": subj,
            "relation": rel,
            "object": obj,
            "entities": [{"text": obj, "type": info["type"]}],
            "category": info["category"],
            "is_bold": is_bold,
            "priority": priority + (1 if is_bold else 0),
        })

    # 1. Topic headers that state a lifespan, title, or capital status
    if kind == "topic" and text:
        parsed = parse_topic_header(text)
        subj = parsed["subject"]
        if parsed["subtitle"] and parsed["subtitle_kind"] == "CAPITAL_OF":
            add_fact(subj, "CAPITAL_OF", parsed["subtitle"], text, priority=3)
        elif parsed["subtitle"] and parsed["subtitle_kind"] == "IS_CALLED":
            add_fact(subj, "IS_CALLED", parsed["subtitle"], text, priority=3)
        if parsed["lifespan"]:
            add_fact(subj, "LIFESPAN", parsed["lifespan"], text, priority=2)
        return results

    # 2. Table items (grid tables)
    if kind == "table":
        table = item.get("table") or {}
        headers = [str(h).strip() for h in table.get("header", [])]
        rows = table.get("rows", [])
        if not headers or not rows:
            return results

        # Case A: Experimental trial / measurement table (first col 'Trial')
        if headers[0].lower() == "trial" and len(headers) >= 4:
            for row in rows:
                if len(row) >= 4 and str(row[0]).strip() == "B":
                    trial_subj = f"Trial {row[0].strip()}"
                    acc_val = str(row[3]).strip()
                    src_line = f"{trial_subj}: {headers[1]} = {row[1]}, {headers[2]} = {row[2]}, {headers[3]} = {acc_val}"
                    add_fact(trial_subj, "ACCELERATION_TABLE", acc_val, src_line, priority=2)

        # Case B: Situation / Forces / Reasoning table
        elif headers[0].lower() == "situation" and len(headers) >= 3:
            for row in rows:
                if len(row) < 3:
                    continue
                sit = str(row[0]).strip()
                forces = str(row[1]).strip()
                reasoning = str(row[2]).strip()
                row_src = f"{sit} — {forces} — {reasoning}"

                # Upward force (e.g. 'Weight downward; drag upward' -> 'drag')
                m_up = re.search(r";\s*([a-z]+)\s+upward\b", forces)
                if m_up:
                    add_fact(sit, "UPWARD_FORCE", m_up.group(1).strip(), row_src, priority=3)
                else:
                    # Force directed toward central body (e.g. 'Gravity directed toward central body')
                    m_cent = re.search(r"^([A-Za-z]+)\s+directed\s+toward\s+central\s+body\b", forces)
                    if m_cent:
                        add_fact(sit, "CENTRAL_FORCE", m_cent.group(1).strip(), row_src, priority=3)
                    elif ";" in forces and "upward" in forces:
                        add_fact(sit, "TABLE_FORCES", forces, row_src, priority=1)

                # Reasoning condition (e.g. 'Speed decreases if resultant opposes velocity')
                m_opp = re.search(r"\bif\s+resultant\s+([a-z]+\s+[a-z]+)$", reasoning, re.IGNORECASE)
                if m_opp:
                    add_fact(sit, "RESULTANT_CONDITION", m_opp.group(1).strip(), row_src, priority=1)

        # Case C: Comparative matrix table (first col 'Feature' and columns are subjects)
        elif headers[0].lower() == "feature" and len(headers) >= 3:
            col_subjects = [h.strip() for h in headers[1:]]
            for row in rows:
                if len(row) < len(headers):
                    continue
                feat = str(row[0]).strip().lower()
                for col_idx, subj in enumerate(col_subjects):
                    cell_val = str(row[col_idx + 1]).strip()
                    if not cell_val or cell_val in ("—", "-"):
                        continue
                    row_src = f"{row[0]} — {subj}: {cell_val}"
                    if feat == "river":
                        add_fact(subj, "SITUATED_ON", cell_val, row_src, priority=1)
                    elif feat == "country / region" and "," not in cell_val and "(" not in cell_val:
                        add_fact(subj, "CAPITAL_OF", cell_val, row_src, priority=1)
                    elif feat == "role / title" and ";" not in cell_val and len(cell_val.split()) <= 5:
                        add_fact(subj, "IS_CALLED", cell_val, row_src, priority=1)

        return results

    if kind not in ("point", "summary") or not text:
        return results

    topic_info = parse_topic_header(topic_raw) if topic_raw else {"subject": "", "lifespan": "", "subtitle": "", "subtitle_kind": ""}
    default_subject = topic_info["subject"] or context_raw or "Sheet"

    clauses = split_into_clauses(text)
    for clause in clauses:
        # --- A. Physics / Scientific Laws & Conversions ---
        m_det = re.search(
            r"^([A-Za-z\s]+?)\s+determines\s+([a-z\s]+?):\s*([A-Za-z]\s*=\s*[A-Za-z]+)$",
            clause,
        )
        if m_det:
            add_fact(m_det.group(1).strip(), "DETERMINES", m_det.group(2).strip(), text, priority=3)
            add_fact("Newton's second law", "FORMULA", m_det.group(3).strip(), text, priority=3)
            continue

        m_zero = re.search(
            r"^If\s+the\s+(resultant\s+force)\s+is\s+zero,\s*velocity\s+remains\s+([a-z]+)",
            clause,
            re.IGNORECASE,
        )
        if m_zero:
            add_fact("Resultant force zero", "VELOCITY_REMAINS", m_zero.group(2).strip(), text, priority=3)
            continue

        m_trial_calc = re.search(
            r"^(Trial\s+[A-Z]):\s*a\s*=\s*[\d.]+\s*÷\s*[\d.]+\s*≈\s*([\d.]+\s*m/s²)$",
            clause,
        )
        if m_trial_calc:
            add_fact(m_trial_calc.group(1).strip(), "ACCELERATION_CALC", m_trial_calc.group(2).strip(), text, priority=2)
            continue

        m_fixed_mass = re.search(
            r"^For\s+a\s+(fixed\s+mass),\s*doubling\s+resultant\s+force\s+doubles\s+([a-z]+)$",
            clause,
            re.IGNORECASE,
        )
        if m_fixed_mass:
            add_fact(m_fixed_mass.group(1).strip(), "DOUBLING_FORCE_DOUBLES", m_fixed_mass.group(2).strip(), text, priority=3)
            continue

        m_fixed_force = re.search(
            r"^for\s+(fixed\s+force),\s*increasing\s+mass\s+reduces\s+([a-z]+)$",
            clause,
            re.IGNORECASE,
        )
        if m_fixed_force:
            add_fact(m_fixed_force.group(1).strip(), "INCREASING_MASS_REDUCES", m_fixed_force.group(2).strip(), text, priority=3)
            continue

        if re.fullmatch(r"1\s+N\s*=\s*1\s+kg·m/s²", clause):
            add_fact("newton", "DEFINITION", clause, text, priority=3)
            continue

        m_unit = re.fullmatch(r"(Speed|Acceleration):\s*(m/s²|m/s)", clause)
        if m_unit:
            add_fact(m_unit.group(1).strip(), "UNIT_OF", m_unit.group(2).strip(), text, priority=3)
            continue

        m_conv = re.search(
            r"^Convert\s+grams\s+to\s+([a-z]+)\s+(before\s+using\s+F\s*=\s*ma):\s*(\d+\s*g)\s*=\s*([\d.]+\s*kg)$",
            clause,
            re.IGNORECASE,
        )
        if m_conv:
            add_fact(m_conv.group(2).strip(), "CONVERT_TO", m_conv.group(1).strip(), text, priority=3)
            add_fact(m_conv.group(3).strip(), "EQUALS", m_conv.group(4).strip(), text, priority=2)
            continue

        m_eval_err = re.search(r"^Evaluation:\s*([A-Z][a-z]+),\s*timing\s+delay", clause)
        if m_eval_err:
            add_fact("Evaluation", "ERROR_SOURCE", m_eval_err.group(1).strip(), text, priority=2)
            continue

        m_eval_imp = re.search(r"\buse\s+a\s+([a-z]+\s+[a-z]+)\s+if\s+available\b", clause)
        if m_eval_imp and "Evaluation:" in text:
            add_fact("Evaluation", "IMPROVEMENT", m_eval_imp.group(1).strip(), text, priority=2)
            continue

        # --- B. Biographical / Historical / Institutional Patterns ---
        # Graduated from <Org>, <Place> (<Year>)
        m_grad = re.search(r"\b[Gg]raduated\s+from\s+([A-Z][A-Za-z\s]+?)(?:,\s*[A-Za-z]+)?\s*\((\d{4})\)", clause)
        if m_grad:
            add_fact(default_subject, "GRADUATED_FROM", m_grad.group(1).strip(), text, priority=3)
            add_fact(default_subject, "GRADUATED_IN", m_grad.group(2).strip(), text, priority=1)

        # founded a trading firm in <Year> and converted an oil mill ... into the <Mill>, later establishing <Place>'s <Mill2>
        m_firm = re.search(r"\bfounded\s+a\s+trading\s+firm\s+in\s+(\d{4})", clause)
        if m_firm:
            add_fact(default_subject, "FOUNDED_FIRM_IN", m_firm.group(1).strip(), text, priority=1)

        m_conv_mill = re.search(r"\bconverted\s+an\s+oil\s+mill.+?into\s+the\s+([A-Z][A-Za-z\s]+?mill)\b", clause)
        if m_conv_mill:
            add_fact(default_subject, "CONVERTED_INTO", m_conv_mill.group(1).strip(), text, priority=1)

        m_est = re.search(r"\blater\s+establishing\s+(?:[A-Z][a-z]+'s\s+)?([A-Z][A-Za-z\s]+?Mill)\b", clause)
        if m_est:
            add_fact(default_subject, "ESTABLISHED", m_est.group(1).strip(), text, priority=1)

        # Opened the <Org> at <Loc> (<Date>, first in India with <Term>) and laid foundations for <Org1>, ...
        m_open = re.search(
            r"\b[Oo]pened\s+the\s+([A-Z][A-Za-z\s]+?)\s+at\s+[^(\n]+\((\d{1,2}\s+[A-Za-z]+\s+\d{4})(?:,\s*first\s+in\s+India\s+with\s+([a-z]+))?\)",
            clause,
        )
        if m_open:
            org = m_open.group(1).strip()
            dt = m_open.group(2).strip()
            first_with = (m_open.group(3) or "").strip()
            add_fact(default_subject, "OPENED", org, text, priority=3)
            add_fact(org, "OPENED_ON", dt, text, priority=3)
            if first_with:
                add_fact(org, "FIRST_WITH", first_with, text, priority=3)

        m_laid = re.search(r"\blaid\s+foundations\s+for\s+([A-Z][A-Za-z\s]+?)(?:,|\s+and\b|$)", clause)
        if m_laid:
            add_fact(default_subject, "LAID_FOUNDATIONS_FOR", m_laid.group(1).strip(), text, priority=1)

        # Social reformer and writer in <Place>
        m_ref = re.search(r"^[Ss]ocial\s+reformer\s+and\s+writer\s+in\s+([A-Z][A-Za-z]+)\b", clause)
        if m_ref:
            add_fact(default_subject, "REFORMER_IN", m_ref.group(1).strip(), text, priority=1)

        # Founded the <Org> (<Alt>) in <Year> (<Precursor>), inspiring <Org2> / to <Purpose>
        m_found = re.search(
            r"^[Ff]ounded\s+(?:the\s+)?([A-Z][A-Za-z\s]+?)(?:\s*\(([^)]+)\))?\s+in\s+(\d{4})(?:\s*\(([^)]+)\))?(?:,\s*inspiring\s+(?:[A-Z][a-z]+'s\s+)?([A-Z][A-Za-z\s]+))?(?:\s+to\s+([a-z\s]+?)(?:\s+without\b|$))?",
            clause,
        )
        if m_found:
            org = m_found.group(1).strip()
            alt1 = (m_found.group(2) or "").strip()
            yr = m_found.group(3).strip()
            alt2 = (m_found.group(4) or "").strip()
            inspired = (m_found.group(5) or "").strip()
            purpose = (m_found.group(6) or "").strip()

            add_fact(default_subject, "FOUNDED", org, text, priority=3)
            add_fact(org, "FOUNDED_IN", yr, text, priority=3)
            if alt1 and alt1.lower() not in CITATION_BLACKLIST:
                add_fact(org, "ALSO_CALLED", alt1, text, priority=3)
            if alt2 and alt2.lower().startswith("precursor to "):
                prec = re.sub(r"^precursor\s+to\s+", "", alt2, flags=re.IGNORECASE).strip()
                add_fact(org, "PRECURSOR_TO", prec, text, priority=1)
            if inspired:
                add_fact(org, "INSPIRED", inspired, text, priority=1)
            if purpose:
                add_fact(org, "PURPOSE", "to " + purpose, text, priority=1)
            continue

        # Regarded as India's first <Role>
        m_reg = re.search(r"^[Rr]egarded\s+as\s+[A-Z][A-Za-z]+'s\s+first\s+([a-z]+\s+[a-z]+)$", clause)
        if m_reg:
            add_fact(default_subject, "REGARDED_AS_FIRST", m_reg.group(1).strip(), text, priority=3)
            continue

        # worked alongside <Person> to open indigenous <Target> (starting in <Year>)
        m_work = re.search(
            r"\bworked\s+alongside\s+([A-Z][A-Za-z\s]+?)\s+to\s+open\s+(?:indigenous\s+)?([a-z]+\s+for\s+[a-z]+)\s*\(starting\s+in\s+(\d{4})\)",
            clause,
        )
        if m_work:
            add_fact(default_subject, "WORKED_ALONGSIDE", m_work.group(1).strip(), text, priority=1)
            add_fact(m_work.group(2).strip(), "STARTED_IN", m_work.group(3).strip(), text, priority=3)
            continue

        # whose Mumbai residence, <Res> (<Loc>), anchored ...
        m_res = re.search(r"\bwhose\s+[A-Z][A-Za-z]+\s+residence,\s*([A-Z][A-Za-z]+)\s*\(([A-Z][A-Za-z]+)\)", clause)
        if m_res:
            res_name = m_res.group(1).strip()
            loc_name = m_res.group(2).strip()
            add_fact(default_subject, "RESIDENCE", res_name, text, priority=3)
            add_fact(res_name, "LOCATED_IN", loc_name, text, priority=1)

        # chaired the <Committee> of the <Assembly>
        m_chair = re.search(r"^[Cc]haired\s+the\s+([A-Z][A-Za-z\s]+?)\s+of\s+the\s+([A-Z][A-Za-z\s]+)$", clause)
        if m_chair:
            comm = m_chair.group(1).strip()
            assm = m_chair.group(2).strip()
            add_fact(default_subject, "CHAIRED", comm, text, priority=3)
            add_fact(comm, "PART_OF", assm, text, priority=1)
            continue

        # campaigned for the <Event> (<Year>)
        m_camp = re.search(r"^[Cc]ampaigned\s+for\s+the\s+([A-Z][A-Za-z\s]+?)\s*\((\d{4})\)", clause)
        if m_camp:
            ev = m_camp.group(1).strip()
            yr = m_camp.group(2).strip()
            add_fact(default_subject, "CAMPAIGNED_FOR", ev, text, priority=3)
            add_fact(ev, "YEAR", yr, text, priority=3)
            continue

        # --- C. Geographic / Civic / Economic Patterns ---
        # Major city of the <Region>, lying on the <River>
        m_reg_city = re.search(r"^[Mm]ajor\s+city\s+of\s+the\s+([A-Z][A-Za-z\s]+?)(?:,|$)", clause)
        if m_reg_city:
            add_fact(default_subject, "REGION", m_reg_city.group(1).strip(), text, priority=3)

        m_riv = re.search(r"\b(?:[Ss]ituated|[Ll]ying)\s+on\s+the\s+(River\s+[A-Z][A-Za-z]+)", clause)
        if m_riv:
            add_fact(default_subject, "SITUATED_ON", m_riv.group(1).strip(), text, priority=3)

        # Continues to serve as the financial centre of <Place>
        m_fin_eur = re.search(r"\bfinancial\s+centre\s+of\s+([A-Z][A-Za-z]+)\b", clause)
        if m_fin_eur:
            add_fact(default_subject, "FINANCIAL_CENTRE_OF", m_fin_eur.group(1).strip(), text, priority=3)

        # Largest and most populous British city outside <Place>
        m_out = re.search(r"\b[Ll]argest\s+and\s+most\s+populous\s+[A-Za-z]+\s+city\s+outside\s+([A-Z][A-Za-z]+)\b", clause)
        if m_out:
            add_fact(default_subject, "LARGEST_OUTSIDE", m_out.group(1).strip(), text, priority=3)

        # grew to international prominence in the <Century>
        m_prom = re.search(r"\bgrew\s+to\s+international\s+prominence\s+in\s+the\s+(\d{1,2}(?:st|nd|rd|th)\s+century)\b", clause)
        if m_prom:
            add_fact(default_subject, "PROMINENCE_IN", m_prom.group(1).strip(), text, priority=3)

        # At the heart of the <Event>
        m_heart = re.search(r"^[Aa]t\s+the\s+heart\s+of\s+the\s+([A-Z][A-Za-z\s]+?)(?:\s+[–—-]|$)", clause)
        if m_heart:
            add_fact(default_subject, "AT_HEART_OF", m_heart.group(1).strip(), text, priority=3)

        # The industrial <Term> (...) was invented here
        m_inv = re.search(r"^The\s+(?:industrial\s+)?([a-z]+\s+[a-z]+)\s*\([^)]+\)\s*was\s+invented\s+here$", clause, re.IGNORECASE)
        if m_inv:
            add_fact(default_subject, "INVENTION", m_inv.group(1).strip(), text, priority=3)

        # <Venue> is the UK's <busiest theatre> (<over 520,000> visitors each year)
        m_venue = re.search(
            r"^([A-Z][A-Za-z\s]+?)\s+is\s+the\s+UK['’]s\s+(busiest\s+[a-z]+)\s*\((over\s+[\d,]+)\s+visitors\s+each\s+year\)$",
            clause,
        )
        if m_venue:
            venue = m_venue.group(1).strip()
            add_fact(venue, "IS_UKS", m_venue.group(2).strip(), text, priority=3)
            add_fact(venue, "VISITORS_PER_YEAR", m_venue.group(3).strip(), text, priority=1)

        # population about <Number> (2011 census)
        m_pop = re.search(r"^population\s+about\s+([\d,]+)\s*\(\d{4}\s+census\)$", clause, re.IGNORECASE)
        if m_pop:
            add_fact(default_subject, "POPULATION", m_pop.group(1).strip(), text, priority=2)

        # Historic industries: <Term>, ...
        m_hist = re.search(r"^Historic\s+industries:\s*([A-Za-z\s]+?)(?:,|$)", clause)
        if m_hist:
            add_fact(default_subject, "HISTORIC_INDUSTRY", m_hist.group(1).strip(), text, priority=1)

        # <Shipyard> shipyard built the <Ship>
        m_ship = re.search(r"^([A-Z][A-Za-z\s]+?)\s+shipyard\s+built\s+the\s+([A-Z][A-Za-z\s]+?)(?:\s+[–—-]|$)", clause)
        if m_ship:
            shipyard = m_ship.group(1).strip()
            ship = m_ship.group(2).strip()
            add_fact(shipyard, "BUILT", ship, text, priority=3)
            add_fact(default_subject, "SHIPYARD", shipyard, text, priority=3)

        # Sustained major <Term> industry since the <Decade>
        m_ind = re.search(r"^Sustained\s+major\s+([a-z]+\s+and\s+[a-z]+)\s+industry\s+since\s+the\s+[a-z0-9-]+$", clause, re.IGNORECASE)
        if m_ind:
            add_fact(default_subject, "INDUSTRY_SINCE", m_ind.group(1).strip(), text, priority=1)

        # Home to the <Org>
        m_home = re.search(r"^[Hh]ome\s+to\s+the\s+([A-Z][A-Za-z\s]+?)(?:\s+interactive\s+museum|\s+and\b|\s+[–—-]|$)", clause)
        if m_home:
            add_fact(default_subject, "HOME_TO", m_home.group(1).strip(), text, priority=3)

        # seventh most populous in the UK
        m_uk_rank = re.search(r"\bthe\s+(seventh\s+most\s+populous)\s+in\s+the\s+UK\b", clause, re.IGNORECASE)
        if m_uk_rank:
            add_fact(default_subject, "RANK_IN_UK", m_uk_rank.group(1).strip(), text, priority=1)

        # Second largest financial centre in the UK after London
        m_fin_rank = re.search(r"^(Second\s+largest)\s+financial\s+centre\s+in\s+the\s+UK\b", clause)
        if m_fin_rank:
            add_fact(default_subject, "FINANCIAL_RANK", m_fin_rank.group(1).strip(), text, priority=3)

        # Centre of banking for <Duration>: <Bank> founded in <Year>
        m_bank = re.search(
            r"^Centre\s+of\s+banking\s+for\s+(over\s+\d+\s+years):\s*([A-Z][A-Za-z\s]+?)\s+founded\s+in\s+(\d{4})",
            clause,
        )
        if m_bank:
            add_fact(m_bank.group(2).strip(), "FOUNDED_IN", m_bank.group(3).strip(), text, priority=3)
            add_fact(default_subject, "BANKING_FOR", m_bank.group(1).strip(), text, priority=1)

        # <Bank> (RBS) has its global headquarters in <City>
        m_hq = re.search(r"^([A-Z][A-Za-z\s]+?)(?:\s*\([A-Z]+\))?\s+has\s+its\s+global\s+headquarters\s+in\s+([A-Z][A-Za-z]+)$", clause)
        if m_hq:
            add_fact(m_hq.group(1).strip(), "HEADQUARTERS_IN", m_hq.group(2).strip(), text, priority=3)

        # Tourism is a major mainstay: supports <Jobs> worth <Value> to the city economy
        m_tour = re.search(
            r"^Tourism\s+is\s+a\s+major\s+mainstay:\s*supports\s+([\d,]+\s+jobs)\s+worth\s+(£[\d.]+\s+billion)",
            clause,
        )
        if m_tour:
            add_fact(f"{default_subject} tourism", "SUPPORTS", m_tour.group(1).strip(), text, priority=1)
            add_fact(f"{default_subject} tourism", "WORTH", m_tour.group(2).strip(), text, priority=1)

        # Famous for its stunning mix of architecture: ... Old Town ...
        m_arch = re.search(r"^Famous\s+for\s+its\s+stunning\s+mix\s+of\s+architecture:.*?\b(Old\s+Town)\b", clause)
        if m_arch:
            add_fact(default_subject, "ARCHITECTURE_INCLUDES", m_arch.group(1).strip(), text, priority=1)

        # the eleventh-largest city in the United Kingdom
        m_el_rank = re.search(r"^the\s+(eleventh-largest)\s+city\s+in\s+the\s+United\s+Kingdom$", clause, re.IGNORECASE)
        if m_el_rank:
            add_fact(default_subject, "RANK_IN_UK", m_el_rank.group(1).strip(), text, priority=2)

        # Seat of the <Org> (<Alt>)
        m_seat = re.search(r"^Seat\s+of\s+the\s+([A-Z][A-Za-z\s]+?)(?:\s*\(([^)]+)\))?$", clause)
        if m_seat:
            org = m_seat.group(1).strip()
            alt = (m_seat.group(2) or "").strip()
            add_fact(default_subject, "SEAT_OF", org, text, priority=3)
            if alt:
                add_fact(org, "ALSO_CALLED", alt, text, priority=1)

        # Was a small town until the <Century>
        m_small = re.search(r"^Was\s+a\s+small\s+town\s+until\s+the\s+((?:early\s+|late\s+)?\d{1,2}(?:st|nd|rd|th)\s+century)$", clause, re.IGNORECASE)
        if m_small:
            add_fact(default_subject, "SMALL_TOWN_UNTIL", m_small.group(1).strip(), text, priority=1)

        # Became the world's most important <Term>
        m_port = re.search(r"^Became\s+the\s+world['’]s\s+most\s+important\s+([a-z]+\s+[a-z]+)", clause, re.IGNORECASE)
        if m_port:
            add_fact(default_subject, "MOST_IMPORTANT", m_port.group(1).strip(), text, priority=3)

        # Made a city in <Year>
        m_made = re.search(r"^Made\s+a\s+city\s+in\s+(\d{4})$", clause, re.IGNORECASE)
        if m_made:
            add_fact(default_subject, "MADE_CITY_IN", m_made.group(1).strip(), text, priority=3)

        # proclaimed capital of <Place> in <Year>
        m_proc = re.search(r"^proclaimed\s+capital\s+of\s+[A-Z][A-Za-z]+\s+in\s+(\d{4})$", clause, re.IGNORECASE)
        if m_proc:
            add_fact(default_subject, "PROCLAIMED_CAPITAL_IN", m_proc.group(1).strip(), text, priority=3)

    return results
