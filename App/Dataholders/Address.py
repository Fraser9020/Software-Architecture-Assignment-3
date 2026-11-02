from typing import Optional
from pydantic import BaseModel, Field
class Delivery_Address(BaseModel):

    # Set after the order request is created, so it can be empty while validating
    order_id: Optional[str] = None
    street: str = Field(min_length=3, pattern=r"^[a-zA-Z0-9\s,.'/-]+$")
    suburb: str = Field(min_length=2, pattern=r"^[a-zA-Z\s'-]+$")
    postcode: str = Field(pattern=r"^\d{4}$")


    def pickup_address(self):
        # Logic to retrieve the pickup address for the delivery
        pass

    def delivery_address(self):
        # Logic to retrieve the delivery address for the delivery
        pass

#GET
#POST
#DELETE
