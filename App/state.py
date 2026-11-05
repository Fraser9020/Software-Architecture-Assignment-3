"""In-memory stores shared by app.py and the area blueprints."""

customers = {}       # customer_id -> Customer
order_requests = {}  # request_id  -> OrderRequest
quotes = {}          # quote_id    -> Quote
deliveries = {}      # delivery_id -> Delivery
staff = {}           # staff_id    -> OfficeStaff | DeliveryStaff
history = []         # (delivery_id, event, by, note)


class DeliveryHistory:
    """Minimal event log until the Delivery History class is built."""

    @staticmethod
    def record(delivery_id, event, by, note=""):
        """Add an event to the shared history."""
        history.append((delivery_id, event, by, note))
