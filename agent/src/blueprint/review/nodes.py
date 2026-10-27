"""The design review nodes: three lens reviewers in parallel, then the merger (SPECS S6)."""

from typing import Annotated, Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from blueprint.domain.models import Design, Lens
from blueprint.domain.state import DesignState
from blueprint.graph.context import Context, Update, ask, invalid_output
from blueprint.graph.gates import DECIDE_GAPS
from blueprint.llm.gateway import InvalidStructuredOutput, Meter, ModelCallFailed
from blueprint.review.gaps import (
    LENSES,
    Findings,
    GapFinding,
    MergedGaps,
    cited,
    findings_payload,
    gap_register,
    merger_messages,
    review_summary,
    reviewer_messages,
)
from blueprint.review.resolution import decide_gaps_args
from blueprint.utils.models import dump


def _merge_lenses(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class ReviewChannel(DesignState):
    """Graph-internal channel for the parallel reviewers (S6.1): findings, tokens or an error
    per lens, gathered by the gap_merger. It is not part of the session state (S2.2)."""

    review: Annotated[dict[str, Any], _merge_lenses]


async def reviewer(
    ctx: Context, lens: Lens, state: ReviewChannel, config: RunnableConfig
) -> Update:
    """The S6.1 reviewer for one lens, on the review model."""
    meter = Meter.for_node(state, f"review_{lens}")
    spent = meter.used.get("review", 0)
    design = Design.model_validate(state["design"])
    prompt = reviewer_messages(ctx.assets, lens, design)
    try:
        result = await ctx.calls.structured(meter, "review", Findings, prompt, config)
        entry: dict[str, Any] = {"findings": findings_payload(result.findings, lens)}
    except ModelCallFailed as failure:
        entry = {"error": failure.info()}
    except InvalidStructuredOutput as invalid:
        entry = {"error": invalid_output(str(invalid))}
    entry["tokens"] = meter.used.get("review", 0) - spent
    return {"review": {lens: entry}}


async def gap_merger(ctx: Context, state: ReviewChannel, config: RunnableConfig) -> Update:
    """S6.4: merge the three lists on the review model, then hold the result to the rules."""
    review = state.get("review") or {}
    meter = Meter.for_node(state, "gap_merger")
    meter.used["review"] = meter.used.get("review", 0) + sum(
        int((review.get(lens) or {}).get("tokens", 0)) for lens in LENSES
    )
    errors = [review[lens]["error"] for lens in LENSES if (review.get(lens) or {}).get("error")]
    if errors or any(lens not in review for lens in LENSES):
        incomplete = ModelCallFailed(
            "review_incomplete", "The design review did not finish; retry it.", retryable=True
        )
        return {"last_error": errors[0] if errors else incomplete.info(), "tokens_used": meter.used}
    design = Design.model_validate(state["design"])
    findings = [GapFinding.model_validate(f) for lens in LENSES for f in review[lens]["findings"]]
    inputs = cited(findings, design)
    counters = dict(state["id_counters"])
    gaps = []
    if inputs:
        prompt = merger_messages(ctx.assets, design, inputs)
        try:
            merged = await ctx.calls.structured(meter, "review", MergedGaps, prompt, config)
        except ModelCallFailed as failure:
            return {"last_error": failure.info(), "tokens_used": meter.used}
        except InvalidStructuredOutput as invalid:
            return {"last_error": invalid_output(str(invalid)), "tokens_used": meter.used}
        gaps = gap_register(merged.gaps, inputs, design, counters)
    summary = review_summary(gaps)
    message = await ask(config, DECIDE_GAPS, decide_gaps_args(gaps), summary) if gaps else None
    return {
        "gaps": dump(gaps),
        "id_counters": counters,
        "stage": "gap_resolution" if gaps else "prd_draft",
        "tokens_used": meter.used,
        "last_error": None,
        "messages": [message or AIMessage(summary)],
    }
