"""Diagram source as a plain-text outline (SPEC-document-import §2.2).

Mermaid flowcharts, ER diagrams and sequence diagrams, and draw.io files, are read
deterministically into lists of nodes and edges with their labels, so the import model
maps what the diagram says rather than how its syntax looks. Flowchart node shapes map
back to component kinds by reversing ``diagrams.SHAPES``.
"""

import base64
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zlib

from blueprint.exports.diagrams import CARDINALITY, SHAPES

# (opening, closing) brackets of each component kind's shape, without the label quotes.
SHAPE_KINDS = {(start.strip('"'), end.strip('"')): kind for kind, (start, end) in SHAPES.items()}
CARDINALITY_ENDS = {ends: cardinality for cardinality, ends in CARDINALITY.items()}
ENTITY_CODES = {"#quot;": '"', "#35;": "#", "#59;": ";"}

NODE = re.compile(
    r"(?P<id>[A-Za-z0-9_]+)(?P<open>\(\[|\[\[|\[\(|\[/|\[\\|\(\(|\{\{|[\[\(\{>])"
    r'(?P<label>"[^"]*"|[^\]\)\}"]*)'
    r"(?P<close>\]\)|\]\]|\)\]|/\]|\\\]|\)\)|\}\}|[\]\)\}])"
)
EDGE = re.compile(
    r"(?P<a>[A-Za-z0-9_]+)\s*(?P<arrow>-\.+->|-\.-|={2,}>|-{2,}>|-{3,})"
    r'\s*(?:\|"?(?P<label>[^|"]*)"?\|)?\s*(?=(?P<b>[A-Za-z0-9_]+))'
)
TEXT_EDGE = re.compile(
    r"(?P<a>[A-Za-z0-9_]+)\s*--\s+(?P<label>[^-][^>]*?)\s+-->\s*(?P<b>[A-Za-z0-9_]+)"
)
# An entity, optionally labelled, optionally opening a block of fields with "{".
ER_ENTITY = re.compile(r'^(?P<id>[A-Za-z0-9_-]+)(?:\["(?P<label>[^"]*)"\])?(?P<fields>\s*\{)?$')
ER_RELATION = re.compile(
    r'^(?P<a>[A-Za-z0-9_-]+)\s+(?P<ends>\S+--\S+)\s+(?P<b>[A-Za-z0-9_-]+)\s*:\s*"?(?P<label>[^"]*)"?$'
)
PARTICIPANT = re.compile(r"^(?:participant|actor)\s+(?P<id>\S+)(?:\s+as\s+(?P<label>.+))?$")
MESSAGE = re.compile(
    r"^(?P<a>[^-\s>]+)\s*(?P<arrow>-->>|->>|-->|->|--x|-x|--\)|-\))\s*(?P<b>[^:\s]+)\s*:\s*(?P<label>.*)$"
)
ARROW_STYLES = {"-.": "dotted", "==": "thick"}


