"""Data-quality rules applied after normalization.

Rules explicitly required by the Phase 1 spec:

    physical_progress >= 0
    physical_progress <= 100
    expenditure >= 0
    original_cost > 0
    observation_date is valid   (handled during normalization: INVALID_DATE)
    project_id is not null      (handled during normalization: MISSING_REQUIRED_FIELD)

Plus duplicate project-month detection, and two soft (WARNING) monotonicity
checks on the cumulative fields, since a "cumulative" value that decreases
month over month is a strong signal of a data problem worth surfacing.

No rule here deletes a record. Violations are attached as `RowIssue`s to the
observation for the pipeline to persist to `data_quality_issues`; the
observation itself is still written to `project_monthly_observations` as
parsed, except when project_id is missing (no valid primary key to attach to
in the cleaned schema) or the row is a detected duplicate (only one copy of a
given project-month can exist under the table's unique constraint) — both
cases remain visible via `raw_observations` and `data_quality_issues`.
"""

from __future__ import annotations

from app.services.ingestion.schema import NormalizedObservation, RowIssue


def validate_ranges(obs: NormalizedObservation) -> list[RowIssue]:
    issues: list[RowIssue] = []

    if obs.physical_progress_percent is not None and not (0 <= obs.physical_progress_percent <= 100):
        issues.append(
            RowIssue(
                "INVALID_RANGE",
                "ERROR",
                "physical_progress_percent",
                str(obs.physical_progress_percent),
                "physical_progress_percent must be within [0, 100]",
            )
        )

    if obs.cumulative_expenditure_crore is not None and obs.cumulative_expenditure_crore < 0:
        issues.append(
            RowIssue(
                "INVALID_RANGE",
                "ERROR",
                "cumulative_expenditure_crore",
                str(obs.cumulative_expenditure_crore),
                "cumulative_expenditure_crore must be >= 0",
            )
        )

    if obs.original_cost_crore is not None and obs.original_cost_crore <= 0:
        issues.append(
            RowIssue(
                "INVALID_RANGE",
                "ERROR",
                "original_cost_crore",
                str(obs.original_cost_crore),
                "original_cost_crore must be > 0",
            )
        )

    return issues


def _completeness_score(obs: NormalizedObservation) -> int:
    fields = (
        obs.cumulative_expenditure_crore,
        obs.physical_progress_percent,
        obs.revised_cost_crore,
        obs.notes,
    )
    return sum(1 for value in fields if value is not None)


def deduplicate_project_month(
    observations: list[NormalizedObservation],
) -> tuple[list[NormalizedObservation], list[tuple[NormalizedObservation, RowIssue]]]:
    """Given observations for a single project, keep at most one per
    observation_month. Returns (kept, [(dropped_obs, issue), ...])."""

    by_month: dict[object, list[NormalizedObservation]] = {}
    for obs in observations:
        by_month.setdefault(obs.observation_month, []).append(obs)

    kept: list[NormalizedObservation] = []
    dropped: list[tuple[NormalizedObservation, RowIssue]] = []

    for month, candidates in by_month.items():
        if len(candidates) == 1:
            kept.append(candidates[0])
            continue

        ordered = sorted(
            candidates, key=lambda o: (_completeness_score(o), o.source_row), reverse=True
        )
        winner, *losers = ordered
        kept.append(winner)
        for loser in losers:
            dropped.append(
                (
                    loser,
                    RowIssue(
                        "DUPLICATE_PROJECT_MONTH",
                        "ERROR",
                        "observation_month",
                        str(month),
                        f"duplicate observation for {loser.project_id} / {month}; kept "
                        f"{winner.source_file}:{winner.source_row}, dropped "
                        f"{loser.source_file}:{loser.source_row}",
                    ),
                )
            )

    return kept, dropped


def check_monotonic_sequences(
    observations_sorted: list[NormalizedObservation],
) -> list[tuple[NormalizedObservation, RowIssue]]:
    """observations_sorted must already be sorted chronologically for one project."""
    issues: list[tuple[NormalizedObservation, RowIssue]] = []
    prev: NormalizedObservation | None = None

    for obs in observations_sorted:
        if prev is not None:
            if (
                obs.cumulative_expenditure_crore is not None
                and prev.cumulative_expenditure_crore is not None
                and obs.cumulative_expenditure_crore < prev.cumulative_expenditure_crore
            ):
                issues.append(
                    (
                        obs,
                        RowIssue(
                            "NON_MONOTONIC_CUMULATIVE_EXPENDITURE",
                            "WARNING",
                            "cumulative_expenditure_crore",
                            str(obs.cumulative_expenditure_crore),
                            f"decreased from {prev.cumulative_expenditure_crore} in "
                            f"{prev.observation_month} to {obs.cumulative_expenditure_crore} in "
                            f"{obs.observation_month}",
                        ),
                    )
                )
            if (
                obs.physical_progress_percent is not None
                and prev.physical_progress_percent is not None
                and obs.physical_progress_percent < prev.physical_progress_percent
            ):
                issues.append(
                    (
                        obs,
                        RowIssue(
                            "NON_MONOTONIC_PHYSICAL_PROGRESS",
                            "WARNING",
                            "physical_progress_percent",
                            str(obs.physical_progress_percent),
                            f"decreased from {prev.physical_progress_percent} in "
                            f"{prev.observation_month} to {obs.physical_progress_percent} in "
                            f"{obs.observation_month}",
                        ),
                    )
                )
        prev = obs

    return issues
