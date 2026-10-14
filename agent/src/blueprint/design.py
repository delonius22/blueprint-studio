"""The design record's rules and the interviewer's backend tools (SPECS S2.5, S2.15, S5.3-S5.5).

The interviewer records design data only through these tools. Each ``upsert_*``
tool creates an item (issuing a new ID) when called without ``id`` and replaces
the item with that ID otherwise. IDs come from ``id_counters`` and are never
reused, even after deletion (S2.5).
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, create_model

from blueprint.domain import (
    DESIGN_PREFIXES,
    Design,
    Endpoint,
    Entity,
    Estimate,
    Model,
    NfrTarget,
    Note,
    Relationship,
    Requirement,
    StorageChoice,
)

ID_PATTERN = re.compile(r"^([A-Z]+)-(\d+)$")


class ToolFailure(Exception):
    """A tool call was rejected; the message goes back to the model as the tool result."""


# --- S2.5 IDs ----------------------------------------------------------------------------


def issue_id(counters: dict[str, int], prefix: str) -> str:
    """Increment the prefix's counter in place and return the new ID."""
    counters[prefix] = counters.get(prefix, 0) + 1
    width = 2 if prefix == "T" else 1
    return f"{prefix}-{counters[prefix]:0{width}d}"


def all_item_ids(design: Design) -> set[str]:
    return {item.id for field in DESIGN_PREFIXES for item in getattr(design, field)}


# --- S2.15 validation ----------------------------------------------------------------------


def violations(design: Design, counters: dict[str, int]) -> list[str]:
    """Every rule of S2.15 the design breaks: ID prefixes, issued counters, uniqueness, references."""
    problems: list[str] = []
    seen: set[str] = set()
    for field, prefix in DESIGN_PREFIXES.items():
        for item in getattr(design, field):
            match = ID_PATTERN.match(item.id)
            if not match or match.group(1) != prefix:
                problems.append(f"{item.id} is not a valid {prefix}- ID for {field}")
            elif int(match.group(2)) > counters.get(prefix, 0):
                problems.append(f"{item.id} was never issued")
            if item.id in seen:
                problems.append(f"{item.id} is used more than once")
            seen.add(item.id)

    entities = {e.id for e in design.entities}
    components = {c.id for c in design.components}
    for entity in design.entities:
        for field_ in entity.fields:
            if field_.key == "fk" and field_.references not in entities:
                problems.append(
                    f"{entity.id}.{field_.name} references {field_.references or 'nothing'}, "
                    "which is not an entity"
                )
    for rel in design.relationships:
        for end in (rel.from_entity, rel.to_entity):
            if end not in entities:
                problems.append(f"{rel.id} refers to {end}, which is not an entity")
    for flow in design.flows:
        for step in flow.steps:
            for end in (step.from_component, step.to_component):
                if end not in components:
                    problems.append(f"{flow.id} refers to {end}, which is not a component")
    for spof in design.spofs:
        if spof.component_id not in components:
            problems.append(f"{spof.id} refers to {spof.component_id}, which is not a component")
    return problems


# --- S5.3 backend tools ----------------------------------------------------------------------


@dataclass(frozen=True)
class ListTool:
    """An ``upsert_*`` tool for one Design list."""

    name: str
    field: str
    item: type[Model]
    description: str
    args: type[BaseModel]
    fixed: dict[str, Any]
    note: str


def _list_tool(
    name: str,
    field: str,
    item: type[Model],
    description: str,
    fixed: dict[str, Any] | None = None,
    note: str = "",
) -> ListTool:
    """``fixed`` fields are set by the app on every write and are not tool arguments."""
    fixed = fixed or {}
    fields: dict[str, Any] = {
        key: (info.annotation, info)
        for key, info in item.model_fields.items()
        if key != "id" and key not in fixed
    }
    args = create_model(
        f"{name}_args",
        __base__=Model,
        id=(str | None, None),
        **fields,
    )
    return ListTool(name, field, item, description, args, fixed, note)


