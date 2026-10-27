"""Shared helpers for the college -> discipline option hierarchy."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def group_disciplines_by_college(teachers: Iterable) -> dict[str, list[str]]:
    """Return ``{college: [discipline, ...]}`` from teacher records.

    The UI uses this mapping to keep the discipline selector dependent on the
    selected college, so a user cannot combine a college with a discipline that
    does not belong to it.
    """
    grouped: dict[str, set[str]] = defaultdict(set)
    for teacher in teachers:
        college = getattr(teacher, "college", None)
        discipline = getattr(teacher, "discipline", None)
        if college and discipline:
            grouped[college].add(discipline)
    return {
        college: sorted(disciplines)
        for college, disciplines in sorted(grouped.items())
    }
