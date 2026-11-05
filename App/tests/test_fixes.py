"""Tests for the fixes after merging: reallocation and parcel checks."""

from datetime import date, time, timedelta

import pytest

import state
from Dataholders.Time_Window import TimeWindow

TOMORROW = date.today() + timedelta(days=1)
GOOD_ORDER = {
    "first_name": "Ann", "last_name": "Lee", "email": "ann@example.com", "phone": "0412345678",
    "parcel_weight": ["2"], "dimensions": ["10x10x10"], "parcel_fragile": ["false"],
    "pickup_street": "1 Main St", "pickup_suburb": "Richmond", "pickup_postcode": "3121",
    "delivery_street": "2 High St", "delivery_suburb": "Hawthorn", "delivery_postcode": "3122",
}


@pytest.fixture
def client():
    """A test client with empty stores and the seed staff."""
    import app as flask_app
    from allocation import seed_staff
    stores = (state.staff, state.deliveries, state.quotes, state.order_requests, state.customers)
    for store in stores:
        store.clear()
    state.history.clear()
    seed_staff()
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


def find_staff(staff_id):
    """Look up a staff member in the shared store."""
    return state.staff[staff_id]


def make_order(client):
    """Create an order and send it, so it is ready for a quote."""
    client.post("/submit_order", data=GOOD_ORDER)
    request_id = list(state.order_requests)[-1]
    client.post("/verify_order_request", data={"request_id": request_id})
    return request_id


def quote_form(request_id, fee="45", days="5"):
    """Form data for the submit_quote route."""
    return {"request_id": request_id, "delivery_fee": fee, "estimated_delivery_time": days}


# -- reallocation ------------------------------------------------------------

def allocated_delivery(client):
    """An accepted delivery allocated to S001 tomorrow 10:00-12:00."""
    request_id = make_order(client)
    client.post("/submit_quote", data=quote_form(request_id))
    client.post("/accept_quote", data={"quote_id": list(state.quotes)[0]})
    delivery = list(state.deliveries.values())[0]
    window = TimeWindow(TOMORROW, time(10), time(12))
    state.staff["O001"].allocate(delivery, state.staff["S001"], window, state.DeliveryHistory)
    return delivery, window


def test_reallocation_works_on_an_assigned_delivery(client):
    delivery, window = allocated_delivery(client)
    state.staff["S002"].declare_availability(TimeWindow(TOMORROW, time(9), time(17)))
    state.staff["O001"].reallocate(delivery, state.staff["S002"], "Driver sick",
                                   find_staff, state.DeliveryHistory)
    assert delivery.current_assignment().staff_id == "S002"
    assert delivery.delivery_status == "Assigned"


def test_failed_reallocation_keeps_the_old_assignment(client):
    delivery, window = allocated_delivery(client)
    # S002 has no availability, so reallocating to S002 must fail and change nothing
    with pytest.raises(ValueError):
        state.staff["O001"].reallocate(delivery, state.staff["S002"], "Driver sick",
                                       find_staff, state.DeliveryHistory)
    assert delivery.current_assignment().staff_id == "S001"


# -- parcel checks -------------------------------------------------------------

@pytest.mark.parametrize("weight", ["-5", "0", "abc", ""])
def test_bad_parcel_weight_is_rejected(client, weight):
    page = client.post("/submit_order", data=dict(GOOD_ORDER, parcel_weight=[weight]))
    assert b"parcel 1 weight" in page.data
    assert state.order_requests == {}


def test_order_without_parcels_is_rejected(client):
    order = dict(GOOD_ORDER, parcel_weight=[], dimensions=[], parcel_fragile=[])
    page = client.post("/submit_order", data=order)
    assert state.order_requests == {}
