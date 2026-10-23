"""Unit tests for the pure sentiment-shift service (no database involved)."""

import ast
import inspect
import math
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.services import sentiment_shift_service as svc
from backend.app.services.sentiment_shift_service import (
    DEFAULT_SHIFT_RULES,
    SentimentObservation,
    ShiftRules,
    ShiftStatus,
    collapse_latest_observations,
    compute_windows,
    detect_sentiment_shift,
    detect_shifts,
)

AS_OF = datetime(2026, 10, 23, 12, 0, 0)
_AUTO = object()


def _label_for(score):
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        if score > 0:
            return "positive"
        if score < 0:
            return "negative"
    return "neutral"


def make_obs(
    article_id,
    *,
    days_ago=3,
    score=0.0,
    company_id=1,
    label=None,
    published_at=_AUTO,
    created_at=None,
    analysis_id=None,
):
    if published_at is _AUTO:
        published_at = AS_OF - timedelta(days=days_ago)
    return SentimentObservation(
        article_id=article_id,
        company_id=company_id,
        published_at=published_at,
        label=label if label is not None else _label_for(score),
        score=score,
        analysis_created_at=created_at,
        analysis_id=analysis_id,
    )


def batch(start_id, count, *, days_ago, score, company_id=1):
    return [
        make_obs(start_id + i, days_ago=days_ago, score=score, company_id=company_id)
        for i in range(count)
    ]


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------


def test_default_rules_match_approved_values():
    assert DEFAULT_SHIFT_RULES.window_days == 7
    assert DEFAULT_SHIFT_RULES.min_articles_per_window == 5
    assert DEFAULT_SHIFT_RULES.shift_threshold == 0.25


def test_rules_are_frozen():
    with pytest.raises(FrozenInstanceError):
        DEFAULT_SHIFT_RULES.window_days = 3  # type: ignore[misc]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"window_days": 0},
        {"window_days": True},
        {"window_days": 1.5},
        {"min_articles_per_window": 0},
        {"min_articles_per_window": True},
        {"shift_threshold": 0},
        {"shift_threshold": -0.1},
        {"shift_threshold": math.nan},
        {"shift_threshold": math.inf},
        {"shift_threshold": True},
    ],
)
def test_invalid_rules_are_rejected(kwargs):
    with pytest.raises(ValueError):
        ShiftRules(**kwargs)


def test_module_has_no_database_or_framework_imports():
    tree = ast.parse(inspect.getsource(svc))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"sqlalchemy", "shared", "backend", "fastapi", "nlp", "pydantic"}
    assert imported.isdisjoint(forbidden)


# --------------------------------------------------------------------------
# Windows and boundaries
# --------------------------------------------------------------------------


def test_compute_windows_boundaries():
    windows = compute_windows(AS_OF)
    assert windows.as_of == AS_OF
    assert windows.current_start == AS_OF - timedelta(days=7)
    assert windows.previous_start == AS_OF - timedelta(days=14)


def test_window_boundaries_are_half_open():
    observations = [
        make_obs(1, published_at=AS_OF - timedelta(days=7)),  # current (inclusive start)
        make_obs(2, published_at=AS_OF - timedelta(days=14)),  # previous (inclusive start)
        make_obs(3, published_at=AS_OF - timedelta(days=14, seconds=1)),  # before both
        make_obs(4, published_at=AS_OF),  # eligible but in neither window
        make_obs(5, published_at=AS_OF - timedelta(days=7, seconds=1)),  # previous
    ]
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.current.article_count == 1
    assert result.previous.article_count == 2
    assert result.ineligible_count == 0


def test_missing_and_future_published_at_are_ineligible():
    observations = [
        make_obs(1, published_at=None),
        make_obs(2, published_at=AS_OF + timedelta(seconds=1)),
        make_obs(3, days_ago=2),
    ]
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.ineligible_count == 2
    assert result.current.article_count == 1


def test_windows_use_published_at_not_analysis_creation_time():
    observations = [
        # Published 20 days ago, analysed just now: must not count.
        make_obs(1, days_ago=20, created_at=AS_OF),
        # Published 1 day ago, analysed 20 days ago: must count.
        make_obs(2, days_ago=1, created_at=AS_OF - timedelta(days=20)),
    ]
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.current.article_count == 1
    assert result.previous.article_count == 0


