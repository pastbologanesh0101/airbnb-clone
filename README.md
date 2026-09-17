# Airbnb Clone

A small, fully working property rental booking app built with Flask and
SQLite. It covers the core mechanics of a booking platform: listing search,
date-range availability checks, bookings with correct overlap detection,
pricing, cancellation, and reviews.

## Features

- **Listings** - hosts create listings with a title, description, city,
  nightly price, and max guest capacity.
- **Search** - filter listings by city, price range, and guest capacity.
- **Availability** - checks a requested `[check_in, check_out)` date range
  against every active (non-cancelled) booking on a listing.
- **Bookings** - creating a booking computes `total_price = nights *
  price_per_night`, rejects `check_out <= check_in`, and rejects any date
  range that overlaps an existing active booking.
- **Cancellation** - cancelling a booking immediately frees its dates for
  new bookings.
- **Reviews** - guests leave a 1-5 star rating and comment; each listing
  shows its average rating (and gracefully shows "No reviews yet" with zero
  reviews, no divide-by-zero).

## Date / overlap convention

Bookings are modeled as **half-open date ranges**: `[check_in, check_out)`.
A guest occupies the listing from the night of `check_in` through the night
*before* `check_out`. Two ranges A and B overlap if and only if:

```
A.check_in < B.check_out  AND  A.check_out > B.check_in
```

Under this rule, a new booking whose `check_in` equals an existing booking's
`check_out` is **allowed** - that's a same-day turnover (one guest checks
out in the morning, the next checks in that afternoon), which is how real
booking platforms treat checkout/checkin days. This is implemented in
`app/booking_logic.py::ranges_overlap` and covered by
`tests/test_booking.py::test_booking_adjacent_dates_succeed`.

## Project structure

```
app/
  __init__.py       # app factory (create_app)
  db.py             # SQLite connection + schema
  booking_logic.py  # core domain logic: overlap detection, pricing, ratings
  routes.py         # Flask views
  templates/        # Jinja2 templates
  static/style.css  # plain CSS
tests/
  test_booking.py   # 14 unit tests via Flask's test client
run.py              # dev entry point
```

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Then open http://127.0.0.1:5000/ in a browser. The app stores data in
`instance/airbnb.db` (SQLite), created automatically on first run.

## Running tests

```bash
pip install pytest
pytest -v
```

Tests run against an isolated temporary SQLite database created per test app
(`create_app(testing=True)`), so they never touch your local `instance/`
data.

## Example usage

1. Go to **+ Host a listing** and create a listing (e.g. "River View Condo"
   in Austin, $120/night, up to 4 guests).
2. From the home page, search by city/price/guests to find it.
3. Open the listing and submit a booking with a check-in and check-out date.
   The total price is computed automatically from the number of nights.
4. Try booking overlapping dates on the same listing - it will be rejected
   with an "unavailable" message.
5. Cancel a booking from the listing page to free its dates back up.
6. Leave a review (1-5 stars + comment); the listing's average rating
   updates immediately.

## CI

`.github/workflows/tests.yml` runs the full test suite on every push and
pull request against Python 3.11 and 3.12.

## License

MIT - see [LICENSE](LICENSE).
