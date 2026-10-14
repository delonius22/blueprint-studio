"""The LangGraph graph served at /agent (SPECS S4.1, S5.1)."""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from blueprint.models import RoleModels
from blueprint.state import DesignState


def build_graph(
    models: RoleModels, checkpointer: BaseCheckpointSaver[Any]
) -> CompiledStateGraph[DesignState, None, DesignState, DesignState]:
    async def interviewer(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        reply = await models.interview.ainvoke(state["messages"], config)
        return {"messages": [reply]}

    builder = StateGraph(DesignState)
    builder.add_node("interviewer", interviewer)
    builder.add_edge(START, "interviewer")
    builder.add_edge("interviewer", END)
    return builder.compile(checkpointer=checkpointer)
