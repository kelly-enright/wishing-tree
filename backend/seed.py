"""Synthetic seed data for Wishing Tree.

EVERYTHING HERE IS INVENTED. There is no real data in this project.
 - Family and donor aliases are made up labels, never real names.
 - Street names are invented; they are not real New Haven addresses.
 - Phone numbers all use the 555-01xx range, which is reserved for fiction,
   and some people have none at all, because phone is optional.
 - Email addresses are all at example.com, which is reserved for
   documentation and reaches nobody.
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


def previous_weekday(start: date, day: Weekday) -> date:
    """The last date on or before `start` that falls on `day`."""
    back = (start.weekday() - _WEEKDAY_INDEX[day]) % 7
    return start - timedelta(days=back)


# --------------------------------------------------------------------------
# Families — alias, zip, invented street address, fiction-range phone
# --------------------------------------------------------------------------

FAMILIES: list[tuple[str, str, str, str, str]] = [
    # alias, zip, address, email, phone
    # Every zip is inside the New Haven city service area. Emails use
    # example.com, which is reserved for documentation and reaches nobody.
    ("Neighbor A04", "06511", "118 Larkspur St, Apt 3B, New Haven, CT 06511",
     "familya04@example.com", "(203) 555-0104"),
    ("Neighbor A07", "06513", "42 Ridgewillow Ave, New Haven, CT 06513",
     "familya07@example.com", "(203) 555-0107"),
    ("Neighbor A12", "06519", "9 Tannery Row, Unit 2, New Haven, CT 06519",
     "familya12@example.com", "(203) 555-0112"),
    ("Neighbor A15", "06511", "260 Fernbrook Ln, New Haven, CT 06511",
     "familya15@example.com", "(203) 555-0115"),
    ("Neighbor A19", "06515", "77 Hollowmill Rd, New Haven, CT 06515",
     "familya19@example.com", "(203) 555-0119"),
    ("Neighbor A23", "06513", "515 Candleberry Dr, New Haven, CT 06513",
     "familya23@example.com", None),
    ("Neighbor A27", "06513", "31 Quarry Bend, Apt 1, New Haven, CT 06513",
     "familya27@example.com", "(203) 555-0127"),
    ("Neighbor A31", "06519", "804 Saltmeadow Way, New Haven, CT 06519",
     "familya31@example.com", "(203) 555-0131"),
    ("Neighbor A34", "06510", "16 Printers Ct, Apt 5, New Haven, CT 06510",
     "familya34@example.com", "(203) 555-0134"),
    ("Neighbor A38", "06515", "233 Thistledown Rd, New Haven, CT 06515",
     "familya38@example.com", "(203) 555-0138"),
    ("Neighbor A42", "06511", "58 Copperleaf St, Apt 2C, New Haven, CT 06511",
     "familya42@example.com", None),
    ("Neighbor A46", "06519", "140 Millpond Walk, New Haven, CT 06519",
     "familya46@example.com", "(203) 555-0146"),
    ("Neighbor A51", "06511", "67 Brambleton Ave, New Haven, CT 06511",
     "familya51@example.com", "(203) 555-0151"),
    ("Neighbor A55", "06513", "390 Winterbourne Rd, New Haven, CT 06513",
     "familya55@example.com", "(203) 555-0155"),
    ("Neighbor A58", "06515", "12 Stonefield Ln, New Haven, CT 06515",
     "familya58@example.com", "(203) 555-0158"),
]

# --------------------------------------------------------------------------
# Donors
# --------------------------------------------------------------------------

DONORS: list[dict] = [
    dict(alias="Granter D01", zip="06511", contact_address="88 Elmcrest Ter, New Haven, CT 06511",
         contact_email="donord01@example.com", contact_phone="(203) 555-0201", budget_usd=75.0,
         preferred_categories=[Category.CLOTHING, Category.SCHOOL_SUPPLIES],
         preference=DonorPreference.SPECIFIC),
    dict(alias="Granter D02", zip="06511", contact_address="451 Harrowgate Rd, New Haven, CT 06511",
         contact_email="donord02@example.com", contact_phone="(203) 555-0202", budget_usd=200.0,
         preferred_categories=[Category.RENT_UTILITIES, Category.FOOD],
         preference=DonorPreference.FLEXIBLE),
    dict(alias="Granter D03", zip="06510", contact_address="7 Clocktower Sq, Apt 9, New Haven, CT 06510",
         contact_email="donord03@example.com", contact_phone="(203) 555-0203", budget_usd=50.0,
         preferred_categories=[Category.ESSENTIALS, Category.FOOD],
         preference=DonorPreference.EITHER),
    dict(alias="Granter D04", zip="06515", contact_address="202 Birchfield Ave, New Haven, CT 06515",
         contact_email="donord04@example.com", contact_phone="(203) 555-0204", budget_usd=120.0,
         preferred_categories=[Category.GIFTS, Category.CLOTHING],
         preference=DonorPreference.SPECIFIC),
    dict(alias="Granter D05", zip="06520", contact_address="1 Gateway Hall, Box 414, New Haven, CT 06520",
         contact_email="donord05@example.com", contact_phone=None, budget_usd=40.0,
         preferred_categories=[Category.SCHOOL_SUPPLIES],
         preference=DonorPreference.EITHER),
    dict(alias="Granter D06", zip="06515", contact_address="315 Foxglove Dr, New Haven, CT 06515",
         contact_email="donord06@example.com", contact_phone="(203) 555-0206", budget_usd=350.0,
         preferred_categories=[Category.RENT_UTILITIES, Category.OTHER],
         preference=DonorPreference.FLEXIBLE),
    dict(alias="Granter D07", zip="06513", contact_address="60 Seabright Ct, New Haven, CT 06513",
         contact_email="donord07@example.com", contact_phone="(203) 555-0207", budget_usd=90.0,
         preferred_categories=[Category.CLOTHING, Category.ESSENTIALS, Category.GIFTS],
         preference=DonorPreference.EITHER),
    dict(alias="Granter D08", zip="06519", contact_address="24 Orchard Gate, New Haven, CT 06519",
         contact_email="donord08@example.com", contact_phone="(203) 555-0208", budget_usd=500.0,
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
    dict(family="Neighbor A04", category=Category.CLOTHING, type=S, days=18,
         occasion="back_to_school", status=RequestStatus.OPEN, cost=42.0,
         desc="Winter coat for a child, size 8",
         link="https://www.target.com/p/kids-puffer-jacket/-/A-88204117",
         brand="Cat & Jack", size="Boys 8", color="Navy", sub=True),
    dict(family="Neighbor A04", category=Category.FOOD, type=F, days=9,
         occasion="everyday", status=RequestStatus.OPEN, budget=(40.0, 70.0),
         desc="Grocery gift card for a household with children",
         prefs="No pork; one child has a peanut allergy."),
    dict(family="Neighbor A04", category=Category.SCHOOL_SUPPLIES, type=S, days=25,
         occasion="back_to_school", status=RequestStatus.OPEN, cost=28.0,
         desc="Backpack, 17 inch, for a school-age child",
         link="https://www.walmart.com/ip/classic-backpack-17in/553001942",
         brand="JanSport", size="17 in", color="Black", sub=True),

    # --- Family A07: child in cancer treatment ---
    dict(family="Neighbor A07", category=Category.OTHER, type=F, days=5,
         occasion="emergency", status=RequestStatus.OPEN, budget=(60.0, 100.0),
         desc="Gas cards for travel to medical appointments",
         prefs="Any major station works."),
    dict(family="Neighbor A07", category=Category.ESSENTIALS, type=S, days=12,
         occasion="everyday", status=RequestStatus.OPEN, cost=22.0,
         desc="Unscented soap and lotion, sensitive skin",
         link="https://www.cvs.com/shop/sensitive-skin-care-bundle-prod9931204",
         brand="Cetaphil", size="16 oz", color=None, sub=True),
    dict(family="Neighbor A07", category=Category.GIFTS, type=S, days=33,
         occasion="birthday", status=RequestStatus.OPEN, cost=34.0,
         desc="Weighted lap blanket for a 7-year-old",
         link="https://www.amazon.com/dp/B0CT7QKMN4",
         brand="Bearaby", size="36x48 in", color="Lavender", sub=True),
    dict(family="Neighbor A07", category=Category.FOOD, type=F, days=3,
         occasion="emergency", status=RequestStatus.PENDING_REVIEW, budget=(50.0, 80.0),
         desc="Freezer meals, microwave only",
         prefs="Nothing that needs more than a microwave."),

    # --- Family A12: facing eviction ---
    dict(family="Neighbor A12", category=Category.RENT_UTILITIES, type=F, days=7,
         occasion="emergency", status=RequestStatus.OPEN, budget=(400.0, 600.0),
         desc="Rent help, paid to the landlord",
         prefs="Partial help is still useful."),
    dict(family="Neighbor A12", category=Category.RENT_UTILITIES, type=F, days=14,
         occasion="emergency", status=RequestStatus.OPEN, budget=(120.0, 180.0),
         desc="Electric bill help, paid to the utility company",
         prefs="Paid directly to the utility company."),
    dict(family="Neighbor A12", category=Category.ESSENTIALS, type=F, days=20,
         occasion="everyday", status=RequestStatus.OPEN, budget=(30.0, 50.0),
         desc="Diapers and wipes for a 14-month-old",
         prefs="Size 4 diapers."),

    # --- Family A15: parent needs an interview outfit ---
    dict(family="Neighbor A15", category=Category.CLOTHING, type=S, days=6,
         occasion="job_interview", status=RequestStatus.OPEN, cost=55.0,
         desc="Interview blazer for an adult",
         link="https://www.oldnavy.com/product/womens-classic-blazer-p-8814402",
         brand="Old Navy", size="Women's 12", color="Charcoal", sub=True),
    dict(family="Neighbor A15", category=Category.CLOTHING, type=S, days=6,
         occasion="job_interview", status=RequestStatus.GRANTED, cost=45.0,
         desc="Closed-toe flats for an adult",
         link="https://www.dsw.com/en/shop/womens-pointed-flat-6618093",
         brand="LifeStride", size="Women's 8.5", color="Black", sub=True),
    dict(family="Neighbor A15", category=Category.OTHER, type=F, days=11,
         occasion="job_interview", status=RequestStatus.OPEN, budget=(25.0, 40.0),
         desc="One-month bus pass for an adult",
         prefs=None),

    # --- Family A19: grandmother raising two grandchildren ---
    dict(family="Neighbor A19", category=Category.SCHOOL_SUPPLIES, type=F, days=16,
         occasion="back_to_school", status=RequestStatus.GRANTED, budget=(35.0, 60.0),
         desc="Notebooks, folders and pencils for a 4th grader and a 6th grader",
         prefs="Teacher's list is mostly basics."),
    dict(family="Neighbor A19", category=Category.CLOTHING, type=F, days=22,
         occasion="everyday", status=RequestStatus.OPEN, budget=(50.0, 90.0),
         desc="Warm layers for two children",
         prefs="Girls 10 and boys 12."),
    dict(family="Neighbor A19", category=Category.GIFTS, type=S, days=68,
         occasion="holiday", status=RequestStatus.OPEN, cost=30.0,
         desc="Build-your-own robot kit for a child",
         link="https://www.target.com/p/stem-robot-building-kit/-/A-79114502",
         brand="Thames & Kosmos", size=None, color=None, sub=True),

    # --- Family A23: recently arrived, in English classes ---
    dict(family="Neighbor A23", category=Category.OTHER, type=F, days=30,
         occasion="everyday", status=RequestStatus.OPEN, budget=(80.0, 150.0),
         desc="English workbook set and a dictionary for an adult learner",
         prefs="Beginner level."),
    dict(family="Neighbor A23", category=Category.FOOD, type=S, days=10,
         occasion="everyday", status=RequestStatus.OPEN, cost=50.0,
         desc="Grocery gift card for a household with children",
         link="https://www.stopandshop.com/gift-cards/product/sas-gc-50",
         brand="Stop & Shop", size="$50", color=None, sub=False),

    # --- Family A27: mother returning to work after an injury ---
    dict(family="Neighbor A27", category=Category.CLOTHING, type=S, days=8,
         occasion="job_interview", status=RequestStatus.OPEN, cost=38.0,
         desc="Non-slip work shoes for an adult, kitchen work",
         link="https://www.walmart.com/ip/slip-resistant-work-shoe/118920334",
         brand="Tredsafe", size="Women's 9", color="Black", sub=True),
    dict(family="Neighbor A27", category=Category.RENT_UTILITIES, type=F, days=26,
         occasion="everyday", status=RequestStatus.DRAFT, budget=(150.0, 250.0),
         desc="Gas bill help, paid to the utility company",
         prefs="Paid directly to the gas company."),

    # --- Family A31: father on disability ---
    dict(family="Neighbor A31", category=Category.OTHER, type=S, days=29,
         occasion="everyday", status=RequestStatus.OPEN, cost=65.0,
         desc="Shower chair for an adult",
         link="https://www.walgreens.com/store/c/shower-chair-with-back/ID=300411227",
         brand="Carex", size="Standard", color=None, sub=True),
    dict(family="Neighbor A31", category=Category.ESSENTIALS, type=F, days=35,
         occasion="everyday", status=RequestStatus.MISSED, days_override=-6,
         budget=(20.0, 35.0),
         desc="Wound care supplies for an adult",
         prefs=None),

    # --- Family A34: after an apartment fire ---
    dict(family="Neighbor A34", category=Category.ESSENTIALS, type=F, days=2,
         occasion="emergency", status=RequestStatus.DELIVERED, budget=(70.0, 120.0),
         desc="Sheets, towels and basic pots and pans",
         prefs="Two twin beds and one full."),
    dict(family="Neighbor A34", category=Category.CLOTHING, type=F, days=15,
         occasion="emergency", status=RequestStatus.OPEN, budget=(100.0, 160.0),
         desc="School clothes for three children",
         prefs="Boys 6, girls 9, girls 13."),
    dict(family="Neighbor A34", category=Category.OTHER, type=S, days=21,
         occasion="emergency", status=RequestStatus.GRANTED, cost=48.0,
         desc="Smoke detector set and a small fire extinguisher",
         link="https://www.bestbuy.com/site/smoke-detector-2-pack/6501338.p",
         brand="First Alert", size="2-pack", color=None, sub=True),

    # --- Family A38: twins starting kindergarten ---
    dict(family="Neighbor A38", category=Category.SCHOOL_SUPPLIES, type=S, days=17,
         occasion="back_to_school", status=RequestStatus.OPEN, cost=36.0,
         desc="Two sets of the kindergarten supply list",
         link="https://www.staples.com/kindergarten-supply-bundle/product_24119087",
         brand="Staples", size="2 sets", color=None, sub=True),
    dict(family="Neighbor A38", category=Category.CLOTHING, type=S, days=24,
         occasion="back_to_school", status=RequestStatus.DROPPED_OFF, cost=52.0,
         desc="Two pairs of sneakers, same size",
         link="https://www.kohls.com/product/prd-6611904/kids-sneakers.jsp",
         brand="Carter's", size="Kids 11", color="Any", sub=True),
    dict(family="Neighbor A38", category=Category.GIFTS, type=F, days=45,
         occasion="birthday", status=RequestStatus.OPEN, budget=(30.0, 50.0),
         desc="A shared gift for two 6-year-olds",
         prefs="They both like dinosaurs."),

    # --- Family A42: teen aging out of foster care ---
    dict(family="Neighbor A42", category=Category.CLOTHING, type=S, days=9,
         occasion="job_interview", status=RequestStatus.OPEN, cost=40.0,
         desc="Dress shirt and tie for an adult",
         link="https://www.macys.com/shop/product/mens-dress-shirt-tie-set?ID=14920337",
         brand="Van Heusen", size="Men's 15.5 x 33", color="White", sub=True),
    dict(family="Neighbor A42", category=Category.FOOD, type=F, days=12,
         occasion="everyday", status=RequestStatus.PENDING_REVIEW, budget=(45.0, 70.0),
         desc="Grocery gift card for one adult",
         prefs=None),

    # --- Family A46: parent recovering from surgery ---
    dict(family="Neighbor A46", category=Category.FOOD, type=F, days=6,
         occasion="emergency", status=RequestStatus.DELIVERED, budget=(50.0, 80.0),
         desc="Prepared meals for an adult, no cooking required",
         prefs="Soft foods."),
    dict(family="Neighbor A46", category=Category.ESSENTIALS, type=S, days=14,
         occasion="everyday", status=RequestStatus.OPEN, cost=26.0,
         desc="Reacher grabber tool for an adult",
         link="https://www.amazon.com/dp/B07YFG4K2Q",
         brand="RMS", size='32 in', color=None, sub=True),

    # --- Family A51: family with a newborn ---
    dict(family="Neighbor A51", category=Category.ESSENTIALS, type=S, days=5,
         occasion="everyday", status=RequestStatus.GRANTED, cost=44.0,
         desc="Newborn diapers and wipes",
         link="https://www.target.com/p/newborn-diaper-wipes-bundle/-/A-54720118",
         brand="Pampers", size="Newborn", color=None, sub=True),
    dict(family="Neighbor A51", category=Category.GIFTS, type=F, days=70,
         occasion="holiday", status=RequestStatus.OPEN, budget=(40.0, 70.0),
         desc="Holiday gifts for an infant and a young child",
         prefs="The younger child is 4."),

    # --- Family A55: household after a job loss ---
    dict(family="Neighbor A55", category=Category.RENT_UTILITIES, type=F, days=10,
         occasion="emergency", status=RequestStatus.OPEN, budget=(300.0, 500.0),
         desc="One month of rent, paid to the landlord",
         prefs="Paid directly to the property manager."),
    dict(family="Neighbor A55", category=Category.SCHOOL_SUPPLIES, type=F, days=23,
         occasion="back_to_school", status=RequestStatus.MISSED, days_override=-3,
         budget=(25.0, 45.0),
         desc="Calculator for a middle school math class",
         prefs="The school asked for a graphing one."),
    dict(family="Neighbor A55", category=Category.GIFTS, type=S, days=66,
         occasion="holiday", status=RequestStatus.OPEN, cost=25.0,
         desc="Holiday gift for each of two children",
         link="https://www.target.com/p/holiday-art-set-kids/-/A-61880294",
         brand="Crayola", size=None, color=None, sub=True),

    # --- Family A58: caregiver for a parent with dementia ---
    dict(family="Neighbor A58", category=Category.OTHER, type=F, days=31,
         occasion="everyday", status=RequestStatus.OPEN, budget=(90.0, 140.0),
         desc="A few hours of respite care",
         prefs=None),
    dict(family="Neighbor A58", category=Category.GIFTS, type=S, days=72,
         occasion="holiday", status=RequestStatus.OPEN, cost=32.0,
         desc="Large-button digital photo frame for an older adult",
         link="https://www.amazon.com/dp/B08X9QJ7RT",
         brand="Aura", size='10 in', color="Walnut", sub=True),
    dict(family="Neighbor A58", category=Category.FOOD, type=S, days=20,
         occasion="birthday", status=RequestStatus.DELIVERED, cost=35.0,
         desc="Small birthday cake and dinner for an 81st birthday",
         link="https://www.shoprite.com/sm/pickup/rsid/3000/product/bakery-cake-8in-600412",
         brand="ShopRite Bakery", size='8 in', color=None, sub=True),
]


# --------------------------------------------------------------------------
# History — wishes already granted, so the tree is not starting from nothing.
#
# A giving tree that stays up all year should look like it has been up all
# year. These are past wishes: delivered, off the tree, and counted by the
# landing page. `ago` is days since the delivery, so the spread stays right
# whenever the seed is run — a handful inside the 30-day gold-leaf window,
# the rest further back.
#
# Invented, like every other row in this file. No real person is described.
# --------------------------------------------------------------------------

HISTORY: list[dict] = [
    # --- inside the gold-leaf window: these still show on the tree ---
    dict(ago=5,   category=Category.CLOTHING,        cost=38.0, occasion="everyday",
         desc="Rain boots for a child, size 1"),
    dict(ago=9,   category=Category.FOOD,            cost=60.0, occasion="everyday",
         desc="Grocery gift card for a household of five"),
    dict(ago=12,  category=Category.SCHOOL_SUPPLIES, cost=24.0, occasion="back_to_school",
         desc="Scientific calculator for a high school class"),
    dict(ago=16,  category=Category.ESSENTIALS,      cost=31.0, occasion="everyday",
         desc="Toddler diapers, size 5, and wipes"),
    dict(ago=23,  category=Category.GIFTS,           cost=29.0, occasion="birthday",
         desc="Art set for a 9-year-old"),
    dict(ago=27,  category=Category.OTHER,           cost=45.0, occasion="everyday",
         desc="Laundry card refill for an apartment building"),

    # --- older: counted on the landing page, no longer on the tree ---
    dict(ago=38,  category=Category.CLOTHING,        cost=52.0, occasion="everyday",
         desc="Work boots for an adult, steel toe, size 10"),
    dict(ago=44,  category=Category.RENT_UTILITIES,  cost=310.0, occasion="emergency",
         desc="Electric bill help, paid to the utility company"),
    dict(ago=51,  category=Category.SCHOOL_SUPPLIES, cost=36.0, occasion="back_to_school",
         desc="Two sets of notebooks, folders and pencils"),
    dict(ago=58,  category=Category.FOOD,            cost=55.0, occasion="everyday",
         desc="Grocery gift card for one adult"),
    dict(ago=66,  category=Category.ESSENTIALS,      cost=27.0, occasion="everyday",
         desc="Unscented laundry detergent and dish soap"),
    dict(ago=74,  category=Category.CLOTHING,        cost=44.0, occasion="everyday",
         desc="School shoes for two children, sizes 11 and 13"),
    dict(ago=83,  category=Category.OTHER,           cost=70.0, occasion="emergency",
         desc="Gas cards for travel to medical appointments"),
    dict(ago=91,  category=Category.GIFTS,           cost=33.0, occasion="birthday",
         desc="Building block set for a 5-year-old"),
    dict(ago=102, category=Category.RENT_UTILITIES,  cost=420.0, occasion="emergency",
         desc="Rent help, paid to the landlord"),
    dict(ago=113, category=Category.FOOD,            cost=48.0, occasion="everyday",
         desc="Freezer meals, microwave only"),
    dict(ago=126, category=Category.ESSENTIALS,      cost=22.0, occasion="everyday",
         desc="Shower chair for an adult"),
    dict(ago=140, category=Category.SCHOOL_SUPPLIES, cost=19.0, occasion="back_to_school",
         desc="Backpack, 17 inch, for a school-age child"),
    dict(ago=158, category=Category.CLOTHING,        cost=41.0, occasion="everyday",
         desc="Warm layers for two children"),
    dict(ago=179, category=Category.GIFTS,           cost=26.0, occasion="holiday",
         desc="Holiday gift for each of two children"),
    dict(ago=203, category=Category.OTHER,           cost=58.0, occasion="everyday",
         desc="One-month bus pass for an adult"),
]


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

def _build_requests(today: date) -> list[Request]:
    by_alias = {alias: zipc for alias, zipc, _addr, _email, _phone in FAMILIES}
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
        for alias, zipc, address, email, phone in FAMILIES:
            db.insert_family(
                Family(alias=alias, zip=zipc, region_slug=region.slug,
                       contact_address=address, contact_email=email,
                       contact_phone=phone),
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

        # Wishes already granted in past weeks. Each one is delivered and off
        # the tree; together they are what the landing page counts.
        family_aliases = [alias for alias, *_ in FAMILIES]
        for i, row in enumerate(HISTORY):
            delivered = today - timedelta(days=row["ago"])
            dropped = previous_weekday(delivered, region.dropoff_window.day)
            alias = family_aliases[i % len(family_aliases)]
            request_id = db.insert_request(
                Request(
                    family_alias=alias,
                    category=row["category"],
                    request_type=RequestType.FLEXIBLE,
                    item_description=row["desc"],
                    deadline=delivered,
                    occasion=row["occasion"],
                    zip=dict((a, z) for a, z, *_ in FAMILIES)[alias],
                    status=RequestStatus.DELIVERED,
                    estimated_cost_usd=row["cost"],
                ),
                conn,
            )
            db.insert_pledge(
                Pledge(
                    request_id=request_id,
                    donor_alias=donor_aliases[i % len(donor_aliases)],
                    dropoff_date=dropped,
                    delivery_date=delivered,
                    window_response=WindowResponse.CONFIRMED,
                    status=PledgeStatus.DELIVERED,
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
