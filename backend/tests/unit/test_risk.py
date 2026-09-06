import pytest

from app.services.prediction.risk import risk_level_for_probability


@pytest.mark.parametrize(
    "probability,expected",
    [
        (0.0, "LOW"),
        (0.29, "LOW"),
        (0.30, "MODERATE"),
        (0.49, "MODERATE"),
        (0.50, "ELEVATED"),
        (0.69, "ELEVATED"),
        (0.70, "HIGH"),
        (0.84, "HIGH"),
        (0.85, "CRITICAL"),
        (1.0, "CRITICAL"),
    ],
)
def test_risk_level_thresholds(probability: float, expected: str) -> None:
    assert risk_level_for_probability(probability) == expected


@pytest.mark.parametrize("probability", [-0.01, 1.01])
def test_risk_level_rejects_out_of_range(probability: float) -> None:
    with pytest.raises(ValueError):
        risk_level_for_probability(probability)
