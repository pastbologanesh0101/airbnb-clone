# Contributing

Thanks for looking at contributing to this Airbnb Clone. It's a small
Flask + SQLite app that models the core mechanics of a booking platform
(listings, availability, bookings, cancellation, reviews).

## Running the app locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Running the tests

```bash
pip install pytest
pytest -v
```

Tests use `create_app(testing=True)`, which points the app at a fresh
temporary SQLite file per test app, so the suite never touches your local
`instance/airbnb.db`. Run the full suite before opening a pull request.

## Code style

- Keep domain logic (overlap detection, pricing, ratings, search) in
  `app/booking_logic.py`, and keep `app/routes.py` thin — routes should
  parse the request, call into `booking_logic`, and render/redirect.
- Raise `booking_logic.BookingError` for invalid booking operations rather
  than letting a raw exception surface to the user; routes catch
  `BookingError` and turn it into a flashed message.
- Bookings use a half-open `[check_in, check_out)` date convention — see
  the "Date / overlap convention" section in the README before touching
  `ranges_overlap` or `is_available`.
- Match the existing style: 4-space indents, parameterized SQL (never
  string-interpolate user input into a query).

## Submitting changes

1. Fork the repo and create a branch for your change.
2. Add or update tests in `tests/test_booking.py` for any behavior change.
3. Run `pytest -v` and make sure everything passes.
4. Open a pull request describing what changed and why.
