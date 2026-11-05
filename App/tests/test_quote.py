"""Tests for the quote flow: request, accept and deny."""

from datetime import date, timedelta

import pytest

import state
from Models.Order_Request import OrderRequest
from Models.Quote import Quote


def make_order():
    """An order request the customer has already sent."""
    order = OrderRequest.create("customer-1", number_of_parcels=1)
    order.send()
    return order


@pytest.fixture
def client():
    import app as flask_app
    for store in (state.deliveries, state.quotes, state.order_requests, state.customers):
        store.clear()
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


def submit_order(client):
    """Submit and send a valid order and return the order request that was stored."""
    response = client.post("/submit_order", data={
        "firstname": "Ann", "lastname": "Lee", "email": "ann@example.com",
        "phone": "0400000000",
        "pickupstreet": "1 High St", "pickupsuburb": "Hawthorn", "pickuppostcode": "3122",
        "deliverystreet": "2 Low St", "deliverysuburb": "Kew", "deliverypostcode": "3101",
        "parcel_weight": "2", "dimensions": "10 x 10 x 10", "parcel_fragile": "false",
    })
    assert response.status_code == 302
    order = next(iter(state.order_requests.values()))
    assert client.post("/verify_order_request",
                       data={"request_id": order.request_id}).status_code == 200
    return order


def submit_quote(client, request_id, fee="45"):
    return client.post("/submit_quote", data={
        "request_id": request_id, "deliveryfee": fee,
        "estimateddeliverytime": "5",
    })


# -- models ------------------------------------------------------------------

def test_request_quote_links_quote_and_marks_order_quoted():
    order = make_order()
    quote = order.request_quote(45, 5)
    assert quote.request_id == order.request_id
    assert quote.deliveryfee == 45
    assert order.status == "quoted"


def test_order_request_only_gets_one_quote():
    order = make_order()
    order.request_quote(45, 5)
    with pytest.raises(ValueError, match="pending order requests"):
        order.request_quote(50, 6)


def test_invalid_quote_leaves_order_pending():
    order = make_order()
    with pytest.raises(ValueError):
        order.request_quote("not a number", 5)
    assert order.status == "pending"


def test_accept_creates_delivery_and_updates_order():
    order = make_order()
    quote = order.request_quote(45, 5)
    delivery = quote.accept(order)
    assert quote.status == "accepted"
    assert order.status == "accepted"
    assert delivery.request_id == order.request_id
    assert delivery.delivery_date == (date.today() + timedelta(days=5)).isoformat()


def test_expired_quote_cannot_be_accepted():
    order = make_order()
    order.status = "quoted"
    quote = Quote(request_id=order.request_id, deliveryfee=45,
                  estimateddeliverytime=5,
                  expiredate=date.today() - timedelta(days=1))
    with pytest.raises(ValueError, match="expired"):
        quote.accept(order)
    assert quote.status == "pending"
    assert order.status == "quoted"


def test_answered_quote_cannot_be_answered_again():
    order = make_order()
    quote = order.request_quote(45, 5)
    quote.deny()
    assert quote.status == "denied"
    with pytest.raises(ValueError, match="already been denied"):
        quote.accept(order)
    with pytest.raises(ValueError, match="already been denied"):
        quote.deny()


# -- routes ------------------------------------------------------------------

def test_order_to_delivery_through_the_routes(client):
    order = submit_order(client)
    assert submit_quote(client, order.request_id).status_code == 200
    quote = next(iter(state.quotes.values()))
    response = client.post("/accept_quote", data={"quote_id": quote.quoteid})
    assert response.status_code == 200
    assert order.status == "accepted"
    delivery = next(iter(state.deliveries.values()))
    assert delivery.request_id == order.request_id


def test_second_quote_is_rejected(client):
    order = submit_order(client)
    submit_quote(client, order.request_id)
    response = submit_quote(client, order.request_id, fee="50")
    assert response.status_code == 400
    assert len(state.quotes) == 1


def test_invalid_fee_shows_the_quote_page_again(client):
    order = submit_order(client)
    response = submit_quote(client, order.request_id, fee="abc")
    assert response.status_code == 200
    assert not state.quotes
    assert order.status == "pending"


def test_accepting_twice_creates_one_delivery(client):
    order = submit_order(client)
    submit_quote(client, order.request_id)
    quote = next(iter(state.quotes.values()))
    client.post("/accept_quote", data={"quote_id": quote.quoteid})
    response = client.post("/accept_quote", data={"quote_id": quote.quoteid})
    assert response.status_code == 400
    assert len(state.deliveries) == 1


def test_deny_creates_no_delivery(client):
    order = submit_order(client)
    submit_quote(client, order.request_id)
    quote = next(iter(state.quotes.values()))
    response = client.post("/deny_quote", data={"quote_id": quote.quoteid})
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "successfully denied" in page and quote.quoteid in page
    assert quote.status == "denied"
    assert not state.deliveries


def test_accept_shows_the_accepted_page(client):
    order = submit_order(client)
    submit_quote(client, order.request_id)
    quote = next(iter(state.quotes.values()))
    response = client.post("/accept_quote", data={"quote_id": quote.quoteid})
    page = response.get_data(as_text=True)
    delivery = next(iter(state.deliveries.values()))
    assert "Quote accepted!" in page and "denied" not in page
    assert quote.quoteid in page and delivery.delivery_id in page


@pytest.mark.parametrize("days", ["1", "30"])
def test_estimate_limits_are_accepted(client, days):
    order = submit_order(client)
    client.post("/submit_quote", data={
        "request_id": order.request_id, "deliveryfee": "45", "estimateddeliverytime": days,
    })
    quote = next(iter(state.quotes.values()))
    response = client.post("/accept_quote", data={"quote_id": quote.quoteid})
    expected = date.today() + timedelta(days=int(days))
    assert response.status_code == 200
    assert expected.isoformat() in response.get_data(as_text=True)


@pytest.mark.parametrize("days", ["", "0", "31", "-5", "2.5", "banana", "<script>x</script>"])
def test_invalid_estimate_shows_the_quote_page_again(client, days):
    order = submit_order(client)
    response = client.post("/submit_quote", data={
        "request_id": order.request_id, "deliveryfee": "45", "estimateddeliverytime": days,
    })
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "estimateddeliverytime:" in page and "<script>" not in page
    assert not state.quotes
    assert order.status == "pending"
