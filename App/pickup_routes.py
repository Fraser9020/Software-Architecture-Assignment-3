"""Web pages for pickup and payment (a Flask Blueprint)."""
from flask import Blueprint, render_template, request

from Models.Staff import DeliveryStaff
from pickup_data import get_history, get_invoice
from pickup_logic import PAYMENT_METHODS, confirm_pickup
from state import deliveries, staff

pickup_bp = Blueprint("pickup", __name__)


def delivery_staff_members():
    return {sid: s for sid, s in staff.items() if isinstance(s, DeliveryStaff)}


@pickup_bp.route("/pickup")
def pickup_list():
    """List the deliveries waiting for pickup for the chosen employee."""
    staff_id = request.args.get("staff_id", "")
    mine = []
    for delivery in deliveries.values():
        assignment = delivery.current_assignment()
        if assignment is not None and assignment.is_assigned_to(staff_id):
            mine.append({"delivery": delivery, "invoice": get_invoice(delivery)})
    return render_template("pickup_list.html", staff_members=delivery_staff_members(),
                           staff_id=staff_id, mine=mine)


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
