"""PDF -> numbered source units SRC-P{page}-U{n} (pipeline step 2).

Text pages use PyMuPDF text blocks. Pages with almost no text layer are sent to OCR.
Figures are detected and reported but not interpreted in V1.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional

import pymupdf

MIN_PAGE_CHARS = 30  # below this the page is treated as scanned and OCR is attempted
HEADING_CHARS = 60  # short blocks (headings) are merged into the following block


class ExtractionError(Exception):
    """The file cannot be opened as a PDF."""


@dataclass
class SourceUnit:
    id: str
    page: int
    text: str
    method: str  # "text" | "ocr"


@dataclass
class ExtractedSource:
    units: list[SourceUnit]
    page_count: int
    ocr_pages: list[int] = field(default_factory=list)
    unreadable_pages: list[int] = field(default_factory=list)
    figure_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


OcrFn = Callable[[bytes], str]


def tesseract_ocr(png: bytes) -> str:
    proc = subprocess.run(["tesseract", "stdin", "stdout"], input=png, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="ignore")[:200])
    return proc.stdout.decode("utf-8", errors="ignore")


def choose_ocr(setting: str, llm=None) -> tuple[Optional[OcrFn], str]:
    """Pick the OCR backend. Returns (function or None, description)."""
    has_tess = shutil.which("tesseract") is not None
    if setting == "off":
        return None, "OCR disabled"
    if setting in ("auto", "tesseract") and has_tess:
        return tesseract_ocr, "tesseract"
    if setting == "tesseract":
        return None, "tesseract requested but not installed"
    if llm is not None and setting in ("auto", "claude"):
        return llm.transcribe_image, "claude-vision"
    return None, "no OCR backend available"


def _clean(text: str) -> str:
    text = text.replace("­", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)  # re-join hyphenated line breaks
    return re.sub(r"\s+", " ", text).strip()


def _merge_blocks(texts: list[str]) -> list[str]:
    return [text for text, _ in _merge_block_sources(texts)]


def _merge_block_sources(texts: list[str]) -> list[tuple[str, list[int]]]:
    """Merge short heading blocks into the next block; also return which input blocks each unit came from."""
    out: list[tuple[str, list[int]]] = []
    carry, carried = "", []
    for index, t in enumerate(texts):
        t = _clean(t)
        if not t:
            continue
        if len(t) < HEADING_CHARS and not t.endswith((".", "?", "!")):
            carry = f"{carry} {t}".strip()
            carried.append(index)
            continue
        out.append((f"{carry} {t}".strip() if carry else t, [*carried, index]))
        carry, carried = "", []
    if carry:
        if out:
            text, sources = out[-1]
            out[-1] = (f"{text} {carry}", [*sources, *carried])
        else:
            out.append((carry, carried))
    return out


def text_block_units(page, pno: int) -> list[tuple[pymupdf.Rect, str]]:
    """The text blocks of a text-layer page with the unit ID ``extract`` gives each of them."""
    blocks = [b for b in page.get_text("blocks", sort=True) if b[6] == 0]
    merged = _merge_block_sources([b[4] for b in blocks])
    return [
        (pymupdf.Rect(blocks[index][:4]), f"SRC-P{pno}-U{n}")
        for n, (_, sources) in enumerate(merged, start=1)
        for index in sources
    ]


def _paragraphs(ocr_text: str) -> list[str]:
    return _merge_blocks(re.split(r"\n\s*\n", ocr_text))


def _open_pdf(pdf_input: str | bytes):
    try:
        if isinstance(pdf_input, bytes):
            return pymupdf.open(stream=pdf_input, filetype="pdf")
        return pymupdf.open(pdf_input)
    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"cannot open PDF: {e}") from e


def pdf_page_count(pdf_input: str | bytes) -> int:
    with _open_pdf(pdf_input) as doc:
        if not doc.is_pdf:
            raise ExtractionError("the file is not a PDF")
        return doc.page_count


def extract(
    pdf_input: str | bytes, ocr: Optional[OcrFn] = None, ocr_name: str = "none", pages: Optional[set[int]] = None
) -> ExtractedSource:
    try:
        doc = _open_pdf(pdf_input)
    except Exception as e:  # PyMuPDF raises several types for bad files
        raise ExtractionError(f"cannot open PDF: {e}") from e
    if doc.needs_pass:
        raise ExtractionError("the PDF is password-protected")
    if not doc.is_pdf:
        raise ExtractionError("the file is not a PDF")

    result = ExtractedSource(units=[], page_count=doc.page_count)
    for index, page in enumerate(doc):
        pno = index + 1
        if pages is not None and pno not in pages:
            continue
        blocks = [b[4] for b in page.get_text("blocks", sort=True) if b[6] == 0]
        method = "text"
        if sum(len(b.strip()) for b in blocks) < MIN_PAGE_CHARS:
            if ocr is None:
                result.unreadable_pages.append(pno)
                continue
            try:
                png = page.get_pixmap(dpi=200).tobytes("png")
                blocks = _paragraphs(ocr(png))
                method = "ocr"
                result.ocr_pages.append(pno)
            except Exception as e:
                result.unreadable_pages.append(pno)
                result.warnings.append(f"OCR failed on page {pno} ({ocr_name}): {e}")
                continue
            if sum(len(b) for b in blocks) < MIN_PAGE_CHARS:
                result.unreadable_pages.append(pno)
                continue
        else:
            blocks = _merge_blocks(blocks)
        if page.get_images(full=False) or len(page.get_drawings()) > 20:  # vector diagrams have many paths
            result.figure_pages.append(pno)
        for n, text in enumerate(blocks, start=1):
            result.units.append(SourceUnit(id=f"SRC-P{pno}-U{n}", page=pno, text=text, method=method))

    if result.ocr_pages:
        result.warnings.append(
            f"Pages {_fmt(result.ocr_pages)} were read with OCR ({ocr_name}); OCR text can contain errors."
        )
    if result.unreadable_pages:
        result.warnings.append(f"Pages {_fmt(result.unreadable_pages)} had no readable text and were not used.")
    if result.figure_pages:
        result.warnings.append(
            f"Pages {_fmt(result.figure_pages)} contain pictures or diagrams. Learn V1 does not interpret "
            "figures, so only their surrounding text was used."
        )
    return result


def _fmt(pages: list[int]) -> str:
    return ", ".join(str(p) for p in pages)
