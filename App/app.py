import os
import sys 
from pydantic import ValidationError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, redirect, render_template, request, url_for
from Models.Customer import Customer
from Models.Order_Request import OrderRequest
from Models.Parcel import Parcel
from Dataholders.Address import Delivery_Address


# Shared in-memory stores (see state.py) so every area sees the same objects
from state import customers, order_requests, quotes, deliveries
from allocation import allocation_bp, seed_staff
from pickup_routes import pickup_bp




app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.register_blueprint(allocation_bp)   # staff allocation area (Sam)
app.register_blueprint(pickup_bp)       # pickup and payment area (Eugene)
seed_staff()

#1 Renders the page to create an order. 
@app.route("/create_order.html", methods=["GET", "POST"])
def create_order():
    return render_template("create_order.html")


# Helper (not a route) - re-shows the order form with what the customer typed
def order_form_with_errors(errors):
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


# Helper (not a route) - called once the customer sends the order request
def create_quote(customer, order_request, parcels, pickupaddress, deliveryaddress):
    return render_template(
        "create_quote.html",
        customer=customer,
        order_request=order_request,
        parcels=parcels,
        pickupaddress=pickupaddress,
        deliveryaddress=deliveryaddress,
    )



#2 once submit order is clicked this function is called
@app.route("/submit_order", methods=["POST"])
def submit_order():

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
    firstname = (request.form.get("firstname") or "").strip()
    lastname = (request.form.get("lastname") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()

    # Get address info
    pickupstreet = (request.form.get("pickupstreet") or "").strip()
    pickupsuburb = (request.form.get("pickupsuburb") or "").strip()
    pickuppostcode = (request.form.get("pickuppostcode") or "").strip()

    deliverystreet = (request.form.get("deliverystreet") or "").strip()
    deliverysuburb = (request.form.get("deliverysuburb") or "").strip()
    deliverypostcode = (request.form.get("deliverypostcode") or "").strip()


    # validate info - collect every error so the user sees them all at once
    errors = []

    try:
        # Validate input and create customer
        customer = Customer(
            firstname=firstname,
            lastname=lastname,
            email=email,
            phone=phone
        )
    except ValidationError as e:
        errors += e.errors()

    try:
        # Validate pick up address
        pickupaddress = Delivery_Address(street=pickupstreet, suburb=pickupsuburb, postcode=pickuppostcode)
    except ValidationError as e:
        # Both addresses have the same field names, so label which one failed
        for err in e.errors():
            err["loc"] = ("pickup " + err["loc"][0],)
            errors.append(err)

    try:
        # Validate delivery address
        deliveryaddress = Delivery_Address(street=deliverystreet, suburb=deliverysuburb, postcode=deliverypostcode)
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
    for number, (weight, dimension, fragile) in enumerate(zip(weights, dimensions, fragiles), start=1):
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

    #Once customer is created create order request and parcels associated with the customer

    #Create order request, or keep the same IDs when editing
    print("Customer ID:", customer.customer_id)
    try:
        if order_request is None:
            order_request = OrderRequest.create(customer.customer_id, number_of_parcels=len(parcels))
        else:
            customer.customer_id = order_request.customer_id

        #save parcels and the validated addresses on the order request
        order_request.update_details(parcels, pickupaddress, deliveryaddress)
    except ValidationError as e:
        return order_form_with_errors(e.errors())

    print("Order request created with ID:", order_request.customer_id, order_request.request_id,customer.customer_id)
    #save customer and order request (only once everything is valid)
    customers[customer.customer_id] = customer
    order_requests[order_request.request_id] = order_request

    # Verify customer and order request created
    print("Customer created!")
    print("Name:", customer.firstname, customer.lastname)
    print("Customer ID:", customer.customer_id)
    print("Order request created!")
    print("Number of Parcels:", order_request.number_of_parcels)
    print("Request ID:", order_request.request_id)

    # Verify parcels created
    for parcel in parcels:
        print("Parcel created!")
        print("Weight:", parcel.weight)
        print("Dimension:", parcel.dimension)
        print("Fragile:", parcel.fragile)
        print("Parcel ID:", parcel.id)



    # The customer reviews it before it is sent. Redirect so a refresh can't create a second order
    return redirect(url_for("review_order_request", request_id=order_request.request_id))


#Customer reviews their order request and can edit, delete or send it
@app.route("/verify_order_request", methods=["GET"])
def review_order_request():
    order_request = order_requests.get((request.args.get("request_id") or "").strip())
    if order_request is None:
        return "Order request not found", 404

    return render_template(
        "verify_order_request.html",
        customer=customers.get(order_request.customer_id),
        order_request=order_request,
    )


#Customer sends the order request. After this it can't be changed
@app.route("/verify_order_request", methods=["POST"])
def send_order_request():
    order_request = order_requests.get((request.form.get("request_id") or "").strip())
    if order_request is None:
        return "Order request not found", 404

    try:
        order_request.send()
    except ValueError as e:
        return str(e), 400

    print("Order request sent:", order_request.request_id)

    return create_quote(
        customers.get(order_request.customer_id),
        order_request,
        order_request.parcels,
        order_request.pickup_address,
        order_request.delivery_address,
    )


#Customer changes their mind - shows the order form filled in with their order request
@app.route("/edit_order_request", methods=["GET"])
def edit_order_request():
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
        "firstname": customer.firstname,
        "lastname": customer.lastname,
        "email": customer.email,
        "phone": customer.phone,
        "pickupstreet": order_request.pickup_address.street,
        "pickupsuburb": order_request.pickup_address.suburb,
        "pickuppostcode": order_request.pickup_address.postcode,
        "deliverystreet": order_request.delivery_address.street,
        "deliverysuburb": order_request.delivery_address.suburb,
        "deliverypostcode": order_request.delivery_address.postcode,
    }
    return render_template("create_order.html", form=form, parcel_rows=order_request.parcels)