def test_timezone_aware_and_naive_inputs_give_identical_results():
    tz = timezone(timedelta(hours=5, minutes=30))
    as_of_aware = datetime(2026, 10, 23, 17, 30, 0, tzinfo=tz)  # == AS_OF in UTC
    naive = batch(1, 5, days_ago=3, score=0.5) + batch(10, 5, days_ago=10, score=0.0)
    aware = [
        SentimentObservation(
            article_id=o.article_id,
            company_id=o.company_id,
            published_at=(o.published_at.replace(tzinfo=timezone.utc)).astimezone(tz),
            label=o.label,
            score=o.score,
        )
        for o in naive
    ]
    assert detect_sentiment_shift(1, naive, as_of=AS_OF) == detect_sentiment_shift(
        1, aware, as_of=as_of_aware
    )


# --------------------------------------------------------------------------
# Minimum article counts and threshold
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_count, previous_count, expected",
    [
        (5, 5, ShiftStatus.IMPROVING),
        (4, 5, ShiftStatus.INSUFFICIENT_DATA),
        (5, 4, ShiftStatus.INSUFFICIENT_DATA),
        (0, 0, ShiftStatus.INSUFFICIENT_DATA),
    ],
)
def test_minimum_articles_required_in_each_window(
    current_count, previous_count, expected
):
    observations = batch(1, current_count, days_ago=3, score=0.6) + batch(
        100, previous_count, days_ago=10, score=0.0
    )
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.status is expected
    if expected is ShiftStatus.INSUFFICIENT_DATA:
        assert result.delta is None
    else:
        assert result.delta == pytest.approx(0.6)


def test_insufficient_data_still_reports_measured_values():
    observations = batch(1, 4, days_ago=3, score=0.4) + batch(
        100, 5, days_ago=10, score=-0.2
    )
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.status is ShiftStatus.INSUFFICIENT_DATA
    assert result.current.mean_score == pytest.approx(0.4)
    assert result.previous.mean_score == pytest.approx(-0.2)
    assert result.delta is None


def test_delta_at_threshold_is_flagged_despite_float_error():
    # 0.35 - 0.10 == 0.24999999999999997 in binary floating point.
    observations = batch(1, 5, days_ago=3, score=0.35) + batch(
        100, 5, days_ago=10, score=0.10
    )
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.status is ShiftStatus.IMPROVING
    assert result.delta == pytest.approx(0.25)


def test_delta_just_below_threshold_is_stable():
    observations = batch(1, 5, days_ago=3, score=0.34) + batch(
        100, 5, days_ago=10, score=0.10
    )
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.status is ShiftStatus.STABLE
    assert result.delta == pytest.approx(0.24)


def test_negative_delta_is_deteriorating():
    observations = batch(1, 5, days_ago=3, score=-0.5) + batch(
        100, 5, days_ago=10, score=0.0
    )
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.status is ShiftStatus.DETERIORATING
    assert result.delta == pytest.approx(-0.5)


def test_custom_rules_are_respected():
    rules = ShiftRules(window_days=3, min_articles_per_window=2, shift_threshold=0.5)
    observations = (
        batch(1, 2, days_ago=1, score=0.6)  # current: [-3d, now)
        + batch(10, 2, days_ago=4, score=0.0)  # previous: [-6d, -3d)
        + batch(20, 3, days_ago=8, score=-1.0)  # outside both windows
    )
    result = detect_sentiment_shift(1, observations, as_of=AS_OF, rules=rules)
    assert result.status is ShiftStatus.IMPROVING
    assert result.current.article_count == 2
    assert result.previous.article_count == 2
    assert result.rules is rules


# --------------------------------------------------------------------------
# Eligibility
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        {"score": math.nan, "label": "neutral"},
        {"score": 1.5, "label": "positive"},
        {"score": -1.01, "label": "negative"},
        {"score": True, "label": "positive"},
        {"score": 0.4, "label": "bullish"},
    ],
)
def test_invalid_scores_and_labels_are_excluded(bad):
    observation = make_obs(1, days_ago=2, **bad)
    result = detect_sentiment_shift(1, [observation], as_of=AS_OF)
    assert result.ineligible_count == 1
    assert result.current.article_count == 0


def test_scores_at_scale_limits_are_accepted():
    observations = [
        make_obs(1, days_ago=2, score=1.0),
        make_obs(2, days_ago=2, score=-1.0),
    ]
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.ineligible_count == 0
    assert result.current.article_count == 2
    assert result.current.mean_score == pytest.approx(0.0)


def test_label_counts_and_mean_are_reported():
    observations = [
        make_obs(1, days_ago=1, score=0.5),
        make_obs(2, days_ago=1, score=0.3),
        make_obs(3, days_ago=1, score=0.0),
        make_obs(4, days_ago=1, score=-0.4),
        make_obs(5, days_ago=1, score=-0.4),
    ]
    stats = detect_sentiment_shift(1, observations, as_of=AS_OF).current
    assert (stats.positive_count, stats.neutral_count, stats.negative_count) == (2, 1, 2)
    assert stats.article_count == 5
    assert stats.mean_score == pytest.approx(0.0)


def test_other_companies_are_ignored_by_single_company_detection():
    observations = batch(1, 5, days_ago=3, score=0.9, company_id=2)
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.current.article_count == 0


# --------------------------------------------------------------------------
# Collapsing multiple sentiment records per article-company pair
# --------------------------------------------------------------------------


def test_collapse_prefers_latest_created_at():
    older = make_obs(1, score=-0.9, created_at=AS_OF - timedelta(days=5), analysis_id=7)
    newer = make_obs(1, score=0.8, created_at=AS_OF - timedelta(days=1), analysis_id=3)
    collapsed = collapse_latest_observations([newer, older])
    assert [o.score for o in collapsed] == [0.8]


def test_collapse_breaks_created_at_ties_by_analysis_id():
    created = AS_OF - timedelta(days=1)
    low = make_obs(1, score=0.1, created_at=created, analysis_id=5)
    high = make_obs(1, score=-0.7, created_at=created, analysis_id=9)
    assert collapse_latest_observations([low, high])[0].analysis_id == 9
    assert collapse_latest_observations([high, low])[0].analysis_id == 9


def test_collapse_missing_created_at_loses_to_dated_record():
    undated = make_obs(1, score=0.9, created_at=None, analysis_id=99)
    dated = make_obs(1, score=-0.3, created_at=AS_OF - timedelta(days=30), analysis_id=1)
    assert collapse_latest_observations([undated, dated])[0].score == -0.3


def test_collapse_is_deterministic_on_full_ties():
    a = make_obs(1, score=0.2, created_at=AS_OF, analysis_id=None)
    b = make_obs(1, score=-0.4, created_at=AS_OF, analysis_id=None)
    assert collapse_latest_observations([a, b]) == collapse_latest_observations([b, a])


def test_collapse_keeps_separate_companies_for_the_same_article():
    first = make_obs(1, company_id=1, score=0.5)
    second = make_obs(1, company_id=2, score=-0.5)
    collapsed = collapse_latest_observations([second, first])
    assert [(o.company_id, o.article_id) for o in collapsed] == [(1, 1), (2, 1)]


def test_detection_counts_each_article_once_using_latest_record():
    observations = []
    for article_id in range(1, 6):
        observations.append(
            make_obs(
                article_id,
                days_ago=2,
                score=-0.9,
                created_at=AS_OF - timedelta(days=4),
                analysis_id=article_id,
            )
        )
        observations.append(
            make_obs(
                article_id,
                days_ago=2,
                score=0.5,
                created_at=AS_OF - timedelta(days=1),
                analysis_id=100 + article_id,
            )
        )
    observations += batch(50, 5, days_ago=10, score=0.0)
    result = detect_sentiment_shift(1, observations, as_of=AS_OF)
    assert result.current.article_count == 5
    assert result.current.mean_score == pytest.approx(0.5)
    assert result.status is ShiftStatus.IMPROVING


def test_result_does_not_depend_on_input_order():
    observations = (
        batch(1, 5, days_ago=3, score=0.45)
        + batch(10, 5, days_ago=10, score=0.05)
        + [make_obs(99, published_at=None)]
    )
    forward = detect_sentiment_shift(1, observations, as_of=AS_OF)
    backward = detect_sentiment_shift(1, list(reversed(observations)), as_of=AS_OF)
    assert forward == backward


# --------------------------------------------------------------------------
# Multi-company detection
# --------------------------------------------------------------------------


def test_detect_shifts_covers_every_requested_company_once():
    observations = (
        batch(1, 5, days_ago=3, score=0.6, company_id=1)
        + batch(20, 5, days_ago=10, score=0.0, company_id=1)
        + batch(40, 5, days_ago=3, score=0.9, company_id=9)  # not requested
    )
    results = detect_shifts([1, 2, 2, 3], observations, as_of=AS_OF)
    assert list(results) == [1, 2, 3]
    assert results[1].status is ShiftStatus.IMPROVING
    for company_id in (2, 3):
        assert results[company_id].status is ShiftStatus.INSUFFICIENT_DATA
        assert results[company_id].current.article_count == 0
        assert results[company_id].current.mean_score is None


def test_detect_shifts_matches_single_company_detection():
    observations = batch(1, 5, days_ago=3, score=-0.4, company_id=4) + batch(
        20, 6, days_ago=9, score=0.1, company_id=4
    )
    assert detect_shifts([4], observations, as_of=AS_OF)[4] == detect_sentiment_shift(
        4, observations, as_of=AS_OF
    )