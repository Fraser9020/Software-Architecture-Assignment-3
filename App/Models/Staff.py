"""Staff classes: abstract Staff with OfficeStaff and DeliveryStaff subclasses."""

from __future__ import annotations

from abc import ABC
from datetime import date

from Models.Staff_Availability import StaffAvailability
from Dataholders.Time_Window import TimeWindow


class Staff(ABC):
    """Common staff record. Deactivated staff are kept, never deleted."""

    def __init__(self, staff_id: str, name: str, phone: str,
                 start_date: date | None = None) -> None:
        if not staff_id.strip():
            raise ValueError("Staff ID cannot be blank.")
        if not name.strip():
            raise ValueError("Name cannot be blank.")
        if not phone.strip():
            raise ValueError("Phone cannot be blank.")
        self.staff_id = staff_id
        self.name = name
        self.phone = phone
        self.start_date = start_date or date.today()
        self.end_date: date | None = None

    @property
    def role(self) -> str:
        return type(self).__name__

    def is_active(self) -> bool:
        return self.end_date is None

    def deactivate(self, end_date: date | None = None) -> None:
        if not self.is_active():
            raise ValueError(f"{self.staff_id} is already inactive.")
        self.end_date = end_date or date.today()

    def __str__(self) -> str:
        state = "active" if self.is_active() else f"inactive from {self.end_date}"
        return f"{self.staff_id} {self.name} ({self.role}, {state})"


class OfficeStaff(Staff):
    """Prepares quotes and allocates delivery staff to deliveries."""

    def allocate(self, delivery, staff: DeliveryStaff, window: TimeWindow,
                 history=None):
        """Create and activate an assignment. Raises ValueError if not possible."""
        from Models.Delivery_Assignment import DeliveryAssignment  # avoid cycle

        assignment = DeliveryAssignment(
            delivery_id=delivery.delivery_id,
            staff_id=staff.staff_id,
            assigned_by=self.staff_id,
            window=window,
        )
        assignment.activate(staff)
        delivery.set_assignment(assignment)
        if history is not None:
            history.record(delivery.delivery_id, "Assigned",
                           self.staff_id, f"to {staff.staff_id} for {window}")
        return assignment

    def reallocate(self, delivery, new_staff: DeliveryStaff, reason: str,
                   staff_lookup, history=None):
        """Withdraw the current assignment and allocate a new one."""
        if not reason.strip():
            raise ValueError("A reason is required to reallocate.")
        current = delivery.current_assignment()
        if current is None:
            raise ValueError(
                f"Delivery {delivery.delivery_id} has no current assignment.")
        old_staff = staff_lookup(current.staff_id)
        # Check the new employee first, so a failed reallocation changes nothing
        if not new_staff.is_active():
            raise ValueError(f"{new_staff.staff_id} is inactive and cannot be assigned.")
        if not new_staff.availability.is_free(current.window):
            raise ValueError(f"{new_staff.staff_id} is not free for {current.window}.")
        current.withdraw(reason, old_staff.availability)
        if history is not None:
            history.record(delivery.delivery_id, "Assignment withdrawn",
                           self.staff_id, reason)
        return self.allocate(delivery, new_staff, current.window, history)


class DeliveryStaff(Staff):
    """Picks up and delivers parcels; owns their own availability."""

    def __init__(self, staff_id: str, name: str, phone: str,
                 start_date: date | None = None,
                 employee_number: str | None = None) -> None:
        super().__init__(staff_id, name, phone, start_date)
        self.employee_number = employee_number or staff_id
        self.availability = StaffAvailability(staff_id)

    def declare_availability(self, window: TimeWindow) -> None:
        self.availability.add_window(window)

    def remove_availability(self, window: TimeWindow) -> None:
        self.availability.remove_window(window)

    def deactivate(self, end_date: date | None = None) -> None:
        super().deactivate(end_date)
        self.availability.withdraw_future(self.end_date)
