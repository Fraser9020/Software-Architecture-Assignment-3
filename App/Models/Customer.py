"""Customer: the person making an order request."""
import uuid
from pydantic import BaseModel, EmailStr, Field


class Customer(BaseModel):
    """A customer's validated contact details."""

    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: EmailStr
    phone: str = Field(pattern=r"^\d{10}$")

    customer_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
