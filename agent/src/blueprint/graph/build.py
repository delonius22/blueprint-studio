"""The LangGraph graph served at /agent (SPECS S4.1, S5.1): nodes and the edges between them.

The nodes live with their stage (``interview``, ``imports``, ``review``, ``planning``); the
routing is in ``graph.routing``. This module only wires them together.
"""

from functools import partial
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from blueprint.config.assets import Assets
from blueprint.domain.state import DesignState
from blueprint.graph import routing
from blueprint.graph.context import Context
from blueprint.imports.nodes import import_applier, importer
from blueprint.interview.nodes import critic, design_tools, interviewer
from blueprint.llm.clients import RoleModels
from blueprint.llm.gateway import ModelGateway
from blueprint.planning import nodes as planning
from blueprint.review.gaps import LENSES
from blueprint.review.nodes import ReviewChannel, gap_merger, reviewer
from blueprint.storage.sessions import AttachmentSource

Graph = CompiledStateGraph[DesignState, None, DesignState, DesignState]


def build_graph(
    models: RoleModels,
    checkpointer: BaseCheckpointSaver[Any],
    assets: Assets,
    gateway: ModelGateway | None = None,
    files: AttachmentSource | None = None,
) -> Graph:
    ctx = Context(gateway or ModelGateway(models), assets, files)
    builder = StateGraph(DesignState)
    builder.add_node("interviewer", partial(interviewer, ctx))
    builder.add_node("design_tools", partial(design_tools, ctx))
    builder.add_node("importer", partial(importer, ctx))
    builder.add_node("import_applier", partial(import_applier, ctx))
    builder.add_node("critic", partial(critic, ctx))
    for lens, name in zip(LENSES, routing.REVIEWERS, strict=True):
        builder.add_node(name, partial(reviewer, ctx, lens), input_schema=ReviewChannel)
    builder.add_node("gap_merger", partial(gap_merger, ctx), input_schema=ReviewChannel)
    builder.add_node("prd_drafter", partial(planning.prd_drafter, ctx))
    builder.add_node("spec_synthesizer", partial(planning.spec_synthesizer, ctx))
    builder.add_node("seam_proposer", partial(planning.seam_proposer, ctx))
    builder.add_node("change_applier", partial(planning.change_applier, ctx))
    builder.add_node(
        "ticket_planner",
        partial(planning.ticket_planner, ctx),
        input_schema=planning.PlanningChannel,
    )
    builder.add_node(
        "dag_validator", partial(planning.dag_validator, ctx), input_schema=planning.PlanningChannel
    )
    builder.add_node("completer", partial(planning.completer, ctx))

    builder.add_conditional_edges(
        START,
        routing.route_start,
        [
            "interviewer",
            "importer",
            "import_applier",
            "critic",
            *routing.REVIEWERS,
            *routing.AUTOMATIC_STAGES.values(),
            END,
        ],
    )
    builder.add_conditional_edges(
        "interviewer", routing.route_interviewer, ["design_tools", "prd_drafter", END]
    )
    builder.add_conditional_edges("design_tools", routing.route_design_tools, ["interviewer", END])
    builder.add_conditional_edges("importer", routing.route_importer, ["interviewer", END])
    builder.add_edge("import_applier", "interviewer")
    builder.add_conditional_edges("critic", routing.route_critic, [*routing.REVIEWERS, END])
    builder.add_edge(routing.REVIEWERS, "gap_merger")
    builder.add_conditional_edges("gap_merger", routing.route_gap_merger, ["prd_drafter", END])
    builder.add_conditional_edges(
        "prd_drafter", routing.route_prd_drafter, ["spec_synthesizer", END]
    )
    builder.add_conditional_edges(
        "spec_synthesizer", routing.route_spec_synthesizer, ["seam_proposer", END]
    )
    builder.add_conditional_edges(
        "seam_proposer", routing.route_seam_proposer, ["change_applier", "ticket_planner", END]
    )
    builder.add_conditional_edges(
        "change_applier", routing.route_change_applier, ["ticket_planner", END]
    )
    builder.add_conditional_edges(
        "ticket_planner", routing.route_ticket_planner, ["dag_validator", END]
    )
    builder.add_conditional_edges(
        "dag_validator", routing.route_dag_validator, ["ticket_planner", "completer", END]
    )
    builder.add_edge("completer", END)
    return builder.compile(checkpointer=checkpointer)
