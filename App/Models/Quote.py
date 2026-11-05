import uuid
from datetime import date, timedelta 
from pydantic import BaseModel, Field

from Models.Delivery import Delivery


class Quote(BaseModel):

   
    # Associate quote with an order request
    request_id: str = Field(min_length=1)

    deliveryfee: float = Field(ge=1, le=100000)

   
    # Number of days the delivery is estimated to take
    estimateddeliverytime: int = Field(ge=1, le=30)

    
    expiredate: date = Field(
        default_factory=lambda: date.today() + timedelta(days=30)
    )
    status: str = "pending"

    quoteid: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )


    # Responsibilities of quote

    def Is_Valid(self):
        return date.today() <= self.expiredate

    def _check_pending(self):
        # Stop the same quote being answered twice (e.g. double click or refresh)
        if self.status != "pending":
            raise ValueError(f"This quote has already been {self.status}")

    def _checkquothasnotexpired(self):
        if not self.Is_Valid():
            raise ValueError("This quote has expired")

    def accept(self, order_request):
        # Accepting commits the order, so it creates the delivery linked to the order request
        self._check_pending()
        if not self.Is_Valid():
            raise ValueError("This quote has expired")
        # The delivery date is counted from the day the quote is accepted
        delivery_date = date.today() + timedelta(days=self.estimateddeliverytime)
        delivery = Delivery(self.request_id, delivery_date.isoformat())
        self.status = "accepted"
        order_request.status = "accepted"
        return delivery

    def deny(self):
        # The quote is kept with a denied status, not removed
        self._check_pending()
        self.status = "denied"

