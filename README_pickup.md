# Pickup and payment area (Eugene) - A1 task T7

## What's where
App/Models/Invoice.py, Payment.py     Invoice creates the Payment; Payment checks the amount
App/Models/Delivery_History.py        events of one delivery (failed payments are counted)
App/Models/Delivery_Event.py          one event
App/pickup_data.py                    invoices and pickup histories; invoice made from the accepted quote fee
App/pickup_logic.py                   confirm_pickup() = Delivery.confirmPickup from the class diagram
App/pickup_routes.py                  Flask blueprint: /pickup
App/templates/pickup_*.html           list, form, result pages
App/tests/test_pickup.py              pytest cases

Uses from the other areas: state.py (shared dictionaries), Models/Staff.py (DeliveryStaff),
Delivery.current_assignment().is_assigned_to(staff_id) and delivery_status "Assigned".
Changes to existing files: app.py (2 lines: import and register the blueprint), templates/index.html (one link).

## Demo path
1. Create Order -> quote -> Accept Quote (Fraser)
2. /allocate: allocate the delivery to S001 Jess Lee (Sam)
3. /pickup: choose Jess Lee -> Record pickup
4. Wrong amount -> rejected, stays Assigned. Correct amount -> Picked Up. /history shows the events.

## Run
    pip install flask pytest
    python App/app.py
    python -m pytest App/tests -q
