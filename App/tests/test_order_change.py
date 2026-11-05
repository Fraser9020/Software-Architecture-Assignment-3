"""Tests for the customer changing their mind: review, edit and delete before sending."""

import pytest

import state


ORDER = {
    "first_name": "Ann", "last_name": "Lee", "email": "ann@example.com",
    "phone": "0400000000",
    "pickup_street": "1 High St", "pickup_suburb": "Hawthorn", "pickup_postcode": "3122",
    "delivery_street": "2 Low St", "delivery_suburb": "Kew", "delivery_postcode": "3101",
    "parcel_weight": ["2", "3.5"], "dimensions": ["10 x 10 x 10", "20 x 20 x 20"],
    "parcel_fragile": ["false", "true"],
}


@pytest.fixture
def client():
    import app as flask_app
    for store in (state.deliveries, state.quotes, state.order_requests, state.customers):
        store.clear()
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


def draft_order(client):
    assert client.post("/submit_order", data=ORDER).status_code == 302
    return next(iter(state.order_requests.values()))


def send(client, order):
    return client.post("/verify_order_request", data={"request_id": order.request_id})


def test_new_order_goes_to_review_as_a_draft(client):
    response = client.post("/submit_order", data=ORDER, follow_redirects=True)
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Your order request is ready" in page
    assert "Hawthorn" in page and "20 x 20 x 20" in page
    order = next(iter(state.order_requests.values()))
    assert order.status == "draft"


def test_draft_cannot_be_quoted_until_sent(client):
    order = draft_order(client)
    response = client.post("/submit_quote", data={
        "request_id": order.request_id, "delivery_fee": "45",
        "estimated_delivery_time": "5",
    })
    assert response.status_code == 400
    assert not state.quotes


def test_sending_shows_the_quote_page(client):
    order = draft_order(client)
    response = send(client, order)
    assert response.status_code == 200
    assert "Create a Delivery Quote" in response.get_data(as_text=True)
    assert order.status == "pending"


def test_edit_page_is_filled_in_with_the_order(client):
    order = draft_order(client)
    page = client.get(f"/edit_order_request?request_id={order.request_id}").get_data(as_text=True)
    assert 'value="Ann"' in page and 'value="Hawthorn"' in page
    assert 'value="3.5"' in page and 'value="20 x 20 x 20"' in page
    assert 'value="true" selected' in page
    assert f'name="request_id" value="{order.request_id}"' in page
    assert "Go back without saving changes" in page


def test_edit_updates_the_same_order(client):
    order = draft_order(client)
    request_id, customer_id = order.request_id, order.customer_id
    changed = {**ORDER, "request_id": request_id, "first_name": "Bea", "pickup_suburb": "Carlton",
               "parcel_weight": ["7"], "dimensions": ["5 x 5 x 5"], "parcel_fragile": ["true"]}
    assert client.post("/submit_order", data=changed).status_code == 302
    assert list(state.order_requests) == [request_id]
    assert list(state.customers) == [customer_id]
    assert state.customers[customer_id].first_name == "Bea"
    assert order.pickup_address.suburb == "Carlton"
    assert order.pickup_address.order_id == request_id
    assert order.number_of_parcels == 1
    assert order.parcels[0].weight == 7 and order.parcels[0].fragile
    assert order.status == "draft"


def test_invalid_edit_shows_errors_and_changes_nothing(client):
    order = draft_order(client)
    changed = {**ORDER, "request_id": order.request_id, "first_name": "Bea",
               "pickup_postcode": "12", "parcel_weight": ["999", "3.5"]}
    response = client.post("/submit_order", data=changed)
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "pickup postcode" in page and "parcel 1 weight" in page
    assert 'value="Bea"' in page and 'value="999"' in page
    assert f'name="request_id" value="{order.request_id}"' in page
    assert state.customers[order.customer_id].first_name == "Ann"
    assert order.pickup_address.postcode == "3122"
    assert order.parcels[0].weight == 2


def test_new_order_with_errors_keeps_parcels_and_stores_nothing(client):
    response = client.post("/submit_order", data={**ORDER, "phone": "12"})
    page = response.get_data(as_text=True)
    assert 'value="3.5"' in page and 'value="20 x 20 x 20"' in page
    assert 'name="request_id"' not in page
    assert not state.order_requests and not state.customers


def test_delete_asks_first_and_can_go_back(client):
    order = draft_order(client)
    url = f"/delete_order_request?request_id={order.request_id}"
    page = client.get(url).get_data(as_text=True)
    assert "Delete this order request?" in page and "Go back" in page
    assert f"/verify_order_request?request_id={order.request_id}" in page
    assert order.request_id in state.order_requests


def test_confirmed_delete_removes_order_and_customer(client):
    order = draft_order(client)
    data = {"request_id": order.request_id}
    response = client.post("/delete_order_request", data=data)
    assert response.status_code == 200
    assert "has been deleted" in response.get_data(as_text=True)
    assert not state.order_requests and not state.customers
    assert client.post("/delete_order_request", data=data).status_code == 404


def test_sent_order_cannot_be_changed(client):
    order = draft_order(client)
    send(client, order)
    args = f"?request_id={order.request_id}"
    assert client.get("/edit_order_request" + args).status_code == 400
    assert client.get("/delete_order_request" + args).status_code == 400
    data = {"request_id": order.request_id}
    assert client.post("/delete_order_request", data=data).status_code == 400
    assert client.post("/submit_order", data={**ORDER, **data}).status_code == 400
    assert send(client, order).status_code == 400
    assert order.request_id in state.order_requests
    response = client.get("/verify_order_request" + args)
    assert "no longer be changed" in response.get_data(as_text=True)


def test_unknown_order_is_not_found(client):
    args = "?request_id=missing"
    for url in ("/verify_order_request", "/edit_order_request", "/delete_order_request"):
        assert client.get(url + args).status_code == 404
    assert client.post("/submit_order", data={**ORDER, "request_id": "missing"}).status_code == 404
