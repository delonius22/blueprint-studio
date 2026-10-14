"""The LangGraph graph served at /agent (SPECS S4.1, S5.1)."""

from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from blueprint.models import RoleModels
from blueprint.state import DesignState


def route_start(state: DesignState) -> str:
    """Pure routing (S5.1): a run with nothing new from the user ends at once."""
    messages = state.get("messages") or []
    if messages and isinstance(messages[-1], HumanMessage):
        return "interviewer"
    return END


def build_graph(
    models: RoleModels, checkpointer: BaseCheckpointSaver[Any]
) -> CompiledStateGraph[DesignState, None, DesignState, DesignState]:
    async def interviewer(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        reply = await models.interview.ainvoke(state["messages"], config)
        return {"messages": [reply]}

    builder = StateGraph(DesignState)
    builder.add_node("interviewer", interviewer)
    builder.add_conditional_edges(START, route_start, ["interviewer", END])
    builder.add_edge("interviewer", END)
    return builder.compile(checkpointer=checkpointer)
