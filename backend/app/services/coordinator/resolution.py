"""Project Identity Resolution (spec section 8) - deterministic, no LLM.

    User Input -> Project Name/Code Extraction -> Exact Project ID Lookup
    If exact match -> continue
    If multiple matches -> disambiguate
    If no match -> report not found

Project code (project_id) is the preferred internal identifier - an
explicit `project_id` always short-circuits straight to RESOLVED.

Matching a free-text query against a project name is inherently fuzzy: real
project names are long formal titles built from a small, recurring
infrastructure-domain vocabulary ("transmission", "system", "integration",
"limited", ...) shared across many projects, so a naive "any shared word"
match would false-positive constantly. `_STOPWORDS` removes that shared
vocabulary (plus basic English function words) before comparing, so a match
requires the query to actually name the project's *distinctive* part (e.g.
"Keshod Airport"), not just mention infrastructure jargon it happens to
share with dozens of other projects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.project_repository import get_project, list_all_projects

RESOLVED = "RESOLVED"
AMBIGUOUS = "AMBIGUOUS"
NOT_FOUND = "NOT_FOUND"

MATCH_RATIO_THRESHOLD = 0.6

_STOPWORDS = {
    # basic English function words
    "the", "of", "and", "for", "in", "at", "to", "is", "this", "that", "what",
    "who", "when", "where", "why", "how", "on", "with", "by", "an", "a",
    # recurring infrastructure/project-title vocabulary (not distinctive)
    "power", "project", "projects", "system", "systems", "transmission",
    "integration", "limited", "scheme", "name", "spv", "augmentation",
    "development", "station", "generating", "capacity", "phase", "part",
    "strengthening", "evacuation", "corporation", "india", "grid",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class ProjectCandidate:
    project_id: str
    project_name: str


@dataclass(frozen=True)
class ProjectResolution:
    status: str  # RESOLVED | AMBIGUOUS | NOT_FOUND
    project_id: str | None
    candidates: list[ProjectCandidate]


def _distinctive_tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2 and t not in _STOPWORDS}


def _matches(query_tokens: set[str], project: Project) -> bool:
    name_tokens = _distinctive_tokens(project.project_name)
    if not name_tokens:
        return False
    overlap = query_tokens & name_tokens
    return len(overlap) / len(name_tokens) >= MATCH_RATIO_THRESHOLD


def resolve_project(
    session: Session, query: str, explicit_project_id: str | None = None
) -> ProjectResolution:
    if explicit_project_id:
        project = get_project(session, explicit_project_id)
        if project is None:
            return ProjectResolution(status=NOT_FOUND, project_id=None, candidates=[])
        return ProjectResolution(status=RESOLVED, project_id=project.project_id, candidates=[])

    direct = get_project(session, query.strip())
    if direct is not None:
        return ProjectResolution(status=RESOLVED, project_id=direct.project_id, candidates=[])

    query_tokens = _distinctive_tokens(query)
    if not query_tokens:
        return ProjectResolution(status=NOT_FOUND, project_id=None, candidates=[])

    all_projects: list[Project] = list_all_projects(session)
    matches = [p for p in all_projects if _matches(query_tokens, p)]

    if len(matches) == 1:
        return ProjectResolution(status=RESOLVED, project_id=matches[0].project_id, candidates=[])
    if len(matches) > 1:
        candidates = [ProjectCandidate(p.project_id, p.project_name) for p in matches]
        return ProjectResolution(status=AMBIGUOUS, project_id=None, candidates=candidates)
    return ProjectResolution(status=NOT_FOUND, project_id=None, candidates=[])
