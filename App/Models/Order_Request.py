import uuid
from datetime import datetime 


class OrderRequest: 

    #Attributes of order request
    def __init__(self, customer_id,number_of_parcels=0,submittedAt=None, status=None, ): 
        
        self.customer_id = customer_id # Associate the order request with a customer
        self.number_of_parcels = number_of_parcels 
        self.request_id = str(uuid.uuid4())
        self.submittedAt = submittedAt if submittedAt is not None else datetime.now()
        self.status = status if status is not None else "pending"
         
        

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
        return cls(customer_id, number_of_parcels=int(number_of_parcels))


    #Responsibilities of order request


    

    #Responsibilities of order request 

