"""Delivery: the committed job created when a quote is accepted."""
import uuid
from typing import ClassVar, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from Dataholders.Time_Window import TimeWindow


class Delivery(BaseModel):
    """A committed delivery created when a quote is accepted.

    Status flow (A2 §5.2): accepted -> Assigned -> picked up -> in transit
    -> delivered. Allocation may only happen while the delivery is in one
    of ALLOCATABLE.
    """

    # TimeWindow is a dataclass, and status changes later in the flow should be checked too
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    ALLOCATABLE: ClassVar[tuple] = ("accepted", "allocation required")   # compared lower-case
    STATUSES: ClassVar[tuple] = ALLOCATABLE + ("assigned", "picked up", "in transit", "delivered")

    request_id: str = Field(min_length=1)  # Associate the delivery with an order request
    delivery_date: str = Field(min_length=1)
    delivery_status: str = "accepted"
    delivery_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    pickup_window: Optional[TimeWindow] = None   # set at allocation
    assignments: list = Field(default_factory=list)   # history, one current

    def __init__(self, request_id, delivery_date, delivery_status="accepted", **data):
        """Keep Delivery(request_id, delivery_date, status) working for existing callers."""
        super().__init__(request_id=request_id, delivery_date=delivery_date,
                         delivery_status=delivery_status, **data)

    @field_validator("delivery_status")
    @classmethod
    def check_status(cls, value):
        """Reject a status that isn't in STATUSES."""
        # Areas use different casing ("Assigned", "picked up"), so compare lower-case
        if value.lower() not in cls.STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(cls.STATUSES)}")
        return value

    def __str__(self):
        return (f"Delivery ID: {self.delivery_id}, Request ID: {self.request_id}, "
                f"Delivery Date: {self.delivery_date}, "
                f"Delivery Status: {self.delivery_status}")

    # -- used by the staff allocation area (Sam) ---------------------------

    @property
    def status(self):
        """Return the delivery status."""
        return self.delivery_status

    @status.setter
    def status(self, value):
        """Set the delivery status."""
        self.delivery_status = value

    def scheduled_window(self):
        """Return the pickup window, or None before allocation."""
        return self.pickup_window

    def current_assignment(self):
        """Return the current assignment, or None if there isn't one."""
        for assignment in self.assignments:
            if assignment.is_current():
                return assignment
        return None

    def set_assignment(self, assignment):
        """Add an assignment and mark the delivery Assigned. Raises ValueError."""
        awaiting = self.delivery_status.lower() in self.ALLOCATABLE
        # after a withdrawal (reallocation) an Assigned delivery has no current assignment
        reallocating = (self.delivery_status == "Assigned"
                        and self.current_assignment() is None)
        if not (awaiting or reallocating):
            raise ValueError(
                f"Delivery {self.delivery_id[:8]} is not awaiting allocation "
                f"(status: {self.delivery_status}).")
        self.assignments.append(assignment)
        self.pickup_window = assignment.window
        self.delivery_status = "Assigned"
