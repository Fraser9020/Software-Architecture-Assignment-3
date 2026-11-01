import uuid

from Dataholders.Time_Window import TimeWindow


class Delivery:
    """A committed delivery created when a quote is accepted.

    Status flow (A2 §5.2): accepted -> allocated -> picked up -> in transit
    -> delivered. Allocation may only happen while the delivery is in one
    of ALLOCATABLE.
    """

    ALLOCATABLE = ("accepted", "allocation required")

    def __init__(self, request_id, delivery_date, delivery_status="accepted"):
        self.request_id = request_id  # Associate the delivery with an order request
        self.delivery_date = delivery_date
        self.delivery_status = delivery_status
        self.delivery_id = str(uuid.uuid4())
        self.pickup_window: TimeWindow | None = None   # set at allocation
        self.assignments = []                           # history, one current

    def __str__(self):
        return (f"Delivery ID: {self.delivery_id}, Request ID: {self.request_id}, "
                f"Delivery Date: {self.delivery_date}, "
                f"Delivery Status: {self.delivery_status}")

    # -- used by the staff allocation area (Sam) ---------------------------

    @property
    def status(self):
        return self.delivery_status

    @status.setter
    def status(self, value):
        self.delivery_status = value

    def scheduled_window(self):
        return self.pickup_window

    def current_assignment(self):
        for assignment in self.assignments:
            if assignment.is_current():
                return assignment
        return None

    def set_assignment(self, assignment):
        if self.delivery_status not in self.ALLOCATABLE:
            raise ValueError(
                f"Delivery {self.delivery_id[:8]} is not awaiting allocation "
                f"(status: {self.delivery_status}).")
        self.assignments.append(assignment)
        self.pickup_window = assignment.window
        self.delivery_status = "allocated"

    def schedule_delivery(self, status, delivery_date, request_id):
        # Logic to schedule a delivery for the given order
        pass

    def complete_delivery(self, delivery_id):
        # Logic to mark the delivery as completed
        pass
