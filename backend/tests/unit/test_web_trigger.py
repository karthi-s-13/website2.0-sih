from app.services.web.trigger import should_trigger


def test_no_trigger_when_risk_low_and_no_force() -> None:
    decision = should_trigger(overall_health="NORMAL", ml_risk_level="LOW")
    assert decision.triggered is False


def test_trigger_on_high_health() -> None:
    decision = should_trigger(overall_health="HIGH", ml_risk_level="LOW")
    assert decision.triggered is True
    assert "HIGH" in decision.reason


def test_trigger_on_critical_health() -> None:
    decision = should_trigger(overall_health="CRITICAL", ml_risk_level=None)
    assert decision.triggered is True


def test_trigger_on_high_ml_risk() -> None:
    decision = should_trigger(overall_health="NORMAL", ml_risk_level="HIGH")
    assert decision.triggered is True
    assert "HIGH" in decision.reason


def test_trigger_on_critical_ml_risk() -> None:
    decision = should_trigger(overall_health="WATCH", ml_risk_level="CRITICAL")
    assert decision.triggered is True


def test_no_trigger_on_moderate_risk() -> None:
    decision = should_trigger(overall_health="WATCH", ml_risk_level="MODERATE")
    assert decision.triggered is False


def test_trigger_on_force() -> None:
    decision = should_trigger(overall_health="NORMAL", ml_risk_level="LOW", force=True)
    assert decision.triggered is True
    assert "force" in decision.reason.lower()


def test_trigger_on_for_diagnosis() -> None:
    decision = should_trigger(overall_health="NORMAL", ml_risk_level="LOW", for_diagnosis=True)
    assert decision.triggered is True
