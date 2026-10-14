"""The graph seam: the real compiled graph driven with two scripted fake models, one per role."""

from typing import Any

from fakes import ScriptedChatModel
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from blueprint.assets import load_assets
from blueprint.domain import Design
from blueprint.graph import build_graph
from blueprint.models import RoleModels
from blueprint.state import new_session_state


class GraphSeam:
    def __init__(
        self,
        interview: ScriptedChatModel,
        review: ScriptedChatModel | None = None,
        *,
        frontend_tools: list[dict[str, Any]] | None = None,
        review_model_distinct: bool = True,
        token_budget: int = 2_000_000,
        initial: dict[str, Any] | None = None,
    ) -> None:
        self.interview = interview
        self.review = review or ScriptedChatModel.with_script(name="review")
        self.assets = load_assets()
        self.graph = build_graph(
            RoleModels(interview=self.interview, review=self.review), InMemorySaver(), self.assets
        )
        self.frontend_tools = frontend_tools or []
        self.review_model_distinct = review_model_distinct
        self.token_budget = token_budget
        self.initial = initial or {}
        self._started: set[str] = set()

    def config(self, thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}}

    async def _ensure_session(self, thread_id: str) -> None:
        if thread_id not in self._started:
            initial = new_session_state(thread_id, self.token_budget, self.review_model_distinct)
            initial |= self.initial
            await self.graph.aupdate_state(self.config(thread_id), initial, as_node="__start__")
            self._started.add(thread_id)

    async def _run(self, message: BaseMessage, thread_id: str) -> dict[str, Any]:
        await self._ensure_session(thread_id)
        update: Any = {
            "messages": [message],
            "copilotkit": {"actions": self.frontend_tools, "context": []},
        }
        return dict(await self.graph.ainvoke(update, self.config(thread_id)))

    async def send(self, text: str, thread_id: str = "session-1") -> dict[str, Any]:
        """A user chat message."""
        return await self._run(HumanMessage(text), thread_id)

    async def answer(
        self, call_id: str, content: str, thread_id: str = "session-1"
    ) -> dict[str, Any]:
        """The user's answer to a frontend gate tool call."""
        return await self._run(ToolMessage(content, tool_call_id=call_id), thread_id)

    async def state(self, thread_id: str = "session-1") -> dict[str, Any]:
        return dict((await self.graph.aget_state(self.config(thread_id))).values)

    async def design(self, thread_id: str = "session-1") -> Design:
        return Design.model_validate((await self.state(thread_id))["design"])

    async def messages(self, thread_id: str = "session-1") -> list[BaseMessage]:
        return list((await self.state(thread_id))["messages"])


def at_step(
    step: int, design: Design | None = None, counters: dict[str, int] | None = None
) -> dict[str, Any]:
    """Initial state overrides for a session that has confirmed every step before ``step``."""
    overrides: dict[str, Any] = {"current_step": step, "confirmed_steps": list(range(1, step))}
    if design is not None:
        overrides["design"] = design.model_dump(mode="json")
        overrides["agent_design"] = overrides["design"]
    if counters is not None:
        overrides["id_counters"] = counters
    return overrides
