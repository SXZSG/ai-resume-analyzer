import re
from typing import List

import fitz


class PDFParseError(Exception):
    """Raised when a PDF cannot be parsed into usable text."""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF byte stream with PyMuPDF."""
    if not pdf_bytes:
        raise PDFParseError("PDF 文件为空。")

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            page_texts: List[str] = []
            for page in document:
                page_texts.append(page.get_text("text"))
    except Exception as exc:
        raise PDFParseError("PDF 无法解析，请确认文件未损坏且不是加密 PDF。") from exc

    text = "\n".join(page_texts)
    cleaned = clean_resume_text(text)
    if not cleaned:
        raise PDFParseError("PDF 内容为空或无法提取文本。")
    return cleaned


def clean_resume_text(text: str) -> str:
    """Normalize whitespace and remove invisible control characters."""
    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
