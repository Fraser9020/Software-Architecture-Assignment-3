"""Flask application: the order request and quote routes."""
import os
import sys

from flask import Flask, redirect, render_template, request, url_for
from pydantic import ValidationError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from Models.Customer import Customer  # noqa: E402
from Models.Order_Request import OrderRequest  # noqa: E402
from Models.Parcel import Parcel  # noqa: E402
from Dataholders.Address import DeliveryAddress  # noqa: E402

# Shared in-memory stores (see state.py) so every area sees the same objects
from state import customers, order_requests, quotes, deliveries  # noqa: E402
from allocation import allocation_bp, seed_staff  # noqa: E402
from pickup_routes import pickup_bp  # noqa: E402

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.register_blueprint(allocation_bp)   # staff allocation area (Sam)
app.register_blueprint(pickup_bp)       # pickup and payment area (Eugene)
seed_staff()


@app.route("/create_order.html", methods=["GET", "POST"])
def create_order():
    """Show the create order form."""
    return render_template("create_order.html")


def order_form_with_errors(errors):
    """Re-show the order form with what the customer typed (helper, not a route)."""
    parcel_rows = [
        {"weight": weight, "dimension": dimension, "fragile": fragile == "true"}
        for weight, dimension, fragile in zip(
            request.form.getlist("parcel_weight"),
            request.form.getlist("dimensions"),
            request.form.getlist("parcel_fragile"),
        )
    ]
    return render_template(
        "create_order.html",
        errors=errors,
        form=request.form,
        parcel_rows=parcel_rows,
    )


def create_quote(customer, order_request, parcels, pickup_address, delivery_address):
    """Show the create quote page for a sent order request (helper, not a route)."""
    return render_template(
        "create_quote.html",
        customer=customer,
        order_request=order_request,
        parcels=parcels,
        pickup_address=pickup_address,
        delivery_address=delivery_address,
    )


@app.route("/submit_order", methods=["POST"])
def submit_order():
    """Validate the submitted order form, then create or update the order request."""

    # Only set when the customer is editing an order request they have not sent
    order_request = None
    request_id = (request.form.get("request_id") or "").strip()
    if request_id:
        order_request = order_requests.get(request_id)
        if order_request is None:
            return "Order request not found", 404
        try:
            order_request.check_can_change()
        except ValueError as e:
            return str(e), 400

    # Get customer info
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()

    # Get address info
    pickup_street = (request.form.get("pickup_street") or "").strip()
    pickup_suburb = (request.form.get("pickup_suburb") or "").strip()
    pickup_postcode = (request.form.get("pickup_postcode") or "").strip()

    delivery_street = (request.form.get("delivery_street") or "").strip()
    delivery_suburb = (request.form.get("delivery_suburb") or "").strip()
    delivery_postcode = (request.form.get("delivery_postcode") or "").strip()

    # validate info - collect every error so the user sees them all at once
    errors = []

    try:
        # Validate input and create customer
        customer = Customer(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone
        )
    except ValidationError as e:
        errors += e.errors()

    try:
        # Validate pick up address
        pickup_address = DeliveryAddress(
            street=pickup_street, suburb=pickup_suburb, postcode=pickup_postcode
        )
    except ValidationError as e:
        # Both addresses have the same field names, so label which one failed
        for err in e.errors():
            err["loc"] = ("pickup " + err["loc"][0],)
            errors.append(err)

    try:
        # Validate delivery address
        delivery_address = DeliveryAddress(
            street=delivery_street, suburb=delivery_suburb, postcode=delivery_postcode
        )
    except ValidationError as e:
        for err in e.errors():
            err["loc"] = ("delivery " + err["loc"][0],)
            errors.append(err)

    # Get parcel info
    weights = request.form.getlist("parcel_weight")
    dimensions = request.form.getlist("dimensions")
    fragiles = request.form.getlist("parcel_fragile")

    # Validate parcels
    parcels = []
    rows = zip(weights, dimensions, fragiles)
    for number, (weight, dimension, fragile) in enumerate(rows, start=1):
        try:
            parcel = Parcel(
                weight=(weight or "").strip(),
                dimension=(dimension or "").strip(),
                fragile=str(fragile).strip().lower() == "true",
            )
            parcels.append(parcel)
        except ValidationError as e:
            # Label which parcel failed when there are several
            for err in e.errors():
                err["loc"] = (f"parcel {number} " + err["loc"][0],)
                errors.append(err)

    if errors:
        return order_form_with_errors(errors)

    # Once customer is created create order request and parcels associated with the customer

    # Create order request, or keep the same IDs when editing
    try:
        if order_request is None:
            order_request = OrderRequest.create(
                customer.customer_id, number_of_parcels=len(parcels)
            )
        else:
            customer.customer_id = order_request.customer_id

        # Save parcels and the validated addresses on the order request
        order_request.update_details(parcels, pickup_address, delivery_address)
    except ValidationError as e:
        return order_form_with_errors(e.errors())

    # Save customer and order request (only once everything is valid)
    customers[customer.customer_id] = customer
    order_requests[order_request.request_id] = order_request

    # The customer reviews it before it is sent. Redirect so a refresh can't create a second order
    return redirect(url_for("review_order_request", request_id=order_request.request_id))


