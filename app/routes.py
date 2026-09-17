from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import booking_logic
from .db import get_db

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    db = get_db()
    city = request.args.get("city") or None
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    guests = request.args.get("guests", type=int)

    listings = booking_logic.search_listings(
        db, city=city, min_price=min_price, max_price=max_price, guests=guests
    )

    listings_with_ratings = []
    for listing in listings:
        listings_with_ratings.append(
            {
                "listing": listing,
                "avg_rating": booking_logic.average_rating(db, listing["id"]),
            }
        )

    return render_template(
        "index.html",
        listings=listings_with_ratings,
        filters={
            "city": city or "",
            "min_price": request.args.get("min_price", ""),
            "max_price": request.args.get("max_price", ""),
            "guests": request.args.get("guests", ""),
        },
    )


@bp.route("/listings/new", methods=["GET", "POST"])
def new_listing():
    db = get_db()
    if request.method == "POST":
        host_name = request.form["host_name"].strip()
        title = request.form["title"].strip()
        description = request.form.get("description", "").strip()
        city = request.form["city"].strip()
        price_per_night = float(request.form["price_per_night"])
        max_guests = int(request.form["max_guests"])

        if not host_name or not title or not city:
            flash("Host name, title, and city are required.")
            return render_template("new_listing.html", form=request.form)
        if price_per_night <= 0 or max_guests <= 0:
            flash("Price and guest capacity must be positive.")
            return render_template("new_listing.html", form=request.form)

        cur = db.execute("INSERT INTO host (name) VALUES (?)", (host_name,))
        host_id = cur.lastrowid
        cur = db.execute(
            "INSERT INTO listing (host_id, title, description, city, "
            "price_per_night, max_guests) VALUES (?, ?, ?, ?, ?, ?)",
            (host_id, title, description, city, price_per_night, max_guests),
        )
        db.commit()
        return redirect(url_for("main.listing_detail", listing_id=cur.lastrowid))

    return render_template("new_listing.html", form={})


@bp.route("/listings/<int:listing_id>")
def listing_detail(listing_id):
    db = get_db()
    listing = db.execute(
        "SELECT * FROM listing WHERE id = ?", (listing_id,)
    ).fetchone()
    if listing is None:
        return render_template("not_found.html"), 404

    bookings = db.execute(
        "SELECT * FROM booking WHERE listing_id = ? AND status != 'cancelled' "
        "ORDER BY check_in",
        (listing_id,),
    ).fetchall()
    reviews = db.execute(
        "SELECT * FROM review WHERE listing_id = ? ORDER BY id DESC",
        (listing_id,),
    ).fetchall()
    avg_rating = booking_logic.average_rating(db, listing_id)

    return render_template(
        "listing_detail.html",
        listing=listing,
        bookings=bookings,
        reviews=reviews,
        avg_rating=avg_rating,
    )


@bp.route("/listings/<int:listing_id>/book", methods=["POST"])
def book_listing(listing_id):
    db = get_db()
    guest_name = request.form["guest_name"].strip()
    check_in = request.form["check_in"]
    check_out = request.form["check_out"]

    try:
        booking_logic.create_booking(db, listing_id, guest_name, check_in, check_out)
        flash("Booking confirmed!")
    except booking_logic.BookingError as e:
        flash(str(e))

    return redirect(url_for("main.listing_detail", listing_id=listing_id))


@bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id):
    db = get_db()
    booking = db.execute(
        "SELECT * FROM booking WHERE id = ?", (booking_id,)
    ).fetchone()
    if booking is None:
        return render_template("not_found.html"), 404

    booking_logic.cancel_booking(db, booking_id)
    flash("Booking cancelled.")
    return redirect(url_for("main.listing_detail", listing_id=booking["listing_id"]))


@bp.route("/listings/<int:listing_id>/review", methods=["POST"])
def add_review(listing_id):
    db = get_db()
    guest_name = request.form["guest_name"].strip()
    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip()

    if not guest_name or rating is None or not (1 <= rating <= 5):
        flash("A guest name and a rating from 1-5 are required.")
        return redirect(url_for("main.listing_detail", listing_id=listing_id))

    db.execute(
        "INSERT INTO review (listing_id, guest_name, rating, comment) "
        "VALUES (?, ?, ?, ?)",
        (listing_id, guest_name, rating, comment),
    )
    db.commit()
    flash("Review submitted, thank you!")
    return redirect(url_for("main.listing_detail", listing_id=listing_id))