def _decode(value: str) -> str:
    """Mermaid text as written: outer quotes removed first, then entity codes decoded."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    for code, char in ENTITY_CODES.items():
        value = value.replace(code, char)
    return value.strip()


def _lines(source: str) -> list[str]:
    """Meaningful lines: no blanks, no ``%%`` comments, no surrounding whitespace."""
    return [s for line in source.splitlines() if (s := line.strip()) and not s.startswith("%%")]


def _flowchart(lines: list[str]) -> str:
    nodes: dict[str, str] = {}
    shapes: dict[str, str] = {}
    edges: list[str] = []
    for line in lines[1:]:
        for match in NODE.finditer(line):
            nodes[match["id"]] = _decode(match["label"]) or match["id"]
            kind = SHAPE_KINDS.get((match["open"], match["close"]))
            shapes[match["id"]] = kind or f"shape {match['open']}{match['close']}"
        bare = NODE.sub(lambda m: m["id"], line)
        found = [(m["a"], m["b"], m["label"] or "", m["arrow"]) for m in EDGE.finditer(bare)]
        found += [(m["a"], m["b"], m["label"], "-->") for m in TEXT_EDGE.finditer(bare)]
        for a, b, label, arrow in found:
            nodes.setdefault(a, a)
            nodes.setdefault(b, b)
            style = ARROW_STYLES.get(arrow[:2], "solid")
            edges.append(
                f"- {nodes[a]} -> {nodes[b]} ({style} arrow)"
                + (f": {_decode(label)}" if label else "")
            )
    out = ["Flowchart nodes:"]
    out += [f"- {label} ({shapes.get(node_id, 'no shape')})" for node_id, label in nodes.items()]
    return "\n".join([*out, "Flowchart edges:", *(edges or ["- (none)"])])


def _er_diagram(lines: list[str]) -> str:
    names: dict[str, str] = {}
    out = ["Entities:"]
    relations: list[str] = []
    current: str | None = None
    for line in lines[1:]:
        if current is not None:
            if line == "}":
                current = None
            else:
                out.append(f"  - field {_decode(line)}")
        elif match := ER_ENTITY.match(line):
            names[match["id"]] = _decode(match["label"] or "") or match["id"]
            out.append(f"- {names[match['id']]}")
            current = match["id"] if match["fields"] else None
        elif match := ER_RELATION.match(line):
            cardinality = CARDINALITY_ENDS.get(match["ends"], match["ends"])
            a, b = (names.get(match[k], match[k]) for k in ("a", "b"))
            relations.append(f"- {a} {cardinality} {b}: {_decode(match['label'])}")
    return "\n".join([*out, "Relationships:", *(relations or ["- (none)"])])


def _sequence(lines: list[str]) -> str:
    names: dict[str, str] = {}
    messages: list[str] = []
    for line in lines[1:]:
        if match := PARTICIPANT.match(line):
            names[match["id"]] = _decode(match["label"] or match["id"])
        elif match := MESSAGE.match(line):
            a, b = (names.setdefault(match[k], match[k]) for k in ("a", "b"))
            style = "dotted" if match["arrow"].startswith("--") else "solid"
            messages.append(f"- {a} -> {b} ({style} arrow): {_decode(match['label'])}")
    participants = [f"- {name}" for name in names.values()]
    return "\n".join(
        ["Participants:", *participants, "Messages in order:", *(messages or ["- (none)"])]
    )


def mermaid_outline(source: str) -> str | None:
    """The outline of one Mermaid diagram, or None for a diagram type this app does not read."""
    lines = _lines(source)
    if not lines:
        return None
    head = lines[0].split()[0]
    if head in ("flowchart", "graph"):
        return _flowchart(lines)
    if head == "erDiagram":
        return _er_diagram(lines)
    if head == "sequenceDiagram":
        return _sequence(lines)
    return None


# --- draw.io ---------------------------------------------------------------------------------


def _strip_html(value: str) -> str:
    """draw.io labels may hold HTML; keep the words, one line."""
    text = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    for entity, char in (("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&")):
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def _shape(style: str) -> str:
    """The shape a draw.io style names, e.g. ``cylinder3`` or ``mxgraph.aws4.lambda``."""
    parts = dict(p.split("=", 1) for p in style.split(";") if "=" in p)
    if "shape" in parts:
        return parts["shape"]
    bare = [p for p in style.split(";") if p and "=" not in p]
    return bare[0] if bare else "rectangle"


def _inflate(text: str, limit: int) -> str:
    """A compressed draw.io page: base64, raw deflate, then URL-encoded XML."""
    inflater = zlib.decompressobj(-15)
    raw = inflater.decompress(base64.b64decode(text), limit)
    if inflater.unconsumed_tail:
        raise ValueError("the diagram unpacks to more than the size limit")
    return urllib.parse.unquote(raw.decode("utf-8"))


def _page(model: ET.Element) -> str:
    cells = list(model.iter("mxCell"))
    vertices = {c.get("id", ""): c for c in cells if c.get("vertex") == "1"}
    edges = {c.get("id", ""): c for c in cells if c.get("edge") == "1"}
    labels: dict[str, str] = {}
    for cell_id, cell in list(vertices.items()):
        parent = cell.get("parent", "")
        if parent in edges:  # a label placed on an edge
            labels[parent] = _strip_html(cell.get("value", ""))
            del vertices[cell_id]
    names = {i: _strip_html(c.get("value", "")) or f"(unlabelled {i})" for i, c in vertices.items()}
    out = ["Shapes:"]
    out += [f"- {names[i]} (shape {_shape(c.get('style', ''))})" for i, c in vertices.items()]
    out.append("Connectors:")
    lines = []
    for edge_id, edge in edges.items():
        source, target = edge.get("source", ""), edge.get("target", "")
        label = _strip_html(edge.get("value", "")) or labels.get(edge_id, "")
        dashed = "dashed=1" in edge.get("style", "")
        line = f"- {names.get(source, '(unconnected)')} -> {names.get(target, '(unconnected)')}"
        line += f" ({'dashed' if dashed else 'solid'} line)" + (f": {label}" if label else "")
        lines.append(line)
    return "\n".join([*out, *(lines or ["- (none)"])])


def drawio_outline(data: bytes, limit: int) -> list[tuple[str, str]]:
    """Each page of a draw.io file as (locator, outline); raises ValueError when unreadable.

    ``limit`` caps how far a compressed page may unpack. Python's expat refuses
    entity-expansion bombs itself, so the standard XML parser is safe here.
    """
    try:
        root = ET.fromstring(data)
        pages: list[tuple[str, str]] = []
        diagrams = root.findall("diagram") if root.tag == "mxfile" else []
        if root.tag == "mxGraphModel":
            pages.append(("page 1", _page(root)))
        for index, diagram in enumerate(diagrams, start=1):
            model = diagram.find("mxGraphModel")
            if model is None and (diagram.text or "").strip():
                model = ET.fromstring(_inflate((diagram.text or "").strip(), limit))
            if model is not None:
                pages.append((f"page {diagram.get('name') or index}", _page(model)))
    except (ET.ParseError, zlib.error, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"not a readable draw.io file ({exc})") from exc
    if not pages:
        raise ValueError("the draw.io file has no diagram pages")
    return pages
