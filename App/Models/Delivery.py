class Delivery: 

    def __init__(self, delivery_id, status, delivery_date, delivery_status):
        self.delivery_id = delivery_id
        self.status = status 
        self.delivery_date = delivery_date
        self.delivery_status = delivery_status

    def __str__(self):
        return f"Delivery ID: {self.delivery_id}, Status: {self.status}, Delivery Date: {self.delivery_date}, Delivery Status: {self.delivery_status}"

    def schedule_delivery(self, status , delivery_date, request_id):
        # Logic to schedule a delivery for the given order
        pass

    def complete_delivery(self, delivery_id):
        # Logic to mark the delivery as completed
        pass