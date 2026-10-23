"""Pure sentiment-shift detection.

Compares the mean sentiment score of a company's articles in the latest window
with the immediately preceding window. This module deliberately has no
database, web-framework or NLP imports: callers load persisted sentiment
records, convert them to :class:`SentimentObservation`, and pass them in.

Conventions
-----------
* Windows are assigned by the article's ``published_at`` (never by the time the
  sentiment analysis was created).
* Windows are half-open: current = ``[as_of - N days, as_of)`` and
  previous = ``[as_of - 2N days, as_of - N days)``. An article is therefore
  counted in at most one window. An article published exactly at ``as_of`` is
  eligible but falls in neither window.
* Datetimes are normalised to naive UTC. Naive inputs are assumed to already be
  UTC (the application stores naive ``DateTime`` columns).
* Scores use the persisted scale: signed floats in ``[-1.0, 1.0]``.
* Several sentiment records for the same (article, company) pair collapse to
  the most recent one, with a deterministic tie-breaker.
* A detected shift is a measured difference in mean score. It makes no claim
  about causes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable, Sequence

__all__ = [
    "ALLOWED_LABELS",
    "DEFAULT_SHIFT_RULES",
    "SentimentObservation",
    "SentimentShiftResult",
    "ShiftRules",
    "ShiftStatus",
    "ShiftWindows",
    "WindowStats",
    "collapse_latest_observations",
    "compute_windows",
    "detect_sentiment_shift",
    "detect_shifts",
]

ALLOWED_LABELS = frozenset({"positive", "neutral", "negative"})

# Absorbs binary floating-point error when comparing |delta| to the threshold
# (for example 0.35 - 0.10 evaluates to 0.24999999999999997).
_TOLERANCE = 1e-9

_MIN_DATETIME = datetime.min


@dataclass(frozen=True)
class ShiftRules:
    """Centralised, immutable shift-detection rules."""

    window_days: int = 7
    min_articles_per_window: int = 5
    shift_threshold: float = 0.25

    def __post_init__(self) -> None:
        if not isinstance(self.window_days, int) or isinstance(self.window_days, bool):
            raise ValueError("window_days must be an integer")
        if self.window_days < 1:
            raise ValueError("window_days must be at least 1")
        if (
            not isinstance(self.min_articles_per_window, int)
            or isinstance(self.min_articles_per_window, bool)
        ):
            raise ValueError("min_articles_per_window must be an integer")
        if self.min_articles_per_window < 1:
            raise ValueError("min_articles_per_window must be at least 1")
        if (
            isinstance(self.shift_threshold, bool)
            or not isinstance(self.shift_threshold, (int, float))
            or not math.isfinite(self.shift_threshold)
            or self.shift_threshold <= 0
        ):
            raise ValueError("shift_threshold must be a positive finite number")


DEFAULT_SHIFT_RULES = ShiftRules()


class ShiftStatus(str, Enum):
    """Outcome of comparing the current window with the previous one."""

    INSUFFICIENT_DATA = "insufficient_data"
    STABLE = "stable"
    IMPROVING = "improving"
    DETERIORATING = "deteriorating"


@dataclass(frozen=True)
class SentimentObservation:
    """One persisted sentiment record joined with its article's publish time."""

    article_id: int
    company_id: int
    published_at: datetime | None
    label: str
    score: float
    analysis_created_at: datetime | None = None
    analysis_id: int | None = None


@dataclass(frozen=True)
class ShiftWindows:
    """Window boundaries as naive UTC datetimes."""

    previous_start: datetime
    current_start: datetime
    as_of: datetime


@dataclass(frozen=True)
class WindowStats:
    """Measured values for one window (bounds are naive UTC)."""

    start: datetime
    end: datetime
    article_count: int
    mean_score: float | None
    positive_count: int
    neutral_count: int
    negative_count: int


@dataclass(frozen=True)
class SentimentShiftResult:
    """Shift outcome for one company.

    ``delta`` is ``current.mean_score - previous.mean_score`` and is ``None``
    when either window has fewer than ``rules.min_articles_per_window``
    eligible articles. ``ineligible_count`` counts collapsed article-company
    records dropped for a missing or future ``published_at``, an unknown label,
    or an invalid score.
    """

    company_id: int
    status: ShiftStatus
    current: WindowStats
    previous: WindowStats
    delta: float | None
    rules: ShiftRules
    ineligible_count: int


