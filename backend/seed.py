"""Synthetic seed data for Wishing Tree.

EVERYTHING HERE IS INVENTED. There is no real data in this project.
 - Family and donor aliases are made up labels, never real names.
 - Street names are invented; they are not real New Haven addresses.
 - Phone numbers all use the 555-01xx range, which is reserved for fiction.
 - Product links point at allowlisted retailers with made-up product paths.
   No part of this app ever fetches them.

Run it directly to rebuild the database:

    ./.venv/bin/python -m backend.seed --reset

The app also calls seed_if_empty() on startup, so a fresh clone comes up with
a populated wish wall without the teaching staff running anything extra.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from backend import config, db
from backend.models import (
    Category,
    Donor,
    DonorPreference,
    Family,
    Pledge,
    PledgeStatus,
    Request,
    RequestStatus,
    RequestType,
    Weekday,
    WindowResponse,
)

_WEEKDAY_INDEX = {
    Weekday.MONDAY: 0, Weekday.TUESDAY: 1, Weekday.WEDNESDAY: 2, Weekday.THURSDAY: 3,
    Weekday.FRIDAY: 4, Weekday.SATURDAY: 5, Weekday.SUNDAY: 6,
}


def next_weekday(start: date, day: Weekday) -> date:
    """The next date on or after `start` that falls on `day`."""
    ahead = (_WEEKDAY_INDEX[day] - start.weekday()) % 7
    return start + timedelta(days=ahead)


# --------------------------------------------------------------------------
# Families — alias, zip, invented street address, fiction-range phone
# --------------------------------------------------------------------------

FAMILIES: list[tuple[str, str, str, str]] = [
    ("Family A04", "06511", "118 Larkspur St, Apt 3B, New Haven, CT 06511", "(203) 555-0104"),
    ("Family A07", "06513", "42 Ridgewillow Ave, New Haven, CT 06513",      "(203) 555-0107"),
    ("Family A12", "06519", "9 Tannery Row, Unit 2, New Haven, CT 06519",   "(203) 555-0112"),
    ("Family A15", "06511", "260 Fernbrook Ln, New Haven, CT 06511",        "(203) 555-0115"),
    ("Family A19", "06515", "77 Hollowmill Rd, New Haven, CT 06515",        "(203) 555-0119"),
    ("Family A23", "06512", "515 Candleberry Dr, East Haven, CT 06512",     "(203) 555-0123"),
    ("Family A27", "06513", "31 Quarry Bend, Apt 1, New Haven, CT 06513",   "(203) 555-0127"),
    ("Family A31", "06516", "804 Saltmeadow Way, West Haven, CT 06516",     "(203) 555-0131"),
    ("Family A34", "06510", "16 Printers Ct, Apt 5, New Haven, CT 06510",   "(203) 555-0134"),
    ("Family A38", "06514", "233 Thistledown Rd, Hamden, CT 06514",         "(203) 555-0138"),
    ("Family A42", "06511", "58 Copperleaf St, Apt 2C, New Haven, CT 06511", "(203) 555-0142"),
    ("Family A46", "06519", "140 Millpond Walk, New Haven, CT 06519",       "(203) 555-0146"),
    ("Family A51", "06517", "67 Brambleton Ave, Hamden, CT 06517",          "(203) 555-0151"),
    ("Family A55", "06518", "390 Winterbourne Rd, Hamden, CT 06518",        "(203) 555-0155"),
    ("Family A58", "06525", "12 Stonefield Ln, Woodbridge, CT 06525",       "(203) 555-0158"),
]

# --------------------------------------------------------------------------
# Donors
# --------------------------------------------------------------------------

DONORS: list[dict] = [
    dict(alias="Donor D01", zip="06511", contact_address="88 Elmcrest Ter, New Haven, CT 06511",
         contact_phone="(203) 555-0201", budget_usd=75.0,
         preferred_categories=[Category.CLOTHING, Category.SCHOOL_SUPPLIES],
         preference=DonorPreference.SPECIFIC),
    dict(alias="Donor D02", zip="06517", contact_address="451 Harrowgate Rd, Hamden, CT 06517",
         contact_phone="(203) 555-0202", budget_usd=200.0,
         preferred_categories=[Category.RENT_UTILITIES, Category.FOOD],
         preference=DonorPreference.FLEXIBLE),
    dict(alias="Donor D03", zip="06510", contact_address="7 Clocktower Sq, Apt 9, New Haven, CT 06510",
         contact_phone="(203) 555-0203", budget_usd=50.0,
         preferred_categories=[Category.ESSENTIALS, Category.FOOD],
         preference=DonorPreference.EITHER),
    dict(alias="Donor D04", zip="06515", contact_address="202 Birchfield Ave, New Haven, CT 06515",
         contact_phone="(203) 555-0204", budget_usd=120.0,
         preferred_categories=[Category.GIFTS, Category.CLOTHING],
         preference=DonorPreference.SPECIFIC),
    dict(alias="Donor D05", zip="06520", contact_address="1 Gateway Hall, Box 414, New Haven, CT 06520",
         contact_phone="(203) 555-0205", budget_usd=40.0,
         preferred_categories=[Category.SCHOOL_SUPPLIES],
         preference=DonorPreference.EITHER),
    dict(alias="Donor D06", zip="06518", contact_address="315 Foxglove Dr, Hamden, CT 06518",
         contact_phone="(203) 555-0206", budget_usd=350.0,
         preferred_categories=[Category.RENT_UTILITIES, Category.OTHER],
         preference=DonorPreference.FLEXIBLE),
    dict(alias="Donor D07", zip="06512", contact_address="60 Seabright Ct, East Haven, CT 06512",
         contact_phone="(203) 555-0207", budget_usd=90.0,
         preferred_categories=[Category.CLOTHING, Category.ESSENTIALS, Category.GIFTS],
         preference=DonorPreference.EITHER),
    dict(alias="Donor D08", zip="06525", contact_address="24 Orchard Gate, Woodbridge, CT 06525",
         contact_phone="(203) 555-0208", budget_usd=500.0,
         preferred_categories=[Category.RENT_UTILITIES, Category.FOOD, Category.OTHER],
         preference=DonorPreference.FLEXIBLE),
]

# --------------------------------------------------------------------------
# Requests — 40 wishes. `days` is an offset from today, so the data stays fresh.
# Specific wishes carry a product link; flexible ones carry essentials only.
# --------------------------------------------------------------------------

S, F = RequestType.SPECIFIC, RequestType.FLEXIBLE

REQUESTS: list[dict] = [
    # --- Family A04: single parent working two jobs ---
    dict(family="Family A04", category=Category.CLOTHING, type=S, days=18,
         occasion="back_to_school", status=RequestStatus.OPEN, cost=42.0,
         desc="Winter coat for my 8-year-old so he can wait for the bus in the cold.",
         link="https://www.target.com/p/kids-puffer-jacket/-/A-88204117",
         brand="Cat & Jack", size="Boys 8", color="Navy", sub=True),
    dict(family="Family A04", category=Category.FOOD, type=F, days=9,
         occasion="everyday", status=RequestStatus.OPEN, budget=(40.0, 70.0),
         desc="A grocery gift card would cover the gap in the week my hours get cut.",
         prefs="No pork; one child has a peanut allergy."),
    dict(family="Family A04", category=Category.SCHOOL_SUPPLIES, type=S, days=25,
         occasion="back_to_school", status=RequestStatus.OPEN, cost=28.0,
         desc="Backpack to replace one that split at the seam in September.",
         link="https://www.walmart.com/ip/classic-backpack-17in/553001942",
         brand="JanSport", size="17 in", color="Black", sub=True),

    # --- Family A07: child in cancer treatment ---
    dict(family="Family A07", category=Category.OTHER, type=F, days=5,
         occasion="emergency", status=RequestStatus.OPEN, budget=(60.0, 100.0),
         desc="Gas cards for the drive to my daughter's chemo appointments twice a week.",
         prefs="Any station near the hospital works."),
    dict(family="Family A07", category=Category.ESSENTIALS, type=S, days=12,
         occasion="everyday", status=RequestStatus.OPEN, cost=22.0,
         desc="Gentle unscented soap and lotion; her skin reacts to everything right now.",
         link="https://www.cvs.com/shop/sensitive-skin-care-bundle-prod9931204",
         brand="Cetaphil", size="16 oz", color=None, sub=True),
    dict(family="Family A07", category=Category.GIFTS, type=S, days=33,
         occasion="birthday", status=RequestStatus.OPEN, cost=34.0,
         desc="A soft weighted lap blanket for her 7th birthday, for the infusion chair.",
         link="https://www.amazon.com/dp/B0CT7QKMN4",
         brand="Bearaby", size="36x48 in", color="Lavender", sub=True),
    dict(family="Family A07", category=Category.FOOD, type=F, days=3,
         occasion="emergency", status=RequestStatus.PENDING_REVIEW, budget=(50.0, 80.0),
         desc="Easy freezer meals for the weeks we are at the hospital late.",
         prefs="Nothing that needs more than a microwave."),

    # --- Family A12: facing eviction ---
    dict(family="Family A12", category=Category.RENT_UTILITIES, type=F, days=7,
         occasion="emergency", status=RequestStatus.OPEN, budget=(400.0, 600.0),
         desc="Short on rent after a car repair. Paid straight to the landlord, not to us.",
         prefs="Partial help still keeps the case out of court."),
    dict(family="Family A12", category=Category.RENT_UTILITIES, type=F, days=14,
         occasion="emergency", status=RequestStatus.OPEN, budget=(120.0, 180.0),
         desc="Electric bill is past due and the shutoff notice is dated this month.",
         prefs="Paid directly to the utility company."),
    dict(family="Family A12", category=Category.ESSENTIALS, type=F, days=20,
         occasion="everyday", status=RequestStatus.OPEN, budget=(30.0, 50.0),
         desc="Diapers and wipes for a 14-month-old.",
         prefs="Size 4 diapers."),

    # --- Family A15: parent needs an interview outfit ---
    dict(family="Family A15", category=Category.CLOTHING, type=S, days=6,
         occasion="job_interview", status=RequestStatus.OPEN, cost=55.0,
         desc="Interview blazer for a front desk job I was called back for.",
         link="https://www.oldnavy.com/product/womens-classic-blazer-p-8814402",
         brand="Old Navy", size="Women's 12", color="Charcoal", sub=True),
    dict(family="Family A15", category=Category.CLOTHING, type=S, days=6,
         occasion="job_interview", status=RequestStatus.GRANTED, cost=45.0,
         desc="Closed-toe flats to go with the interview outfit.",
         link="https://www.dsw.com/en/shop/womens-pointed-flat-6618093",
         brand="LifeStride", size="Women's 8.5", color="Black", sub=True),
    dict(family="Family A15", category=Category.OTHER, type=F, days=11,
         occasion="job_interview", status=RequestStatus.OPEN, budget=(25.0, 40.0),
         desc="Bus pass for the first month until the first paycheck comes in.",
         prefs=None),

    # --- Family A19: grandmother raising two grandchildren ---
    dict(family="Family A19", category=Category.SCHOOL_SUPPLIES, type=F, days=16,
         occasion="back_to_school", status=RequestStatus.GRANTED, budget=(35.0, 60.0),
         desc="Notebooks, folders and pencils for a 4th grader and a 6th grader.",
         prefs="Teacher's list is mostly basics."),
    dict(family="Family A19", category=Category.CLOTHING, type=F, days=22,
         occasion="everyday", status=RequestStatus.OPEN, budget=(50.0, 90.0),
         desc="Warm layers for two kids who grew out of last winter's clothes.",
         prefs="Girls 10 and boys 12."),
    dict(family="Family A19", category=Category.GIFTS, type=S, days=68,
         occasion="holiday", status=RequestStatus.OPEN, cost=30.0,
         desc="A build-your-own robot kit my grandson has asked about all year.",
         link="https://www.target.com/p/stem-robot-building-kit/-/A-79114502",
         brand="Thames & Kosmos", size=None, color=None, sub=True),

    # --- Family A23: recently arrived, in English classes ---
    dict(family="Family A23", category=Category.OTHER, type=F, days=30,
         occasion="everyday", status=RequestStatus.OPEN, budget=(80.0, 150.0),
         desc="An English workbook set and a dictionary for my evening class.",
         prefs="Beginner level."),
    dict(family="Family A23", category=Category.FOOD, type=S, days=10,
         occasion="everyday", status=RequestStatus.OPEN, cost=50.0,
         desc="Grocery gift card so I can buy what the kids will actually eat.",
         link="https://www.stopandshop.com/gift-cards/product/sas-gc-50",
         brand="Stop & Shop", size="$50", color=None, sub=False),

    # --- Family A27: mother returning to work after an injury ---
    dict(family="Family A27", category=Category.CLOTHING, type=S, days=8,
         occasion="job_interview", status=RequestStatus.OPEN, cost=38.0,
         desc="Non-slip work shoes required for the kitchen job I start next month.",
         link="https://www.walmart.com/ip/slip-resistant-work-shoe/118920334",
         brand="Tredsafe", size="Women's 9", color="Black", sub=True),
    dict(family="Family A27", category=Category.RENT_UTILITIES, type=F, days=26,
         occasion="everyday", status=RequestStatus.DRAFT, budget=(150.0, 250.0),
         desc="Gas bill catch-up before the winter rate starts.",
         prefs="Paid directly to the gas company."),

    # --- Family A31: father on disability ---
    dict(family="Family A31", category=Category.OTHER, type=S, days=29,
         occasion="everyday", status=RequestStatus.OPEN, cost=65.0,
         desc="A shower chair so I can keep bathing on my own.",
         link="https://www.walgreens.com/store/c/shower-chair-with-back/ID=300411227",
         brand="Carex", size="Standard", color=None, sub=True),
    dict(family="Family A31", category=Category.ESSENTIALS, type=F, days=35,
         occasion="everyday", status=RequestStatus.MISSED, days_override=-6,
         budget=(20.0, 35.0),
         desc="Refill on wound care supplies between pharmacy deliveries.",
         prefs=None),

    # --- Family A34: after an apartment fire ---
    dict(family="Family A34", category=Category.ESSENTIALS, type=F, days=2,
         occasion="emergency", status=RequestStatus.DELIVERED, budget=(70.0, 120.0),
         desc="Replacement basics after a kitchen fire: sheets, towels, a few pots.",
         prefs="Two twin beds and one full."),
    dict(family="Family A34", category=Category.CLOTHING, type=F, days=15,
         occasion="emergency", status=RequestStatus.OPEN, budget=(100.0, 160.0),
         desc="School clothes for three kids who lost most of what they had.",
         prefs="Boys 6, girls 9, girls 13."),
    dict(family="Family A34", category=Category.OTHER, type=S, days=21,
         occasion="emergency", status=RequestStatus.GRANTED, cost=48.0,
         desc="A smoke detector set and a small fire extinguisher for the new unit.",
         link="https://www.bestbuy.com/site/smoke-detector-2-pack/6501338.p",
         brand="First Alert", size="2-pack", color=None, sub=True),

    # --- Family A38: twins starting kindergarten ---
    dict(family="Family A38", category=Category.SCHOOL_SUPPLIES, type=S, days=17,
         occasion="back_to_school", status=RequestStatus.OPEN, cost=36.0,
         desc="Two sets of the kindergarten supply list, one for each twin.",
         link="https://www.staples.com/kindergarten-supply-bundle/product_24119087",
         brand="Staples", size="2 sets", color=None, sub=True),
    dict(family="Family A38", category=Category.CLOTHING, type=S, days=24,
         occasion="back_to_school", status=RequestStatus.DROPPED_OFF, cost=52.0,
         desc="Sneakers for both twins; they wear the same size right now.",
         link="https://www.kohls.com/product/prd-6611904/kids-sneakers.jsp",
         brand="Carter's", size="Kids 11", color="Any", sub=True),
    dict(family="Family A38", category=Category.GIFTS, type=F, days=45,
         occasion="birthday", status=RequestStatus.OPEN, budget=(30.0, 50.0),
         desc="Something to share for the twins' joint 6th birthday.",
         prefs="They both like dinosaurs."),

    # --- Family A42: teen aging out of foster care ---
    dict(family="Family A42", category=Category.CLOTHING, type=S, days=9,
         occasion="job_interview", status=RequestStatus.OPEN, cost=40.0,
         desc="A dress shirt and tie for a retail interview downtown.",
         link="https://www.macys.com/shop/product/mens-dress-shirt-tie-set?ID=14920337",
         brand="Van Heusen", size="Men's 15.5 x 33", color="White", sub=True),
    dict(family="Family A42", category=Category.FOOD, type=F, days=12,
         occasion="everyday", status=RequestStatus.PENDING_REVIEW, budget=(45.0, 70.0),
         desc="Grocery help for the first month on my own.",
         prefs=None),

    # --- Family A46: parent recovering from surgery ---
    dict(family="Family A46", category=Category.FOOD, type=F, days=6,
         occasion="emergency", status=RequestStatus.DELIVERED, budget=(50.0, 80.0),
         desc="Prepared meals for the six weeks I cannot stand at the stove.",
         prefs="Soft foods."),
    dict(family="Family A46", category=Category.ESSENTIALS, type=S, days=14,
         occasion="everyday", status=RequestStatus.OPEN, cost=26.0,
         desc="A grabber tool so I can pick things up without bending.",
         link="https://www.amazon.com/dp/B07YFG4K2Q",
         brand="RMS", size='32 in', color=None, sub=True),

    # --- Family A51: family with a newborn ---
    dict(family="Family A51", category=Category.ESSENTIALS, type=S, days=5,
         occasion="everyday", status=RequestStatus.GRANTED, cost=44.0,
         desc="Newborn diapers and wipes; she arrived three weeks early.",
         link="https://www.target.com/p/newborn-diaper-wipes-bundle/-/A-54720118",
         brand="Pampers", size="Newborn", color=None, sub=True),
    dict(family="Family A51", category=Category.GIFTS, type=F, days=70,
         occasion="holiday", status=RequestStatus.OPEN, budget=(40.0, 70.0),
         desc="A first holiday gift for the baby and something small for her brother.",
         prefs="Brother is 4."),

    # --- Family A55: household after a job loss ---
    dict(family="Family A55", category=Category.RENT_UTILITIES, type=F, days=10,
         occasion="emergency", status=RequestStatus.OPEN, budget=(300.0, 500.0),
         desc="One month of rent while the unemployment claim is still processing.",
         prefs="Paid directly to the property manager."),
    dict(family="Family A55", category=Category.SCHOOL_SUPPLIES, type=F, days=23,
         occasion="back_to_school", status=RequestStatus.MISSED, days_override=-3,
         budget=(25.0, 45.0),
         desc="A calculator required for my son's math class.",
         prefs="The school asked for a graphing one."),
    dict(family="Family A55", category=Category.GIFTS, type=S, days=66,
         occasion="holiday", status=RequestStatus.OPEN, cost=25.0,
         desc="One holiday gift each for two kids, so the day is not empty.",
         link="https://www.target.com/p/holiday-art-set-kids/-/A-61880294",
         brand="Crayola", size=None, color=None, sub=True),

    # --- Family A58: caregiver for a parent with dementia ---
    dict(family="Family A58", category=Category.OTHER, type=F, days=31,
         occasion="everyday", status=RequestStatus.OPEN, budget=(90.0, 140.0),
         desc="A few hours of respite care so I can go to my own appointments.",
         prefs=None),
    dict(family="Family A58", category=Category.GIFTS, type=S, days=72,
         occasion="holiday", status=RequestStatus.OPEN, cost=32.0,
         desc="A simple large-button photo frame my mother can use on her own.",
         link="https://www.amazon.com/dp/B08X9QJ7RT",
         brand="Aura", size='10 in', color="Walnut", sub=True),
    dict(family="Family A58", category=Category.FOOD, type=S, days=20,
         occasion="birthday", status=RequestStatus.DELIVERED, cost=35.0,
         desc="A small birthday cake and dinner for my mother turning 81.",
         link="https://www.shoprite.com/sm/pickup/rsid/3000/product/bakery-cake-8in-600412",
         brand="ShopRite Bakery", size='8 in', color=None, sub=True),
]


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def _build_requests(today: date) -> list[Request]:
    by_alias = {alias: zipc for alias, zipc, _addr, _phone in FAMILIES}
    out: list[Request] = []
    for row in REQUESTS:
        offset = row.get("days_override", row["days"])
        cost = row.get("cost")
        budget = row.get("budget", (None, None))
        out.append(
            Request(
                family_alias=row["family"],
                category=row["category"],
                request_type=row["type"],
                item_description=row["desc"],
                deadline=today + timedelta(days=offset),
                occasion=row["occasion"],
                zip=by_alias[row["family"]],
                status=row["status"],
                estimated_cost_usd=cost,
                budget_min_usd=budget[0],
                budget_max_usd=budget[1],
                product_link=row.get("link"),
                brand=row.get("brand"),
                size=row.get("size"),
                color=row.get("color"),
                open_to_substitute=bool(row.get("sub", False)),
                size_preferences=row.get("prefs"),
            )
        )
    return out


def seed(db_path: Path | None = None, today: date | None = None) -> dict[str, int]:
    """Write the synthetic data. Assumes empty tables."""
    today = today or date.today()
    region = config.get_region()
    dropoff = next_weekday(today + timedelta(days=1), region.dropoff_window.day)
    delivery = next_weekday(dropoff, region.delivery_window.day)

    db.init_db(db_path)
    with db.connect(db_path) as conn:
        for alias, zipc, address, phone in FAMILIES:
            db.insert_family(
                Family(alias=alias, zip=zipc, region_slug=region.slug,
                       contact_address=address, contact_phone=phone),
                conn,
            )

        donor_aliases = []
        for row in DONORS:
            db.insert_donor(Donor(region_slug=region.slug, **row), conn)
            donor_aliases.append(row["alias"])

        # A pledge exists for every wish a donor has already claimed, so the
        # coordinator's run sheet has something real to show.
        pledged_statuses = {
            RequestStatus.GRANTED: PledgeStatus.PLEDGED,
            RequestStatus.DROPPED_OFF: PledgeStatus.DROPPED_OFF,
            RequestStatus.DELIVERED: PledgeStatus.DELIVERED,
        }
        for i, request in enumerate(_build_requests(today)):
            request_id = db.insert_request(request, conn)
            pledge_status = pledged_statuses.get(request.status)
            if pledge_status is None:
                continue
            past = request.status is not RequestStatus.GRANTED
            drop = dropoff - timedelta(days=7) if past else dropoff
            deliv = next_weekday(drop, region.delivery_window.day)
            db.insert_pledge(
                Pledge(
                    request_id=request_id,
                    donor_alias=donor_aliases[i % len(donor_aliases)],
                    dropoff_date=drop,
                    delivery_date=deliv,
                    window_response=(
                        WindowResponse.CONFIRMED
                        if request.status is RequestStatus.DELIVERED
                        else WindowResponse.PENDING
                    ),
                    status=pledge_status,
                ),
                conn,
            )
        conn.commit()
        return db.counts(conn)


def seed_if_empty(db_path: Path | None = None) -> dict[str, int]:
    """Called on startup so a fresh clone comes up with a populated wall."""
    db.init_db(db_path)
    if not db.is_empty(db_path):
        with db.connect(db_path) as conn:
            return db.counts(conn)
    return seed(db_path)


def reset(db_path: Path | None = None) -> dict[str, int]:
    path = Path(db_path or config.DB_PATH)
    if path.exists():
        path.unlink()
    return seed(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Wishing Tree database.")
    parser.add_argument("--reset", action="store_true",
                        help="delete the database first and rebuild it")
    parser.add_argument("--db", default=None, help="path to the SQLite file")
    args = parser.parse_args()

    path = Path(args.db) if args.db else config.DB_PATH
    counts = reset(path) if args.reset else seed_if_empty(path)
    print(f"Database: {path}")
    for table, n in counts.items():
        print(f"  {table:<10} {n}")


if __name__ == "__main__":
    main()
