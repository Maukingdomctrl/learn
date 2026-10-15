"""Builds the sample sheets in cards/sample/, in the same layout as the UK cities notes:

- sample-sheet.pdf: places (two cities);
- history-sheet.pdf: an event (the 1857 uprising) with causes, course, leaders and results;
- people-sheet.pdf: three social reformers, each with life years, a summary line and a placeholder
  portrait beside the heading (a drawn silhouette, not a real photo);
- industries-sheet.pdf: three Indian industries with raw materials, centres, products and why they are where they are.


Words wrapped in **double stars** are printed bold, the way a teacher marks the key words.
Run from the repo root: python cards/test/fixtures/make_sample.py
"""

import re
from pathlib import Path

import pymupdf

SAMPLES = Path(__file__).resolve().parents[2] / "sample"
BODY, HEAD = 9.5, 12
FONTS = Path("/usr/share/fonts/truetype/liberation")
REGULAR, BOLD = FONTS / "LiberationSans-Regular.ttf", FONTS / "LiberationSans-Bold.ttf"
MEASURE = {"reg": pymupdf.Font(fontfile=str(REGULAR)), "bold": pymupdf.Font(fontfile=str(BOLD))}

PAGES = [
    [
        ("title", "IMPORTANT CITIES OF THE UNITED KINGDOM"),
        ("sub", "Grade 8 Social Studies | Sample notes"),
        ("section", "1. QUICK REVISION NOTES"),
        ("heading", "1. BELFAST – Capital of Northern Ireland"),
        ("bullet", "Capital and **largest city of Northern Ireland**; second largest city on the island of Ireland."),
        ("bullet", "Situated on the **River Lagan**; population about **286,000** (2011 census)."),
        ("bullet", "Historic industries: Irish linen, tobacco processing, rope-making and **shipbuilding**."),
        ("bullet", "**Harland and Wolff** shipyard built the **RMS Titanic**."),
        ("bullet", "Home to the **Titanic Belfast** interactive museum."),
        ("heading", "2. EDINBURGH – Capital of Scotland"),
        ("bullet", "Home to the **Scottish Parliament** and the seat of the monarchy in Scotland."),
        ("bullet", "Centre of banking for over 300 years: **Bank of Scotland** founded in **1695**."),
        ("bullet", "Tourism is a major mainstay: supports **30,000 jobs** worth £1.6 billion to the city economy."),
        ("bullet", "Famous for its stunning mix of architecture: medieval tenements, Old Town, cobbled wynds and"),
        ("wrap", "Georgian-era buildings."),
    ],
    [
        ("section", "2. QUICK COMPARISON"),
        ("bullet", "Belfast = Shipbuilding & Titanic (Lagan + Harland & Wolff)"),
        ("bullet", "Edinburgh = Banking Capital of Scotland (Parliament + Bank of Scotland)"),
        ("note", "MEMORY TIP: Belfast builds ships; Edinburgh keeps the money."),
    ],
]


HISTORY = [
    [
        ("title", "THE GREAT UPRISING OF 1857"),
        ("sub", "Class 8 History | Sample notes"),
        ("section", "1. CAUSES OF THE UPRISING"),
        ("bullet", "Political: Lord Dalhousie's **Doctrine of Lapse** annexed states whose rulers died without a"),
        ("wrap", "natural heir; Jhansi and Nagpur were annexed this way."),
        ("bullet", "Economic: heavy **land revenue** demands pushed many peasants into debt."),
        ("bullet", "Military: Indian sepoys were **paid less** than British soldiers and had little chance"),
        ("wrap", "of promotion."),
        ("bullet", "Immediate cause: the cartridges of the new **Enfield rifle** were rumoured to be greased with"),
        ("wrap", "cow and pig fat."),
        ("section", "2. COURSE OF THE UPRISING"),
        ("bullet", "On 29 March 1857, **Mangal Pandey** attacked his officers at **Barrackpore**."),
        ("bullet", "On 10 May 1857, sepoys at **Meerut** rose in revolt and marched to Delhi."),
        ("bullet", "The rebels proclaimed **Bahadur Shah Zafar** as their emperor."),
        ("bullet", "The British recaptured Delhi in September 1857."),
        ("section", "3. LEADERS AND CENTRES"),
        ("bullet", "**Rani Lakshmibai** led the fight at **Jhansi**."),
        ("bullet", "**Nana Saheb** led the revolt at **Kanpur**."),
        ("bullet", "**Begum Hazrat Mahal** led the revolt at **Lucknow**."),
        ("bullet", "**Kunwar Singh** led the revolt in **Bihar**."),
    ],
    [
        ("section", "4. RESULTS OF THE UPRISING"),
        ("bullet", "The **Government of India Act, 1858** ended the rule of the East India Company."),
        ("bullet", "Power passed to the **British Crown**; the Governor-General became the **Viceroy**."),
        ("bullet", "**Queen Victoria's Proclamation** of 1858 promised to respect Indian rulers and religions."),
        ("bullet", "The army was reorganised because the British wanted to prevent another revolt."),
        ("bullet", "The uprising led to the end of the Mughal dynasty."),
        ("note", "MEMORY TIP: Lapse, land, low pay and the rifle lit the fire."),
    ],
]


