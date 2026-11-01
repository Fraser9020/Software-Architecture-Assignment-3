"""Delivery History: the list of events for one delivery."""
import uuid

from Models.Delivery_Event import DeliveryEvent


class DeliveryHistory:
    def __init__(self, delivery_id):
        self.history_id = str(uuid.uuid4())
        self.delivery_id = delivery_id
        self.events = []

    def record_event(self, event_type, details):
        self.events.append(DeliveryEvent(event_type, details))

    def failed_attempts(self):
        """How many payment attempts were rejected."""
        return len([e for e in self.events if e.event_type == "Payment failed"])
