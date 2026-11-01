"""Food Waste Matcher: donors post leftover food, nearby NGOs claim it."""
import math
import os
import random
import sqlite3
from datetime import datetime, timedelta
from html import escape

import folium
from flask import Flask, flash, g, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "food.db")

# Named areas so people without GPS can still pick a spot (lat, lng).
AREAS = {
    "Bhatpara": (22.8667, 88.4167),
    "Barrackpore": (22.7650, 88.3770),
    "Kalyani": (22.9750, 88.4340),
    "Dum Dum": (22.6230, 88.4190),
    "Salt Lake": (22.5800, 88.4160),
    "Park Street": (22.5530, 88.3520),
    "Howrah": (22.5958, 88.2636),
    "Jadavpur": (22.4990, 88.3710),
}
DONOR_TYPES = {
    "restaurant": "Restaurant",
    "wedding": "Wedding or event",
    "bakery": "Bakery or sweet shop",
    "home": "Home or community kitchen",
}
TYPE_COLOURS = {"restaurant": "#F6B79F", "wedding": "#B9A9E8", "bakery": "#F3D86B", "home": "#F0A9BE"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_name TEXT NOT NULL, donor_type TEXT NOT NULL,
    food TEXT NOT NULL, servings INTEGER NOT NULL,
    address TEXT, contact TEXT,
    lat REAL NOT NULL, lng REAL NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    claimed_by TEXT, claimed_phone TEXT, claimed_at TEXT,
    created_at TEXT NOT NULL
);
"""


# ---------- database helpers ----------
def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM donations").fetchone()[0] == 0:
        seed(conn)
    conn.commit()
    conn.close()


def seed(conn):
    """A few demo rows so the app looks alive on first run."""
    demo = [
        ("Sharma's Biryani House", "restaurant", "Chicken biryani and raita", 40, "Park Street", 4),
        ("Mehta-Das Wedding", "wedding", "Veg thali: rice, dal, two sabzis", 120, "Salt Lake", 3),
        ("Mithai Mahal", "bakery", "Assorted sweets and samosas", 30, "Barrackpore", 8),
        ("Maa Annapurna Kitchen", "home", "Khichuri and begun bhaja", 25, "Bhatpara", 5),
        ("Hotel Sagar", "restaurant", "Roti, paneer curry, jeera rice", 50, "Howrah", 2),
    ]
    for name, kind, food, servings, area, hours in demo:
        lat, lng = jitter(*AREAS[area])
        conn.execute(
            "INSERT INTO donations (donor_name, donor_type, food, servings, address, contact,"
            " lat, lng, expires_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (name, kind, food, servings, area, "98300 00000", lat, lng,
             (datetime.now() + timedelta(hours=hours)).isoformat(timespec="seconds"), now_iso()),
        )


def jitter(lat, lng, spread=0.006):
    """Nudge area-based pins slightly so donors in one area don't stack on the map."""
    return lat + random.uniform(-spread, spread), lng + random.uniform(-spread, spread)


# ---------- small utilities ----------
def haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@app.template_filter("time_left")
def time_left(expires_at):
    mins = int((datetime.fromisoformat(expires_at) - datetime.now()).total_seconds() // 60)
    if mins <= 0:
        return "expired"
    h, m = divmod(mins, 60)
    return f"{h}h {m}m left" if h else f"{m} min left"


def safe_back(url):
    return url if url and url.startswith("/") and not url.startswith("//") else url_for("find")


# ---------- routes ----------
@app.route("/")
def index():
    conn = db()
    now = now_iso()
    stats = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN status='claimed' THEN servings END),0) AS meals,"
        " COUNT(CASE WHEN status='available' AND expires_at>? THEN 1 END) AS open_now,"
        " COUNT(CASE WHEN status='claimed' THEN 1 END) AS pickups FROM donations", (now,)
    ).fetchone()
    latest = conn.execute(
        "SELECT * FROM donations WHERE status='available' AND expires_at>? ORDER BY id DESC LIMIT 3", (now,)
    ).fetchall()
    recent = conn.execute(
        "SELECT * FROM donations WHERE status='claimed' ORDER BY claimed_at DESC LIMIT 4"
    ).fetchall()
    return render_template("index.html", stats=stats, latest=latest, recent=recent, types=DONOR_TYPES)


