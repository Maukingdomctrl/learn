"""
Stage 4: questions.py
Turn each relation into ONE card using fixed templates (WHO, WHEN, WHAT, WHERE,
HOW_MANY, TITLE, TABLE, FORMULA, GAP) with a short subject label and gap prompt.
"""
from __future__ import annotations
from typing import Dict, Any

ALLOWED_QUESTION_WORDS = {
    "who", "what", "when", "where", "which", "how", "many",
    "in", "year", "was", "were", "is", "are", "did", "does", "do",
    "the", "a", "an", "of", "on", "at", "to", "for", "with",
    "by", "from", "goes", "called", "also", "located", "situated",
    "founded", "found", "opened", "open", "started", "start",
    "made", "proclaimed", "built", "build", "invented", "chaired", "chair",
    "graduated", "graduate", "convert", "converted", "before", "using",
    "if", "then", "has", "have", "get", "each", "unit", "formula",
    "definition", "river", "city", "capital", "region", "shipyard",
    "museum", "residence", "worth", "supports", "support", "population", "rank",
    "acceleration", "force", "forces", "upward", "downward", "velocity",
    "speed", "mass", "error", "improvement", "purpose", "equals", "equal",
    "lifespan", "first", "india", "indian", "uk", "british", "outside",
    "heart", "theatre", "industry", "seat", "famous", "port", "home",
    "headquarters", "global", "remains", "remain", "determines", "determine",
    "zero", "doubling", "doubles", "double", "increasing", "reduces", "reduce",
    "directed", "toward", "central", "body", "opposes", "decreases",
    "sources", "source", "include", "campaigned", "campaign", "regarded",
    "as", "worked", "work", "alongside", "date", "organisation", "college",
    "event", "century", "until", "small", "town", "precursor", "inspired",
    "inspire", "established", "establish", "laid", "lay", "foundations", "part",
    "visitors", "jobs", "banking", "historic", "architecture", "grow", "become",
    "consider", "used", "can", "be",
}


def shorten_label(subject: str) -> str:
    """Create a concise card label naming its subject without cutting off short phrases."""
    s = subject.strip()
    words = s.split()
    if len(words) > 5:
        return " ".join(words[:5])
    return s


def make_gap_prompt(category: str) -> str:
    """Return a clean prompt for GAP cards based on answer category."""
    if category == "date":
        return "Which year fits the gap?"
    if category in ("person", "organisation", "place"):
        return "Which name fits the gap?"
    if category in ("number", "quantity"):
        return "Which number fits the gap?"
    return "Which word fits the gap?"


