"""Endpoints voor project-beheer."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from .schemas import (
    CreateProjectIn,
    PageOut,
    ProjectDetailOut,
    ProjectListItem,
    ProjectSettingsIn,
)
from .state import get_state


router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_list_item(meta) -> ProjectListItem:
    return ProjectListItem(
        slug=meta.slug,
        name=meta.name,
        pages=len(meta.pages),
        created_at=meta.created_at,
        updated_at=meta.updated_at,
        description=meta.description,
    )


def _to_detail(project) -> ProjectDetailOut:
    pages = [
        PageOut(
            id=p.id,
            index=i + 1,
            width=p.width,
            height=p.height,
            has_processed=bool(p.processed_filename),
            has_thumb=bool(p.thumb_filename),
            has_ocr=bool(p.ocr_filename),
            text_preview=p.text_preview,
            avg_confidence=p.avg_confidence,
            created_at=p.created_at,
        )
        for i, p in enumerate(project.meta.pages)
    ]
    return ProjectDetailOut(
        slug=project.meta.slug,
        name=project.meta.name,
        description=project.meta.description,
        created_at=project.meta.created_at,
        updated_at=project.meta.updated_at,
        settings=project.meta.settings.model_dump(),
        pages=pages,
    )


@router.get("", response_model=List[ProjectListItem])
def list_projects():
    state = get_state()
    return [_to_list_item(m) for m in state.manager.list_projects()]


@router.post("", response_model=ProjectDetailOut)
def create_project(payload: CreateProjectIn):
    state = get_state()
    project = state.manager.create(name=payload.name, description=payload.description)
    state.set_active(project)
    return _to_detail(project)


@router.get("/active", response_model=ProjectDetailOut)
def active_project():
    state = get_state()
    project = state.active_project
    if project is None:
        raise HTTPException(status_code=404, detail="Geen actief project.")
    # Hernlaad om vers te zijn
    project = state.manager.open(project.meta.slug)
    state.set_active(project)
    return _to_detail(project)


@router.post("/{slug}/open", response_model=ProjectDetailOut)
def open_project(slug: str):
    state = get_state()
    try:
        project = state.manager.open(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    state.set_active(project)
    return _to_detail(project)


@router.delete("/{slug}", status_code=204)
def delete_project(slug: str):
    state = get_state()
    if state.active_project and state.active_project.meta.slug == slug:
        state.set_active(None)
    state.manager.delete(slug)
    return None


@router.put("/{slug}/settings", response_model=ProjectDetailOut)
def update_settings(slug: str, payload: ProjectSettingsIn):
    state = get_state()
    try:
        project = state.manager.open(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(project.meta.settings, k, v)
    project.save()
    if state.active_project and state.active_project.meta.slug == slug:
        state.set_active(project)
    return _to_detail(project)
