"""Tests for the staff allocation area (A1 tasks T5, T6)."""

from datetime import date, time, timedelta

import pytest

from Models.Delivery_Assignment import AssignmentStatus
from Models.Delivery import Delivery
from state import DeliveryHistory
from Models.Staff import DeliveryStaff, OfficeStaff
from Dataholders.Time_Window import TimeWindow

TOMORROW = date.today() + timedelta(days=1)


def win(start: int, end: int, day: date = TOMORROW) -> TimeWindow:
    return TimeWindow(day, time(start), time(end))


@pytest.fixture
def office():
    return OfficeStaff("O001", "Alex", "0400000001")


@pytest.fixture
def driver():
    d = DeliveryStaff("S001", "Jess", "0400000002")
    d.declare_availability(win(9, 17))
    return d


# -- staff records ---------------------------------------------------------

def test_blank_name_rejected():
    with pytest.raises(ValueError, match="Name cannot be blank"):
        DeliveryStaff("S009", "  ", "0400")


def test_deactivate_withdraws_future_availability(driver):
    driver.deactivate()
    assert not driver.is_active()
    assert driver.availability.windows == []


# -- availability (T5) -----------------------------------------------------

def test_end_before_start_rejected(driver):
    with pytest.raises(ValueError, match="End time must be after start"):
        driver.declare_availability(win(12, 9))


def test_past_date_rejected(driver):
    with pytest.raises(ValueError, match="today or later"):
        driver.declare_availability(win(9, 10, date.today() - timedelta(days=1)))


def test_overlapping_window_rejected(driver):
    with pytest.raises(ValueError, match="Overlaps existing window"):
        driver.declare_availability(win(16, 18))


def test_is_free_inside_declared_window(driver):
    assert driver.availability.is_free(win(10, 12))
    assert not driver.availability.is_free(win(16, 19))


# -- allocation (T6) -------------------------------------------------------

def test_allocate_reserves_time_and_updates_delivery(office, driver):
    delivery = Delivery("R-D001", "2026-11-05")
    from state import history as history_log
    a = office.allocate(delivery, driver, win(10, 12), DeliveryHistory)
    assert a.status is AssignmentStatus.ACTIVE
    assert delivery.status == "Assigned"
    assert delivery.current_assignment() is a
    assert not driver.availability.is_free(win(10, 12))  # reserved
    assert history_log[-1][1] == "Assigned"


def test_double_booking_prevented(office, driver):
    office.allocate(Delivery("R-D001", "2026-11-05"), driver, win(10, 12))
    with pytest.raises(ValueError, match="not free"):
        office.allocate(Delivery("R-D002", "2026-11-05"), driver, win(11, 13))


def test_inactive_staff_cannot_be_allocated(office, driver):
    driver.deactivate()
    with pytest.raises(ValueError, match="inactive"):
        office.allocate(Delivery("R-D001", "2026-11-05"), driver, win(10, 12))


def test_delivery_not_awaiting_allocation(office, driver):
    delivery = Delivery("R001", "2026-11-05", "picked up")
    with pytest.raises(ValueError, match="not awaiting allocation"):
        office.allocate(delivery, driver, win(10, 12))


def test_reserved_window_cannot_be_removed(office, driver):
    office.allocate(Delivery("R-D001", "2026-11-05"), driver, win(10, 12))
    with pytest.raises(ValueError, match="reserved by assignment"):
        driver.remove_availability(win(9, 17))


def test_is_assigned_to_for_pickup_check(office, driver):
    a = office.allocate(Delivery("R-D001", "2026-11-05"), driver, win(10, 12))
    assert a.is_assigned_to("S001")
    assert not a.is_assigned_to("S002")


# -- reallocation ("change of mind") ------------------------------------

def test_reallocate_withdraws_old_and_frees_time(office, driver):
    other = DeliveryStaff("S002", "Sam", "0400000003")
    other.declare_availability(win(8, 18))
    delivery = Delivery("R-D001", "2026-11-05")
    delivery.status = "accepted"
    old = office.allocate(delivery, driver, win(10, 12))
    delivery.status = "allocation required"  # office flags it for reallocation
    staff = {"S001": driver, "S002": other}
    new = office.reallocate(delivery, other, "Driver sick", staff.get)
    assert old.status is AssignmentStatus.WITHDRAWN
    assert old.withdrawn_reason == "Driver sick"
    assert driver.availability.is_free(win(10, 12))  # released
    assert delivery.current_assignment() is new
    assert len(delivery.assignments) == 2  # history kept


def test_reallocate_requires_reason(office, driver):
    delivery = Delivery("R-D001", "2026-11-05")
    office.allocate(delivery, driver, win(10, 12))
    with pytest.raises(ValueError, match="reason is required"):
        office.reallocate(delivery, driver, "  ", lambda _: driver)


# -- interface used by the pickup/payment area --------------------------

def test_pickup_area_contract(office, driver):
    from Models.Delivery_Staff import DeliveryStaff as Reexported
    assert Reexported is type(driver)
    assert driver.employee_number == "S001"
    delivery = Delivery("R-D001", "2026-11-05")
    a = office.allocate(delivery, driver, win(10, 12))
    assert delivery.delivery_status == "Assigned"
    assert a.active and a.assigned_at is not None
    assert a.is_assigned_to("S001")
    a.complete(driver.availability)
    assert not a.active and driver.availability.is_free(win(10, 12))
