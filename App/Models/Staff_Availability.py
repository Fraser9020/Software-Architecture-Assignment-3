"""StaffAvailability: when a delivery staff member can work, and what is reserved."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from Dataholders.Time_Window import TimeWindow


@dataclass
class AvailabilityWindow:
    """A declared window and, if reserved, the assignment holding it."""

    window: TimeWindow
    reserved_by: str | None = None


@dataclass
class StaffAvailability:
    """Single source of truth for whether one staff member is free."""

    staff_id: str
    windows: list[AvailabilityWindow] = field(default_factory=list)

    # -- declaring availability -------------------------------------------

    def add_window(self, window: TimeWindow) -> None:
        """Validate and add a declared window."""
        self._validate_window(window)
        self.windows.append(AvailabilityWindow(window))

    def remove_window(self, window: TimeWindow) -> None:
        """Remove an unreserved window. Raises ValueError if reserved or missing."""
        for entry in self.windows:
            if entry.window == window:
                if entry.reserved_by is not None:
                    raise ValueError(
                        f"Window {window} is reserved by assignment "
                        f"{entry.reserved_by} and cannot be removed.")
                self.windows.remove(entry)
                return
        raise ValueError(f"Window {window} not found for {self.staff_id}.")

    def withdraw_future(self, from_date: date) -> None:
        """On deactivation: drop unreserved windows on or after from_date."""
        self.windows = [
            e for e in self.windows
            if e.window.day < from_date or e.reserved_by is not None
        ]

    # -- answering and reserving ------------------------------------------

    def is_free(self, window: TimeWindow) -> bool:
        """Free = some unreserved declared window fully contains *window*."""
        return self._find_free(window) is not None

    def reserve(self, window: TimeWindow, assignment_id: str) -> None:
        """Reserve a free window for an assignment. Raises ValueError if none is free."""
        entry = self._find_free(window)
        if entry is None:
            raise ValueError(f"{self.staff_id} is not free for {window}.")
        entry.reserved_by = assignment_id

    def release(self, assignment_id: str) -> None:
        """Free the window held by an assignment, if there is one."""
        for entry in self.windows:
            if entry.reserved_by == assignment_id:
                entry.reserved_by = None
                return
        # Nothing reserved under that id: releasing is idempotent.

    # -- helpers ------------------------------------------------------------

    def _find_free(self, window: TimeWindow) -> AvailabilityWindow | None:
        """Return the unreserved window containing *window*, or None."""
        for entry in self.windows:
            if entry.reserved_by is None and entry.window.contains(window):
                return entry
        return None

    def _validate_window(self, window: TimeWindow) -> None:
        """Raise ValueError if the window is invalid, past or overlapping."""
        if not window.is_valid():
            raise ValueError("End time must be after start time.")
        if window.day < date.today():
            raise ValueError("Date must be today or later.")
        for entry in self.windows:
            if entry.window.overlaps(window):
                raise ValueError(f"Overlaps existing window {entry.window}.")
