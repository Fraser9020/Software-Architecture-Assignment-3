"""Invoice: the delivery fee that must be paid at pickup."""
import uuid
from datetime import datetime

from Models.Payment import Payment


class Invoice:
    """The fee owed for a delivery and the attempts to pay it."""

    def __init__(self, delivery_id, amount_due):
        """Create a payable invoice for the delivery."""
        self.invoice_id = str(uuid.uuid4())
        self.delivery_id = delivery_id
        self.amount_due = amount_due
        self.issued_at = datetime.now()
        self.status = "payable"  # "payable" until paid, then "paid"
        self.payments = []  # every attempt, failed ones too

    def mark_payable(self):
        """Mark the invoice as payable."""
        self.status = "payable"

    def close(self):
        """Mark the invoice as paid."""
        self.status = "paid"

    def create_payment(self, amount, method, staff_id):
        """Create a Payment for this invoice and check it.

        Returns the Payment. The invoice is closed only if it succeeded.
        """
        payment = Payment(self.invoice_id, amount, method, staff_id)
        success = payment.authorize(self.amount_due)
        payment.record_outcome(success)
        self.payments.append(payment)
        if success:
            self.close()
        return payment
