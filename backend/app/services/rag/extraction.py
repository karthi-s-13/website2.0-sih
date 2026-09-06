"""PDF text extraction with an optional OCR fallback (Phase 7 pipeline stages
1-2: "PDF -> Text extraction -> OCR where required").

Real review-report PDFs in this project are almost entirely text-based
(confirmed by inspection); only cover/title pages tend to be a single
embedded image. OCR is implemented as a genuine, working code path - it
activates automatically wherever Tesseract is actually installed - but
degrades gracefully (skips the page, logs why) when it is not, rather than
failing the whole ingestion run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MIN_TEXT_CHARS_BEFORE_OCR = 20


@dataclass(frozen=True)
class PageText:
    page: int  # 1-based
    text: str
    method: str  # TEXT | OCR | EMPTY


def _try_ocr(page) -> str | None:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return None

    try:
        pix = page.get_pixmap(dpi=200)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        text = pytesseract.image_to_string(image)
        return text.strip() or None
    except Exception:  # noqa: BLE001 - OCR is best-effort, never fatal
        return None


def extract_pdf_pages(path: Path) -> list[PageText]:
    import fitz  # PyMuPDF

    pages: list[PageText] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if len(text) >= MIN_TEXT_CHARS_BEFORE_OCR:
                pages.append(PageText(page=i, text=text, method="TEXT"))
                continue

            has_images = len(page.get_images(full=True)) > 0
            ocr_text = _try_ocr(page) if has_images else None
            if ocr_text:
                pages.append(PageText(page=i, text=ocr_text, method="OCR"))
            else:
                pages.append(PageText(page=i, text=text, method="EMPTY"))

    return pages
