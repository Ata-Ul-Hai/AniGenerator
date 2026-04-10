"""Document parsing and chunking utilities for PDF, DOCX, and TXT files."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber
from docx import Document

logger = logging.getLogger(__name__)

SECTION_WORD_THRESHOLD = 3000


def _extract_pdf_text(file_path: Path) -> str:
    """Extract plain text from a PDF document."""

    pages: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text.strip())
            else:
                logger.debug("Skipping empty PDF page %s in %s", idx, file_path)
    return "\n\n".join(pages)


def _extract_docx_text(file_path: Path) -> str:
    """Extract plain text from a DOCX document."""

    doc = Document(file_path)
    lines = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
    return "\n".join(lines)


def _extract_txt_text(file_path: Path) -> str:
    """Extract plain text from a text file with encoding fallback."""

    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("Non-UTF-8 encoding detected in %s; using replacement characters", file_path)
        return file_path.read_text(encoding="utf-8", errors="replace")


def _normalize_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph boundaries."""

    collapsed = re.sub(r"\r\n?", "\n", text)
    collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
    return collapsed.strip()


def _count_words(text: str) -> int:
    """Count words in a text blob using whitespace tokenization."""

    return len(text.split())


def extract_text(file_path: str, max_file_size_mb: int = 50) -> str:
    """Extract text content from PDF, DOCX, or TXT file paths."""

    source = Path(file_path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # Pre-check file size to prevent OOM on huge files
    size_mb = source.stat().st_size / (1024 * 1024)
    if size_mb > max_file_size_mb:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Maximum supported: {max_file_size_mb} MB")

    suffix = source.suffix.lower()
    logger.info("Extracting text from %s (%.1f MB)", source, size_mb)

    if suffix == ".pdf":
        raw = _extract_pdf_text(source)
    elif suffix == ".docx":
        raw = _extract_docx_text(source)
    elif suffix == ".txt":
        raw = _extract_txt_text(source)
    else:
        raise ValueError("Unsupported file type. Expected .pdf, .docx, or .txt")

    normalized = _normalize_text(raw)
    if not normalized:
        raise ValueError("Document contains no extractable text")

    logger.info("Extracted %s words from %s", _count_words(normalized), source)
    return normalized


def chunk_text(extracted_text: str, threshold_words: int = SECTION_WORD_THRESHOLD) -> list[str]:
    """Split long text into section-aligned chunks when it exceeds a word threshold."""

    text = _normalize_text(extracted_text)
    if not text:
        return []

    total_words = _count_words(text)
    if total_words <= threshold_words:
        return [text]

    sections = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    chunks: list[str] = []
    current_parts: list[str] = []
    current_words = 0

    for section in sections:
        section_words = _count_words(section)

        if section_words >= threshold_words:
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_words = 0

            words = section.split()
            for start in range(0, len(words), threshold_words):
                chunks.append(" ".join(words[start : start + threshold_words]))
            continue

        if current_words + section_words > threshold_words and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = [section]
            current_words = section_words
        else:
            current_parts.append(section)
            current_words += section_words

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    logger.info("Chunked document into %s chunk(s)", len(chunks))
    return chunks


def extract_text_chunks(file_path: str, threshold_words: int = SECTION_WORD_THRESHOLD) -> list[str]:
    """Extract document text and return section-aware chunks for long inputs."""

    return chunk_text(extract_text(file_path), threshold_words=threshold_words)
