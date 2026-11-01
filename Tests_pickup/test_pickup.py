"""Tests for pickup and payment. Run from the repository folder:  pytest Tests_pickup"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "App"))

import pytest

import pickup_data
from app import app
from pickup_logic import confirm_pickup
from pickup_routes import pickup_bp

app.register_blueprint(pickup_bp)


@pytest.fixture(autouse=True)
def fresh_data():
    """Empty everything, then load the two test deliveries again."""
    from app import deliveries, quotes
    for store in (deliveries, quotes, pickup_data.staff_members, pickup_data.assignments,
                  pickup_data.invoices, pickup_data.histories):
        store.clear()
    pickup_data.load_test_data()


def first_delivery():
    from app import deliveries
    delivery = list(deliveries.values())[0]
    staff_id = pickup_data.assignments[delivery.delivery_id].staff_id
    return delivery, staff_id


def test_wrong_amount_is_rejected_and_delivery_stays_assigned():
    delivery, staff_id = first_delivery()
    ok, messages = confirm_pickup(delivery, staff_id, "Good", "40", "Cash", True)
    assert not ok and "rejected" in messages[0]
    assert delivery.delivery_status == "Assigned"
    assert pickup_data.get_history(delivery).failed_attempts() == 1


def test_correct_amount_marks_picked_up():
    delivery, staff_id = first_delivery()
    confirm_pickup(delivery, staff_id, "Good", "40", "Cash", True)
    ok, messages = confirm_pickup(delivery, staff_id, "Good", "45", "Cash", True)
    assert ok and delivery.delivery_status == "Picked Up"
    assert pickup_data.get_invoice(delivery).status == "paid"
    assert len(pickup_data.get_invoice(delivery).payments) == 2


def test_cannot_pick_up_twice():
    delivery, staff_id = first_delivery()
    confirm_pickup(delivery, staff_id, "Good", "45", "Card", True)
    ok, messages = confirm_pickup(delivery, staff_id, "Good", "45", "Card", True)
    assert not ok and "already" in messages[0]


def test_other_employee_is_refused():
    delivery, staff_id = first_delivery()
    other = [s for s in pickup_data.staff_members if s != staff_id][0]
    ok, messages = confirm_pickup(delivery, other, "Good", "45", "Cash", True)
    assert not ok and "assigned employee" in messages[0]


@pytest.mark.parametrize("condition, amount, method, parcels_ok", [
    ("", "45", "Cash", True),
    ("Good", "abc", "Cash", True),
    ("Good", "-5", "Cash", True),
    ("Good", "45", "", True),
    ("Good", "45", "Cash", False),
])
def test_bad_input_changes_nothing(condition, amount, method, parcels_ok):
    delivery, staff_id = first_delivery()
    ok, messages = confirm_pickup(delivery, staff_id, condition, amount, method, parcels_ok)
    assert not ok and messages
    assert delivery.delivery_status == "Assigned"
    assert pickup_data.get_invoice(delivery).payments == []


def test_unassigned_delivery_cannot_be_picked_up():
    from app import deliveries
    delivery = list(deliveries.values())[1]
    staff_id = list(pickup_data.staff_members)[0]
    ok, messages = confirm_pickup(delivery, staff_id, "Good", "30", "Cash", True)
    assert not ok and "no employee" in messages[0]


def test_pages_work_end_to_end():
    client = app.test_client()
    delivery, staff_id = first_delivery()
    assert client.get(f"/pickup?staff_id={staff_id}").status_code == 200
    assert client.get(f"/pickup/{delivery.delivery_id}?staff_id={staff_id}").status_code == 200
    data = {"staff_id": staff_id, "condition": "Good", "amount": "40", "method": "Cash", "parcels_ok": "yes"}
    page = client.post(f"/pickup/{delivery.delivery_id}", data=data)
    assert b"rejected" in page.data
    data["amount"] = "45"
    page = client.post(f"/pickup/{delivery.delivery_id}", data=data)
    assert b"Payment processed" in page.data