@app.route("/donate", methods=["GET", "POST"])
def donate():
    if request.method == "POST":
        f = request.form
        errors = []
        for field, label in [("donor_name", "your name"), ("food", "what food you have")]:
            if not f.get(field, "").strip():
                errors.append(f"Please add {label}.")
        try:
            servings = int(f.get("servings", ""))
            if not 1 <= servings <= 5000:
                raise ValueError
        except ValueError:
            errors.append("Servings should be a number between 1 and 5000.")
        if f.get("donor_type") not in DONOR_TYPES:
            errors.append("Please choose what kind of donor you are.")

        if f.get("lat") and f.get("lng"):
            try:
                lat, lng = float(f["lat"]), float(f["lng"])
            except ValueError:
                lat = lng = None
        elif f.get("area") in AREAS:
            lat, lng = jitter(*AREAS[f["area"]])
        else:
            lat = lng = None
        if lat is None:
            errors.append("Please pick your area or share your location.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("donate.html", areas=AREAS, types=DONOR_TYPES, form=f), 400

        hours = min(max(int(f.get("hours", 4) or 4), 1), 24)
        db().execute(
            "INSERT INTO donations (donor_name, donor_type, food, servings, address, contact,"
            " lat, lng, expires_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f["donor_name"].strip(), f["donor_type"], f["food"].strip(), servings,
             f.get("address", "").strip() or f.get("area", ""), f.get("contact", "").strip(),
             lat, lng, (datetime.now() + timedelta(hours=hours)).isoformat(timespec="seconds"), now_iso()),
        )
        db().commit()
        flash("Thank you! Your food is now visible to NGOs nearby.", "ok")
        return redirect(url_for("find", area=f.get("area", "")) if not f.get("lat")
                        else url_for("find", lat=lat, lng=lng))
    return render_template("donate.html", areas=AREAS, types=DONOR_TYPES, form={})


@app.route("/find")
def find():
    area = request.args.get("area", "Bhatpara")
    try:
        lat, lng = float(request.args["lat"]), float(request.args["lng"])
        where = "your location"
    except (KeyError, ValueError):
        area = area if area in AREAS else "Bhatpara"
        lat, lng = AREAS[area]
        where = area

    rows = db().execute(
        "SELECT * FROM donations WHERE status='available' AND expires_at>?", (now_iso(),)
    ).fetchall()
    items = [dict(r, distance=haversine_km(lat, lng, r["lat"], r["lng"])) for r in rows]
    items.sort(key=lambda d: d["distance"])

    m = folium.Map(location=[lat, lng], zoom_start=11, tiles="OpenStreetMap", width="100%", height=480)
    folium.CircleMarker([lat, lng], radius=9, color="#6C8EBF", fill=True, fill_color="#A8C8F0",
                        fill_opacity=0.95, tooltip="You are here").add_to(m)
    for d in items:
        folium.CircleMarker(
            [d["lat"], d["lng"]], radius=11, color="#ffffff", weight=2, fill=True,
            fill_color=TYPE_COLOURS[d["donor_type"]], fill_opacity=0.95,
            popup=folium.Popup(
                f"<b>{escape(d['donor_name'])}</b><br>{escape(d['food'])}<br>{d['servings']} servings"
                f" · {d['distance']:.1f} km away", max_width=240),
            tooltip=d["donor_name"],
        ).add_to(m)
    if items:
        m.fit_bounds([[lat, lng]] + [[d["lat"], d["lng"]] for d in items[:8]], padding=(30, 30))

    return render_template("find.html", items=items, map_html=m._repr_html_(), areas=AREAS,
                           area=area, where=where, types=DONOR_TYPES, back=request.full_path.rstrip("?"))


@app.route("/claim/<int:donation_id>", methods=["POST"])
def claim(donation_id):
    name, phone = request.form.get("ngo_name", "").strip(), request.form.get("phone", "").strip()
    back = safe_back(request.form.get("back"))
    if not name or not phone:
        flash("Please add your NGO name and phone number to claim.", "error")
        return redirect(back)
    cur = db().execute(
        "UPDATE donations SET status='claimed', claimed_by=?, claimed_phone=?, claimed_at=?"
        " WHERE id=? AND status='available' AND expires_at>?",
        (name, phone, now_iso(), donation_id, now_iso()),
    )
    db().commit()
    if cur.rowcount:
        d = db().execute("SELECT * FROM donations WHERE id=?", (donation_id,)).fetchone()
        flash(f"It's yours! Contact {d['donor_name']} on {d['contact'] or 'the address shown'} "
              f"and pick up from {d['address']}.", "ok")
    else:
        flash("Sorry, someone else just claimed this one, or it has expired.", "error")
    return redirect(back)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
