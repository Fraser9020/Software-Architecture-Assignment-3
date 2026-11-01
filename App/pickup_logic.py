"""The pickup and payment rules (scenario 7.3 of Assignment 2).

confirm_pickup() is the Delivery.confirmPickup operation from the class
diagram. It is a function here so Fraser's Delivery class stays unchanged.
"""
from pickup_data import assignments, get_history, get_invoice, staff_members

PAYMENT_METHODS = ["Cash", "Card", "Bank transfer"]


def confirm_pickup(delivery, staff_id, condition, amount_text, method, parcels_ok):
    """Check the input, take the payment and mark the delivery Picked Up.

    Returns (success, messages). Nothing changes if the input is wrong.
    """
    errors = []
    history = get_history(delivery)

    # 1. Is the delivery ready, and is this the assigned employee?
    if delivery.delivery_status == "Picked Up":
        return False, ["This delivery has already been picked up."]
    if delivery.delivery_status != "Assigned":
        return False, ["This delivery has no employee assigned yet."]
    assignment = assignments.get(delivery.delivery_id)
    if staff_id not in staff_members:
        return False, ["Please choose an employee."]
    if assignment is None or not assignment.is_assigned_to(staff_id):
        return False, ["Only the assigned employee can record this pickup."]

    # 2. Check what the employee typed in
    if not parcels_ok:
        errors.append("Please confirm that all parcels match the description.")
    if not condition.strip():
        errors.append("Please describe the condition of the parcels.")
    if method not in PAYMENT_METHODS:
        errors.append("Please choose a payment method.")
    amount = None
    try:
        amount = float(amount_text)
        if amount <= 0:
            errors.append("The amount must be more than 0.")
    except ValueError:
        errors.append("The amount must be a number, for example 45.00.")
    invoice = get_invoice(delivery)
    if invoice is None:
        errors.append("There is no accepted quote for this delivery.")
    if errors:
        return False, errors

    # 3. Take the payment: the Invoice creates it and the Payment checks it
    payment = invoice.create_payment(amount, method, staff_id)
    if payment.outcome != "success":
        history.record_event(
            "Payment failed",
            f"${amount:.2f} by {method}, amount due is ${invoice.amount_due:.2f}",
        )
        return False, [
            f"Payment rejected: ${amount:.2f} does not match the amount due "
            f"(${invoice.amount_due:.2f}). The delivery stays Assigned."
        ]

    # 4. Success: record everything and change the status
    history.record_event("Payment processed", f"${amount:.2f} by {method}")
    history.record_event("Parcel condition", condition.strip())
    history.record_event("Picked Up", f"By {staff_members[staff_id].name}")
    delivery.delivery_status = "Picked Up"
    return True, ["Payment processed. The delivery is now Picked Up."]
