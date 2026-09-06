"""Agent Budget (spec section 52). A single wall-clock deadline for the
whole analysis - enforced centrally by the Coordinator, not by individual
agents. A stage due to run after the deadline is recorded `SKIPPED` (spec
section 67's status vocabulary) with a warning rather than silently
omitted or allowed to run unbounded.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

DEFAULT_MAX_EXECUTION_SECONDS = 90.0


@dataclass
class Budget:
    max_execution_seconds: float = DEFAULT_MAX_EXECUTION_SECONDS


@dataclass
class BudgetTracker:
    budget: Budget = field(default_factory=Budget)
    _start: float = field(default_factory=time.monotonic, init=False)
    stage_count: int = field(default=0, init=False)

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start

    def is_exceeded(self) -> bool:
        return self.elapsed_seconds() >= self.budget.max_execution_seconds

    def record_stage(self) -> None:
        self.stage_count += 1
