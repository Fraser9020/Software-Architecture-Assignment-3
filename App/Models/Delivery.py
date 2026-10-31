import uuid


class Delivery:

    def __init__(self, request_id, delivery_date, delivery_status="being delivered"):
        self.request_id = request_id # Associate the delivery with an order request
        self.delivery_date = delivery_date
        self.delivery_status = delivery_status
        self.delivery_id = str(uuid.uuid4())

    def __str__(self):
        return f"Delivery ID: {self.delivery_id}, Request ID: {self.request_id}, Delivery Date: {self.delivery_date}, Delivery Status: {self.delivery_status}"

    def schedule_delivery(self, status , delivery_date, request_id):
        # Logic to schedule a delivery for the given order
        pass

    def complete_delivery(self, delivery_id):
        # Logic to mark the delivery as completed
        pass
