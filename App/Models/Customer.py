import uuid


class Customer:
    # Attributes of customer
    def __init__(self, firstname, lastname, email, phone, ):
        self.firstname = firstname
        self.lastname = lastname
        self.email = email
        self.phone = phone


        # generate customer id using uuid4
        self.customer_id = str(uuid.uuid4())

  

    def accept_quote(self, order):
        # Logic to accept an order
        pass
