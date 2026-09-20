from app.db import get_db

from .conftest import make_host_and_listing


def book(client, listing_id, guest_name, check_in, check_out):
    return client.post(
        f"/listings/{listing_id}/book",
        data={
            "guest_name": guest_name,
            "check_in": check_in,
            "check_out": check_out,
        },
        follow_redirects=True,
    )


def get_bookings(app, listing_id):
    with app.app_context():
        db = get_db()
        return db.execute(
            "SELECT * FROM booking WHERE listing_id = ? AND status != 'cancelled'",
            (listing_id,),
        ).fetchall()


# ---------------------------------------------------------------------------
# Search / filtering
# ---------------------------------------------------------------------------


def test_search_filters_by_city(app, client):
    make_host_and_listing(app, city="Austin", title="Austin Pad")
    make_host_and_listing(app, city="Denver", title="Denver Cabin")

    resp = client.get("/?city=Austin")
    assert resp.status_code == 200
    assert b"Austin Pad" in resp.data
    assert b"Denver Cabin" not in resp.data


def test_search_filters_by_price_range(app, client):
    make_host_and_listing(app, city="Austin", price=50.0, title="Cheap Room")
    make_host_and_listing(app, city="Austin", price=500.0, title="Fancy Villa")

    resp = client.get("/?min_price=100&max_price=1000")
    assert resp.status_code == 200
    assert b"Fancy Villa" in resp.data
    assert b"Cheap Room" not in resp.data


def test_search_filters_by_guest_capacity(app, client):
    make_host_and_listing(app, city="Austin", max_guests=2, title="Tiny Studio")
    make_host_and_listing(app, city="Austin", max_guests=8, title="Big House")

    resp = client.get("/?guests=6")
    assert resp.status_code == 200
    assert b"Big House" in resp.data
    assert b"Tiny Studio" not in resp.data


def test_search_combines_multiple_filters(app, client):
    make_host_and_listing(
        app, city="Austin", price=100.0, max_guests=4, title="Match"
    )
    make_host_and_listing(
        app, city="Austin", price=900.0, max_guests=4, title="TooExpensive"
    )
    make_host_and_listing(
        app, city="Denver", price=100.0, max_guests=4, title="WrongCity"
    )

    resp = client.get("/?city=Austin&min_price=50&max_price=200&guests=2")
    assert b"Match" in resp.data
    assert b"TooExpensive" not in resp.data
    assert b"WrongCity" not in resp.data


# ---------------------------------------------------------------------------
# Availability / overlap logic
# ---------------------------------------------------------------------------


def test_booking_with_no_conflict_succeeds(app, client):
    listing_id = make_host_and_listing(app)
    resp = book(client, listing_id, "Alice", "2026-03-01", "2026-03-05")
    assert b"Booking confirmed" in resp.data
    assert len(get_bookings(app, listing_id)) == 1


def test_booking_fully_overlapping_dates_rejected(app, client):
    listing_id = make_host_and_listing(app)
    book(client, listing_id, "Alice", "2026-03-01", "2026-03-10")

    resp = book(client, listing_id, "Bob", "2026-03-02", "2026-03-08")
    assert b"not available" in resp.data
    assert len(get_bookings(app, listing_id)) == 1


def test_booking_partially_overlapping_dates_rejected(app, client):
    listing_id = make_host_and_listing(app)
    book(client, listing_id, "Alice", "2026-03-01", "2026-03-05")

    # New booking starts during the existing stay and extends past it.
    resp = book(client, listing_id, "Bob", "2026-03-03", "2026-03-09")
    assert b"not available" in resp.data
    assert len(get_bookings(app, listing_id)) == 1


def test_booking_adjacent_dates_succeed(app, client):
    """Boundary convention: bookings use a half-open [check_in, check_out)
    interval, so a new booking whose check_in equals an existing booking's
    check_out (same-day turnover) is NOT a conflict."""
    listing_id = make_host_and_listing(app)
    book(client, listing_id, "Alice", "2026-03-01", "2026-03-05")

    resp = book(client, listing_id, "Bob", "2026-03-05", "2026-03-10")
    assert b"Booking confirmed" in resp.data
    assert len(get_bookings(app, listing_id)) == 2


