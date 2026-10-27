"""The graph seam: the real compiled graph driven with two scripted fake models, one per role."""

from typing import Any

from fakes import ScriptedChatModel
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from blueprint.config.assets import load_assets
from blueprint.domain.models import Design, DocumentRole
from blueprint.domain.state import new_session_state
from blueprint.graph.build import build_graph
from blueprint.imports.files import read_file
from blueprint.imports.proposal import sync_attachments
from blueprint.llm.clients import RoleModels
from blueprint.llm.gateway import ModelGateway
from blueprint.storage.sessions import AttachmentRow, StoredAttachment


class MemoryFiles:
    """The attachments table in memory: what the importer reads and the run start syncs."""

    def __init__(self) -> None:
        self.files: dict[str, list[StoredAttachment | None]] = {}

    def add(
        self, session_id: str, name: str, data: bytes, role: DocumentRole = "prd"
    ) -> AttachmentRow:
        files = self.files.setdefault(session_id, [])
        parsed = read_file(name, data, vision=True)
        row = AttachmentRow(
            f"ATT-{len(files) + 1}",
            name,
            role,
            parsed.kind,
            parsed.media_type,
            len(data),
            "",
            parsed.warnings,
        )
        files.append(StoredAttachment(row, data, parsed.sections))
        return row

    def remove(self, session_id: str, attachment_id: str) -> None:
        files = self.files[session_id]
        files[int(attachment_id.removeprefix("ATT-")) - 1] = None

    def rows(self, session_id: str) -> list[AttachmentRow]:
        return [f.row for f in self.files.get(session_id, []) if f is not None]

    async def attachment(self, session_id: str, attachment_id: str) -> StoredAttachment | None:
        return next(
            (f for f in self.files.get(session_id, []) if f and f.row.id == attachment_id), None
        )


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
        jitter: float = 0.5,
    ) -> None:
        self.interview = interview
        self.review = review or ScriptedChatModel.with_script(name="review")
        self.assets = load_assets()
        self.sleeps: list[float] = []
        models = RoleModels(interview=self.interview, review=self.review)
        self.gateway = ModelGateway(models, sleep=self._sleep, jitter=lambda: jitter)
        self.files = MemoryFiles()
        self.graph = build_graph(models, InMemorySaver(), self.assets, self.gateway, self.files)
        self.frontend_tools = frontend_tools or []
        self.review_model_distinct = review_model_distinct
        self.token_budget = token_budget
        self.initial = initial or {}
        self._started: set[str] = set()

    async def _sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)

    async def resync(self, thread_id: str = "session-1") -> dict[str, Any]:
        """A run that adds no message (what the workspace does on page load)."""
        await self._ensure_session(thread_id)
        update: Any = {"messages": []}
        return dict(await self.graph.ainvoke(update, self.config(thread_id)))

    async def retry(self, thread_id: str = "session-1") -> dict[str, Any]:
        """What the workspace's Retry action does: clear last_error and run with no new message."""
        update: Any = {
            "last_error": None,
            "copilotkit": {"actions": self.frontend_tools, "context": []},
        }
        return dict(await self.graph.ainvoke(update, self.config(thread_id)))

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
        # What the agent endpoint does at the start of every run: sync the attachments table.
        synced = sync_attachments(await self.state(thread_id), self.files.rows(thread_id))
        update: Any = synced | {
            "messages": [message],
            "copilotkit": {"actions": self.frontend_tools, "context": []},
        }
        return dict(await self.graph.ainvoke(update, self.config(thread_id)))

    async def attach(self, name: str, data: bytes, thread_id: str = "session-1") -> dict[str, Any]:
        """What the workspace does: upload a file, then say so in the chat."""
        row = self.files.add(thread_id, name, data)
        return await self.send(f"Attached {name} ({row.id}).", thread_id)

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
    if counters is not None:
        overrides["id_counters"] = counters
    return overrides
