# Changelog

## [0.1.0] - Initial release

The first working version of the Airbnb Clone: a small Flask + SQLite
property rental booking app covering the core mechanics of a booking
platform.

Included in the initial commit:

- `app/db.py` — SQLite schema (`host`, `listing`, `booking`, `review`
  tables) and a `get_db`/`close_db` per-request connection pattern.
- `app/booking_logic.py` — core domain logic:
  - Half-open `[check_in, check_out)` date-range overlap detection.
  - `is_available` / `create_booking` with overlap rejection and
    `total_price = nights * price_per_night` computation.
  - `cancel_booking`, which immediately frees a booking's dates.
  - `average_rating`, with graceful zero-review handling.
  - `search_listings`, filterable by city, price range, and guest count.
- `app/routes.py` — Flask views: home/search, new listing form, listing
  detail, book, cancel, and add-review endpoints.
- Jinja2 templates and a plain CSS stylesheet under `app/templates` /
  `app/static`.
- `run.py` — dev entry point.
- `tests/test_booking.py` — 14 unit tests via Flask's test client, covering
  search filtering, overlap/adjacency rules, pricing, cancellation, and
  reviews, run against an isolated temporary SQLite database per test app.
- A GitHub Actions workflow running the test suite on Python 3.11 and
  3.12.
- MIT license.

## [Unreleased]

- `CONTRIBUTING.md` with setup/test/style guidelines.
- Tests for `is_available`'s `exclude_booking_id` parameter and for
  booking against a nonexistent listing (previously untested).
- Fixed a bug where submitting a malformed booking date (e.g. not in
  `YYYY-MM-DD` format) raised an unhandled `ValueError` and returned a
  raw Flask 500 error page; it now flashes a friendly message instead.
- Troubleshooting/FAQ section in the README.
