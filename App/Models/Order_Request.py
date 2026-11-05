"""OrderRequest: a customer's request to have parcels delivered."""
import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from Models.Parcel import Parcel
from Models.Quote import Quote
from Dataholders.Address import DeliveryAddress


class OrderRequest(BaseModel):
    """A customer's request to have parcels delivered."""

    # Parcel is a plain class, and status changes later in the flow should be checked too
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    # Associate the order request with a customer
    customer_id: str = Field(min_length=1)
    number_of_parcels: int = Field(ge=1, le=50)

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    submitted_at: datetime = Field(default_factory=datetime.now)
    # draft: the customer can still change or delete it. pending: sent, waiting for a quote
    status: Literal["draft", "pending", "quoted", "accepted"] = "draft"

    # Set after the order request is created, once parcels and addresses are validated
    parcels: list[Parcel] = Field(default_factory=list)
    pickup_address: Optional[DeliveryAddress] = None
    delivery_address: Optional[DeliveryAddress] = None

    def to_dict(self):
        """Return the main order request details as a dictionary."""
        return {
            "request_id": self.request_id,
            "submitted_at": self.submitted_at,
            "status": self.status,
            "number_of_parcels": self.number_of_parcels,
            "customer_id": self.customer_id
        }

    @classmethod
    def create(cls, customer_id, number_of_parcels):
        """Create an order request: create(customer_id, number_of_parcels=...)."""
        return cls(customer_id=customer_id, number_of_parcels=number_of_parcels)

    # Responsibilities of order request

    def check_can_change(self):
        """Raise ValueError once the order request has been sent."""
        # Once it is sent it is sent
        if self.status != "draft":
            raise ValueError("This order request has been sent and can no longer be changed.")

    def update_details(self, parcels, pickup_address, delivery_address):
        """Replace the parcels and addresses while the order request is a draft."""
        self.check_can_change()
        # Set first because it is validated, so a bad count leaves the order unchanged
        self.number_of_parcels = len(parcels)
        self.parcels = parcels
        pickup_address.order_id = self.request_id
        self.pickup_address = pickup_address
        delivery_address.order_id = self.request_id
        self.delivery_address = delivery_address

    def send(self):
        """Send the order request so it can no longer be changed."""
        self.check_can_change()
        self.status = "pending"

    def request_quote(self, delivery_fee, estimated_delivery_time):
        """Create the quote for a pending order request and mark it quoted."""
        if self.status != "pending":
            raise ValueError("Quote can only be created for pending order requests.")
        # Build the quote first so an invalid fee leaves the order pending and can be retried
        quote = Quote(
            request_id=self.request_id,
            delivery_fee=delivery_fee,
            estimated_delivery_time=estimated_delivery_time,
        )
        self.status = "quoted"
        return quote
