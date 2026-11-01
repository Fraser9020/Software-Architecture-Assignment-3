"""Compatibility import: DeliveryStaff lives in Models/Staff.py (subclass of Staff).

Kept so code that imports Models.Delivery_Staff (pickup area) keeps working.
"""

from Models.Staff import DeliveryStaff  # noqa: F401
