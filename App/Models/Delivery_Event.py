"""Delivery Event: one thing that happened to a delivery."""
import uuid
from datetime import datetime


class DeliveryEvent:
    """One thing that happened to a delivery."""

    def __init__(self, event_type, details):
        """Create an event timestamped now."""
        self.event_id = str(uuid.uuid4())
        self.occurred_at = datetime.now()
        self.event_type = event_type
        self.details = details

    def record(self):
        """Return the event as a line of text."""
        return f"{self.occurred_at:%d/%m/%Y %H:%M} - {self.event_type}: {self.details}"
