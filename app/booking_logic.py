"""Core booking domain logic: availability, overlap detection, pricing.

Date convention
---------------
Bookings are stored as half-open intervals [check_in, check_out): the guest
occupies the listing on the night of check_in through the night *before*
check_out. Two bookings A and B overlap if and only if:

    A.check_in < B.check_out  AND  A.check_out > B.check_in

Under this rule, a booking that checks out on day X does NOT conflict with a
booking that checks in on day X (the same calendar day is a legitimate
turnover day - one guest leaves in the morning, the next arrives in the
afternoon). This is the standard convention used by real booking platforms.

Only bookings with status != 'cancelled' are considered "active" and can
block a date range; cancelling a booking frees its dates immediately.
"""

from datetime import date, datetime


def parse_date(value):
    """Accept a date, a datetime, or an ISO 'YYYY-MM-DD' string."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(value, "%Y-%m-%d").date()


def ranges_overlap(check_in_a, check_out_a, check_in_b, check_out_b):
    """True if half-open ranges [check_in_a, check_out_a) and
    [check_in_b, check_out_b) overlap."""
    return check_in_a < check_out_b and check_out_a > check_in_b


def is_available(db, listing_id, check_in, check_out, exclude_booking_id=None):
    """Check whether [check_in, check_out) is free of any active
    (non-cancelled) booking on the given listing."""
    check_in = parse_date(check_in)
    check_out = parse_date(check_out)

    rows = db.execute(
        "SELECT id, check_in, check_out FROM booking "
        "WHERE listing_id = ? AND status != 'cancelled'",
        (listing_id,),
    ).fetchall()

    for row in rows:
        if exclude_booking_id is not None and row["id"] == exclude_booking_id:
            continue
        existing_in = parse_date(row["check_in"])
        existing_out = parse_date(row["check_out"])
        if ranges_overlap(check_in, check_out, existing_in, existing_out):
            return False
    return True


def compute_total_price(price_per_night, check_in, check_out):
    check_in = parse_date(check_in)
    check_out = parse_date(check_out)
    nights = (check_out - check_in).days
    return round(nights * price_per_night, 2)


class BookingError(ValueError):
    """Raised when a requested booking is invalid or unavailable."""


def create_booking(db, listing_id, guest_name, check_in, check_out):
    if not guest_name or not guest_name.strip():
        raise BookingError("Guest name is required.")

    try:
        check_in_d = parse_date(check_in)
        check_out_d = parse_date(check_out)
    except (ValueError, TypeError):
        raise BookingError(
            "Check-in and check-out must be valid dates in YYYY-MM-DD format."
        )

    if check_out_d <= check_in_d:
        raise BookingError("Check-out date must be after check-in date.")

    listing = db.execute(
        "SELECT * FROM listing WHERE id = ?", (listing_id,)
    ).fetchone()
    if listing is None:
        raise BookingError("Listing not found.")

    if not is_available(db, listing_id, check_in_d, check_out_d):
        raise BookingError("Listing is not available for the selected dates.")

    total_price = compute_total_price(
        listing["price_per_night"], check_in_d, check_out_d
    )

    cur = db.execute(
        "INSERT INTO booking (listing_id, guest_name, check_in, check_out, "
        "total_price, status) VALUES (?, ?, ?, ?, ?, 'confirmed')",
        (
            listing_id,
            guest_name,
            check_in_d.isoformat(),
            check_out_d.isoformat(),
            total_price,
        ),
    )
    db.commit()
    return cur.lastrowid


def cancel_booking(db, booking_id):
    booking = db.execute(
        "SELECT * FROM booking WHERE id = ?", (booking_id,)
    ).fetchone()
    if booking is None:
        raise BookingError("Booking not found.")
    db.execute(
        "UPDATE booking SET status = 'cancelled' WHERE id = ?", (booking_id,)
    )
    db.commit()


def average_rating(db, listing_id):
    row = db.execute(
        "SELECT AVG(rating) AS avg_rating, COUNT(*) AS n FROM review "
        "WHERE listing_id = ?",
        (listing_id,),
    ).fetchone()
    if row["n"] == 0 or row["avg_rating"] is None:
        return None
    return round(row["avg_rating"], 2)


def search_listings(db, city=None, min_price=None, max_price=None, guests=None):
    query = "SELECT * FROM listing WHERE 1=1"
    params = []

    if city:
        query += " AND LOWER(city) = LOWER(?)"
        params.append(city)
    if min_price is not None:
        query += " AND price_per_night >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND price_per_night <= ?"
        params.append(max_price)
    if guests is not None:
        query += " AND max_guests >= ?"
        params.append(guests)

    query += " ORDER BY id"
    return db.execute(query, params).fetchall()