_UPSERT = " Omit id to add a new item (the app issues its ID); pass an existing id to replace it."

LIST_TOOLS: dict[str, ListTool] = {
    tool.name: tool
    for tool in (
        _list_tool(
            "upsert_requirement",
            "functional_requirements",
            Requirement,
            "Record a functional requirement: one use case the system must support, "
            "as the user stated it." + _UPSERT,
        ),
        _list_tool(
            "upsert_nfr",
            "non_functional_requirements",
            NfrTarget,
            "Record a non-functional requirement target (latency, throughput, availability, "
            "durability, scale, security, cost or other), with metric, numeric target and "
            "unit when the user gave them." + _UPSERT,
        ),
        _list_tool(
            "upsert_out_of_scope",
            "out_of_scope",
            Note,
            "Record something the user explicitly placed out of scope." + _UPSERT,
        ),
        _list_tool(
            "upsert_estimate",
            "capacity_estimates",
            Estimate,
            "Record a capacity estimate with the formula that produced it and its result, "
            "so anyone can check the arithmetic." + _UPSERT,
        ),
        _list_tool(
            "upsert_entity",
            "entities",
            Entity,
            "Record a data entity with its fields (key pk, fk or none; an fk field names the "
            "entity ID it references), its indexes and, when known, the estimated record size "
            "in bytes." + _UPSERT,
        ),
        _list_tool(
            "upsert_relationship",
            "relationships",
            Relationship,
            "Record a relationship between two recorded entities (by entity ID) with its "
            "cardinality." + _UPSERT,
        ),
        _list_tool(
            "upsert_endpoint",
            "endpoints",
            Endpoint,
            "Record an API endpoint: method, path, request and response shapes, pagination, "
            "error cases and rate limit." + _UPSERT,
        ),
        _list_tool(
            "upsert_storage_choice",
            "storage_choices",
            StorageChoice,
            "Record a storage technology the user has named for some data, with any "
            "justification given so far and the alternatives they rejected. Every storage "
            "choice is recorded as proposed; only decide_storage_choice makes it decided."
            + _UPSERT,
            fixed={"status": "proposed"},
            note=(
                "This storage choice is proposed, not decided. Ask the user to justify it with "
                "workload facts (read/write ratio, consistency need, latency or throughput), "
                "then call decide_storage_choice."
            ),
        ),
    )
}


class DecideStorageChoiceArgs(Model):
    id: str = Field(description="The STO- ID of the proposed storage choice.")
    basis: list[Literal["read_write_ratio", "consistency", "latency", "throughput"]] = Field(
        min_length=1, description="The workload facts the user's justification rests on."
    )
    justification: str = Field(
        min_length=1, description="The user's justification, in their words."
    )


DECIDE_STORAGE_CHOICE = "decide_storage_choice"


class DeleteItemArgs(Model):
    item_id: str


DELETE_ITEM = "delete_item"

# S5.4: architecture tools are not bound while Step 1 is open.
STEP_1_EXCLUDED = {"upsert_component", "upsert_flow", "upsert_storage_choice", "upsert_endpoint"}


def bound_tool_names(current_step: int) -> list[str]:
    names = [*LIST_TOOLS, DECIDE_STORAGE_CHOICE, DELETE_ITEM]
    if current_step == 1:
        names = [n for n in names if n not in STEP_1_EXCLUDED]
    return names


def tool_schemas(names: list[str]) -> list[dict[str, Any]]:
    """OpenAI-format function definitions for the named backend tools."""
    schemas = []
    for name in names:
        if name == DELETE_ITEM:
            description = "Delete a design item by its ID. Its ID is never reused."
            parameters = DeleteItemArgs.model_json_schema()
        elif name == DECIDE_STORAGE_CHOICE:
            description = (
                "Mark a proposed storage choice as decided, once the user has justified it with "
                "workload facts. basis must name at least one of read_write_ratio, consistency, "
                "latency, throughput."
            )
            parameters = DecideStorageChoiceArgs.model_json_schema()
        else:
            tool = LIST_TOOLS[name]
            description, parameters = tool.description, tool.args.model_json_schema()
        schemas.append(
            {
                "type": "function",
                "function": {"name": name, "description": description, "parameters": parameters},
            }
        )
    return schemas


