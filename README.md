# Food-Waste-Matcher
A tiny web app where restaurants and weddings post leftover food and nearby NGOs claim it, sorted by distance. Stack: Flask or FastAPI, SQLite, Folium. Simple CRUD, but the social impact story is very strong.
# 🍲 Plate Share

**Tonight's leftovers can be someone's dinner.**

Plate Share is a small web app that connects people who have surplus cooked food with NGOs and volunteers who can collect it, before it goes to waste.

## The problem

Every day, restaurants, wedding halls, sweet shops and community kitchens throw away large amounts of perfectly good cooked food, often just because nobody knew who to call in time. At the same time, NGOs and shelters struggle to feed people. The food is there and the need is there, but cooked food spoils within hours, and there is no quick way to connect the two.

## The solution

Plate Share makes that connection simple and fast:

1. **Donors post** what's left: the dish, number of servings, pickup address and how long the food stays good.
2. **NGOs see it instantly** as a list sorted by real distance, alongside a map with colour-coded pins.
3. **One NGO claims it.** The claim is first-come, first-served, and the donor's contact and pickup details are shown straight away.
4. **Expired offers disappear on their own**, so nobody travels for food that is no longer safe.

No sign-up wall, no complicated setup. A donor can post in about a minute, and an NGO can claim in two taps.

## Features

- Post surplus food with servings, expiry window and pickup details
- Distance-sorted offers using the haversine formula, with exact GPS or a named area
- Interactive Folium map with pins coloured by donor type (restaurant, wedding or event, bakery, home kitchen)
- Safe claiming: a single conditional database update means two NGOs can never claim the same food
- Automatic expiry of old offers
- Live impact counters: meals rescued, open offers, successful pickups
- Gentle pastel interface that works on phones, with visible keyboard focus and reduced-motion support
- Automated tests and CI through GitHub Actions

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Flask (Python) | Small, readable, quick to build |
| Database | SQLite | Zero setup, single file |
| Maps | Folium (Leaflet + OpenStreetMap) | Interactive maps from Python |
| Frontend | Jinja templates, plain CSS and JS | No build step, fast on slow connections |
| Testing | pytest + GitHub Actions | Reliable, easy to run |

## Quick start

```bash
git clone https://github.com/<your-username>/plate-share.git
cd plate-share
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. Demo data is added on the first run. If port 5000 is busy, run `PORT=5001 python app.py`.

A clickable preview of the interface is in [`docs/demo.html`](docs/demo.html).

## Design choices

- **Distance first.** Cooked food is time-sensitive, so the closest offers always appear at the top.
- **Race-safe claims.** The claim is one `UPDATE ... WHERE status='available' AND expires_at > now`, so it is correct even when two NGOs tap at the same moment.
- **Low barrier to use.** Donors can pick a named area if they don't want to share GPS, with a small random offset so pins don't stack.
- **Human tone.** Soft colours and plain, friendly language, because this is meant to be used by busy kitchen staff and volunteers, not by tech people.

## Roadmap

- [ ] WhatsApp or SMS alerts to NGOs within a chosen radius
- [ ] Donor and NGO verification for trust and safety
- [ ] Pickup route planner for volunteers collecting from several donors
- [ ] Bengali and Hindi language toggle
- [ ] Food-safety guidance and "best before" prompts
- [ ] Admin dashboard and monthly impact reports
- [ ] Production deployment with Postgres and PostGIS

## Who it's for

Restaurants and caterers, wedding and event venues, sweet shops and bakeries, home and community kitchens, and the NGOs, shelters and volunteer groups who feed people in their neighbourhood.

## Contributing

Issues and pull requests are welcome. Run `pytest` before opening a PR. Look for the **good first issue** label if you're new.

## Licence

MIT. See [LICENSE](LICENSE).
