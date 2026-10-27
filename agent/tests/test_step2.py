"""T-05: Step 2 — entities, relationships, endpoints and storage choices (S2.7, S5.3, S5.5)."""

import json
from collections.abc import Sequence

from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage, ToolMessage
from seam import GraphSeam, at_step

from blueprint.domain.models import Endpoint, Entity, EntityField, Relationship, StorageChoice


def calls(*entries: tuple[str, dict[str, object]]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(entries)],
    )


def results(messages: Sequence[object]) -> list[dict[str, object]]:
    return [json.loads(m.text) for m in messages if isinstance(m, ToolMessage)]


def step2(*script: object) -> GraphSeam:
    return GraphSeam(ScriptedChatModel.with_script(*script), initial=at_step(2))  # type: ignore[arg-type]


async def test_entities_relationships_and_endpoints_are_recorded_with_ids() -> None:
    seam = step2(
        calls(
            ("upsert_entity", {"name": "User", "fields": [{"name": "id", "type": "uuid", "key": "pk"}],
                               "indexes": [], "est_record_bytes": 200}),
            ("upsert_entity", {"name": "Url", "fields": [
                {"name": "code", "type": "varchar(8)", "key": "pk"},
                {"name": "owner_id", "type": "uuid", "key": "fk", "references": "ENT-1"},
                {"name": "target", "type": "text", "key": "none"}],
                "indexes": ["owner_id"], "est_record_bytes": 500}),
            ("upsert_relationship", {"from_entity": "ENT-1", "to_entity": "ENT-2", "cardinality": "1:N"}),
            ("upsert_endpoint", {"method": "POST", "path": "/urls", "request": "{target}",
                                 "response": "{code}", "errors": ["400 invalid URL"], "rate_limit": "10/min"}),
        ),
        AIMessage("Which storage fits these entities?"),
    )  # fmt: skip
    await seam.send("Users own URLs; POST /urls creates a code")

    design = await seam.design()
    assert [e.id for e in design.entities] == ["ENT-1", "ENT-2"]
    assert design.entities[1] == Entity(
        id="ENT-2",
        name="Url",
        fields=[
            EntityField(name="code", type="varchar(8)", key="pk"),
            EntityField(name="owner_id", type="uuid", key="fk", references="ENT-1"),
            EntityField(name="target", type="text", key="none"),
        ],
        indexes=["owner_id"],
        est_record_bytes=500,
    )
    assert design.relationships == [
        Relationship(id="REL-1", from_entity="ENT-1", to_entity="ENT-2", cardinality="1:N")
    ]
    assert design.endpoints == [
        Endpoint(id="EP-1", method="POST", path="/urls", request="{target}", response="{code}",
                 errors=["400 invalid URL"], rate_limit="10/min")
    ]  # fmt: skip


async def test_references_to_missing_entities_are_rejected() -> None:
    seam = step2(
        calls(
            ("upsert_relationship", {"from_entity": "ENT-1", "to_entity": "ENT-2", "cardinality": "1:N"}),
            ("upsert_entity", {"name": "Url", "fields": [
                {"name": "owner_id", "type": "uuid", "key": "fk", "references": "ENT-7"}]}),
        ),
        AIMessage("Let me record the entities first."),
    )  # fmt: skip
    await seam.send("relationships first")

    outcomes = results(seam.interview.calls[1].messages)
    assert "REL-1 refers to ENT-1, which is not an entity" in str(outcomes[0]["error"])
    assert "references ENT-7, which is not an entity" in str(outcomes[1]["error"])
    assert (await seam.design()).relationships == []
    assert (await seam.design()).entities == []


async def test_naming_a_technology_alone_leaves_it_proposed_until_justified() -> None:
    seam = step2(
        calls(("upsert_storage_choice", {"data": "URL mappings", "technology": "Cassandra",
                                         "justification": "", "rejected_alternatives": ["PostgreSQL"]})),
        AIMessage("Why Cassandra: what read/write ratio, consistency or throughput does it serve?"),
        calls(("decide_storage_choice", {"id": "STO-1", "basis": ["read_write_ratio", "throughput"],
                                         "justification": "100:1 reads, 50k redirects/s, key lookups only"})),
        AIMessage("Decided. Next, the API contracts."),
    )  # fmt: skip

    await seam.send("I'll use Cassandra for the URL mappings, not Postgres.")

    proposed = (await seam.design()).storage_choices
    assert proposed == [
        StorageChoice(id="STO-1", data="URL mappings", technology="Cassandra", justification="",
                      rejected_alternatives=["PostgreSQL"], status="proposed")
    ]  # fmt: skip
    # the tool result tells the interviewer to ask for a justification, and it does
    outcome = results(seam.interview.calls[1].messages)[0]
    assert outcome["recorded"] == "STO-1" and "decide_storage_choice" in str(outcome["note"])
    assert (await seam.messages())[-1].text.startswith("Why Cassandra")

    await seam.send("Reads outnumber writes 100 to 1 and we need 50k redirects per second.")

    decided = (await seam.design()).storage_choices[0]
    assert decided.status == "decided"
    assert decided.justification == "100:1 reads, 50k redirects/s, key lookups only"
    assert decided.rejected_alternatives == ["PostgreSQL"]


async def test_decision_needs_a_valid_basis_and_upsert_cannot_decide() -> None:
    seam = step2(
        calls(
            ("upsert_storage_choice", {"data": "URLs", "technology": "Redis", "justification": "fast",
                                       "status": "decided"}),
            ("upsert_storage_choice", {"data": "URLs", "technology": "Redis", "justification": "fast"}),
            ("decide_storage_choice", {"id": "STO-1", "basis": [], "justification": "it is popular"}),
            ("decide_storage_choice", {"id": "STO-1", "basis": ["popularity"], "justification": "popular"}),
        ),
        AIMessage("What workload facts support Redis?"),
    )  # fmt: skip
    await seam.send("Redis because it's fast")

    outcomes = results(seam.interview.calls[1].messages)
    assert "error" in outcomes[0]  # status is not an argument: only decide_storage_choice decides
    assert outcomes[1]["recorded"] == "STO-1"
    assert "error" in outcomes[2] and "error" in outcomes[3]
    assert (await seam.design()).storage_choices[0].status == "proposed"
