"""Typed HTTP surfaces over the shared services (ADR 0017)."""

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict
from typing import cast

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from news.service.db import create_engine_for
from news.service.drafts import (
    DraftConflict,
    DraftNotFound,
    create_draft,
    delete_draft,
    get_draft,
    list_drafts,
    promote_draft,
    save_draft,
)
from news.service.observability import configure_logging
from news.service.plugin_data import DraftDetails, PluginStarter, RevisionDetails, RevisionHistory
from news.service.plugins import create_plugin
from news.service.readers import ReaderNotFound
from news.service.revision_history import (
    CurrentSelectionConflict,
    PluginNotFound,
    list_revisions,
    select_current_revision,
)
from news.service.validation import ValidationRejected

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    engine = create_engine_for(os.environ.get("NEWS_DATABASE_URL", "sqlite:///news.db"))
    app.state.engine = engine
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="news", lifespan=lifespan)


@contextmanager
def transaction(request: Request) -> Generator[Session]:
    # Explicit surface-owned scope exits before returning a response, including on COMMIT
    # failures. No request-lifetime dependency can accidentally send success before commit.
    engine = cast(Engine, request.app.state.engine)
    try:
        with Session(engine) as session, session.begin():
            yield session
    except SQLAlchemyError as error:
        log.error("api.database_failed", error_type=type(error).__name__)
        raise HTTPException(503, "Database operation failed; try again.") from error


class PluginCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)


class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_revision_id: uuid.UUID


class DraftSave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(gt=0, strict=True)
    manifest: str
    code: dict[str, str]


class DraftPromote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(gt=0, strict=True)
    # Required when the Draft's parent is not the current Revision (ADR 0024).
    expected_current_revision_id: uuid.UUID | None = None


class CurrentRevisionSelect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: uuid.UUID
    expected_current_revision_id: uuid.UUID


@app.exception_handler(CurrentSelectionConflict)
async def selection_conflict_response(
    _request: Request, error: CurrentSelectionConflict
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "errors": [asdict(field) for field in error.errors],
            "reason": error.reason,
            "expected_current_revision_id": str(error.expected) if error.expected else None,
            "actual_current_revision_id": str(error.actual) if error.actual else None,
        },
    )


@app.exception_handler(DraftConflict)
async def conflict_response(_request: Request, error: DraftConflict) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "errors": [asdict(field) for field in error.errors],
            "expected_version": error.expected,
            "actual_version": error.actual,
        },
    )


@app.exception_handler(ValidationRejected)
async def validation_response(_request: Request, error: ValidationRejected) -> JSONResponse:
    return JSONResponse(
        status_code=422, content={"errors": [asdict(field) for field in error.errors]}
    )


@app.exception_handler(DraftNotFound)
@app.exception_handler(PluginNotFound)
@app.exception_handler(ReaderNotFound)
async def missing_response(_request: Request, error: LookupError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.post("/readers/{reader_id}/plugins", status_code=201)
def plugin_create(request: Request, reader_id: uuid.UUID, body: PluginCreate) -> PluginStarter:
    with transaction(request) as session:
        revision = create_plugin(session, reader_id, body.name)
        result = PluginStarter(plugin_id=revision.plugin_id, revision_id=revision.id)
    return result


DRAFTS = "/readers/{reader_id}/plugins/{plugin_id}/drafts"


@app.post(DRAFTS, status_code=201)
def draft_create(
    request: Request,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    body: DraftCreate,
) -> DraftDetails:
    with transaction(request) as session:
        result = DraftDetails.model_validate(
            create_draft(session, reader_id, plugin_id, body.parent_revision_id)
        )
    return result


@app.get(DRAFTS)
def draft_list(request: Request, reader_id: uuid.UUID, plugin_id: uuid.UUID) -> list[DraftDetails]:
    with transaction(request) as session:
        result = [
            DraftDetails.model_validate(draft)
            for draft in list_drafts(session, reader_id, plugin_id)
        ]
    return result


@app.get(DRAFTS + "/{draft_id}")
def draft_read(
    request: Request,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> DraftDetails:
    with transaction(request) as session:
        result = DraftDetails.model_validate(get_draft(session, reader_id, plugin_id, draft_id))
    return result


@app.put(DRAFTS + "/{draft_id}")
def draft_save(
    request: Request,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
    body: DraftSave,
) -> DraftDetails:
    with transaction(request) as session:
        result = DraftDetails.model_validate(
            save_draft(
                session,
                reader_id,
                plugin_id,
                draft_id,
                body.expected_version,
                body.manifest,
                body.code,
            )
        )
    return result


@app.delete(DRAFTS + "/{draft_id}", status_code=204)
def draft_delete(
    request: Request,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> Response:
    with transaction(request) as session:
        delete_draft(session, reader_id, plugin_id, draft_id)
    return Response(status_code=204)


@app.post(DRAFTS + "/{draft_id}/promote", status_code=201)
def draft_promote(
    request: Request,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
    body: DraftPromote,
) -> RevisionDetails:
    with transaction(request) as session:
        result = RevisionDetails.model_validate(
            promote_draft(
                session,
                reader_id,
                plugin_id,
                draft_id,
                body.expected_version,
                body.expected_current_revision_id,
            )
        )
    return result


PLUGIN = "/readers/{reader_id}/plugins/{plugin_id}"


@app.get(PLUGIN + "/revisions")
def revision_history(
    request: Request, reader_id: uuid.UUID, plugin_id: uuid.UUID
) -> RevisionHistory:
    with transaction(request) as session:
        result = list_revisions(session, reader_id, plugin_id)
    return result


@app.put(PLUGIN + "/current-revision")
def current_revision_select(
    request: Request,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    body: CurrentRevisionSelect,
) -> RevisionHistory:
    with transaction(request) as session:
        select_current_revision(
            session, reader_id, plugin_id, body.revision_id, body.expected_current_revision_id
        )
        result = list_revisions(session, reader_id, plugin_id)
    return result
