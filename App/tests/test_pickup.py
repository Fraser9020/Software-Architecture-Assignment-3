"""Tests for the pickup and payment area."""

from datetime import date, time, timedelta

import pytest

import pickup_data
import state
from Dataholders.Time_Window import TimeWindow
from Models.Delivery import Delivery
from Models.Quote import Quote
from pickup_logic import confirm_pickup

DAY = date.today() + timedelta(days=1)


def make_delivery(office, driver, fee, number):
    """An accepted quote and a delivery, allocated to the driver."""
    request_id = f"request-{number}"
    quote = Quote(request_id=request_id, delivery_fee=fee,
                  estimated_delivery_time=5, status="accepted")
    state.quotes[quote.quote_id] = quote
    delivery = Delivery(request_id, "2026-11-10")
    state.deliveries[delivery.delivery_id] = delivery
    return delivery


@pytest.fixture
def setup():
    """Seeded staff, one allocated $45 delivery and one unallocated $30 delivery."""
    import app as flask_app
    from allocation import seed_staff
    for store in (state.staff, state.deliveries, state.quotes, state.order_requests,
                  state.customers, pickup_data.invoices, pickup_data.histories):
        store.clear()
    state.history.clear()
    seed_staff()
    office = state.staff["O001"]
    driver = state.staff["S001"]
    allocated = make_delivery(office, driver, 45.0, 1)
    office.allocate(allocated, driver, TimeWindow(DAY, time(10), time(12)), state.DeliveryHistory)
    unallocated = make_delivery(office, driver, 30.0, 2)
    flask_app.app.config["TESTING"] = True
    return allocated, unallocated, driver, flask_app.app.test_client()


def test_wrong_amount_is_rejected_and_delivery_stays_assigned(setup):
    delivery, _, driver, _ = setup
    ok, messages = confirm_pickup(delivery, driver.staff_id, "Good", "40", "Cash", True)
    assert not ok and "rejected" in messages[0]
    assert delivery.delivery_status == "Assigned"
    assert pickup_data.get_history(delivery).failed_attempts() == 1


def test_correct_amount_marks_picked_up(setup):
    delivery, _, driver, _ = setup
    confirm_pickup(delivery, driver.staff_id, "Good", "40", "Cash", True)
    ok, _ = confirm_pickup(delivery, driver.staff_id, "Good", "45", "Cash", True)
    assert ok and delivery.delivery_status == "Picked Up"
    invoice = pickup_data.get_invoice(delivery)
    assert invoice.status == "paid" and len(invoice.payments) == 2


def test_pickup_events_appear_on_shared_history(setup):
    delivery, _, driver, _ = setup
    confirm_pickup(delivery, driver.staff_id, "Good", "45", "Cash", True)
    events = [row[1] for row in state.history if row[0] == delivery.delivery_id]
    assert "Payment processed" in events and "Picked Up" in events


def test_cannot_pick_up_twice(setup):
    delivery, _, driver, _ = setup
    confirm_pickup(delivery, driver.staff_id, "Good", "45", "Card", True)
    ok, messages = confirm_pickup(delivery, driver.staff_id, "Good", "45", "Card", True)
    assert not ok and "already" in messages[0]


def test_other_employee_is_refused(setup):
    delivery, _, _, _ = setup
    ok, messages = confirm_pickup(delivery, "S002", "Good", "45", "Cash", True)
    assert not ok and "assigned employee" in messages[0]


@pytest.mark.parametrize("condition, amount, method, parcels_ok", [
    ("", "45", "Cash", True),
    ("Good", "abc", "Cash", True),
    ("Good", "-5", "Cash", True),
    ("Good", "45", "", True),
    ("Good", "45", "Cash", False),
])
def test_bad_input_changes_nothing(setup, condition, amount, method, parcels_ok):
    delivery, _, driver, _ = setup
    ok, messages = confirm_pickup(delivery, driver.staff_id, condition, amount, method, parcels_ok)
    assert not ok and messages
    assert delivery.delivery_status == "Assigned"
    assert pickup_data.get_invoice(delivery).payments == []


def test_unallocated_delivery_cannot_be_picked_up(setup):
    _, unallocated, driver, _ = setup
    ok, messages = confirm_pickup(unallocated, driver.staff_id, "Good", "30", "Cash", True)
    assert not ok and "no employee" in messages[0]


def test_pages_work_end_to_end(setup):
    delivery, _, driver, client = setup
    assert b"Record pickup" in client.get(f"/pickup?staff_id={driver.staff_id}").data
    url = f"/pickup/{delivery.delivery_id}?staff_id={driver.staff_id}"
    assert client.get(url).status_code == 200
    data = {"staff_id": driver.staff_id, "condition": "Good", "amount": "40",
            "method": "Cash", "parcels_ok": "yes"}
    assert b"rejected" in client.post(f"/pickup/{delivery.delivery_id}", data=data).data
    data["amount"] = "45"
    assert b"Payment processed" in client.post(f"/pickup/{delivery.delivery_id}", data=data).data


def test_pickup_completes_assignment_so_it_cannot_be_reallocated(setup):
    delivery, _, driver, client = setup
    confirm_pickup(delivery, driver.staff_id, "Good", "45", "Cash", True)
    assert delivery.current_assignment() is None   # assignment is Completed
    assert driver.availability.windows[0].reserved_by is None   # driver's time is free
    client.post("/allocate/reallocate", data={"office_id": "O001", "staff_id": "S002",
                                              "delivery_id": delivery.delivery_id,
                                              "reason": "sick"})
    assert delivery.delivery_status == "Picked Up"


def test_inactive_employee_cannot_record_pickup(setup):
    delivery, _, driver, _ = setup
    driver.deactivate()
    ok, messages = confirm_pickup(delivery, driver.staff_id, "Good", "45", "Cash", True)
    assert not ok and "no longer active" in messages[0]
    assert delivery.delivery_status == "Assigned"