PEOPLE = [
    [
        ("title", "SOCIAL REFORMERS OF THE 19TH CENTURY"),
        ("sub", "Class 8 History | Sample notes"),
        ("heading", "1. RAJA RAM MOHAN ROY – Social reformer (1772–1833)"),
        ("bullet", "Founded the **Brahmo Samaj** in 1828."),
        ("bullet", "Campaigned against **Sati**, which was banned in 1829."),
        ("bullet", "Supported **Western education** and English schools."),
        ("bullet", "Roy is called the **Father of the Indian Renaissance**."),
        ("heading", "2. ISHWAR CHANDRA VIDYASAGAR – Educationist and reformer (1820–1891)"),
        ("bullet", "Worked to improve the lives of **widows**."),
        ("bullet", "His efforts led to the **Widow Remarriage Act** of 1856."),
        ("bullet", "Opened many **schools for girls** in Bengal."),
        ("bullet", "Vidyasagar was a title meaning **ocean of learning**."),
        ("heading", "3. JYOTIRAO PHULE – Social reformer (1827–1890)"),
        ("bullet", "Fought against **caste** discrimination."),
        ("bullet", "Started a school for girls in **Pune** in 1848 with his wife **Savitribai Phule**."),
        ("bullet", "Founded the **Satyashodhak Samaj** in 1873."),
        ("section", "QUICK COMPARISON"),
        ("bullet", "Raja Ram Mohan Roy = Brahmo Samaj + end of Sati"),
        ("bullet", "Ishwar Chandra Vidyasagar = Widows + girls' schools"),
        ("bullet", "Jyotirao Phule = Against caste + Satyashodhak Samaj"),
    ],
]


INDUSTRIES = [
    [
        ("title", "MAJOR INDUSTRIES OF INDIA"),
        ("sub", "Class 8 Geography | Sample notes"),
        ("heading", "1. COTTON TEXTILE INDUSTRY – Agro-based industry"),
        ("bullet", "Raw material: **raw cotton**."),
        ("bullet", "Main centres: **Mumbai**, **Ahmedabad** and **Coimbatore**."),
        ("bullet", "It grew in Mumbai because of the **humid climate**, a port for importing machinery and"),
        ("wrap", "a large supply of workers."),
        ("bullet", "Products: **cloth**, yarn and garments."),
        ("bullet", "Ahmedabad is called the **Manchester of India**."),
        ("heading", "2. IRON AND STEEL INDUSTRY – Mineral-based industry"),
        ("bullet", "Raw materials: **iron ore**, coking coal and limestone."),
        ("bullet", "The Tata Iron and Steel Company was set up at **Jamshedpur** in 1907."),
        ("bullet", "Plants are near the **Chota Nagpur Plateau** because iron ore and coal are found there."),
        ("bullet", "Other centres: **Bhilai**, **Rourkela** and **Bokaro**."),
        ("bullet", "Products: **steel** for machines, rails and bridges."),
        ("heading", "3. SUGAR INDUSTRY – Agro-based industry"),
        ("bullet", "Raw material: **sugarcane**."),
        ("bullet", "Mills are near the fields because sugarcane dries quickly and must be crushed soon after"),
        ("wrap", "cutting."),
        ("bullet", "Main states: **Uttar Pradesh** and **Maharashtra**."),
        ("bullet", "Products: **sugar**, with molasses as a by-product."),
        ("section", "QUICK COMPARISON"),
        ("bullet", "Cotton Textile Industry = cotton to cloth (Mumbai, Ahmedabad)"),
        ("bullet", "Iron and Steel Industry = ore and coal to steel (Jamshedpur)"),
        ("bullet", "Sugar Industry = cane to sugar (near the fields)"),
    ],
]