def generate_card(fact: Dict[str, Any], card_id: str) -> Dict[str, Any]:
    """Turn a single fact dict into a candidate card dict."""
    subj = fact["subject"]
    rel = fact["relation"]
    ans = fact["object"]
    label = shorten_label(subj)
    prompt = ""
    q_type = "WHAT"

    if rel == "IS_CALLED":
        front = f"What is {subj} called?"
        q_type = "TITLE"
    elif rel == "ALSO_CALLED":
        front = f"What is the {subj} also called?"
        q_type = "WHAT"
    elif rel == "REGARDED_AS_FIRST":
        front = f"What is {subj} regarded as India's first?"
        q_type = "TITLE"
    elif rel == "FOUNDED":
        front = f"Which organisation did {subj} found?"
        q_type = "WHAT"
    elif rel == "FOUNDED_IN":
        front = f"In which year was the {subj} founded?"
        q_type = "WHEN"
    elif rel == "GRADUATED_FROM":
        front = f"Which college did {subj} graduate from?"
        q_type = "WHERE"
    elif rel == "GRADUATED_IN":
        front = f"In which year did {subj} graduate?"
        q_type = "WHEN"
    elif rel == "FOUNDED_FIRM_IN":
        front = f"In which year did {subj} found a trading firm?"
        q_type = "WHEN"
    elif rel == "CONVERTED_INTO":
        front = f"What did {subj} convert an oil mill into?"
        q_type = "WHAT"
    elif rel == "ESTABLISHED":
        front = f"Which mill did {subj} establish?"
        q_type = "WHAT"
    elif rel == "OPENED":
        front = f"What did {subj} open?"
        q_type = "WHAT"
    elif rel == "OPENED_ON":
        front = f"On what date did the {subj} open?"
        q_type = "WHEN"
    elif rel == "FIRST_WITH":
        front = f"The {subj} was the first in India with what?"
        q_type = "WHAT"
    elif rel == "LAID_FOUNDATIONS_FOR":
        front = f"What did {subj} lay foundations for?"
        q_type = "WHAT"
    elif rel == "REFORMER_IN":
        front = f"Where was {subj} a social reformer and writer?"
        q_type = "WHERE"
    elif rel == "PURPOSE":
        front = f"What was the purpose of the {subj}?"
        q_type = "WHAT"
    elif rel == "WORKED_ALONGSIDE":
        front = f"Who did {subj} work alongside?"
        q_type = "WHO"
    elif rel == "STARTED_IN":
        front = f"In which year were {subj} started?"
        q_type = "WHEN"
    elif rel == "RESIDENCE":
        front = f"What was the Mumbai residence of {subj}?"
        q_type = "WHERE"
    elif rel == "LOCATED_IN":
        front = f"Where is {subj} located?"
        q_type = "WHERE"
    elif rel == "CHAIRED":
        front = f"Which committee did {subj} chair?"
        q_type = "WHAT"
    elif rel == "PART_OF":
        front = f"What was the {subj} part of?"
        q_type = "WHAT"
    elif rel == "PRECURSOR_TO":
        front = f"What was the {subj} a precursor to?"
        q_type = "WHAT"
    elif rel == "INSPIRED":
        front = f"Which organisation did the {subj} inspire?"
        q_type = "WHAT"
    elif rel == "CAMPAIGNED_FOR":
        front = f"What event did {subj} campaign for?"
        q_type = "WHAT"
    elif rel == "YEAR":
        front = f"In which year was the {subj}?"
        q_type = "WHEN"
    elif rel == "CAPITAL_OF":
        front = f"What is {subj} the capital of?"
        q_type = "WHERE"
    elif rel == "SITUATED_ON":
        front = f"Which river is {subj} situated on?"
        q_type = "WHERE"
    elif rel == "FINANCIAL_CENTRE_OF":
        front = f"What is {subj} the financial centre of?"
        q_type = "WHERE"
    elif rel == "REGION":
        front = f"Which region is {subj} a major city of?"
        q_type = "WHERE"
    elif rel == "LARGEST_OUTSIDE":
        front = f"Outside which city is {subj} the largest British city?"
        q_type = "WHERE"
    elif rel == "PROMINENCE_IN":
        front = f"In which century did {subj} grow to international prominence?"
        q_type = "WHEN"
    elif rel == "AT_HEART_OF":
        front = f"What was {subj} at the heart of?"
        q_type = "WHAT"
    elif rel == "INVENTION":
        front = f"What was invented in {subj}?"
        q_type = "WHAT"
    elif rel == "IS_UKS":
        front = f"What is {subj} in the UK?"
        q_type = "TITLE"
    elif rel == "VISITORS_PER_YEAR":
        front = f"How many visitors does {subj} get each year?"
        q_type = "HOW_MANY"
    elif rel == "POPULATION":
        front = f"What was the population of {subj} in the 2011 census?"
        q_type = "HOW_MANY"
    elif rel == "HISTORIC_INDUSTRY":
        front = f"What is a historic industry of {subj}?"
        q_type = "WHAT"
    elif rel == "BUILT":
        front = f"What did {subj} build?"
        q_type = "WHAT"
    elif rel == "SHIPYARD":
        front = f"Which shipyard is in {subj}?"
        q_type = "WHAT"
    elif rel == "INDUSTRY_SINCE":
        front = f"Which industry has {subj} sustained since the mid-1930s?"
        q_type = "WHAT"
    elif rel == "HOME_TO":
        front = f"What is {subj} home to?"
        q_type = "WHAT"
    elif rel == "RANK_IN_UK":
        front = f"What is the population rank of {subj} in the UK?"
        q_type = "HOW_MANY"
    elif rel == "FINANCIAL_RANK":
        front = f"What rank is {subj} as a financial centre in the UK?"
        q_type = "HOW_MANY"
    elif rel == "BANKING_FOR":
        front = f"For how many years has {subj} been a centre of banking?"
        q_type = "HOW_MANY"
    elif rel == "HEADQUARTERS_IN":
        front = f"Where does the {subj} have its global headquarters?"
        q_type = "WHERE"
    elif rel == "SUPPORTS":
        front = f"How many jobs does {subj} support?"
        q_type = "HOW_MANY"
    elif rel == "WORTH":
        front = f"What is {subj} worth to the city economy?"
        q_type = "HOW_MANY"
    elif rel == "ARCHITECTURE_INCLUDES":
        front = f"What famous area is part of the architecture of {subj}?"
        q_type = "WHERE"
    elif rel == "SEAT_OF":
        front = f"What is {subj} the seat of?"
        q_type = "WHAT"
    elif rel == "SMALL_TOWN_UNTIL":
        front = f"Until which century was {subj} a small town?"
        q_type = "WHEN"
    elif rel == "MOST_IMPORTANT":
        front = f"What did {subj} become the world's most important?"
        q_type = "WHAT"
    elif rel == "MADE_CITY_IN":
        front = f"In which year was {subj} made a city?"
        q_type = "WHEN"
    elif rel == "PROCLAIMED_CAPITAL_IN":
        front = f"In which year was {subj} proclaimed capital of Wales?"
        q_type = "WHEN"
    elif rel == "DETERMINES":
        front = f"What does {subj} determine?"
        q_type = "WHAT"
    elif rel == "FORMULA":
        front = f"What is the formula for {subj}?"
        q_type = "FORMULA"
    elif rel == "VELOCITY_REMAINS":
        front = "If the resultant force is zero, what does velocity remain?"
        q_type = "WHAT"
    elif rel == "ACCELERATION_TABLE":
        front = f"What is the acceleration in m/s² for {subj}?"
        q_type = "TABLE"
    elif rel == "ACCELERATION_CALC":
        front = f"What is the acceleration for {subj}?"
        q_type = "HOW_MANY"
    elif rel == "DOUBLING_FORCE_DOUBLES":
        front = f"For a {subj}, what does doubling resultant force double?"
        q_type = "WHAT"
    elif rel == "INCREASING_MASS_REDUCES":
        front = f"For {subj}, what does increasing mass reduce?"
        q_type = "WHAT"
    elif rel == "TABLE_FORCES":
        front = f"What are the forces to consider for a {subj}?"
        q_type = "TABLE"
    elif rel == "UPWARD_FORCE":
        front = f"For a {subj}, what is the upward force?"
        q_type = "TABLE"
    elif rel == "RESULTANT_CONDITION":
        front = f"For {subj}, speed decreases if the resultant does what?"
        q_type = "TABLE"
    elif rel == "CENTRAL_FORCE":
        front = f"For a {subj}, which force is directed toward the central body?"
        q_type = "TABLE"
    elif rel == "DEFINITION":
        front = f"What is the definition of 1 {subj}?"
        q_type = "FORMULA"
    elif rel == "UNIT_OF":
        front = f"What is the unit of {subj}?"
        q_type = "WHAT"
    elif rel == "CONVERT_TO":
        front = f"What are grams converted to {subj}?"
        q_type = "WHAT"
    elif rel == "EQUALS":
        front = f"How many kilograms does {subj} equal?"
        q_type = "HOW_MANY"
    elif rel == "ERROR_SOURCE":
        front = f"In {subj}, what is a source of error?"
        q_type = "WHAT"
    elif rel == "IMPROVEMENT":
        front = f"In {subj}, what can be used as an improvement?"
        q_type = "WHAT"
    else:
        src = fact["source_text"]
        front = src.replace(ans, "______", 1)
        if not front.endswith(".") and not front.endswith("?"):
            front += "."
        q_type = "GAP"
        prompt = make_gap_prompt(fact.get("category", "term"))

    return {
        "id": card_id,
        "fact_id": fact["id"],
        "item_id": fact["item_id"],
        "page": fact["page"],
        "label": label,
        "front": front,
        "prompt": prompt,
        "answer": ans,
        "question_type": q_type,
        "source_text": fact["source_text"],
        "subject": subj,
        "status": "candidate",
    }
