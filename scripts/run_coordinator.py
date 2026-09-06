#!/usr/bin/env python
"""Phase 11 CLI: run the Coordinator Agent end-to-end for a handful of
representative "golden questions" (spec section 57) against the 5
validation-cohort projects, live - real Postgres, real Gemini/Tavily.

This is also where genuine parallel execution (HISTORY + DIAGNOSIS/
INTERVENTION on separate threads/sessions) actually gets exercised for
real, since the backend test suite deliberately runs the Coordinator with
parallel=False (a shared in-memory sqlite connection isn't safe under
real concurrent cursor use - see app/services/coordinator/service.py).

Usage (from repo root, with the backend venv active):

    python scripts/run_coordinator.py
    python scripts/run_coordinator.py --portfolio
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.services.coordinator.portfolio import rank_portfolio  # noqa: E402
from app.services.coordinator.service import run_analysis  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)

GOLDEN_QUESTIONS = [
    "What is the current health?",
    "What is the cost-overrun probability?",
    "What happened to this project?",
    "Why is this project risky?",
    "What should be reviewed?",
]

VALIDATION_PROJECT_ID = "617069"


def _print_report(state) -> None:
    print(f"intent={state.intent} ({state.intent_source})  plan={state.plan}  expanded={state.expanded}")
    for sr in state.stage_results:
        print(f"  [{sr.status}] {sr.stage} ({sr.duration_ms:.0f} ms){' - ' + sr.error if sr.error else ''}")
    if state.report is None:
        print("  (no report - resolution was ambiguous or portfolio mode)")
        return
    r = state.report
    print(f"  Executive summary: {r.executive_summary}")
    if r.current_health:
        print(f"  Current health: {r.current_health['overall_health']}")
    if r.cost_overrun_risk:
        print(f"  Cost-overrun risk: {r.cost_overrun_risk['risk_level']} ({r.cost_overrun_risk['probability'] * 100:.1f}%)")
    if r.top_risk_drivers:
        print(f"  Top driver: {r.top_risk_drivers[0]['driver']}")
    if r.recommended_monitoring_actions:
        print(f"  Top recommendation: {r.recommended_monitoring_actions[0]['action']}")
    print(f"  human_review_required={r.human_review_required} ({r.human_review_reason})")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", action="store_true", help="Run portfolio ranking instead of golden questions")
    args = parser.parse_args()

    configure_logging()
    log = get_logger("run_coordinator")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        if args.portfolio:
            result = rank_portfolio(session, top_n=3)
            print(f"\n{'=' * 78}\nPortfolio ranking (as of {result.as_of_date})\n{'-' * 78}")
            for r in result.ranked:
                print(
                    f"  {r.rank}. {r.project_name[:60]} - risk_score={r.risk_score} "
                    f"health={r.overall_health} ml_risk={r.ml_risk_level}"
                )
                if r.diagnosis_summary:
                    print(f"       diagnosis: {r.diagnosis_summary.overall_risk} - {r.diagnosis_summary.top_driver}")
            return

        for question in GOLDEN_QUESTIONS:
            print(f"\n{'=' * 78}\nQ: {question}")
            state = run_analysis(session, question, project_id=VALIDATION_PROJECT_ID)
            _print_report(state)
    finally:
        session.close()


if __name__ == "__main__":
    main()
