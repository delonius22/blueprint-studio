"""The session REST API (SPECS S3) and the agent endpoint wiring (S4.1, S4.2)."""

import json
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime
from typing import Annotated, Any, Self
from urllib.parse import quote

from ag_ui.core import (
    CustomEvent,
    EventType,
    RunAgentInput,
    RunErrorEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from copilotkit import LangGraphAGUIAgent
from fastapi import APIRouter, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from blueprint.api.browser import apply_browser_write
from blueprint.domain.state import SESSION_FIELDS, SessionState, new_session_state
from blueprint.exports import downloads
from blueprint.graph.gates import OPEN_GATE_EVENT
from blueprint.storage.sessions import InvalidCursor, SessionRow, SessionStore

AGENT_NAME = "blueprint"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorBody(BaseModel):
    error: ErrorDetail


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def error_response(status: int, code: str, message: str) -> JSONResponse:
    body = ErrorBody(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status, content=body.model_dump())


def errors(*statuses: int) -> dict[int | str, dict[str, Any]]:
    return {status: {"model": ErrorBody} for status in statuses}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'] if p != 'body')}: {e['msg']}" for e in exc.errors()
        )
        return error_response(422, "invalid_request", problems or "invalid request")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, str(exc.detail))


# --- S3.1 to S3.5 models -----------------------------------------------------------------------


class SessionName(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(description="1-120 characters after trimming")]

    @field_validator("name")
    @classmethod
    def trimmed_length(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 120:
            raise ValueError("name must be 1-120 characters after trimming")
        return value


class SessionSummary(BaseModel):
    id: str
    name: str
    stage: str
    current_step: int
    created_at: datetime
    updated_at: datetime


class SessionPage(BaseModel):
    items: list[SessionSummary]
    next_cursor: str | None


class SessionDetail(SessionSummary):
    state: SessionState = Field(
        description="The session state (SPECS S2.2) without messages or CopilotKit's field"
    )


class DownloadItem(BaseModel):
    """S10.3: one download kind, whether it is available and, if not, why."""

    kind: str
    available: bool
    reason: str | None


FILE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "The file, as an attachment named per SPECS S10.2",
        "content": {
            media: {"schema": {"type": "string", "format": "binary"}}
            for media in sorted({k.media_type for k in downloads.KINDS.values()})
        },
    }
}


def content_disposition(file_name: str) -> str:
    """An attachment header that keeps non-ASCII session names (RFC 6266, RFC 5987)."""
    fallback = "".join(c if c.isascii() and c not in '"\\' else "_" for c in file_name)
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(file_name, safe='')}"


def summary(row: SessionRow) -> SessionSummary:
    return SessionSummary(**row.__dict__)


# --- the agent endpoint with session bookkeeping --------------------------------------------


class SessionAgent(LangGraphAGUIAgent):
    """The `blueprint` AG-UI agent; runs only on existing sessions and records progress."""

    exists: Callable[[str], Awaitable[bool]] | None = None
    after_run: Callable[[str], Awaitable[None]] | None = None

    def clone(self) -> Self:
        copy: Self = super().clone()
        copy.exists, copy.after_run = self.exists, self.after_run
        return copy

    async def run(self, input: RunAgentInput) -> AsyncGenerator[Any]:
        if self.exists is not None and not await self.exists(input.thread_id):
            yield RunErrorEvent(
                type=EventType.RUN_ERROR, message="unknown session", code="not_found"
            )
            return
        # S2.15: the browser's state is checked against the checkpoint before the graph sees it.
        checkpoint = await self.graph.aget_state({"configurable": {"thread_id": input.thread_id}})
        state = apply_browser_write(dict(checkpoint.values or {}), dict(input.state or {}))
        input = input.model_copy(update={"state": state})
        async for event in super().run(input):  # type: ignore[no-untyped-call]
            yield event
            if isinstance(event, CustomEvent) and event.name == OPEN_GATE_EVENT:
                for gate_event in gate_tool_call_events(event.value):
                    yield gate_event
        if self.after_run is not None:
            await self.after_run(input.thread_id)


