import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from Models.Parcel import Parcel
from Models.Quote import Quote
from Dataholders.Address import Delivery_Address


class OrderRequest(BaseModel):

    # Parcel is a plain class, and status changes later in the flow should be checked too
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    # Associate the order request with a customer
    customer_id: str = Field(min_length=1)
    number_of_parcels: int = Field(ge=1, le=50)

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    submittedAt: datetime = Field(default_factory=datetime.now)
    # draft: the customer can still change or delete it. pending: sent, waiting for a quote
    status: Literal["draft", "pending", "quoted", "accepted"] = "draft"

    # Set after the order request is created, once parcels and addresses are validated
    parcels: list[Parcel] = Field(default_factory=list)
    pickup_address: Optional[Delivery_Address] = None
    delivery_address: Optional[Delivery_Address] = None


    def to_dict(self):
        return {
            "request_id": self.request_id,
            "submittedAt": self.submittedAt,
            "status": self.status,
            "number_of_parcels": self.number_of_parcels,
            "customer_id": self.customer_id
        }

    @classmethod
    def create(cls, customer_id, number_of_parcels):
        # Usage: OrderRequest.create(customer_id, number_of_parcels=...)
        return cls(customer_id=customer_id, number_of_parcels=number_of_parcels)


    #Responsibilities of order request
    def check_can_change(self):
        # Once it is sent it is sent
        if self.status != "draft":
            raise ValueError("This order request has been sent and can no longer be changed.")

    def update_details(self, parcels, pickup_address, delivery_address):
        self.check_can_change()
        # Set first because it is validated, so a bad count leaves the order unchanged
        self.number_of_parcels = len(parcels)
        self.parcels = parcels
        pickup_address.order_id = self.request_id
        self.pickup_address = pickup_address
        delivery_address.order_id = self.request_id
        self.delivery_address = delivery_address

    def send(self):
        self.check_can_change()
        self.status = "pending"

    def request_quote(self, deliveryfee, estimateddeliverytime):
        if self.status != "pending":
            raise ValueError("Quote can only be created for pending order requests.")
        # Build the quote first so an invalid fee leaves the order pending and can be retried
        quote = Quote(request_id=self.request_id, deliveryfee=deliveryfee, estimateddeliverytime=estimateddeliverytime)
        self.status = "quoted"
        return quote
