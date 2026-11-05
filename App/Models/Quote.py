"""Quote: the price and delivery time offered for an order request."""
import uuid
from datetime import date, timedelta
from pydantic import BaseModel, Field

from Models.Delivery import Delivery


class Quote(BaseModel):
    """The delivery fee and estimated time offered for an order request."""

    # Associate quote with an order request
    request_id: str = Field(min_length=1)

    delivery_fee: float = Field(ge=1, le=100000)

    # Number of days the delivery is estimated to take
    estimated_delivery_time: int = Field(ge=1, le=30)

    expiry_date: date = Field(
        default_factory=lambda: date.today() + timedelta(days=30)
    )
    status: str = "pending"

    quote_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )

    # Responsibilities of quote

    def is_valid(self):
        """Return True until the quote's expiry date has passed."""
        return date.today() <= self.expiry_date

    def _check_pending(self):
        """Raise ValueError if the quote has already been answered."""
        # Stop the same quote being answered twice (e.g. double click or refresh)
        if self.status != "pending":
            raise ValueError(f"This quote has already been {self.status}")

    def accept(self, order_request):
        """Accept the quote, update the order request and return the new delivery."""
        # Accepting commits the order, so it creates the delivery linked to the order request
        self._check_pending()
        if not self.is_valid():
            raise ValueError("This quote has expired")
        # The delivery date is counted from the day the quote is accepted
        delivery_date = date.today() + timedelta(days=self.estimated_delivery_time)
        delivery = Delivery(self.request_id, delivery_date.isoformat())
        self.status = "accepted"
        order_request.status = "accepted"
        return delivery

    def deny(self):
        """Mark the quote as denied."""
        # The quote is kept with a denied status, not removed
        self._check_pending()
        self.status = "denied"
