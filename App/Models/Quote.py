import uuid
from datetime import date, timedelta

class Quote:

    # Attributes
    def __init__(self, request_id, deliveryfee, estimateddeliverytime, status="pending"):
       
        self.request_id = request_id # Associate the quote with an order request
        self.deliveryfee = deliveryfee
        self.estimateddeliverytime = estimateddeliverytime
        self.expiredate = date.today()+ timedelta(days=30)
        self.status = status 
        self.quoteid = str(uuid.uuid4())

    # Responsibilities of quote

    def Is_Valid(self):
        # Logic to check if the quote is still valid
        pass



    def accept_quote(self):
        # Logic to accept the quote
        pass


