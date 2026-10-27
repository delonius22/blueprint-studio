"""The document import nodes: read new files, then record what the user accepted
(SPEC-document-import §2.4, §2.5)."""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from blueprint.domain.models import (
    AttachmentRef,
    Design,
    ImportCandidate,
    ImportNote,
    SourceExcerpt,
)
from blueprint.domain.state import DesignState
from blueprint.graph.context import Context, Update, ask
from blueprint.graph.gates import REVIEW_IMPORT, last_answer
from blueprint.imports.proposal import (
    ImportProposal,
    applied_summary,
    apply_decisions,
    import_decisions,
    importer_messages,
    offer,
    read_proposal,
    review_import_args,
)
from blueprint.interview.nodes import draft_of
from blueprint.interview.prompts import design_summary
from blueprint.interview.tools import bound_tool_names
from blueprint.llm.gateway import InvalidStructuredOutput, Meter, ModelCallFailed
from blueprint.utils.models import dump, load
from blueprint.utils.text import plural

UNREADABLE = "the model's reading of this file could not be used"


async def importer(ctx: Context, state: DesignState, config: RunnableConfig) -> Update:
    """Read each new attachment into candidates, then offer the ones for this step (or a
    confirmed one) in a review_import card."""
    step = state["current_step"]
    design = Design.model_validate(state["design"])
    refs = load(AttachmentRef, state, "attachments")
    queue = load(ImportCandidate, state, "import_queue")
    notes = load(ImportNote, state, "import_notes")
    excerpts = load(SourceExcerpt, state, "prd_context")
    counters = dict(state["id_counters"])
    meter = Meter.for_node(state, "importer")
    read: list[str] = []
    for index, ref in enumerate(refs):
        if ref.status != "parsed":
            continue
        stored = await ctx.files.attachment(state["session_id"], ref.id) if ctx.files else None
        if stored is None:  # removed since the run started
            refs[index] = ref.model_copy(update={"status": "removed"})
            continue
        prompt = importer_messages(
            ctx.assets.document_importer, stored, design_summary(design), step
        )
        try:
            proposal: Any = await ctx.calls.structured(
                meter, "interview", ImportProposal, prompt, config
            )
        except ModelCallFailed as failure:
            return {"last_error": failure.info()}  # S13.2: nothing else changes
        except InvalidStructuredOutput:
            refs[index] = ref.model_copy(
                update={"status": "failed", "warnings": [*ref.warnings, UNREADABLE]}
            )
            read.append(f"{ref.name} could not be read")
            continue
        found, questions, context = read_proposal(proposal, stored, design, counters)
        queue, notes, excerpts = [*queue, *found], [*notes, *questions], [*excerpts, *context]
        refs[index] = ref.model_copy(update={"status": "imported", "summary": proposal.summary})
        read.append(f"{ref.name} ({plural(len(found), 'item')})")
    queue = offer(queue, step)
    update: Update = {
        "attachments": dump(refs),
        "import_queue": dump(queue),
        "import_notes": dump(notes),
        "prd_context": dump(excerpts),
        "id_counters": counters,
        "tokens_used": meter.used,
        "last_error": None,
    }
    text = ("I read " + "; ".join(read) + ".") if read else "That file is no longer attached."
    if any(c.status == "offered" for c in queue):
        args = review_import_args(queue, refs, design)
        return update | {
            "messages": [
                await ask(config, REVIEW_IMPORT, args, text + " Review what I found below.")
            ]
        }
    return update | {"messages": [AIMessage(text)]}


async def import_applier(ctx: Context, state: DesignState) -> Update:
    """Record what the user accepted in review_import; the interviewer then asks about what the
    files left weak."""
    answer = last_answer(list(state["messages"]))
    queue = load(ImportCandidate, state, "import_queue")
    draft = draft_of(state)
    allowed = bound_tool_names(state["current_step"], state["stage"])
    applied = apply_decisions(queue, import_decisions(answer[1] if answer else {}), draft, allowed)
    waiting = [c for c in queue if c.status != "offered"]
    provenance = dict(state.get("provenance") or {})
    provenance |= {item_id: ref.model_dump() for item_id, ref in applied.provenance.items()}
    return {
        "design": draft.design.model_dump(mode="json"),
        "id_counters": draft.counters,
        "import_queue": dump(waiting),
        "import_notes": dump([*load(ImportNote, state, "import_notes"), *applied.notes]),
        "provenance": provenance,
        "last_error": None,
        "messages": [AIMessage(applied_summary(applied, waiting))],
    }