def gate_tool_call_events(value: dict[str, Any]) -> list[Any]:
    """The AG-UI events that make the browser open a gate card for this tool call."""
    call_id = value["id"]
    return [
        ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=call_id,
            tool_call_name=value["name"],
            parent_message_id=value.get("message_id") or call_id,
        ),
        ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS, tool_call_id=call_id, delta=json.dumps(value["args"])
        ),
        ToolCallEndEvent(type=EventType.TOOL_CALL_END, tool_call_id=call_id),
    ]


def session_routes(
    store: SessionStore,
    graph: CompiledStateGraph[Any, Any, Any, Any],
    checkpointer: BaseCheckpointSaver[Any],
    token_budget: int,
    review_model_distinct: bool,
) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    def config(session_id: str) -> Any:
        return {"configurable": {"thread_id": session_id}}

    async def existing(session_id: str) -> SessionRow:
        row = await store.get(session_id)
        if row is None:
            raise ApiError(404, "not_found", f"session {session_id} does not exist")
        return row

    @router.post("", status_code=201, response_model=SessionSummary, responses=errors(422))
    async def create_session(body: SessionName) -> SessionSummary:
        session_id = str(uuid.uuid4())
        initial = new_session_state(session_id, token_budget, review_model_distinct)
        await graph.aupdate_state(config(session_id), initial, as_node="__start__")
        row = await store.create(session_id, body.name, initial["stage"], initial["current_step"])
        return summary(row)

    @router.get("", response_model=SessionPage, responses=errors(422))
    async def list_sessions(
        limit: Annotated[int, Query(ge=1, le=100)] = 20, cursor: str | None = None
    ) -> SessionPage:
        try:
            rows, next_cursor = await store.page(limit, cursor)
        except InvalidCursor as exc:
            raise ApiError(422, "invalid_cursor", str(exc)) from None
        return SessionPage(items=[summary(r) for r in rows], next_cursor=next_cursor)

    @router.get("/{session_id}", response_model=SessionDetail, responses=errors(404, 422))
    async def get_session(session_id: str) -> SessionDetail:
        row = await existing(session_id)
        snapshot = await graph.aget_state(config(session_id))
        values = {k: v for k, v in snapshot.values.items() if k in SESSION_FIELDS}
        state = SessionState.model_validate(values)
        return SessionDetail(**summary(row).model_dump(), state=state)

    async def session_state(session_id: str) -> SessionState:
        values = (await graph.aget_state(config(session_id))).values
        return SessionState.model_validate({k: v for k, v in values.items() if k in SESSION_FIELDS})

    @router.get(
        "/{session_id}/downloads", response_model=list[DownloadItem], responses=errors(404, 422)
    )
    async def list_downloads(session_id: str) -> list[DownloadItem]:
        await existing(session_id)
        state = await session_state(session_id)
        return [
            DownloadItem(kind=kind, available=reason is None, reason=reason)
            for kind in downloads.KINDS
            for reason in [downloads.unmet(state, kind)]
        ]

    @router.get(
        "/{session_id}/downloads/{kind}",
        response_class=Response,
        responses=FILE_RESPONSE | errors(404, 409, 422),
    )
    async def download(session_id: str, kind: str) -> Response:
        row = await existing(session_id)
        if kind not in downloads.KINDS:
            raise ApiError(404, "unknown_kind", f"{kind} is not a download kind")
        state = await session_state(session_id)
        reason = downloads.unmet(state, kind)
        if reason is not None:
            raise ApiError(409, "not_available", f"{kind} is not available: {reason}")
        spec = downloads.KINDS[kind]
        body = downloads.render(state, kind, row.name)
        return Response(
            content=body,
            media_type=spec.media_type,
            headers={"content-disposition": content_disposition(spec.file_name(row.name))},
        )

    @router.patch("/{session_id}", response_model=SessionSummary, responses=errors(404, 422))
    async def rename_session(session_id: str, body: SessionName) -> SessionSummary:
        row = await store.rename(session_id, body.name)
        if row is None:
            raise ApiError(404, "not_found", f"session {session_id} does not exist")
        return summary(row)

    @router.delete("/{session_id}", status_code=204, response_class=Response, responses=errors(422))
    async def delete_session(session_id: str) -> Response:
        await store.delete(session_id)
        await checkpointer.adelete_thread(session_id)
        return Response(status_code=204)

    return router