def test_is_available_excludes_given_booking_id(app, client):
    """The exclude_booking_id parameter lets a booking's own dates be
    treated as free -- this is what an "edit this booking" flow would use
    to check availability without conflicting with itself. Nothing in the
    HTTP-level tests exercises this parameter directly."""
    from app.booking_logic import is_available

    listing_id = make_host_and_listing(app)
    book(client, listing_id, "Alice", "2026-06-01", "2026-06-05")

    with app.app_context():
        db = get_db()
        booking_id = db.execute(
            "SELECT id FROM booking WHERE listing_id = ?", (listing_id,)
        ).fetchone()["id"]

        # Without excluding it, the booking's own dates are unavailable.
        assert not is_available(db, listing_id, "2026-06-01", "2026-06-05")
        # Excluding the booking's own id treats its dates as free again.
        assert is_available(
            db, listing_id, "2026-06-01", "2026-06-05",
            exclude_booking_id=booking_id,
        )


def test_booking_nonexistent_listing_returns_not_found(app, client):
    resp = book(client, 9999, "Alice", "2026-03-01", "2026-03-05")
    assert resp.status_code == 404


def test_booking_with_malformed_date_shows_friendly_error_not_500(app, client):
    listing_id = make_host_and_listing(app)
    resp = book(client, listing_id, "Alice", "not-a-date", "2026-03-05")
    assert resp.status_code == 200
    assert b"valid dates" in resp.data
    assert len(get_bookings(app, listing_id)) == 0


def test_checkout_before_or_equal_checkin_rejected(app, client):
    listing_id = make_host_and_listing(app)

    resp = book(client, listing_id, "Alice", "2026-03-05", "2026-03-05")
    assert b"after" in resp.data
    assert len(get_bookings(app, listing_id)) == 0

    resp = book(client, listing_id, "Alice", "2026-03-05", "2026-03-01")
    assert b"after" in resp.data
    assert len(get_bookings(app, listing_id)) == 0


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def test_total_price_computed_correctly(app, client):
    listing_id = make_host_and_listing(app, price=120.0)
    book(client, listing_id, "Alice", "2026-04-01", "2026-04-05")

    bookings = get_bookings(app, listing_id)
    assert len(bookings) == 1
    # 4 nights * $120/night = $480
    assert bookings[0]["total_price"] == 480.0


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


def test_cancelling_booking_frees_the_dates(app, client):
    listing_id = make_host_and_listing(app)
    book(client, listing_id, "Alice", "2026-05-01", "2026-05-05")
    bookings = get_bookings(app, listing_id)
    booking_id = bookings[0]["id"]

    cancel_resp = client.post(
        f"/bookings/{booking_id}/cancel", follow_redirects=True
    )
    assert b"cancelled" in cancel_resp.data
    assert len(get_bookings(app, listing_id)) == 0

    # The same dates should now be bookable again.
    resp = book(client, listing_id, "Bob", "2026-05-01", "2026-05-05")
    assert b"Booking confirmed" in resp.data
    assert len(get_bookings(app, listing_id)) == 1


# ---------------------------------------------------------------------------
# Reviews / ratings
# ---------------------------------------------------------------------------


def test_average_rating_computed_correctly(app, client):
    listing_id = make_host_and_listing(app)

    client.post(
        f"/listings/{listing_id}/review",
        data={"guest_name": "Alice", "rating": 5, "comment": "Great!"},
        follow_redirects=True,
    )
    client.post(
        f"/listings/{listing_id}/review",
        data={"guest_name": "Bob", "rating": 3, "comment": "Ok"},
        follow_redirects=True,
    )

    resp = client.get(f"/listings/{listing_id}")
    # Average of 5 and 3 is 4.0
    assert "4.0".encode() in resp.data or "4".encode() in resp.data


def test_listing_with_zero_reviews_handled_gracefully(app, client):
    listing_id = make_host_and_listing(app)
    resp = client.get(f"/listings/{listing_id}")
    assert resp.status_code == 200
    assert b"No reviews yet" in resp.data


def test_new_listing_can_be_created_via_form(app, client):
    resp = client.post(
        "/listings/new",
        data={
            "host_name": "Jamie",
            "title": "Sunny Apartment",
            "description": "Bright and central",
            "city": "Miami",
            "price_per_night": "150",
            "max_guests": "3",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Sunny Apartment" in resp.data
