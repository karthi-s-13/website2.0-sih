from app.services.web.query_planner import MAX_TOPICS, plan_queries, select_topics


def test_select_topics_defaults_when_no_drivers() -> None:
    topics = select_topics([])
    assert topics == ["construction delay", "approval"]


def test_select_topics_high_ml_risk_first() -> None:
    topics = select_topics(["HIGH_ML_RISK"])
    assert topics[:3] == ["tender", "court case", "funding"]


def test_select_topics_schedule_behind() -> None:
    topics = select_topics(["SCHEDULE_BEHIND"])
    assert "construction delay" in topics
    assert "land acquisition" in topics


def test_select_topics_respects_budget() -> None:
    topics = select_topics(["HIGH_ML_RISK", "SCHEDULE_BEHIND", "EXPENDITURE_AHEAD", "STAGNANT_TREND"])
    assert len(topics) <= MAX_TOPICS


def test_select_topics_dedupes_across_categories() -> None:
    topics = select_topics(["HIGH_ML_RISK", "EXPENDITURE_AHEAD"], max_topics=10)
    assert topics.count("funding") == 1


def test_plan_queries_includes_project_context() -> None:
    planned = plan_queries(
        project_name="Test Bridge Project",
        agency="NHAI",
        state="Bihar",
        driver_categories=["SCHEDULE_BEHIND"],
    )
    assert len(planned) > 0
    for p in planned:
        assert "Test Bridge Project" in p.query_text
        assert "NHAI" in p.query_text
        assert "Bihar" in p.query_text
        assert p.topic in p.query_text


def test_plan_queries_handles_missing_agency_state() -> None:
    planned = plan_queries(
        project_name="Test Project", agency=None, state=None, driver_categories=["HIGH_ML_RISK"]
    )
    assert len(planned) > 0
    assert planned[0].query_text.startswith("Test Project")
