"""The graph seam: the real compiled graph driven with two scripted fake models, one per role."""

from typing import Any

from fakes import ScriptedChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from blueprint.graph import build_graph
from blueprint.models import RoleModels


class GraphSeam:
    def __init__(self, interview: ScriptedChatModel, review: ScriptedChatModel) -> None:
        self.interview = interview
        self.review = review
        self.graph = build_graph(RoleModels(interview=interview, review=review), InMemorySaver())

    def config(self, thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}}

    async def send(self, text: str, thread_id: str = "session-1") -> dict[str, Any]:
        update: Any = {"messages": [HumanMessage(text)]}
        result = await self.graph.ainvoke(update, self.config(thread_id))
        return dict(result)

    async def messages(self, thread_id: str = "session-1") -> list[BaseMessage]:
        snapshot = await self.graph.aget_state(self.config(thread_id))
        return list(snapshot.values["messages"])
