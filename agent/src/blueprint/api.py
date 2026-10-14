"""The session REST API (SPECS S3) and the agent endpoint wiring (S4.1, S4.2)."""

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime
from typing import Annotated, Any, Self

from ag_ui.core import EventType, RunAgentInput, RunErrorEvent
from copilotkit import LangGraphAGUIAgent
from fastapi import APIRouter, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from blueprint.state import SESSION_FIELDS, new_session_state
from blueprint.store import InvalidCursor, SessionRow, SessionStore

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
    state: dict[str, Any] = Field(
        description="The session state (SPECS S2.2) without messages or CopilotKit's field"
    )


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
        async for event in super().run(input):  # type: ignore[no-untyped-call]
            yield event
        if self.after_run is not None:
            await self.after_run(input.thread_id)


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
        state = {k: v for k, v in snapshot.values.items() if k in SESSION_FIELDS}
        return SessionDetail(**summary(row).model_dump(), state=state)

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
