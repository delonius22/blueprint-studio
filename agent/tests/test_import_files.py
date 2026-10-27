"""Reading attached files into sections, and every refusal (SPEC-document-import §2.2, §2.3)."""

import io
import zipfile
from pathlib import Path

import pytest
from sample_files import BRIEF_MD, PNG, make_docx, make_drawio, make_pdf

from blueprint.domain.models import Design
from blueprint.exports import diagrams
from blueprint.imports.files import (
    MAX_BYTES,
    MAX_CHARS,
    AttachmentRejected,
    Section,
    accepted_extensions,
    read_file,
)
from blueprint.imports.outline import mermaid_outline

EXPECTED = Path(__file__).parent / "expected" / "diagrams"


def rejected(name: str, data: bytes, vision: bool = True) -> tuple[int, str]:
    with pytest.raises(AttachmentRejected) as refusal:
        read_file(name, data, vision)
    return refusal.value.status, refusal.value.code


def test_markdown_is_split_by_heading_path_and_its_mermaid_is_outlined() -> None:
    parsed = read_file("brief.md", BRIEF_MD.encode(), vision=False)
    locators = [s.locator for s in parsed.sections]
    assert locators[:3] == [
        "Link shortener",
        "Link shortener > Requirements",
        "Link shortener > Out of scope",
    ]
    assert "Redirects must be fast." in parsed.sections[1].text
    assert parsed.sections[-1].locator == "diagram 1"
    assert "- Browser (client)" in parsed.sections[-1].text
    assert "- Browser -> API (solid arrow)" in parsed.sections[-1].text


def test_plain_text_is_one_section() -> None:
    parsed = read_file("notes.txt", b"\xef\xbb\xbfJust notes.\n", vision=False)
    assert parsed.sections == [Section("document", "Just notes.")]


def test_pdf_pages_are_located_and_pages_without_text_are_warned_about() -> None:
    parsed = read_file("prd.pdf", make_pdf(["Users shorten URLs", "", "p95 under 50 ms"]), False)
    assert [(s.locator, s.text) for s in parsed.sections] == [
        ("p.1", "Users shorten URLs"),
        ("p.3", "p95 under 50 ms"),
    ]
    assert parsed.warnings == ["page 2 has no text"]


def test_a_pdf_with_no_text_at_all_is_refused() -> None:
    assert rejected("scan.pdf", make_pdf(["", ""])) == (422, "no_text")


def test_docx_headings_and_tables_keep_their_order() -> None:
    data = make_docx(
        [("Title", "Shortener PRD"), ("Heading 1", "Goals"), ("Normal", "Fast redirects")],
        table=[["ID", "Requirement"], ["FR-1", "Shorten a URL"]],
    )
    parsed = read_file("prd.docx", data, vision=False)
    assert parsed.sections[-1].locator == "Shortener PRD > Goals"
    assert parsed.sections[-1].text.splitlines() == [
        "Goals",
        "Fast redirects",
        "ID | Requirement",
        "FR-1 | Shorten a URL",
    ]


@pytest.mark.parametrize("compressed", [False, True])
def test_drawio_pages_become_shapes_and_connectors(compressed: bool) -> None:
    parsed = read_file("arch.drawio", make_drawio(compressed), vision=False)
    (section,) = parsed.sections
    assert section.locator == "page Backend"
    assert "- Web client (shape actor)" in section.text
    assert "- Orders DB (shape cylinder3)" in section.text
    assert "- Web client -> Orders DB (dashed line): place order" in section.text


def test_images_are_taken_only_when_the_model_reads_images() -> None:
    assert read_file("arch.png", PNG, vision=True).kind == "image"
    assert rejected("arch.png", PNG, vision=False) == (422, "vision_unavailable")
    assert ".png" in accepted_extensions(True)
    assert ".png" not in accepted_extensions(False)


@pytest.mark.parametrize(
    ("name", "data", "expected"),
    [
        ("tool.exe", b"MZ", (415, "unsupported_type")),
        ("big.txt", b"a" * (MAX_BYTES + 1), (413, "file_too_large")),
        ("long.txt", b"a" * (MAX_CHARS + 1), (422, "too_long")),
        ("fake.pdf", b"not a pdf", (422, "invalid_file")),
        ("fake.png", b"GIF89a", (422, "invalid_file")),
        ("binary.md", b"abc\x00def", (422, "invalid_file")),
        ("latin1.txt", "café".encode("latin-1"), (422, "invalid_file")),
        ("empty.md", b"   \n", (422, "no_text")),
        ("broken.docx", b"PK\x03\x04broken", (422, "invalid_file")),
        ("broken.drawio", b"<mxfile><diagram>", (422, "invalid_file")),
    ],
)
def test_refusals_name_their_status_and_code(
    name: str, data: bytes, expected: tuple[int, str]
) -> None:
    assert rejected(name, data) == expected


def test_a_docx_that_unpacks_too_far_is_refused_before_it_is_parsed() -> None:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"\x00" * (51 * 1024 * 1024))
    assert rejected("bomb.docx", out.getvalue()) == (422, "invalid_file")


def test_an_xml_entity_bomb_is_refused() -> None:
    entities = '<!ENTITY a "aaaaaaaaaa">' + "".join(
        f'<!ENTITY {c} "{("&" + p + ";") * 10}">'
        for p, c in zip("abcdefgh", "bcdefghi", strict=True)
    )
    bomb = f'<?xml version="1.0"?><!DOCTYPE m [{entities}]><mxfile><diagram>&i;</diagram></mxfile>'
    assert rejected("bomb.drawio", bomb.encode()) == (422, "invalid_file")


def test_the_apps_own_mermaid_round_trips_to_its_components_and_flows() -> None:
    design = Design.model_validate_json((EXPECTED / "design.json").read_text())
    outline = mermaid_outline(diagrams.architecture(design))
    assert outline is not None
    labels = {c.id: f"{c.id}: {c.name}" for c in design.components}
    for component in design.components:
        assert f"- {labels[component.id]} ({component.kind})" in outline
    for flow in design.flows:
        style = "dotted" if flow.kind == "write" else "solid"
        for step in flow.steps:
            ends = [
                labels.get(i, diagrams.node_id(i)) for i in (step.from_component, step.to_component)
            ]
            edge = f"- {ends[0]} -> {ends[1]} ({style} arrow)"
            assert edge + (f": {step.label}" if step.label else "") in outline.splitlines()
    er = mermaid_outline(diagrams.data_model(design))
    assert er is not None
    names = {e.id: f"{e.id}: {e.name}" for e in design.entities}
    for rel in design.relationships:
        line = f"- {names[rel.from_entity]} {rel.cardinality} {names[rel.to_entity]}: {rel.id}"
        assert line in er.splitlines()


def test_other_mermaid_diagram_types_are_read_as_text() -> None:
    parsed = read_file("pie.mmd", b'pie title Pets\n  "Dogs" : 386\n', vision=False)
    assert parsed.sections[0].text.startswith("pie title Pets")
    assert parsed.warnings == ["this Mermaid diagram type is read as plain text"]
