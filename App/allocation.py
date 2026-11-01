"""Staff allocation area (A1 tasks T5, T6) - Flask routes.

Creating/deactivating staff, delivery staff availability, and allocating
or reallocating an active, free delivery staff member to a delivery.
All validation lives in the model classes; these routes only collect
input, call the models, and show the result or the error message.
"""

from datetime import date, datetime, time, timedelta

from flask import Blueprint, redirect, render_template, request, url_for

from Dataholders.Time_Window import TimeWindow
from Models.Staff import DeliveryStaff, OfficeStaff
from state import DeliveryHistory, deliveries, history, staff

allocation_bp = Blueprint("allocation", __name__)


# -- helpers -----------------------------------------------------------------

def _parse_window(form):
    """Build a TimeWindow from form fields; raise ValueError with a message."""
    try:
        day = datetime.strptime(form.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Date must be in the form YYYY-MM-DD.")
    try:
        start = datetime.strptime(form.get("start", ""), "%H:%M").time()
        end = datetime.strptime(form.get("end", ""), "%H:%M").time()
    except ValueError:
        raise ValueError("Start and end must be times in the form HH:MM.")
    return TimeWindow(day, start, end)


def _delivery_staff():
    return [m for m in staff.values() if isinstance(m, DeliveryStaff)]


def _office_staff():
    return [m for m in staff.values() if isinstance(m, OfficeStaff)]


def _allocatable():
    return [d for d in deliveries.values()
            if d.delivery_status in d.ALLOCATABLE]


def _allocated():
    return [d for d in deliveries.values() if d.current_assignment()]


# -- staff records -----------------------------------------------------------

@allocation_bp.route("/staff")
def staff_page():
    return render_template("staff.html", staff=staff.values(),
                           message=request.args.get("message"),
                           error=request.args.get("error"))


@allocation_bp.route("/staff/create", methods=["POST"])
def create_staff():
    role = request.form.get("role", "")
    staff_id = request.form.get("staff_id", "").strip()
    if role not in ("office", "delivery"):
        return redirect(url_for(".staff_page", error="Role must be office or delivery."))
    if staff_id in staff:
        return redirect(url_for(".staff_page", error=f"Staff ID {staff_id} already exists."))
    cls = OfficeStaff if role == "office" else DeliveryStaff
    try:
        member = cls(staff_id, request.form.get("name", ""),
                     request.form.get("phone", ""))
    except ValueError as err:
        return redirect(url_for(".staff_page", error=str(err)))
    staff[member.staff_id] = member
    return redirect(url_for(".staff_page", message=f"Created {member}."))


@allocation_bp.route("/staff/deactivate", methods=["POST"])
def deactivate_staff():
    member = staff.get(request.form.get("staff_id", ""))
    if member is None:
        return redirect(url_for(".staff_page", error="Staff member not found."))
    try:
        member.deactivate()
    except ValueError as err:
        return redirect(url_for(".staff_page", error=str(err)))
    return redirect(url_for(".staff_page", message=f"Deactivated {member}."))


# -- availability (T5) -------------------------------------------------------

@allocation_bp.route("/availability")
def availability_page():
    return render_template("availability.html", drivers=_delivery_staff(),
                           message=request.args.get("message"),
                           error=request.args.get("error"))


@allocation_bp.route("/availability/add", methods=["POST"])
def add_availability():
    member = staff.get(request.form.get("staff_id", ""))
    if not isinstance(member, DeliveryStaff) or not member.is_active():
        return redirect(url_for(".availability_page",
                                error="Active delivery staff member not found."))
    try:
        window = _parse_window(request.form)
        member.declare_availability(window)
    except ValueError as err:
        return redirect(url_for(".availability_page", error=str(err)))
    return redirect(url_for(".availability_page",
                            message=f"{member.name} is available {window}."))


@allocation_bp.route("/availability/remove", methods=["POST"])
def remove_availability():
    member = staff.get(request.form.get("staff_id", ""))
    if not isinstance(member, DeliveryStaff):
        return redirect(url_for(".availability_page",
                                error="Delivery staff member not found."))
    try:
        window = _parse_window(request.form)
        member.remove_availability(window)
    except ValueError as err:
        return redirect(url_for(".availability_page", error=str(err)))
    return redirect(url_for(".availability_page",
                            message=f"Removed {window} for {member.name}."))


# -- allocation (T6) ---------------------------------------------------------

@allocation_bp.route("/allocate")
def allocate_page():
    return render_template("allocate.html",
                           awaiting=_allocatable(), allocated=_allocated(),
                           office=_office_staff(), drivers=_delivery_staff(),
                           message=request.args.get("message"),
                           error=request.args.get("error"))


@allocation_bp.route("/allocate/free", methods=["POST"])
def free_staff():
    """Step 1: office staff enter the pickup window and see who is free."""
    office = staff.get(request.form.get("office_id", ""))
    delivery = deliveries.get(request.form.get("delivery_id", ""))
    if not isinstance(office, OfficeStaff) or not office.is_active():
        return redirect(url_for(".allocate_page", error="Active office staff member not found."))
    if delivery is None:
        return redirect(url_for(".allocate_page", error="Delivery not found."))
    if delivery.delivery_status not in delivery.ALLOCATABLE:
        return redirect(url_for(".allocate_page",
                                error=f"Delivery is not awaiting allocation "
                                      f"(status: {delivery.delivery_status})."))
    try:
        window = _parse_window(request.form)
        if not window.is_valid():
            raise ValueError("End time must be after start time.")
        if window.day < date.today():
            raise ValueError("Pickup date must be today or later.")
    except ValueError as err:
        return redirect(url_for(".allocate_page", error=str(err)))
    free = [m for m in _delivery_staff()
            if m.is_active() and m.availability.is_free(window)]
    return render_template("allocate_choose.html", office=office,
                           delivery=delivery, window=window, free=free,
                           form=request.form)


@allocation_bp.route("/allocate/confirm", methods=["POST"])
def confirm_allocation():
    """Step 2: commit the chosen staff member. Availability is re-checked."""
    office = staff.get(request.form.get("office_id", ""))
    delivery = deliveries.get(request.form.get("delivery_id", ""))
    chosen = staff.get(request.form.get("staff_id", ""))
    if not isinstance(office, OfficeStaff) or delivery is None:
        return redirect(url_for(".allocate_page", error="Delivery or office staff not found."))
    if not isinstance(chosen, DeliveryStaff):
        return redirect(url_for(".allocate_page", error="Choose a delivery staff member."))
    try:
        window = _parse_window(request.form)
        assignment = office.allocate(delivery, chosen, window, DeliveryHistory)
    except ValueError as err:
        return redirect(url_for(".allocate_page", error=str(err)))
    return redirect(url_for(".allocate_page",
                            message=f"Allocated delivery {delivery.delivery_id[:8]} to "
                                    f"{chosen.name} for {window} ({assignment.assignment_id})."))


@allocation_bp.route("/allocate/reallocate", methods=["POST"])
def reallocate():
    office = staff.get(request.form.get("office_id", ""))
    delivery = deliveries.get(request.form.get("delivery_id", ""))
    new_staff = staff.get(request.form.get("staff_id", ""))
    reason = request.form.get("reason", "")
    if not isinstance(office, OfficeStaff) or delivery is None:
        return redirect(url_for(".allocate_page", error="Delivery or office staff not found."))
    if delivery.current_assignment() is None:
        return redirect(url_for(".allocate_page", error="Delivery has no current assignment."))
    if not isinstance(new_staff, DeliveryStaff):
        return redirect(url_for(".allocate_page", error="Choose a delivery staff member."))
    previous = delivery.delivery_status
    delivery.delivery_status = "allocation required"
    try:
        assignment = office.reallocate(delivery, new_staff, reason, staff.get,
                                       DeliveryHistory)
    except ValueError as err:
        delivery.delivery_status = previous
        return redirect(url_for(".allocate_page", error=str(err)))
    return redirect(url_for(".allocate_page",
                            message=f"Reallocated delivery {delivery.delivery_id[:8]} to "
                                    f"{new_staff.name} ({assignment.assignment_id})."))


@allocation_bp.route("/history")
def history_page():
    return render_template("history.html", events=history)


# -- seed data ---------------------------------------------------------------

def seed_staff():
    """Sample staff so the area can be demonstrated straight after launch."""
    if staff:
        return
    tomorrow = date.today() + timedelta(days=1)
    jess = DeliveryStaff("S001", "Jess Lee", "0400 000 002")
    jess.declare_availability(TimeWindow(tomorrow, time(9), time(17)))
    staff["O001"] = OfficeStaff("O001", "Alex Chen", "0400 000 001")
    staff["S001"] = jess
    staff["S002"] = DeliveryStaff("S002", "Sam Glasser", "0400 000 003")
