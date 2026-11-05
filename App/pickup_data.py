"""Storage for the pickup and payment area.

Deliveries, quotes and staff come from state.py (shared with the other
areas). Only invoices and pickup histories are kept here.
"""
from Models.Delivery_History import DeliveryHistory
from Models.Invoice import Invoice
from state import quotes

invoices = {}   # delivery_id -> Invoice
histories = {}  # delivery_id -> DeliveryHistory


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
            invoice = Invoice(delivery.delivery_id, quote.delivery_fee)
            invoices[delivery.delivery_id] = invoice
            return invoice
    return None