@dataclass
class Draft:
    """The design and ID counters being changed by one batch of tool calls."""

    design: Design
    counters: dict[str, int]


def _upsert(tool: ListTool, draft: Draft, args: dict[str, Any]) -> str:
    try:
        parsed = tool.args.model_validate(args)
    except ValidationError as exc:
        raise ToolFailure(f"invalid arguments: {_errors(exc)}") from None
    values = parsed.model_dump(exclude={"id"}) | tool.fixed
    items: list[Model] = list(getattr(draft.design, tool.field))
    prefix = DESIGN_PREFIXES[tool.field]
    if parsed.id is None:  # type: ignore[attr-defined]
        item_id = issue_id(draft.counters, prefix)
        items.append(tool.item.model_validate({"id": item_id, **values}))
    else:
        item_id = parsed.id  # type: ignore[attr-defined]
        index = next((i for i, item in enumerate(items) if item.id == item_id), None)  # type: ignore[attr-defined]
        if index is None:
            raise ToolFailure(f"{item_id} does not exist in {tool.field}; omit id to add an item")
        items[index] = tool.item.model_validate({"id": item_id, **values})
    candidate = draft.design.model_copy(update={tool.field: items})
    problems = violations(candidate, draft.counters)
    if problems:
        raise ToolFailure("; ".join(problems))
    draft.design = candidate
    return item_id


def _decide_storage_choice(draft: Draft, args: dict[str, Any]) -> str:
    """S5.5: a storage choice becomes decided only with a basis in workload facts."""
    try:
        parsed = DecideStorageChoiceArgs.model_validate(args)
    except ValidationError as exc:
        raise ToolFailure(
            f"invalid arguments: {_errors(exc)}. Ask the user to justify the choice with "
            "read/write ratio, consistency, latency or throughput."
        ) from None
    choices = list(draft.design.storage_choices)
    index = next((i for i, c in enumerate(choices) if c.id == parsed.id), None)
    if index is None:
        raise ToolFailure(f"{parsed.id} is not a recorded storage choice")
    choices[index] = choices[index].model_copy(
        update={"status": "decided", "justification": parsed.justification}
    )
    draft.design = draft.design.model_copy(update={"storage_choices": choices})
    return parsed.id


def _delete(draft: Draft, args: dict[str, Any]) -> str:
    try:
        item_id = DeleteItemArgs.model_validate(args).item_id
    except ValidationError as exc:
        raise ToolFailure(f"invalid arguments: {_errors(exc)}") from None
    for field in DESIGN_PREFIXES:
        items = getattr(draft.design, field)
        if any(item.id == item_id for item in items):
            remaining = [item for item in items if item.id != item_id]
            candidate = draft.design.model_copy(update={field: remaining})
            problems = violations(candidate, draft.counters)
            if problems:
                raise ToolFailure(f"cannot delete {item_id}: " + "; ".join(problems))
            draft.design = candidate
            return item_id
    raise ToolFailure(f"{item_id} does not exist")


def _errors(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())


def run_tool(name: str, args: dict[str, Any], draft: Draft, allowed: list[str]) -> str:
    """Apply one backend tool call to the draft and return the JSON tool result."""
    if name not in allowed:
        raise ToolFailure(f"{name} is not available now")
    if name == DELETE_ITEM:
        return json.dumps({"deleted": _delete(draft, args)})
    if name == DECIDE_STORAGE_CHOICE:
        return json.dumps({"decided": _decide_storage_choice(draft, args)})
    tool = LIST_TOOLS[name]
    item_id = _upsert(tool, draft, args)
    result: dict[str, str] = {"recorded": item_id}
    if tool.note:
        result["note"] = tool.note
    return json.dumps(result)
