import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from Models.Parcel import Parcel
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
    status: Literal["pending", "quoted", "accepted"] = "pending"

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
