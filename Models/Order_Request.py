class OrderRequest: 

    #Attributes of order request
    def __init__(self, order_id, customer_id, status):
        self.order_id = order_id
        self.customer_id = customer_id
        self.status = status

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "items": self.items
        } 

    #Responsibilities of order request 

    