def runs(text):
    """Splits '**bold**' markup into (text, bold) runs."""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    return [(p[2:-2], True) if p.startswith("**") else (p, False) for p in parts if p]


def write_line(page, x, y, text, size, bold_all=False):
    for chunk, bold in runs(text):
        font = "bold" if bold or bold_all else "reg"
        page.insert_text((x, y), chunk, fontname=font, fontsize=size)
        x += MEASURE[font].text_length(chunk, fontsize=size)


def placeholder_portrait(variant):
    """A drawn grey silhouette as PNG bytes. Stands in for a real portrait photo in the sample."""
    sketch = pymupdf.open()
    page = sketch.new_page(width=120, height=150)
    page.draw_rect(page.rect, color=None, fill=(0.93, 0.93, 0.93))
    page.draw_oval(
        pymupdf.Rect(35, 25 + variant * 3, 85, 80 + variant * 3), color=(0.2, 0.2, 0.2), fill=(0.55, 0.55, 0.55)
    )
    page.draw_oval(pymupdf.Rect(15, 90, 105, 190), color=(0.2, 0.2, 0.2), fill=(0.4, 0.4, 0.4))
    if variant == 1:
        page.draw_rect(pymupdf.Rect(33, 20, 87, 34), color=(0.2, 0.2, 0.2), fill=(0.25, 0.25, 0.25))
    png = sketch[0].get_pixmap(dpi=96).tobytes("png")
    sketch.close()
    return png


def build(pages, out, header, portraits=False):
    doc = pymupdf.open()
    for n, lines in enumerate(pages, start=1):
        page = doc.new_page(width=595, height=842)
        page.insert_font(fontname="reg", fontfile=str(REGULAR))
        page.insert_font(fontname="bold", fontfile=str(BOLD))
        write_line(page, 43, 28, f"{header}          Page {n}", 8)
        y = 70
        placed = []
        for kind, text in lines:
            if kind == "title":
                write_line(page, 95, y, text, 18, bold_all=True)
                y += 24
            elif kind == "sub":
                write_line(page, 120, y, text, 12, bold_all=True)
                y += 34
            elif kind in ("section", "heading"):
                y += 8
                write_line(page, 50, y, text, 13 if kind == "section" else HEAD, bold_all=True)
                if portraits and kind == "heading":
                    rect = pymupdf.Rect(470, y - 12, 530, y + 63)
                    page.insert_image(rect, stream=placeholder_portrait(len(placed) % 3))
                    placed.append(rect)
                y += 20
            elif kind == "bullet":
                write_line(page, 61, y, "• " + text, BODY)
                y += 15
            elif kind == "wrap":
                write_line(page, 70, y - 1, text, BODY)
                y += 15
            elif kind == "note":
                y += 10
                write_line(page, 50, y, text, BODY)
                y += 15
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.subset_fonts()
    doc.save(out, garbage=4, deflate=True)
    print(f"wrote {out}")


def main():
    build(PAGES, SAMPLES / "sample-sheet.pdf", "Grade 8 Social Studies | Sample sheet")
    build(HISTORY, SAMPLES / "history-sheet.pdf", "Class 8 History | Sample sheet")
    build(PEOPLE, SAMPLES / "people-sheet.pdf", "Class 8 History | Reformers sample", portraits=True)
    build(INDUSTRIES, SAMPLES / "industries-sheet.pdf", "Class 8 Geography | Industries sample")


if __name__ == "__main__":
    main()
