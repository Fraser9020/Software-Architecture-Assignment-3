import uuid
from datetime import date, timedelta 
from pydantic import BaseModel, Field

class Quote(BaseModel):

   
    # Associate quote with an order request
    request_id: str = Field(min_length=1)

    deliveryfee: float = Field(ge=1, le=100000)

   
    estimateddeliverytime: str = Field(min_length=1)

    
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

    def accept_quote(self):
        if not self.Is_Valid():
            return False
        self.status = "accepted"
        return True