def _normalize_datetime(value: datetime) -> datetime:
    """Return a naive UTC datetime (naive input is assumed to be UTC)."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _is_valid_score(score: object) -> bool:
    return (
        isinstance(score, (int, float))
        and not isinstance(score, bool)
        and math.isfinite(score)
        and -1.0 <= score <= 1.0
    )


def _recency_key(obs: SentimentObservation) -> tuple:
    """Sort key: latest analysis wins; ties fall back to id, then values."""
    created = (
        _normalize_datetime(obs.analysis_created_at)
        if obs.analysis_created_at is not None
        else _MIN_DATETIME
    )
    analysis_id = obs.analysis_id if obs.analysis_id is not None else -1
    score = float(obs.score) if _is_valid_score(obs.score) else 0.0
    return (created, analysis_id, score, str(obs.label))


def collapse_latest_observations(
    observations: Iterable[SentimentObservation],
) -> list[SentimentObservation]:
    """Keep one record per (article_id, company_id): the most recent analysis.

    Recency is ``analysis_created_at`` (missing sorts oldest), then
    ``analysis_id`` (missing sorts lowest), then score and label, so the result
    does not depend on input order. Output is sorted by (company_id, article_id).
    """
    latest: dict[tuple[int, int], SentimentObservation] = {}
    for obs in observations:
        key = (obs.company_id, obs.article_id)
        current = latest.get(key)
        if current is None or _recency_key(obs) > _recency_key(current):
            latest[key] = obs
    return [latest[key] for key in sorted(latest)]


def compute_windows(
    as_of: datetime, rules: ShiftRules = DEFAULT_SHIFT_RULES
) -> ShiftWindows:
    """Return the half-open window boundaries for ``as_of``."""
    as_of_utc = _normalize_datetime(as_of)
    span = timedelta(days=rules.window_days)
    return ShiftWindows(
        previous_start=as_of_utc - 2 * span,
        current_start=as_of_utc - span,
        as_of=as_of_utc,
    )


def _build_window_stats(
    start: datetime, end: datetime, items: Sequence[SentimentObservation]
) -> WindowStats:
    count = len(items)
    mean = math.fsum(float(o.score) for o in items) / count if count else None
    return WindowStats(
        start=start,
        end=end,
        article_count=count,
        mean_score=mean,
        positive_count=sum(1 for o in items if o.label == "positive"),
        neutral_count=sum(1 for o in items if o.label == "neutral"),
        negative_count=sum(1 for o in items if o.label == "negative"),
    )


def _detect_for_company(
    company_id: int,
    company_observations: Sequence[SentimentObservation],
    windows: ShiftWindows,
    rules: ShiftRules,
) -> SentimentShiftResult:
    current_items: list[SentimentObservation] = []
    previous_items: list[SentimentObservation] = []
    ineligible = 0

    for obs in collapse_latest_observations(company_observations):
        if obs.published_at is None:
            ineligible += 1
            continue
        published = _normalize_datetime(obs.published_at)
        if published > windows.as_of:
            ineligible += 1
            continue
        if obs.label not in ALLOWED_LABELS or not _is_valid_score(obs.score):
            ineligible += 1
            continue
        if windows.current_start <= published < windows.as_of:
            current_items.append(obs)
        elif windows.previous_start <= published < windows.current_start:
            previous_items.append(obs)

    current = _build_window_stats(windows.current_start, windows.as_of, current_items)
    previous = _build_window_stats(
        windows.previous_start, windows.current_start, previous_items
    )

    enough_data = (
        current.article_count >= rules.min_articles_per_window
        and previous.article_count >= rules.min_articles_per_window
    )
    if not enough_data:
        status = ShiftStatus.INSUFFICIENT_DATA
        delta = None
    else:
        delta = current.mean_score - previous.mean_score  # type: ignore[operator]
        if abs(delta) >= rules.shift_threshold - _TOLERANCE:
            status = (
                ShiftStatus.IMPROVING if delta > 0 else ShiftStatus.DETERIORATING
            )
        else:
            status = ShiftStatus.STABLE

    return SentimentShiftResult(
        company_id=company_id,
        status=status,
        current=current,
        previous=previous,
        delta=delta,
        rules=rules,
        ineligible_count=ineligible,
    )


def detect_sentiment_shift(
    company_id: int,
    observations: Iterable[SentimentObservation],
    *,
    as_of: datetime,
    rules: ShiftRules = DEFAULT_SHIFT_RULES,
) -> SentimentShiftResult:
    """Detect a sentiment shift for one company.

    Observations belonging to other companies are ignored.
    """
    windows = compute_windows(as_of, rules)
    company_observations = [o for o in observations if o.company_id == company_id]
    return _detect_for_company(company_id, company_observations, windows, rules)


def detect_shifts(
    company_ids: Iterable[int],
    observations: Iterable[SentimentObservation],
    *,
    as_of: datetime,
    rules: ShiftRules = DEFAULT_SHIFT_RULES,
) -> dict[int, SentimentShiftResult]:
    """Detect shifts for several companies in one pass.

    Every requested company gets a result (``insufficient_data`` when it has no
    observations). Duplicate ids are collapsed; observations for companies that
    were not requested are ignored. Result order follows first request order.
    """
    windows = compute_windows(as_of, rules)
    requested = list(dict.fromkeys(company_ids))
    wanted = set(requested)

    grouped: dict[int, list[SentimentObservation]] = {cid: [] for cid in requested}
    for obs in observations:
        if obs.company_id in wanted:
            grouped[obs.company_id].append(obs)

    return {
        cid: _detect_for_company(cid, grouped[cid], windows, rules)
        for cid in requested
    }