@app.route("/verify_order_request", methods=["GET"])
def review_order_request():
    """Show the order request so the customer can edit, delete or send it."""
    order_request = order_requests.get((request.args.get("request_id") or "").strip())
    if order_request is None:
        return "Order request not found", 404

    return render_template(
        "verify_order_request.html",
        customer=customers.get(order_request.customer_id),
        order_request=order_request,
    )


@app.route("/verify_order_request", methods=["POST"])
def send_order_request():
    """Send the order request, after which it can't be changed."""
    order_request = order_requests.get((request.form.get("request_id") or "").strip())
    if order_request is None:
        return "Order request not found", 404

    try:
        order_request.send()
    except ValueError as e:
        return str(e), 400

    return create_quote(
        customers.get(order_request.customer_id),
        order_request,
        order_request.parcels,
        order_request.pickup_address,
        order_request.delivery_address,
    )


@app.route("/edit_order_request", methods=["GET"])
def edit_order_request():
    """Show the order form filled in with the customer's order request."""
    order_request = order_requests.get((request.args.get("request_id") or "").strip())
    if order_request is None:
        return "Order request not found", 404

    try:
        order_request.check_can_change()
    except ValueError as e:
        return str(e), 400

    customer = customers.get(order_request.customer_id)
    form = {
        "request_id": order_request.request_id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
        "pickup_street": order_request.pickup_address.street,
        "pickup_suburb": order_request.pickup_address.suburb,
        "pickup_postcode": order_request.pickup_address.postcode,
        "delivery_street": order_request.delivery_address.street,
        "delivery_suburb": order_request.delivery_address.suburb,
        "delivery_postcode": order_request.delivery_address.postcode,
    }
    return render_template("create_order.html", form=form, parcel_rows=order_request.parcels)


@app.route("/delete_order_request", methods=["GET"])
def confirm_delete_order_request():
    """Ask the customer to confirm the delete, or let them go back."""
    order_request = order_requests.get((request.args.get("request_id") or "").strip())
    if order_request is None:
        return "Order request not found", 404

    try:
        order_request.check_can_change()
    except ValueError as e:
        return str(e), 400

    return render_template("delete_order_request.html", order_request=order_request)


@app.route("/delete_order_request", methods=["POST"])
def delete_order_request():
    """Delete the order request and its customer once confirmed."""
    order_request = order_requests.get((request.form.get("request_id") or "").strip())
    if order_request is None:
        return "Order request not found", 404

    try:
        order_request.check_can_change()
    except ValueError as e:
        return str(e), 400

    # Each order request has its own customer record, so remove both
    customers.pop(order_request.customer_id, None)
    del order_requests[order_request.request_id]

    return render_template("delete_order_request.html", deleted=True)


@app.route("/submit_quote", methods=["POST"])
def submit_quote():
    """Create a quote from the details entered on the create quote page."""

    # Get quote info entered by office staff
    request_id = (request.form.get("request_id") or "").strip()
    estimated_delivery_time = (request.form.get("estimated_delivery_time") or "").strip()
    # Pydantic turns this into a float and rejects anything that isn't a number
    delivery_fee = (request.form.get("delivery_fee") or "").strip()

    # Quote must belong to an order request that exists
    order_request = order_requests.get(request_id)
    if order_request is None:
        return "Order request not found", 404

    # validate info and create quote linked to the order request
    try:
        quote = order_request.request_quote(delivery_fee, estimated_delivery_time)
    except ValidationError as e:
        # Re-show the quote page; the order details are all stored on the order request
        return render_template(
            "create_quote.html",
            errors=e.errors(),
            form=request.form,
            customer=customers.get(order_request.customer_id),
            order_request=order_request,
            parcels=order_request.parcels,
            pickup_address=order_request.pickup_address,
            delivery_address=order_request.delivery_address,
        )
    except ValueError as e:
        # The order request already has a quote
        return str(e), 400

    # Save quotes
    quotes[quote.quote_id] = quote

    return render_template("accept_quote.html", quote=quote, order_request=order_request)


@app.route("/accept_quote", methods=["POST"])
def accept_quote():
    """Accept the quote when the customer clicks Accept Quote."""
    quote_id = (request.form.get("quote_id") or "").strip()

    # Look up the quote that was saved in submit_quote
    quote = quotes.get(quote_id)
    if quote is None:
        return "Quote not found", 404

    order_request = order_requests.get(quote.request_id)
    if order_request is None:
        return "Order request not found", 404

    # The quote updates the order request and creates the delivery
    try:
        delivery = quote.accept(order_request)
    except ValueError as e:
        return str(e), 400

    # Save delivery
    deliveries[delivery.delivery_id] = delivery

    return render_template("accepted_quote.html", quote=quote, delivery=delivery)


@app.route("/deny_quote", methods=["POST"])
def deny_quote():
    """Mark the quote denied when the customer clicks Deny Quote, and show the result."""
    quote_id = (request.form.get("quote_id") or "").strip()

    quote = quotes.get(quote_id)
    if quote is None:
        return "Quote not found", 404

    try:
        quote.deny()
    except ValueError as e:
        return str(e), 400

    return render_template("denied_quote.html", quote=quote)


@app.route("/")
def home():
    """Show the home page."""
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
