"""DeliveryAssignment: one delivery, one staff member, one pickup window."""

from __future__ import annotations

import itertools
from datetime import datetime
from enum import Enum

from Models.Staff_Availability import StaffAvailability
from Dataholders.Time_Window import TimeWindow


class AssignmentStatus(Enum):
    PENDING = "Pending"
    ACTIVE = "Active"
    WITHDRAWN = "Withdrawn"
    COMPLETED = "Completed"


_ids = itertools.count(1)


class DeliveryAssignment:
    """Validates the allocation, reserves the staff member's time, keeps history."""

    def __init__(self, delivery_id: str, staff_id: str, assigned_by: str,
                 window: TimeWindow) -> None:
        self.assignment_id = f"A{next(_ids):03d}"
        self.delivery_id = delivery_id
        self.staff_id = staff_id
        self.assigned_by = assigned_by
        self.window = window
        self.status = AssignmentStatus.PENDING
        self.created_at = datetime.now()
        self.withdrawn_reason: str | None = None

    # -- lifecycle ----------------------------------------------------------

    def activate(self, staff) -> None:
        """Check staff is active and free, then reserve. Raises ValueError."""
        if staff.staff_id != self.staff_id:
            raise ValueError("Staff member does not match this assignment.")
        if not staff.is_active():
            raise ValueError(f"{staff.staff_id} is inactive and cannot be assigned.")
        if not staff.availability.is_free(self.window):
            raise ValueError(f"{staff.staff_id} is not free for {self.window}.")
        staff.availability.reserve(self.window, self.assignment_id)
        self.status = AssignmentStatus.ACTIVE

    def withdraw(self, reason: str, availability: StaffAvailability) -> None:
        if self.status is not AssignmentStatus.ACTIVE:
            raise ValueError(f"Assignment {self.assignment_id} is not active.")
        availability.release(self.assignment_id)
        self.status = AssignmentStatus.WITHDRAWN
        self.withdrawn_reason = reason

    def complete(self, availability: StaffAvailability) -> None:
        if self.status is not AssignmentStatus.ACTIVE:
            raise ValueError(f"Assignment {self.assignment_id} is not active.")
        availability.release(self.assignment_id)
        self.status = AssignmentStatus.COMPLETED

    # -- queries ------------------------------------------------------------

    def is_current(self) -> bool:
        return self.status is AssignmentStatus.ACTIVE

    def is_assigned_to(self, staff_id: str) -> bool:
        """Used by pickup/handover to confirm the reporting driver."""
        return self.is_current() and self.staff_id == staff_id

    def __str__(self) -> str:
        return (f"{self.assignment_id}: delivery {self.delivery_id} -> "
                f"{self.staff_id} for {self.window} [{self.status.value}]")
