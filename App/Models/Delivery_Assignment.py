"""Delivery Assignment: links one delivery to one delivery staff member.

NOTE: stand-in for Sam's staff allocation code (test data only).
"""
import uuid
from datetime import datetime


class DeliveryAssignment:
    def __init__(self, delivery_id, staff_id):
        self.assignment_id = str(uuid.uuid4())
        self.delivery_id = delivery_id
        self.staff_id = staff_id
        self.assigned_at = datetime.now()
        self.active = True

    def is_assigned_to(self, staff_id):
        """True if this assignment is active and belongs to this employee."""
        return self.active and self.staff_id == staff_id

    def release(self):
        self.active = False
