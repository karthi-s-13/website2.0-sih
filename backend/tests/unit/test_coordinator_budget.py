import time

from app.services.coordinator.budget import Budget, BudgetTracker


def test_not_exceeded_immediately() -> None:
    tracker = BudgetTracker(budget=Budget(max_execution_seconds=10.0))
    assert tracker.is_exceeded() is False


def test_exceeded_after_deadline() -> None:
    tracker = BudgetTracker(budget=Budget(max_execution_seconds=0.01))
    time.sleep(0.02)
    assert tracker.is_exceeded() is True


def test_record_stage_increments_count() -> None:
    tracker = BudgetTracker()
    assert tracker.stage_count == 0
    tracker.record_stage()
    tracker.record_stage()
    assert tracker.stage_count == 2


def test_elapsed_seconds_increases() -> None:
    tracker = BudgetTracker()
    first = tracker.elapsed_seconds()
    time.sleep(0.05)
    second = tracker.elapsed_seconds()
    assert second > first
