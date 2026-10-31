import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, render_template, request
from Models.Customer import Customer
from Models.Order_Request import OrderRequest
from Models.Parcel import Parcel
from Models.Quote import Quote
from Dataholders.Address import Delivery_Address 


# Ensure that the objects can be accsessed
customers = {}       # customer_id -> Customer
order_requests = {}  # request_id  -> OrderRequest
quotes = {}          # quote_id    -> Quote
deliveries = {}      # delivery_id -> Delivery 




app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

#1 Renders the page to create an order. 
@app.route("/create_order.html", methods=["GET", "POST"])
def create_order():
    return render_template("create_order.html") 


# Helper (not a route) - called from submit_order with the objects it created
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
    # Get customer info
    firstname = (request.form.get("firstname") or "").strip()
    lastname = (request.form.get("lastname") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()

    # Get parcel info 
    weights = request.form.getlist("parcel_weight")
    dimensions = request.form.getlist("dimensions")
    fragiles = request.form.getlist("parcel_fragile")

    # Create customer object 
    customer = Customer(firstname, lastname, email, phone)
    #save customer
    customers[customer.customer_id] = customer 

    
    #Once customer is created create order request and parcels associated with the customer

    #Create order request 

    number_of_parcels = len(weights)   
    print("Customer ID:", customer.customer_id)
    customer_id = customer.customer_id  # Get the customer ID from the created customer object
    order_request = OrderRequest.create(customer.customer_id, number_of_parcels=number_of_parcels) 

    print("Order request created with ID:", order_request.customer_id, order_request.request_id,customer.customer_id)
    #save order request  
    order_requests[order_request.request_id] = order_request


    # Create parcels
    parcels = []
    for weight, dimension, fragile in zip(weights, dimensions, fragiles):
        parcel = Parcel(
            (weight or "").strip(),
            (dimension or "").strip(),
            str(fragile).strip().lower() == "true",
        )
        parcels.append(parcel)

    #save parcels on the order request
    order_request.parcels = parcels

    #Create pick up and delivery address set order request to an address  

    pickupstreet = (request.form.get("pickupstreet") or "").strip()
    pickupsuburb = (request.form.get("pickupsuburb") or "").strip()
    pickuppostcode = (request.form.get("pickuppostcode") or "").strip()

    deliverystreet = (request.form.get("deliverystreet") or "").strip()
    deliverysuburb = (request.form.get("deliverysuburb") or "").strip()
    deliverypostcode = (request.form.get("deliverypostcode") or "").strip()

    # Create pick up address 
    pickupaddress = Delivery_Address( order_request.request_id,pickupstreet,pickupsuburb,pickuppostcode) 

    # save pick up address
    order_request.pickup_address = pickupaddress

    # Create the delivery address
    deliveryaddress = Delivery_Address(order_request.request_id, deliverystreet, deliverysuburb, deliverypostcode)

    #save delivery address
    order_request.delivery_address = deliveryaddress

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



    return create_quote(customer, order_request, parcels, pickupaddress, deliveryaddress)

#Takes ifo from the create quote page to create quote
@app.route("/submit_quote", methods=["POST"])
def submit_quote(): 

    # Get quote info entered by office staff
    request_id = (request.form.get("request_id") or "").strip()
    estimateddeliverytime = (request.form.get("estimateddeliverytime") or "").strip()
    try:
        deliveryfee = float(request.form.get("deliveryfee") or 0)
    except ValueError:
        return "Delivery fee must be a number", 400

    # Quote must belong to an order request that exists
    order_request = order_requests.get(request_id)
    if order_request is None:
        return "Order request not found", 404

    # Create quote linked to the order request
    quote = Quote(request_id, deliveryfee, estimateddeliverytime)
    #save quotes
    quotes[quote.quoteid]= quote
    order_request.status = "quoted"


    print("Quote created!")
    print("Quote ID:", quote.quoteid)
    print("Request ID:", quote.request_id)
    print("Delivery Fee:", quote.deliveryfee)
    print("Estimated Delivery Time:", quote.estimateddeliverytime)
    print("Expires:", quote.expiredate)

    #office staff would call accept

    return (
        f"Quote created successfully! Quote ID: {quote.quoteid}<br>"
        f"For order request: {quote.request_id}<br>"
        f"Delivery fee: ${quote.deliveryfee:.2f}<br>"
        f"Estimated delivery time: {quote.estimateddeliverytime}<br>"
        f"Quote valid until: {quote.expiredate.strftime('%d/%m/%Y')}"
    )



def schedule_delivery():
    delivery_id = (request.form.get("delivery_id") or "").strip()
    status = (request.form.get("status") or "").strip()
    delivery_date = (request.form.get("delivery_date") or "").strip()
    delivery_status = (request.form.get("delivery_status") or "").strip()
    return "Delivery scheduled"


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)