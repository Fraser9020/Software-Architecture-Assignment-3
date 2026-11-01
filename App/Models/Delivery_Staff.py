"""Delivery Staff: an employee who collects parcels.

NOTE: this is a small stand-in so the pickup and payment area can be
tested. Sam's staff code can replace it later (same attribute names).
"""
import uuid


class DeliveryStaff:
    def __init__(self, name, employee_number):
        self.staff_id = str(uuid.uuid4())
        self.name = name
        self.employee_number = employee_number
