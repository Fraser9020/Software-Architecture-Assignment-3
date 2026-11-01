"""TimeWindow data-holder: a date with a start and end time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class TimeWindow:
    """A single contiguous block of time on one day."""

    day: date
    start: time
    end: time

    def is_valid(self) -> bool:
        """End must be after start."""
        return self.end > self.start

    def overlaps(self, other: TimeWindow) -> bool:
        """True if the two windows share any time on the same day."""
        if self.day != other.day:
            return False
        return self.start < other.end and other.start < self.end

    def contains(self, other: TimeWindow) -> bool:
        """True if *other* fits entirely inside this window."""
        return (
            self.day == other.day
            and self.start <= other.start
            and other.end <= self.end
        )

    def __str__(self) -> str:
        return f"{self.day} {self.start:%H:%M}-{self.end:%H:%M}"
