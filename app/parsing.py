from io import BytesIO
import re

from docx import Document
from pypdf import PdfReader


class ParseError(ValueError):
    pass


def extract_sections(filename: str, content: bytes) -> list[tuple[str, str]]:
    suffix = filename.lower().rsplit(".", 1)[-1]
    try:
        if suffix == "pdf":
            reader = PdfReader(BytesIO(content))
            return [(f"第 {i} 页", page.extract_text() or "") for i, page in enumerate(reader.pages, 1)]
        if suffix == "docx":
            doc = Document(BytesIO(content))
            paragraphs = [(i, p.text.strip()) for i, p in enumerate(doc.paragraphs, 1) if p.text.strip()]
            return [(f"段落 {i}", text) for i, text in paragraphs]
        if suffix == "txt":
            paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content.decode("utf-8-sig")) if part.strip()]
            return [(f"段落 {i}", text) for i, text in enumerate(paragraphs, 1)]
    except Exception as exc:
        raise ParseError("文件无法解析，请确认文件未损坏且不是加密文档。") from exc
    raise ParseError("仅支持 PDF、DOCX 和 TXT 文件。")


def split_sections(sections: list[tuple[str, str]], size: int = 550, overlap: int = 80) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    for locator, raw in sections:
        text = " ".join(raw.split())
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = max(text.rfind("。", start + size // 2, end), text.rfind(". ", start + size // 2, end))
                if boundary > start:
                    end = boundary + 1
            chunks.append((locator, text[start:end]))
            if end == len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks
