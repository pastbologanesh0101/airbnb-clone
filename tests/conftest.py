import pytest

from app import create_app
from app.db import get_db


@pytest.fixture
def app():
    app = create_app(testing=True)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def make_host_and_listing(
    app, city="Austin", price=100.0, max_guests=4, title="Cozy Loft"
):
    """Insert a host and listing directly via the DB and return the listing id."""
    with app.app_context():
        db = get_db()
        cur = db.execute("INSERT INTO host (name) VALUES (?)", ("Jordan",))
        host_id = cur.lastrowid
        cur = db.execute(
            "INSERT INTO listing (host_id, title, description, city, "
            "price_per_night, max_guests) VALUES (?, ?, ?, ?, ?, ?)",
            (host_id, title, "A lovely place", city, price, max_guests),
        )
        db.commit()
        return cur.lastrowid
