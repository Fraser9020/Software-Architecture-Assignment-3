# Staff allocation area (Sam) — A1 tasks T5, T6

## What's where
App/Models/Staff.py                Staff (abstract) -> OfficeStaff, DeliveryStaff
App/Models/Staff_Availability.py   StaffAvailability + AvailabilityWindow (data-holder)
App/Models/Delivery_Assignment.py  DeliveryAssignment + AssignmentStatus enum
App/Dataholders/Time_Window.py     TimeWindow data-holder (date, start, end; overlaps/contains)
App/allocation.py                  Flask blueprint: /staff, /availability, /allocate, /history
App/state.py                       Shared in-memory dicts used by app.py and the blueprint
App/templates/staff.html, availability.html, allocate.html, allocate_choose.html, history.html
App/tests/                         30 pytest cases (models + routes)

Changes to existing files:
- App/Models/Delivery.py   added pickup_window, assignments, current_assignment(),
                           set_assignment(), scheduled_window(); default status "accepted"
                           (A2 status flow) instead of "being delivered"
- App/app.py               dicts moved to state.py; blueprint registered; seed_staff()
- App/templates/index.html links to the new pages

## Run
    pip install flask pytest
    python App/app.py                 -> http://127.0.0.1:5000
    python -m pytest App/tests -q     -> 30 passed

## Demo path for screenshots (area: staff allocation)
1. /allocate  with nothing accepted yet -> "No deliveries awaiting allocation"   (empty)
2. Create Order -> quote -> Accept Quote  (Fraser's area; creates the Delivery)
3. /allocate -> choose office staff + delivery, pickup window tomorrow 10:00-12:00
   -> only S001 Jess Lee is listed (S002 has no availability) -> Allocate      (correct input)
4. /availability -> S002, end before start -> "Error: End time must be after start time."  (rejected)
   /allocate -> same window for a second delivery -> "Error: S001 is not free for ..." (double booking)
5. /allocate -> Reallocate to S002 with a reason -> old assignment withdrawn, kept  (change of mind)
6. /history shows Assigned / Assignment withdrawn events                           (result)

## Hooks for other areas
Pickup/handover (Eugene) checks the reporting driver with
    delivery.current_assignment().is_assigned_to(staff_id)
and on handover releases the time with
    delivery.current_assignment().complete(staff.availability)

Seed staff on startup: O001 Alex Chen (office), S001 Jess Lee (delivery, available tomorrow
09:00-17:00), S002 Sam Glasser (delivery, no availability yet).

Coding standard: PEP 8 (checked with pycodestyle --max-line-length=100).
