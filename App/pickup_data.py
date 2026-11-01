"""Storage and test data for the pickup and payment area.

Everything is kept in dictionaries, the same way app.py does it.
Fraser's `deliveries` and `quotes` dictionaries are reused, not copied.
"""
from app import deliveries, quotes
from Models.Delivery import Delivery
from Models.Delivery_Assignment import DeliveryAssignment
from Models.Delivery_History import DeliveryHistory
from Models.Delivery_Staff import DeliveryStaff
from Models.Invoice import Invoice
from Models.Quote import Quote

staff_members = {}  # staff_id    -> DeliveryStaff
assignments = {}    # delivery_id -> DeliveryAssignment
invoices = {}       # delivery_id -> Invoice
histories = {}      # delivery_id -> DeliveryHistory


def get_history(delivery):
    """Return the history of a delivery, creating it the first time."""
    if delivery.delivery_id not in histories:
        histories[delivery.delivery_id] = DeliveryHistory(delivery.delivery_id)
    return histories[delivery.delivery_id]


def get_invoice(delivery):
    """Return the invoice of a delivery, creating it from the quote fee.

    Returns None if there is no accepted quote for the delivery.
    """
    if delivery.delivery_id in invoices:
        return invoices[delivery.delivery_id]
    for quote in quotes.values():
        if quote.request_id == delivery.request_id and quote.status == "accepted":
            invoice = Invoice(delivery.delivery_id, quote.deliveryfee)
            invoices[delivery.delivery_id] = invoice
            return invoice
    return None


def assign_staff(delivery, staff_id):
    """Test-data stand-in for staff allocation (Sam's area)."""
    assignments[delivery.delivery_id] = DeliveryAssignment(delivery.delivery_id, staff_id)
    delivery.delivery_status = "Assigned"
    get_history(delivery).record_event("Assigned", f"Employee {staff_members[staff_id].name}")


def load_test_data():
    """Two employees and two accepted deliveries ($45 fee) ready for pickup."""
    alex = DeliveryStaff("Alex Taylor", "E001")
    sam = DeliveryStaff("Sam Lee", "E002")
    staff_members[alex.staff_id] = alex
    staff_members[sam.staff_id] = sam

    for number, fee in (("T1", 45.0), ("T2", 30.0)):
        request_id = f"test-request-{number}"
        quote = Quote(request_id, fee, "2026-11-10", status="accepted")
        quotes[quote.quoteid] = quote
        delivery = Delivery(request_id, "2026-11-10")
        deliveries[delivery.delivery_id] = delivery
    # only the first test delivery is assigned (to Alex); the second is not
    first = list(deliveries.values())[0]
    assign_staff(first, alex.staff_id)