#Customer clicks Delete - asks them to confirm and lets them go back
@app.route("/delete_order_request", methods=["GET"])
def confirm_delete_order_request():
    order_request = order_requests.get((request.args.get("request_id") or "").strip())
    if order_request is None:
        return "Order request not found", 404

    try:
        order_request.check_can_change()
    except ValueError as e:
        return str(e), 400

    return render_template("delete_order_request.html", order_request=order_request)


#Customer confirmed the delete
@app.route("/delete_order_request", methods=["POST"])
def delete_order_request():
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

    print("Order request deleted:", order_request.request_id)

    return render_template("delete_order_request.html", deleted=True)


#Takes ifo from the create quote page to create quote
@app.route("/submit_quote", methods=["POST"])
def submit_quote(): 

    # Get quote info entered by office staff
    request_id = (request.form.get("request_id") or "").strip()
    estimateddeliverytime = (request.form.get("estimateddeliverytime") or "").strip()
    # Pydantic turns this into a float and rejects anything that isn't a number
    deliveryfee = (request.form.get("deliveryfee") or "").strip()

    # Quote must belong to an order request that exists
    order_request = order_requests.get(request_id)
    if order_request is None:
        return "Order request not found", 404

    # validate info and create quote linked to the order request
    try:
        quote = order_request.request_quote(deliveryfee, estimateddeliverytime)
    except ValidationError as e:
        # Re-show the quote page; the order details are all stored on the order request
        return render_template(
            "create_quote.html",
            errors=e.errors(),
            form=request.form,
            customer=customers.get(order_request.customer_id),
            order_request=order_request,
            parcels=order_request.parcels,
            pickupaddress=order_request.pickup_address,
            deliveryaddress=order_request.delivery_address,
        )
    except ValueError as e:
        # The order request already has a quote
        return str(e), 400

    #save quotes
    quotes[quote.quoteid]= quote


    print("Quote created!")
    print("Quote ID:", quote.quoteid)
    print("Request ID:", quote.request_id)
    print("Delivery Fee:", quote.deliveryfee)
    print("Estimated Delivery Time:", quote.estimateddeliverytime)
    print("Expires:", quote.expiredate)

    #office staff would call accept

    
        
    #f"Quote created successfully! Quote ID: {quote.quoteid}<br>"
    # f"For order request: {quote.request_id}<br>"
    #f"Delivery fee: ${quote.deliveryfee:.2f}<br>"
    # f"Estimated delivery time: {quote.estimateddeliverytime}<br>"
    # f"Quote valid until: {quote.expiredate.strftime('%d/%m/%Y')}" 
    return render_template("accept_quote.html", quote=quote, order_request=order_request)


    
#3 Customer clicks Accept Quote
@app.route("/accept_quote", methods=["POST"])
def accept_quote():
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

    print("Quote accepted:", quote.quoteid)

    #save delivery
    deliveries[delivery.delivery_id] = delivery

    print("Delivery created!")
    print(delivery)

    return render_template("accepted_quote.html", quote=quote, delivery=delivery)


#4 Customer clicks Deny Quote - marks the quote denied and shows the result
@app.route("/deny_quote", methods=["POST"])
def deny_quote():
    quote_id = (request.form.get("quote_id") or "").strip()

    quote = quotes.get(quote_id)
    if quote is None:
        return "Quote not found", 404

    try:
        quote.deny()
    except ValueError as e:
        return str(e), 400

    print("Quote denied:", quote_id, quote.status)

    return render_template("denied_quote.html", quote=quote)


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)