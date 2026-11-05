import uuid
from pydantic import BaseModel, EmailStr, Field


class Customer(BaseModel):

    firstname: str = Field(min_length=1)
    lastname: str = Field(min_length=1)
    email: EmailStr
    phone:  str = Field(pattern=r"^\d{10}$")

    customer_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )