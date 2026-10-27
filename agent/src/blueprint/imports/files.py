"""Attached files read into quotable sections (SPEC-document-import §2.2, §2.3).

Pure functions of the bytes given: no model and no I/O. A file this app cannot take is
refused with ``AttachmentRejected``, which carries the HTTP status and error code the
upload route answers with.
"""

import io
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import Literal, NamedTuple

import docx
import pypdf
from docx.document import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf.errors import PyPdfError

from blueprint.imports.outline import drawio_outline, mermaid_outline

MAX_BYTES = 10 * 1024 * 1024
MAX_CHARS = 150_000
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_ATTACHMENTS = 20

Kind = Literal["text", "pdf", "docx", "mermaid", "drawio", "image"]

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAGIC: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    DOCX: (b"PK\x03\x04",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
}
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
MERMAID_FENCE = re.compile(r"^```mermaid\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)


class AttachmentRejected(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


@dataclass(frozen=True)
class Section:
    """One quotable part of a file, with where it is: a page, a heading path or a diagram page."""

    locator: str
    text: str


@dataclass(frozen=True)
class ParsedFile:
    kind: Kind
    media_type: str
    sections: list[Section]
    warnings: list[str] = field(default_factory=list)


def accepted_extensions(vision: bool) -> list[str]:
    """What the upload route takes right now: images only when the model can read them."""
    return [ext for ext, file_type in FILE_TYPES.items() if vision or file_type.kind != "image"]


def _invalid(message: str) -> AttachmentRejected:
    return AttachmentRejected(422, "invalid_file", message)


def _content_matches(media_type: str, data: bytes) -> bool:
    if media_type == "image/webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    signatures = MAGIC.get(media_type)
    if signatures is not None:
        return data.startswith(signatures)
    return b"\x00" not in data  # every other accepted type is text


def _utf8(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise _invalid("the file is not UTF-8 text") from None


def by_headings(blocks: list[tuple[int, str]], untitled: str) -> list[Section]:
    """Group (heading level, text) blocks into sections located by their heading path.

    Level 0 is body text; a heading of level n closes every open heading of level n or deeper.
    """
    sections: list[Section] = []
    path: list[tuple[int, str]] = []
    body: list[str] = []

    def flush() -> None:
        text = "\n".join(body).strip()
        if text:
            sections.append(Section(" > ".join(t for _, t in path) or untitled, text))
        body.clear()

    for level, text in blocks:
        if level == 0:
            body.append(text)
            continue
        flush()
        path = [(lv, t) for lv, t in path if lv < level] + [(level, text)]
        body.append(text)
    flush()
    return sections


# A reader's result: the file's sections and anything the user should know about the reading.
Reading = tuple[list[Section], list[str]]


def _markdown(data: bytes) -> Reading:
    source = _utf8(data)
    blocks = []
    for line in source.splitlines():
        match = HEADING.match(line)
        blocks.append((len(match[1]), match[2]) if match else (0, line))
    sections = by_headings(blocks, "document")
    diagrams = [mermaid_outline(m[1]) for m in MERMAID_FENCE.finditer(source)]
    sections += [Section(f"diagram {i}", o) for i, o in enumerate(diagrams, start=1) if o]
    return sections, []


def _plain_text(data: bytes) -> Reading:
    text = _utf8(data).strip()
    return ([Section("document", text)] if text else []), []


def _pdf(data: bytes) -> Reading:
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise _invalid("the PDF is password-protected")
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except (PyPdfError, ValueError, KeyError, OSError) as exc:
        raise _invalid(f"the PDF could not be read ({exc})") from None
    sections = [Section(f"p.{n}", text) for n, text in enumerate(pages, start=1) if text]
    warnings = [f"page {n} has no text" for n, text in enumerate(pages, start=1) if not text]
    return sections, warnings


def _unpacked_size(data: bytes) -> int:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile:
        raise _invalid("the .docx file is damaged") from None


def _docx_blocks(document: DocxDocument) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    for item in document.iter_inner_content():
        if isinstance(item, Paragraph):
            style = item.style.name if item.style is not None and item.style.name else ""
            heading = re.fullmatch(r"Heading (\d)", style)
            # The Title sits above "Heading 1", so headings are one level below it.
            level = int(heading[1]) + 1 if heading else 1 if style == "Title" else 0
            if text := item.text.strip():
                blocks.append((level, text))
        elif isinstance(item, Table):
            for row in item.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    blocks.append((0, " | ".join(cells)))
    return blocks


def _docx(data: bytes) -> Reading:
    if _unpacked_size(data) > MAX_UNPACKED_BYTES:
        raise _invalid("the .docx file unpacks to more than 50 MB")
    try:
        document = docx.Document(io.BytesIO(data))
    except (KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise _invalid(f"the .docx file could not be read ({exc})") from None
    images = any("image" in rel.reltype for rel in document.part.rels.values())
    warnings = ["images inside the document are not read"] if images else []
    return by_headings(_docx_blocks(document), "document"), warnings


def _mermaid(data: bytes) -> Reading:
    source = _utf8(data)
    outline = mermaid_outline(source)
    if outline is None:
        return [Section("diagram", source.strip())], [
            "this Mermaid diagram type is read as plain text"
        ]
    return [Section("diagram", outline)], []


def _drawio(data: bytes) -> Reading:
    try:
        pages = drawio_outline(data, MAX_UNPACKED_BYTES)
    except ValueError as exc:
        raise _invalid(str(exc)) from None
    return [Section(*page) for page in pages], []


def _image(data: bytes) -> Reading:
    return [], []  # the interview model reads the image itself


class FileType(NamedTuple):
    kind: Kind
    media_type: str
    read: Callable[[bytes], Reading]


# Extension -> its type. The type is decided by extension and checked by content.
FILE_TYPES: dict[str, FileType] = {
    ".md": FileType("text", "text/markdown", _markdown),
    ".txt": FileType("text", "text/plain", _plain_text),
    ".pdf": FileType("pdf", "application/pdf", _pdf),
    ".docx": FileType("docx", DOCX, _docx),
    ".mmd": FileType("mermaid", "text/vnd.mermaid", _mermaid),
    ".mermaid": FileType("mermaid", "text/vnd.mermaid", _mermaid),
    ".drawio": FileType("drawio", "application/vnd.jgraph.mxfile", _drawio),
    ".png": FileType("image", "image/png", _image),
    ".jpg": FileType("image", "image/jpeg", _image),
    ".jpeg": FileType("image", "image/jpeg", _image),
    ".webp": FileType("image", "image/webp", _image),
}


def read_file(name: str, data: bytes, vision: bool) -> ParsedFile:
    """Check an uploaded file and read it into sections; raises ``AttachmentRejected``."""
    extension = PurePath(name).suffix.lower()
    if extension not in FILE_TYPES:
        accepted = ", ".join(accepted_extensions(vision))
        raise AttachmentRejected(415, "unsupported_type", f"{name} is not one of: {accepted}")
    if len(data) > MAX_BYTES:
        raise AttachmentRejected(413, "file_too_large", f"{name} is larger than 10 MB")
    file_type = FILE_TYPES[extension]
    if file_type.kind == "image" and not vision:
        raise AttachmentRejected(
            422, "vision_unavailable", "the interview model cannot read images, so images are off"
        )
    if not _content_matches(file_type.media_type, data):
        raise _invalid(f"the content of {name} is not a {extension} file")
    sections, warnings = file_type.read(data)
    if file_type.kind != "image" and not sections:
        raise AttachmentRejected(422, "no_text", f"{name} has no text this app can read")
    if sum(len(s.text) for s in sections) > MAX_CHARS:
        raise AttachmentRejected(
            422, "too_long", f"{name} has more than {MAX_CHARS:,} characters of text; split it"
        )
    return ParsedFile(file_type.kind, file_type.media_type, sections, warnings)
