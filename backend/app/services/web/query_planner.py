"""Deterministic query planning for the Web Intelligence Agent (spec section
20's "Query Planner" stage).

Rather than firing all twelve spec topics on every triggered run (the
"budget" anti-pattern §96.5 warns against), the planner maps whichever risk
driver categories are actually present for the project (computed by
`web.service` from the same Health/Prediction/data-quality data Phase 4/3/1
already produce) onto a small, bounded subset of topics.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_TOPICS = 4

# All topics the spec names as candidates - kept as the single source of
# truth for validation/tests, even though most runs only use a subset.
ALL_TOPICS = [
    "land acquisition",
    "environmental clearance",
    "forest clearance",
    "contractor dispute",
    "tender",
    "court case",
    "funding",
    "utility shifting",
    "construction delay",
    "approval",
    "local issue",
    "material shortage",
]

# Priority-ordered: earlier categories' topics win the topic budget first.
DRIVER_TOPIC_MAP: list[tuple[str, list[str]]] = [
    ("HIGH_ML_RISK", ["tender", "court case", "funding"]),
    ("SCHEDULE_BEHIND", ["construction delay", "land acquisition", "approval"]),
    ("EXPENDITURE_AHEAD", ["contractor dispute", "funding"]),
    ("DATA_QUALITY_CONCERN", ["material shortage", "contractor dispute"]),
    ("STAGNANT_TREND", ["utility shifting", "environmental clearance", "forest clearance"]),
]

DEFAULT_TOPICS = ["construction delay", "approval"]


@dataclass(frozen=True)
class PlannedQuery:
    topic: str
    query_text: str


def select_topics(driver_categories: list[str], max_topics: int = MAX_TOPICS) -> list[str]:
    seen: set[str] = set()
    topics: list[str] = []
    for category, category_topics in DRIVER_TOPIC_MAP:
        if category not in driver_categories:
            continue
        for topic in category_topics:
            if topic in seen:
                continue
            seen.add(topic)
            topics.append(topic)
            if len(topics) >= max_topics:
                return topics
    if not topics:
        topics = list(DEFAULT_TOPICS)[:max_topics]
    return topics


def plan_queries(
    *,
    project_name: str,
    agency: str | None,
    state: str | None,
    driver_categories: list[str],
    max_topics: int = MAX_TOPICS,
) -> list[PlannedQuery]:
    topics = select_topics(driver_categories, max_topics=max_topics)
    context = " ".join(filter(None, [project_name, agency, state]))
    return [PlannedQuery(topic=topic, query_text=f"{context} {topic}".strip()) for topic in topics]
