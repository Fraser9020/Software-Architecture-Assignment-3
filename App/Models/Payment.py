"""Payment: one payment attempt made at pickup."""
import uuid
from datetime import datetime


class Payment:
    """One attempt to pay an invoice."""

    def __init__(self, invoice_id, amount, method, staff_id):
        """Create a pending payment attempt."""
        self.payment_id = str(uuid.uuid4())
        self.invoice_id = invoice_id
        self.amount = amount
        self.method = method
        self.staff_id = staff_id  # employee who collected the payment
        self.attempted_at = datetime.now()
        self.outcome = "pending"  # becomes "success" or "failed"

    def authorize(self, amount_due):
        """The payment is accepted only if it matches the amount due."""
        return round(self.amount, 2) == round(amount_due, 2)

    def record_outcome(self, success):
        """Record whether the payment succeeded."""
        self.outcome = "success" if success else "failed"
