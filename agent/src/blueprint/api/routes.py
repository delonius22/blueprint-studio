"""The session REST API (SPECS S3, S10.3, S14.8); the agent endpoint is in ``api.agent``."""

import hashlib
import uuid
from datetime import datetime
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from blueprint.domain.state import SESSION_FIELDS, SessionState, new_session_state
from blueprint.exports import downloads
from blueprint.imports.files import (
    FILE_TYPES,
    MAX_ATTACHMENTS,
    MAX_BYTES,
    AttachmentRejected,
    accepted_extensions,
    read_file,
)
from blueprint.storage.sessions import AttachmentRow, InvalidCursor, SessionRow, SqlSessionStore


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


Responses = dict[int | str, dict[str, Any]]


def errors(*statuses: int) -> Responses:
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


FILE_RESPONSE: Responses = {
    200: {
        "description": "The file, as an attachment named per SPECS S10.2",
        "content": {
            media: {"schema": {"type": "string", "format": "binary"}}
            for media in sorted({k.media_type for k in downloads.KINDS.values()})
        },
    }
}


class AttachmentItem(BaseModel):
    """An attached file (SPEC-document-import §4)."""

    id: str
    name: str
    kind: str
    media_type: str
    size: int
    warnings: list[str]


class AttachmentListing(BaseModel):
    accepts: list[str] = Field(description="The file extensions the upload route takes now")
    attachments: list[AttachmentItem]


class UploadedAttachment(AttachmentItem):
    duplicate: bool = Field(description="True when this exact file was already attached")


def attachment_item(row: AttachmentRow) -> AttachmentItem:
    return AttachmentItem(
        id=row.id,
        name=row.name,
        kind=row.kind,
        media_type=row.media_type,
        size=row.size,
        warnings=row.warnings,
    )


DUPLICATE_UPLOAD: Responses = {
    200: {"model": UploadedAttachment, "description": "Already attached"}
}
ORIGINAL_FILE: Responses = {
    200: {
        "description": "The file as uploaded",
        "content": {
            media: {"schema": {"type": "string", "format": "binary"}}
            for media in sorted({file_type.media_type for file_type in FILE_TYPES.values()})
        },
    }
}
UPLOAD_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "description": "The file's bytes; its name is the `name` query parameter",
        "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
    }
}


async def read_capped(request: Request, limit: int) -> bytes:
    """The request body, refused with 413 as soon as it passes ``limit`` bytes."""
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise ApiError(413, "file_too_large", "the file is larger than 10 MB")
        chunks.append(chunk)
    return b"".join(chunks)


def content_disposition(file_name: str) -> str:
    """An attachment header that keeps non-ASCII session names (RFC 6266, RFC 5987)."""
    fallback = "".join(c if c.isascii() and c not in '"\\' else "_" for c in file_name)
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(file_name, safe='')}"


def summary(row: SessionRow) -> SessionSummary:
    return SessionSummary(**row.__dict__)


def session_routes(
    store: SqlSessionStore,
    graph: CompiledStateGraph[Any, Any, Any, Any],
    checkpointer: BaseCheckpointSaver[Any],
    token_budget: int,
    review_model_distinct: bool,
    vision: bool = False,
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

    async def interviewing(session_id: str) -> None:
        """Files are attached and removed only while the interview runs (SPEC §2.1)."""
        await existing(session_id)
        stage = (await session_state(session_id)).stage
        if stage != "interview":
            raise ApiError(
                409, "wrong_stage", f"files can only be changed in the interview, not {stage}"
            )

    @router.get(
        "/{session_id}/attachments", response_model=AttachmentListing, responses=errors(404, 422)
    )
    async def list_attachments(session_id: str) -> AttachmentListing:
        await existing(session_id)
        rows = await store.attachments(session_id)
        return AttachmentListing(
            accepts=accepted_extensions(vision), attachments=[attachment_item(r) for r in rows]
        )

    @router.post(
        "/{session_id}/attachments",
        status_code=201,
        response_model=UploadedAttachment,
        responses=DUPLICATE_UPLOAD | errors(404, 409, 413, 415, 422),
        openapi_extra=UPLOAD_BODY,
    )
    async def upload_attachment(
        session_id: str,
        name: Annotated[str, Query(min_length=1, max_length=255)],
        request: Request,
        response: Response,
    ) -> UploadedAttachment:
        await interviewing(session_id)
        data = await read_capped(request, MAX_BYTES)
        rows = await store.attachments(session_id)
        digest = hashlib.sha256(data).hexdigest()
        same = next((r for r in rows if r.sha256 == digest), None)
        if same is not None:
            response.status_code = 200
            return UploadedAttachment(**attachment_item(same).model_dump(), duplicate=True)
        if len(rows) >= MAX_ATTACHMENTS:
            raise ApiError(
                409, "attachment_limit", f"a session takes at most {MAX_ATTACHMENTS} files"
            )
        try:
            parsed = read_file(name, data, vision)
        except AttachmentRejected as refused:
            raise ApiError(refused.status, refused.code, refused.message) from None
        row = await store.add_attachment(session_id, name, data, parsed)
        return UploadedAttachment(**attachment_item(row).model_dump(), duplicate=False)

    @router.delete(
        "/{session_id}/attachments/{attachment_id}",
        status_code=204,
        response_class=Response,
        responses=errors(404, 409, 422),
    )
    async def remove_attachment(session_id: str, attachment_id: str) -> Response:
        await interviewing(session_id)
        await store.remove_attachment(session_id, attachment_id)
        return Response(status_code=204)

    @router.get(
        "/{session_id}/attachments/{attachment_id}/content",
        response_class=Response,
        responses=ORIGINAL_FILE | errors(404, 422),
    )
    async def attachment_content(session_id: str, attachment_id: str) -> Response:
        await existing(session_id)
        stored = await store.attachment(session_id, attachment_id)
        if stored is None:
            raise ApiError(404, "not_found", f"{attachment_id} is not attached to this session")
        return Response(
            content=stored.content,
            media_type=stored.row.media_type,
            headers={"content-disposition": content_disposition(stored.row.name)},
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
