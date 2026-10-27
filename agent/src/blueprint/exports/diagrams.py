"""The design as Mermaid diagrams, for the downloads (SPECS S11.3, PRD D12).

Pure functions of the design: the architecture flowchart (components and flows), the
data model as an ER diagram (entities and relationships), and one sequence diagram per
flow. ``web/lib/mermaid.ts`` draws the same diagrams in the browser and must give the
same source; both are checked against ``agent/tests/expected/diagrams/``.
"""

import re

from blueprint.domain.models import Component, Design, Entity, Flow

# Opening and closing delimiters of each component kind's node shape.
SHAPES: dict[str, tuple[str, str]] = {
    "client": ('(["', '"])'),
    "gateway": ('{{"', '"}}'),
    "load_balancer": ('[/"', '"\\]'),
    "service": ('["', '"]'),
    "cache": ('("', '")'),
    "queue": ('[["', '"]]'),
    "database": ('[("', '")]'),
    "object_store": ('>"', '"]'),
    "search": ('{"', '"}'),
    "cdn": ('(("', '"))'),
    "external": ('[/"', '"/]'),
}

# Crow's-foot ends of each relationship cardinality.
CARDINALITY: dict[str, str] = {"1:1": "||--||", "1:N": "||--o{", "N:M": "}o--o{"}


def node_id(item_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", item_id)


def text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace('"', "#quot;")).strip()


def _word(value: str) -> str:
    """An ER attribute type or name as Mermaid allows it: letters, digits, '_', '-', '(', ')',
    '[' and ']', starting with a letter."""
    word = re.sub(r"[^A-Za-z0-9_()\[\]-]", "_", value.strip()) or "x"
    return word if word[0].isalpha() else f"x{word}"


ENTITY_CODES = {"#": "#35;", ";": "#59;"}


def _message(value: str) -> str:
    """Sequence-diagram text: one line, with '#' and ';' written as entity codes."""
    one_line = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"[#;]", lambda m: ENTITY_CODES[m.group()], one_line)


def architecture(design: Design) -> str:
    lines = ["flowchart LR", "  %% read flows: solid arrows; write flows: dotted arrows"]
    for component in design.components:
        start, end = SHAPES[component.kind]
        lines.append(
            f"  {node_id(component.id)}{start}{text(f'{component.id}: {component.name}')}{end}"
        )
    for flow in design.flows:
        arrow = "-.->" if flow.kind == "write" else "-->"
        for step in flow.steps:
            label = text(step.label)
            edge = f'{arrow}|"{label}"|' if label else arrow
            lines.append(f"  {node_id(step.from_component)} {edge} {node_id(step.to_component)}")
    return "\n".join(lines) + "\n"


def _entity(entity: Entity) -> list[str]:
    head = f'  {node_id(entity.id)}["{text(f"{entity.id}: {entity.name}")}"]'
    if not entity.fields:
        return [head]
    lines = [head + " {"]
    for field in entity.fields:
        line = f"    {_word(field.type)} {_word(field.name)}"
        if field.key != "none":
            line += f" {field.key.upper()}"
        if field.key == "fk" and field.references:
            line += f' "references {text(field.references)}"'
        lines.append(line)
    return [*lines, "  }"]


def data_model(design: Design) -> str:
    lines = ["erDiagram"]
    for entity in design.entities:
        lines += _entity(entity)
    for relationship in design.relationships:
        ends = CARDINALITY[relationship.cardinality]
        lines.append(
            f"  {node_id(relationship.from_entity)} {ends} {node_id(relationship.to_entity)}"
            f' : "{text(relationship.id)}"'
        )
    return "\n".join(lines) + "\n"


def sequence(flow: Flow, components: list[Component]) -> str:
    names = {c.id: c.name for c in components}
    participants: list[str] = []
    for step in flow.steps:
        for item_id in (step.from_component, step.to_component):
            if item_id not in participants:
                participants.append(item_id)
    lines = ["sequenceDiagram"]
    for item_id in participants:
        label = f"{item_id}: {names[item_id]}" if item_id in names else item_id
        lines.append(f"  participant {node_id(item_id)} as {_message(label)}")
    for index, step in enumerate(flow.steps):
        arrow = "-->>" if flow.kind == "write" else "->>"  # writes dotted, as in the flowchart
        label = _message(step.label) or f"step {index + 1}"
        lines.append(
            f"  {node_id(step.from_component)}{arrow}{node_id(step.to_component)}: {label}"
        )
    return "\n".join(lines) + "\n"


def all_diagrams(design: Design) -> list[tuple[str, str]]:
    """Every diagram the design has something to draw for, as (title, Mermaid source)."""
    diagrams: list[tuple[str, str]] = []
    if design.components:
        diagrams.append(("Architecture", architecture(design)))
    if design.entities:
        diagrams.append(("Data model", data_model(design)))
    for flow in design.flows:
        if flow.steps:
            diagrams.append(
                (
                    f"Sequence: {flow.id} {flow.name} ({flow.kind})",
                    sequence(flow, design.components),
                )
            )
    return diagrams


def markdown(design: Design, heading_level: int = 2) -> list[str]:
    """The diagrams as Markdown sections with fenced ``mermaid`` blocks."""
    hashes = "#" * heading_level
    lines: list[str] = []
    for title, source in all_diagrams(design):
        lines += [f"{hashes} {title}", "", "```mermaid", source.rstrip("\n"), "```", ""]
    return lines
