# YOWD Delivery System (SWE30003 Assignment 3)

Python 3 / Flask implementation of four business areas from our Assignment 1 and 2 design.
Data is kept in memory (it resets when the app restarts).

| Area | Pages | Owner | Notes |
|---|---|---|---|
| Delivery request | `/create_order.html` | Fraser  | customer, order request, parcels, pickup and delivery addresses |
| Quotes | create quote, accept / decline | Fraser  | accepted quote creates the Delivery |
| Staff allocation | `/staff`, `/availability`, `/allocate`, `/history` | Samuel  | staff records, availability, (re)allocation, history |
| Pickup and payment | `/pickup` | Eugene | assigned employee records pickup and payment, see `README_pickup.md` |

## Run
```
pip install -r requirements.txt
python App/app.py
```
Open http://127.0.0.1:5000

## Test
```
python -m pytest App/tests -q
```

## Demo path
1. Create Order (all fields are validated on the server). On the review page the customer can edit or delete the order request (delete asks first and can go back), then submit it. Once submitted it can no longer be changed.
2. Enter the quote (fee, estimated delivery time of 1 to 30 days) and Accept it. A Delivery is created.
3. `/allocate`: choose office staff O001, the delivery and a pickup window tomorrow 10:00-12:00, then allocate S001 Jess Lee. To try reallocation, give S002 Sam Glasser availability on `/availability` first, then reallocate the delivery to S002.
4. `/pickup`: choose Jess Lee, Record pickup. A wrong amount is rejected and the delivery stays Assigned. The correct amount makes it Picked Up.
5. `/history` shows the events.

Seed staff: O001 Alex Chen (office), S001 Jess Lee (delivery, available tomorrow 09:00-17:00), S002 Sam Glasser (delivery, no availability yet).

## Layout
```
App/app.py                  Flask app, order and quote routes
App/allocation.py           staff allocation routes   (allocation_bp)
App/pickup_routes.py        pickup and payment routes (pickup_bp)
App/state.py                shared in-memory stores
App/Models/                 Customer, OrderRequest, Parcel, Quote, Delivery, Staff,
                            DeliveryAssignment, StaffAvailability, Invoice, Payment,
                            DeliveryHistory, DeliveryEvent
App/Dataholders/            Address, TimeWindow
App/templates/              HTML pages
App/tests/                  pytest tests
```

## Status flow
Order request: draft -> pending -> quoted -> accepted.  Quote: pending -> accepted / denied.  Delivery: accepted -> Assigned -> Picked Up.
Reallocation: an Assigned delivery can be moved to another driver. The old assignment is
withdrawn, the driver's time is freed and the delivery stays Assigned.

## Coding standard
PEP 8 (max line length 99), docstrings on classes and functions.

## Known limitations
- In-memory storage only.
- Payment is only a "Payment processed" message (no payment gateway).
- Employees are chosen from a drop-down (no sign-in).
