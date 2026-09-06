"""Deterministic project-timeline event derivation (FR-006/FR-007).

Events are derived purely from observed field transitions between
consecutive kept observations of the same project - nothing is inferred or
invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.services.ingestion.schema import NormalizedObservation


@dataclass
class DerivedEvent:
    event_month: date
    event_type: str
    description: str
    previous_value: str | None
    new_value: str | None


def derive_events(observations_sorted: list[NormalizedObservation]) -> list[DerivedEvent]:
    events: list[DerivedEvent] = []
    prev: NormalizedObservation | None = None

    for obs in observations_sorted:
        if prev is None:
            events.append(
                DerivedEvent(
                    event_month=obs.observation_month,
                    event_type="PROJECT_FIRST_OBSERVED",
                    description=f"Project first appears in Flash Report data ({obs.report_label}).",
                    previous_value=None,
                    new_value=obs.report_label,
                )
            )
        else:
            if obs.revised_cost_crore != prev.revised_cost_crore:
                events.append(
                    DerivedEvent(
                        event_month=obs.observation_month,
                        event_type="COST_REVISED",
                        description="Revised cost changed between consecutive Flash Report editions.",
                        previous_value=_fmt(prev.revised_cost_crore),
                        new_value=_fmt(obs.revised_cost_crore),
                    )
                )
            if obs.revised_completion_date != prev.revised_completion_date:
                events.append(
                    DerivedEvent(
                        event_month=obs.observation_month,
                        event_type="COMPLETION_DATE_REVISED",
                        description="Revised completion date changed between consecutive Flash Report editions.",
                        previous_value=_fmt(prev.revised_completion_date),
                        new_value=_fmt(obs.revised_completion_date),
                    )
                )
            if (
                obs.record_type is not None
                and prev.record_type is not None
                and obs.record_type != prev.record_type
            ):
                events.append(
                    DerivedEvent(
                        event_month=obs.observation_month,
                        event_type="RECORD_TYPE_CHANGED",
                        description="Project's record classification changed between editions.",
                        previous_value=prev.record_type,
                        new_value=obs.record_type,
                    )
                )
        prev = obs

    return events


def _fmt(value: object) -> str | None:
    return None if value is None else str(value)
