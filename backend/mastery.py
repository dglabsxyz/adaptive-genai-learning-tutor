"""Mastery transition policy and review cadence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

MASTERY_BANDS = [
    ("mastered", 0.88, "0.88 or higher", 21),
    ("proficient", 0.68, "0.68 to 0.87", 7),
    ("developing", 0.28, "0.28 to 0.67", 3),
    ("exposure", 0.0, "below 0.28", 1),
]

REVIEW_STATUS_DAYS = 1


def status_for_score(score: float) -> str:
    for status, threshold, _label, _days in MASTERY_BANDS:
        if score >= threshold:
            return status
    return "exposure"


def band_label(status: str) -> str:
    for item_status, _threshold, label, _days in MASTERY_BANDS:
        if item_status == status:
            return label
    if status == "review":
        return "review date reached"
    return "current band"


def review_days(status: str) -> int:
    if status == "review":
        return REVIEW_STATUS_DAYS
    for item_status, _threshold, _label, days in MASTERY_BANDS:
        if item_status == status:
            return days
    return 3


def next_review_date(status: str) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=review_days(status))).date().isoformat()
