"""Delivery Event: one thing that happened to a delivery."""
import uuid
from datetime import datetime


class DeliveryEvent:
    def __init__(self, event_type, details):
        self.event_id = str(uuid.uuid4())
        self.occurred_at = datetime.now()
        self.event_type = event_type
        self.details = details

    def record(self):
        return f"{self.occurred_at:%d/%m/%Y %H:%M} - {self.event_type}: {self.details}"
