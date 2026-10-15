"""Curated, source-linked open social-studies visuals hosted on Wikimedia Commons."""

from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class LibraryVisual:
    id: str
    title: str
    topic: str
    region: str
    description: str
    filename: str
    author: str
    license_name: str
    license_url: str

    @property
    def source_url(self) -> str:
        return f"https://commons.wikimedia.org/wiki/File:{quote(self.filename.replace(' ', '_'), safe='()')}"

    @property
    def image_url(self) -> str:
        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(self.filename, safe='')}?width=640"


_CC_BY = "https://creativecommons.org/licenses/by/4.0/"
_CC_BY_30 = "https://creativecommons.org/licenses/by/3.0/"
_CC_BY_SA_30 = "https://creativecommons.org/licenses/by-sa/3.0/"
_CC_BY_SA_40 = "https://creativecommons.org/licenses/by-sa/4.0/"
_CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
_PUBLIC_DOMAIN = "https://commons.wikimedia.org/wiki/Commons:Licensing#Public_domain"

VISUAL_LIBRARY = (
    LibraryVisual(
        "ashoka-lion-capital",
        "Lion Capital of Ashoka",
        "Mauryan Empire; symbols and rulers",
        "Indian Studies",
        "Sarnath Lion Capital, a Mauryan-period sculpture photographed in the Sarnath Museum.",
        "Sarnath Lion Capital.jpg",
        "Chrisi1964",
        "CC BY-SA 4.0",
        _CC_BY_SA_40,
    ),
    LibraryVisual(
        "taj-mahal",
        "Taj Mahal",
        "Mughal architecture; monuments",
        "Indian Studies",
        "Photograph of the Taj Mahal in Agra.",
        "Complete Taj Mahal.jpg",
        "Fioselvan",
        "CC BY-SA 4.0",
        _CC_BY_SA_40,
    ),
    LibraryVisual(
        "revolt-meerut-1857",
        "The Sepoy revolt at Meerut (1857)",
        "Revolt of 1857; reading historical images critically",
        "Indian Studies",
        "An 1857 newspaper illustration. It reflects the publication's viewpoint; pair it with other sources rather than treating it as a neutral photograph.",
        "The Sepoy revolt at Meerut.jpg",
        "The Illustrated Times",
        "Public domain",
        _PUBLIC_DOMAIN,
    ),
    LibraryVisual(
        "salt-march",
        "Gandhi during the Salt March",
        "National movement; civil disobedience",
        "Indian Studies",
        "Archival photograph of Gandhi during the Salt March in 1930.",
        "Gandhi Salt March.jpg",
        "Unknown author; scan credited on Commons to Yann",
        "Public domain in India and the United States (Commons tags)",
        _PUBLIC_DOMAIN,
    ),
    LibraryVisual(
        "constitution-preamble",
        "Preamble of the Constitution of India",
        "Civics; Constitution and the Preamble",
        "Indian Studies",
        "Photograph of the Preamble displayed at the University of Mumbai Fort campus.",
        "Constitution of india.jpg",
        "Balajijagadesh",
        "CC0 1.0",
        _CC0,
    ),
    LibraryVisual(
        "parliament-building",
        "Parliament House, New Delhi",
        "Civics; Parliament and institutions",
        "Indian Studies",
        "Photograph of India's Parliament building (the historic Parliament House).",
        "Indian Parliament Building Delhi India.JPG",
        "Shahnoor Habib Munmun",
        "CC BY 3.0",
        _CC_BY_30,
    ),
    LibraryVisual(
        "himalayas",
        "Himalayas in India",
        "Physical geography; mountain environments",
        "Indian Studies",
        "Photograph of the Himalayas in India.",
        "Himalayas in India.jpg",
        "Borkar Pranil",
        "CC BY-SA 4.0",
        _CC_BY_SA_40,
    ),
    LibraryVisual(
        "ganges-river",
        "Ganges River at Patna",
        "Physical geography; rivers and settlements",
        "Indian Studies",
        "Photograph of the Ganges at Patna; use as a visual prompt, not as a map or complete river-system reference.",
        "Ganges River 2.jpg",
        "Ravi Ranjan 04",
        "CC BY-SA 4.0",
        _CC_BY_SA_40,
    ),
    LibraryVisual(
        "watt-steam-engine",
        "Watt's double steam engine (1782 design)",
        "Industrial Revolution; technology and change",
        "UK comparison",
        "An 1822 engraving depicting a double steam engine associated with James Watt's 1782 specification. It is an illustration, not evidence that one person invented the steam engine.",
        "Steam engine - Mr. Watt's double steam engine from his specification of 1782 LCCN2006691752.jpg",
        "Library of Congress",
        "Public domain (Commons record)",
        _PUBLIC_DOMAIN,
    ),
    LibraryVisual(
        "james-watt-engine",
        "Model of a Watt beam engine",
        "Industrial Revolution; engineering and industrial change",
        "UK comparison",
        "Photograph of a later model of a beam engine featuring Watt's parallel linkage; not a photograph of the original machine.",
        "JamesWattEngine.jpg",
        "Tamorlan",
        "Public domain (author dedication)",
        _PUBLIC_DOMAIN,
    ),
)


def list_visuals(region: str | None = None) -> tuple[LibraryVisual, ...]:
    if region is None or region == "all":
        return VISUAL_LIBRARY
    return tuple(visual for visual in VISUAL_LIBRARY if visual.region == region)
