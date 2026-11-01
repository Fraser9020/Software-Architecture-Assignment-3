"""Web pages for pickup and payment (a Flask Blueprint)."""
from flask import Blueprint, render_template, request

from app import deliveries
from pickup_data import (assign_staff, assignments, get_history, get_invoice,
                         staff_members)
from pickup_logic import PAYMENT_METHODS, confirm_pickup

pickup_bp = Blueprint("pickup", __name__)


@pickup_bp.route("/pickup")
def pickup_list():
    """List the deliveries waiting for pickup for the chosen employee."""
    staff_id = request.args.get("staff_id", "")
    mine, unassigned = [], []
    for delivery in deliveries.values():
        invoice = get_invoice(delivery)
        row = {"delivery": delivery, "invoice": invoice}
        assignment = assignments.get(delivery.delivery_id)
        if assignment is None:
            unassigned.append(row)
        elif assignment.is_assigned_to(staff_id):
            mine.append(row)
    return render_template("pickup_list.html", staff_members=staff_members,
                           staff_id=staff_id, mine=mine, unassigned=unassigned)


@pickup_bp.route("/pickup/<delivery_id>")
def pickup_form(delivery_id):
    delivery = deliveries.get(delivery_id)
    if delivery is None:
        return "Delivery not found", 404
    return render_template("pickup_form.html", delivery=delivery,
                           invoice=get_invoice(delivery), staff_id=request.args.get("staff_id", ""),
                           methods=PAYMENT_METHODS, errors=[], values={},
                           history=get_history(delivery))


@pickup_bp.route("/pickup/<delivery_id>", methods=["POST"])
def pickup_submit(delivery_id):
    delivery = deliveries.get(delivery_id)
    if delivery is None:
        return "Delivery not found", 404
    values = {
        "staff_id": request.form.get("staff_id", ""),
        "condition": request.form.get("condition", ""),
        "amount": request.form.get("amount", ""),
        "method": request.form.get("method", ""),
        "parcels_ok": request.form.get("parcels_ok") == "yes",
    }
    success, messages = confirm_pickup(delivery, values["staff_id"], values["condition"],
                                       values["amount"], values["method"], values["parcels_ok"])
    if success:
        return render_template("pickup_done.html", delivery=delivery, messages=messages,
                               history=get_history(delivery))
    return render_template("pickup_form.html", delivery=delivery, invoice=get_invoice(delivery),
                           staff_id=values["staff_id"], methods=PAYMENT_METHODS,
                           errors=messages, values=values, history=get_history(delivery))


@pickup_bp.route("/pickup/test-assign", methods=["POST"])
def test_assign():
    """Test data only: give an unassigned delivery to an employee."""
    delivery = deliveries.get(request.form.get("delivery_id", ""))
    staff_id = request.form.get("staff_id", "")
    if delivery is None or staff_id not in staff_members:
        return "Choose a delivery and an employee", 400
    assign_staff(delivery, staff_id)
    return f"<p>Assigned. <a href='/pickup?staff_id={staff_id}'>Back to pickups</a></p>"
