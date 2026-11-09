from __future__ import annotations

import unicodedata
from pathlib import Path
import re

import pymupdf
from docx import Document
from docx.oxml.ns import qn


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
_PAGE_NUMBER_RE = re.compile(r"^\s*(?:\d+|[ivxlcdm]+)\s*$", flags=re.IGNORECASE)


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported input format {suffix!r}. Supported: {supported}")

    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    pages: list[str] = []
    with pymupdf.open(path) as document:
        for index, page in enumerate(document, start=1):
            # Sorting by coordinates gives a more natural reading order for
            # multi-column PDFs than the object's internal text order.
            text = page.get_text("text", sort=True) or ""
            text = _clean_pdf_page_text(text, index)
            if text:
                pages.append(text)
    if not pages:
        raise ValueError("No selectable PDF text was found. This may be a scanned PDF that needs OCR.")
    full_text = "\n".join(pages)
    bad_text = _bad_text_stats(full_text)
    if bad_text["surrogates"] > 0 or bad_text["replacement_ratio"] > 0.0001 or bad_text["replacements"] > 20:
        raise ValueError(
            "PDF text extraction looks corrupted because it contains invalid or replacement characters. "
            "Use OCR or a cleaner source file before generating audio."
        )
    return full_text


def _clean_pdf_page_text(text: str, page_number: int) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ""

    if _looks_like_table_of_contents(lines):
        return ""

    cleaned: list[str] = []
    for index, line in enumerate(lines):
        if index == 0 and _PAGE_NUMBER_RE.match(line):
            continue
        if line == str(page_number):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _looks_like_table_of_contents(lines: list[str]) -> bool:
    head = " ".join(lines[:6]).casefold()
    return "tartalomjegyz" in head or "contents" in head


def _read_docx(path: Path) -> str:
    doc = Document(str(path))
    parts: list[str] = []

    for paragraph in doc.paragraphs:
        text = _paragraph_text_with_links(paragraph, doc).strip()
        if text:
            parts.append(text)

    for table in doc.tables:
        for row in table.rows:
            cells = []
            for cell in row.cells:
                cell_text = " ".join(
                    _paragraph_text_with_links(paragraph, doc).strip()
                    for paragraph in cell.paragraphs
                ).strip()
                if cell_text:
                    cells.append(cell_text)
            if cells:
                parts.append(" | ".join(cells))

    if not parts:
        raise ValueError("No readable DOCX text was found.")
    return "\n\n".join(parts)


def _paragraph_text_with_links(paragraph, document: Document) -> str:
    pieces: list[str] = []
    for child in paragraph._p:
        if child.tag == qn("w:hyperlink"):
            relationship_id = child.get(qn("r:id"))
            relationship = document.part.rels.get(relationship_id)
            if relationship is not None and relationship.is_external:
                pieces.append(str(relationship.target_ref))
                continue
        pieces.append("".join(node.text or "" for node in child.iter(qn("w:t"))))
    return "".join(pieces) or paragraph.text


def _bad_text_stats(text: str) -> dict[str, float | int]:
    if not text:
        return {"replacements": 0, "replacement_ratio": 0.0, "surrogates": 0}
    replacements = 0
    surrogates = 0
    for char in text:
        if char == "\ufffd":
            replacements += 1
        elif unicodedata.category(char) == "Cs":
            surrogates += 1
    return {
        "replacements": replacements,
        "replacement_ratio": replacements / len(text),
        "surrogates": surrogates,
    }

