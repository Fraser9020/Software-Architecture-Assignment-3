"""Route-level tests for the staff allocation area: validation messages."""

from datetime import date, timedelta

import pytest

import state
from Models.Delivery import Delivery

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


@pytest.fixture
def client():
    import app as flask_app
    for store in (state.staff, state.deliveries, state.quotes,
                  state.order_requests, state.customers):
        store.clear()
    state.history.clear()
    from allocation import seed_staff
    seed_staff()
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


def follow(client, response):
    """Follow the redirect and return the final page text."""
    assert response.status_code == 302
    return client.get(response.headers["Location"]).get_data(as_text=True)


def test_home_links_to_allocation(client):
    page = client.get("/").get_data(as_text=True)
    assert "/allocate" in page and "/availability" in page


def test_create_staff_blank_name_rejected(client):
    page = follow(client, client.post("/staff/create", data={
        "role": "delivery", "staff_id": "S003", "name": "  ", "phone": "04"}))
    assert "Error: Name cannot be blank." in page
    assert "S003" not in state.staff


def test_create_staff_duplicate_id_rejected(client):
    page = follow(client, client.post("/staff/create", data={
        "role": "delivery", "staff_id": "S001", "name": "Dup", "phone": "04"}))
    assert "already exists" in page


def test_create_staff_success(client):
    page = follow(client, client.post("/staff/create", data={
        "role": "office", "staff_id": "O002", "name": "Priya", "phone": "0400000004"}))
    assert "Created O002 Priya (OfficeStaff, active)" in page


def test_availability_end_before_start_rejected(client):
    page = follow(client, client.post("/availability/add", data={
        "staff_id": "S002", "date": TOMORROW, "start": "15:00", "end": "09:00"}))
    assert "Error: End time must be after start time." in page


def test_availability_past_date_rejected(client):
    page = follow(client, client.post("/availability/add", data={
        "staff_id": "S002", "date": YESTERDAY, "start": "09:00", "end": "10:00"}))
    assert "Date must be today or later." in page


def test_availability_bad_date_format_rejected(client):
    page = follow(client, client.post("/availability/add", data={
        "staff_id": "S002", "date": "5/11/2026", "start": "09:00", "end": "10:00"}))
    assert "YYYY-MM-DD" in page


def test_availability_overlap_rejected(client):
    page = follow(client, client.post("/availability/add", data={
        "staff_id": "S001", "date": TOMORROW, "start": "16:00", "end": "18:00"}))
    assert "Overlaps existing window" in page


def test_availability_success(client):
    page = follow(client, client.post("/availability/add", data={
        "staff_id": "S002", "date": TOMORROW, "start": "08:00", "end": "12:00"}))
    assert "Sam Glasser is available" in page


def _delivery():
    d = Delivery("REQ-1", "2026-11-05")
    state.deliveries[d.delivery_id] = d
    return d


def test_allocate_lists_only_free_staff(client):
    d = _delivery()
    page = client.post("/allocate/free", data={
        "office_id": "O001", "delivery_id": d.delivery_id,
        "date": TOMORROW, "start": "10:00", "end": "12:00"}).get_data(as_text=True)
    assert "S001 Jess Lee" in page
    assert "S002 Sam Glasser" not in page     # no availability declared


def test_allocate_no_free_staff_message(client):
    d = _delivery()
    page = client.post("/allocate/free", data={
        "office_id": "O001", "delivery_id": d.delivery_id,
        "date": TOMORROW, "start": "18:00", "end": "20:00"}).get_data(as_text=True)
    assert "No delivery staff are free" in page


def test_allocate_confirm_success_and_history(client):
    d = _delivery()
    page = follow(client, client.post("/allocate/confirm", data={
        "office_id": "O001", "delivery_id": d.delivery_id, "staff_id": "S001",
        "date": TOMORROW, "start": "10:00", "end": "12:00"}))
    assert "Allocated delivery" in page and "Jess Lee" in page
    assert d.delivery_status == "Assigned"
    assert d.current_assignment().is_assigned_to("S001")
    assert state.history[-1][1] == "Assigned"


def test_double_booking_rejected(client):
    d1, d2 = _delivery(), _delivery()
    data = {"office_id": "O001", "staff_id": "S001",
            "date": TOMORROW, "start": "10:00", "end": "12:00"}
    follow(client, client.post("/allocate/confirm",
                               data={**data, "delivery_id": d1.delivery_id}))
    page = follow(client, client.post("/allocate/confirm",
                                      data={**data, "delivery_id": d2.delivery_id}))
    assert "Error: S001 is not free for" in page
    assert d2.current_assignment() is None


def test_reallocate_change_of_mind(client):
    d = _delivery()
    follow(client, client.post("/availability/add", data={
        "staff_id": "S002", "date": TOMORROW, "start": "08:00", "end": "18:00"}))
    follow(client, client.post("/allocate/confirm", data={
        "office_id": "O001", "delivery_id": d.delivery_id, "staff_id": "S001",
        "date": TOMORROW, "start": "10:00", "end": "12:00"}))
    page = follow(client, client.post("/allocate/reallocate", data={
        "office_id": "O001", "delivery_id": d.delivery_id,
        "staff_id": "S002", "reason": "Jess called in sick"}))
    assert "Reallocated delivery" in page and "Sam Glasser" in page
    assert d.current_assignment().staff_id == "S002"
    assert len(d.assignments) == 2                         # old one kept
    assert d.assignments[0].withdrawn_reason == "Jess called in sick"
    assert state.staff["S001"].availability.is_free(
        d.assignments[1].window)                           # Jess's time released


def test_reallocate_requires_reason(client):
    d = _delivery()
    follow(client, client.post("/allocate/confirm", data={
        "office_id": "O001", "delivery_id": d.delivery_id, "staff_id": "S001",
        "date": TOMORROW, "start": "10:00", "end": "12:00"}))
    page = follow(client, client.post("/allocate/reallocate", data={
        "office_id": "O001", "delivery_id": d.delivery_id, "staff_id": "S002", "reason": ""}))
    assert "A reason is required" in page
    assert d.current_assignment().staff_id == "S001"       # unchanged


def test_deactivated_staff_lose_future_availability_and_cannot_be_allocated(client):
    d = _delivery()
    follow(client, client.post("/staff/deactivate", data={"staff_id": "S001"}))
    assert state.staff["S001"].availability.windows == []
    page = follow(client, client.post("/allocate/confirm", data={
        "office_id": "O001", "delivery_id": d.delivery_id, "staff_id": "S001",
        "date": TOMORROW, "start": "10:00", "end": "12:00"}))
    assert "inactive" in page
