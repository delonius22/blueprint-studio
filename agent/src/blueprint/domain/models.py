"""Typed shapes for everything a session holds (SPECS S2.3 to S2.14).

Graph state stores these as plain JSON (``model_dump(mode="json")``) so that
checkpoints, AG-UI state snapshots and frontend edits all carry the same data;
nodes validate into these models before using it. Every model forbids unknown
fields (S2.7).
"""

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Stage = Literal[
    "interview",
    "design_review",
    "gap_resolution",
    "prd_draft",
    "prd_signoff",
    "spec_synthesis",
    "seam_gate",
    "change_review",
    "ticket_breakdown",
    "ticket_gate",
    "complete",
]
STAGES: tuple[Stage, ...] = Stage.__args__  # type: ignore[attr-defined]

Role = Literal["interview", "review"]
NonEmpty = Annotated[str, Field(min_length=1)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- S2.7 design items -----------------------------------------------------------------------


class Requirement(Model):
    id: str
    statement: NonEmpty


class Note(Model):
    id: str
    text: NonEmpty


NfrCategory = Literal[
    "latency", "throughput", "availability", "durability", "scale", "security", "cost", "other"
]


class NfrTarget(Model):
    id: str
    category: NfrCategory
    statement: NonEmpty
    metric: str | None = None
    target: float | None = None
    unit: str | None = None


class Estimate(Model):
    id: str
    quantity: NonEmpty
    formula: NonEmpty
    result: float
    unit: NonEmpty


class EntityField(Model):
    name: NonEmpty
    type: NonEmpty
    key: Literal["pk", "fk", "none"]
    references: str | None = None


class Entity(Model):
    id: str
    name: NonEmpty
    fields: list[EntityField]
    indexes: list[str] = []
    est_record_bytes: int | None = None


class Relationship(Model):
    id: str
    from_entity: str
    to_entity: str
    cardinality: Literal["1:1", "1:N", "N:M"]


class Endpoint(Model):
    id: str
    method: NonEmpty
    path: NonEmpty
    request: str
    response: str
    pagination: str | None = None
    errors: list[str] = []
    rate_limit: str | None = None


class StorageChoice(Model):
    id: str
    data: NonEmpty
    technology: NonEmpty
    justification: str
    rejected_alternatives: list[str] = []
    status: Literal["proposed", "decided"]


ComponentKind = Literal[
    "client",
    "gateway",
    "load_balancer",
    "service",
    "cache",
    "queue",
    "database",
    "object_store",
    "search",
    "cdn",
    "external",
]


class Component(Model):
    id: str
    name: NonEmpty
    kind: ComponentKind
    responsibility: str


class FlowStep(Model):
    from_component: str
    to_component: str
    label: str


class Flow(Model):
    id: str
    name: NonEmpty
    kind: Literal["read", "write"]
    steps: list[FlowStep]


class CapStance(Model):
    choice: Literal["CP", "AP", "mixed"]
    rationale: NonEmpty


class CachePolicy(Model):
    id: str
    data: NonEmpty
    strategy: Literal["cache-aside", "read-through", "write-through", "write-back"]
    eviction: Literal["LRU", "LFU", "TTL-only", "other"]
    ttl_seconds: int | None = None


class FailureMode(Model):
    id: str
    scenario: NonEmpty
    behaviour: NonEmpty
    recovery: str | None = None


class Spof(Model):
    id: str
    component_id: str
    risk: NonEmpty
    mitigation: str | None = None


class Signal(Model):
    id: str
    kind: Literal["log", "metric", "trace", "alert", "health-check"]
    name: NonEmpty
    threshold: str | None = None


class Tradeoff(Model):
    id: str
    decision: NonEmpty
    gained: NonEmpty
    sacrificed: NonEmpty


# --- S2.4 the design record ------------------------------------------------------------------


class Design(Model):
    functional_requirements: list[Requirement] = []
    non_functional_requirements: list[NfrTarget] = []
    out_of_scope: list[Note] = []
    capacity_estimates: list[Estimate] = []
    entities: list[Entity] = []
    relationships: list[Relationship] = []
    endpoints: list[Endpoint] = []
    storage_choices: list[StorageChoice] = []
    components: list[Component] = []
    flows: list[Flow] = []
    cap_stance: CapStance | None = None
    cache_policies: list[CachePolicy] = []
    spofs: list[Spof] = []
    failure_modes: list[FailureMode] = []
    observability: list[Signal] = []
    tradeoffs: list[Tradeoff] = []
    extensions: list[Note] = []


# S2.6: the ID prefix of every Design list.
DESIGN_PREFIXES: dict[str, str] = {
    "functional_requirements": "FR",
    "non_functional_requirements": "NFR",
    "out_of_scope": "OOS",
    "capacity_estimates": "EST",
    "entities": "ENT",
    "relationships": "REL",
    "endpoints": "EP",
    "storage_choices": "STO",
    "components": "CMP",
    "flows": "FLW",
    "cache_policies": "CACHE",
    "failure_modes": "FM",
    "spofs": "SPOF",
    "observability": "OBS",
    "tradeoffs": "TRD",
    "extensions": "EXT",
}


# --- S2.8 critique and scorecard -------------------------------------------------------------


class Critique(Model):
    step: Annotated[int, Field(ge=1, le=5)]
    strengths: list[str]
    bottlenecks: list[str]
    questions: list[str]


Dimension = Literal["communication", "structure", "judgment", "depth", "time"]
DIMENSIONS: tuple[Dimension, ...] = Dimension.__args__  # type: ignore[attr-defined]


class DimensionScore(Model):
    dimension: Dimension
    score: Annotated[int, Field(ge=1, le=4)]
    evidence: list[str]
    advice: str


class Scorecard(Model):
    """Exactly five scores, one per dimension, in the order of DIMENSIONS (S2.8)."""

    dimensions: Annotated[list[DimensionScore], Field(min_length=5, max_length=5)]

    @model_validator(mode="after")
    def one_per_dimension(self) -> Self:
        if tuple(d.dimension for d in self.dimensions) != DIMENSIONS:
            raise ValueError(f"needs one score per dimension, in order: {', '.join(DIMENSIONS)}")
        return self


# --- S2.9 gaps -------------------------------------------------------------------------------

Lens = Literal["security", "efficiency", "maintainability"]
Severity = Literal["high", "medium", "low"]


class Gap(Model):
    id: str
    lens: Lens
    item_ids: Annotated[list[str], Field(min_length=1)]
    risk: NonEmpty
    decision_needed: NonEmpty
    severity: Severity
    status: Literal["open", "resolved", "accepted"] = "open"
    note: str | None = None
    resolved_by: list[str] = []
    feature_ids: list[str] = []


# --- S2.10 to S2.14 the PRD, stories, versions, changes, seams and tickets --------------------


class Feature(Model):
    id: str
    name: NonEmpty
    description: str
    requirement_ids: Annotated[list[str], Field(min_length=1)]


class PrdRequirement(Model):
    id: str
    feature_id: str
    statement: NonEmpty


class PrdNfr(Model):
    id: str
    category: NfrCategory
    statement: NonEmpty
    metric: str | None = None
    target: float | None = None
    unit: str | None = None


class UserStory(Model):
    id: str
    feature_id: str
    actor: NonEmpty
    feature: NonEmpty
    benefit: NonEmpty
    acceptance_criteria: list[str]
    requirement_ids: Annotated[list[str], Field(min_length=1)]


class PrdDoc(Model):
    problem_statement: str
    goals: list[str]
    users: list[str]
    features: list[Feature]
    functional_requirements: list[PrdRequirement]
    non_functional_requirements: list[PrdNfr]
    scope: list[str]
    out_of_scope: list[str]
    open_gaps: list[Gap]
    solution: str = ""
    user_stories: list[UserStory] = []
    implementation_decisions: list[str] = []
    testing_decisions: list[str] = []
    further_notes: list[str] = []


SIGNED_OFF_SECTIONS: tuple[str, ...] = (
    "problem_statement",
    "goals",
    "users",
    "features",
    "functional_requirements",
    "non_functional_requirements",
    "scope",
    "out_of_scope",
    "open_gaps",
)


class PrdVersion(Model):
    version: Literal["1.0", "1.1", "1.2"]
    approved_at: str
    doc: PrdDoc


class ProposedChange(Model):
    id: str
    section: str
    target_id: str | None = None
    kind: Literal["add", "modify", "remove"]
    current_text: str | None = None
    proposed_text: str | None = None
    reason: NonEmpty
    decision: Literal["pending", "approved", "rejected"] = "pending"


class Seam(Model):
    id: str
    name: NonEmpty
    description: str
    covers: list[str]


class Ticket(Model):
    id: str
    title: NonEmpty
    what_to_build: NonEmpty
    blocked_by: list[str] = []
    acceptance_criteria: Annotated[list[str], Field(min_length=1)]
    story_ids: Annotated[list[str], Field(min_length=1)]
    kind: Literal["slice", "prefactor", "expand", "migrate", "contract"] = "slice"


class ErrorInfo(Model):
    code: NonEmpty
    message: NonEmpty
    retryable: bool


# --- document import (SPEC-document-import §3) -----------------------------------------------

Step = Annotated[int, Field(ge=1, le=5)]
WeaknessCode = Literal[
    "missing_target",
    "missing_unit",
    "unjustified_choice",
    "vague",
    "contradicts",
    "no_failure_mode",
    "ambiguous_kind",
]


class SourceRef(Model):
    """Where an imported item came from: the attachment, a page or heading, and the quote."""

    attachment_id: str
    locator: str
    quote: str  # verbatim from the file's text; empty for an image


class Weakness(Model):
    code: WeaknessCode
    detail: NonEmpty


class AttachmentRef(Model):
    """An attached file as the session knows it; the bytes stay in the attachments table."""

    id: str
    name: str
    kind: str
    status: Literal["parsed", "imported", "failed", "removed"] = "parsed"
    summary: str | None = None
    warnings: list[str] = []


class ImportCandidate(Model):
    """One design item a file states, waiting for the user's decision in review_import."""

    id: str
    attachment_id: str
    step: Step
    tool: str
    args: dict[str, Any]
    updates: str | None = None
    source: SourceRef
    weaknesses: list[Weakness] = []
    status: Literal["staged", "offered"]


class ImportNote(Model):
    """A weakness of a recorded item, or a question about the file, for the interviewer."""

    attachment_id: str
    step: Step
    item_id: str | None = None
    code: WeaknessCode | Literal["question"]
    detail: NonEmpty
    quote: str
    status: Literal["open", "asked"] = "open"


class SourceExcerpt(Model):
    """PRD-level text from a file (problem, goals, users), for the PRD drafter."""

    topic: Literal["problem", "goals", "users"]
    source: SourceRef
