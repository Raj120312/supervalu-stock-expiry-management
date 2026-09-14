"""
SuperValu Navan — Stock Expiry Management
Component 1: Synthetic data generator

Generates realistic ~118-SKU Irish supermarket data (products, deliveries,
batches, sales, waste, daily_stock_snapshot) and writes it out as a single
PostgreSQL .sql file of INSERT statements — no live DB connection needed to
run this script. Open the output file in pgAdmin's Query Tool (or run it
with `psql -f`) against the schema created in 01_create_schema.sql.

All data is synthetic / illustrative — product names, prices and supplier
names are realistic examples for a portfolio project, not real SuperValu
Navan sales figures.
"""

import random
from collections import defaultdict
from datetime import date, timedelta

random.seed(42)

TODAY = date(2026, 8, 29)          # generation anchor date
WINDOW_DAYS = 90                    # 3 months of history
WINDOW_START = TODAY - timedelta(days=WINDOW_DAYS)

OUT_PATH = "populate_data.sql"

# ------------------------------------------------------------------
# Category configuration
# db_tier must be one of: Critical, High, Medium, Low (matches the
# CHECK constraint on products.risk_tier). green_pct/amber_pct are the
# %-of-shelf-life-remaining thresholds used to compute risk_status.
# ------------------------------------------------------------------
CATEGORY_CONFIG = {
    "Fresh Meat": {
        "db_tier": "Critical", "green_pct": 0.30, "amber_pct": 0.10,
        "suppliers": ["Kepak Group", "Dawn Meats", "Rosderra Irish Meats", "Liffey Meats"],
        "delivery_every_days": (2, 3), "units_range": (15, 40),
        "daily_sales_range": (2, 6), "waste_chance": 0.28, "margin": 0.28,
    },
    "Dairy": {
        "db_tier": "High", "green_pct": 0.38, "amber_pct": 0.15,
        "suppliers": ["Avonmore (Glanbia)", "Glenisk", "Dairygold"],
        "delivery_every_days": (2, 4), "units_range": (20, 50),
        "daily_sales_range": (3, 8), "waste_chance": 0.24, "margin": 0.30,
    },
    "Baby Food": {
        "db_tier": "High", "green_pct": 0.50, "amber_pct": 0.20,   # stricter — pulled early
        "suppliers": ["Danone Nutricia", "HiPP Ireland"],
        "delivery_every_days": (9, 12), "units_range": (10, 25),
        "daily_sales_range": (1, 3), "waste_chance": 0.16, "margin": 0.32,
    },
    "Tea/Coffee/Biscuits": {
        "db_tier": "Medium", "green_pct": 0.30, "amber_pct": 0.10,
        "suppliers": ["Musgrave Distribution", "Valeo Foods"],
        "delivery_every_days": (6, 8), "units_range": (20, 40),
        "daily_sales_range": (2, 5), "waste_chance": 0.06, "margin": 0.34,
    },
    "Ambient Grocery": {
        "db_tier": "Medium", "green_pct": 0.30, "amber_pct": 0.10,
        "suppliers": ["Musgrave Distribution", "Kerry Foods", "Valeo Foods"],
        "delivery_every_days": (6, 8), "units_range": (20, 45),
        "daily_sales_range": (2, 5), "waste_chance": 0.05, "margin": 0.33,
    },
    "Chocolates": {
        "db_tier": "Low", "green_pct": 0.30, "amber_pct": 0.10,
        "suppliers": ["Mondelez Ireland", "Musgrave Distribution"],
        "delivery_every_days": (13, 16), "units_range": (15, 30),
        "daily_sales_range": (1, 4), "waste_chance": 0.04, "margin": 0.35,
    },
    "Tins": {
        "db_tier": "Low", "green_pct": 0.30, "amber_pct": 0.10,
        "suppliers": ["Musgrave Distribution", "Valeo Foods"],
        "delivery_every_days": (13, 16), "units_range": (25, 50),
        "daily_sales_range": (2, 6), "waste_chance": 0.03, "margin": 0.32,
    },
    "Pet Food": {
        "db_tier": "Low", "green_pct": 0.30, "amber_pct": 0.10,
        "suppliers": ["Mars Petcare", "Musgrave Distribution"],
        "delivery_every_days": (13, 16), "units_range": (15, 30),
        "daily_sales_range": (1, 3), "waste_chance": 0.05, "margin": 0.30,
    },
}

# ------------------------------------------------------------------
# Product catalog: (name, category, brand, shelf_life_days, unit_price)
# unit_cost is derived from unit_price using the category margin above.
# ------------------------------------------------------------------
PRODUCTS = [
    # Fresh Meat (20) — 10-15 day shelf life
    ("SuperValu Irish Beef Mince 500g", "Fresh Meat", "SuperValu", 10, 4.99),
    ("SuperValu Irish Beef Mince 1kg", "Fresh Meat", "SuperValu", 10, 8.99),
    ("SuperValu Diced Irish Beef 500g", "Fresh Meat", "SuperValu", 12, 6.49),
    ("SuperValu Irish Beef Steak Strips 400g", "Fresh Meat", "SuperValu", 12, 6.99),
    ("SuperValu Irish Rump Steak", "Fresh Meat", "SuperValu", 14, 9.99),
    ("SuperValu Irish Sirloin Steak", "Fresh Meat", "SuperValu", 14, 11.49),
    ("SuperValu Stewing Beef 500g", "Fresh Meat", "SuperValu", 12, 5.99),
    ("SuperValu Irish Chicken Fillets 500g", "Fresh Meat", "SuperValu", 10, 6.49),
    ("SuperValu Chicken Thighs 600g", "Fresh Meat", "SuperValu", 10, 4.99),
    ("SuperValu Chicken Drumsticks 800g", "Fresh Meat", "SuperValu", 10, 4.49),
    ("SuperValu Chicken Wings 700g", "Fresh Meat", "SuperValu", 10, 3.99),
    ("SuperValu Whole Chicken 1.5kg", "Fresh Meat", "SuperValu", 12, 7.99),
    ("SuperValu Pork Chops 500g", "Fresh Meat", "SuperValu", 12, 5.49),
    ("SuperValu Pork Belly Slices 500g", "Fresh Meat", "SuperValu", 12, 5.99),
    ("SuperValu Irish Pork Sausages 454g", "Fresh Meat", "SuperValu", 14, 3.49),
    ("SuperValu Streaky Bacon Rashers 300g", "Fresh Meat", "SuperValu", 15, 3.99),
    ("SuperValu Back Bacon Rashers 300g", "Fresh Meat", "SuperValu", 15, 4.49),
    ("SuperValu Lamb Chops 400g", "Fresh Meat", "SuperValu", 12, 8.49),
    ("SuperValu Minced Lamb 500g", "Fresh Meat", "SuperValu", 10, 7.49),
    ("SuperValu Beef Burgers 4 Pack", "Fresh Meat", "SuperValu", 12, 4.49),

    # Dairy (20) — 18-120 day shelf life
    ("Avonmore Fresh Milk 2L", "Dairy", "Avonmore", 8, 2.79),
    ("Avonmore Low Fat Milk 1L", "Dairy", "Avonmore", 8, 1.65),
    ("Avonmore Fresh Cream 250ml", "Dairy", "Avonmore", 20, 1.99),
    ("Glenisk Natural Yogurt 500g", "Dairy", "Glenisk", 22, 2.49),
    ("Glenisk Greek Style Yogurt 4pk", "Dairy", "Glenisk", 25, 3.29),
    ("Glenisk Organic Milk 1L", "Dairy", "Glenisk", 15, 2.19),
    ("Kerrygold Butter 200g", "Dairy", "Kerrygold", 90, 3.49),
    ("Kerrygold Garlic Butter 100g", "Dairy", "Kerrygold", 75, 2.29),
    ("Dubliner Cheese Block 200g", "Dairy", "Dubliner", 100, 4.29),
    ("Charleville Cheddar Cheese 200g", "Dairy", "Charleville", 100, 3.29),
    ("SuperValu Sliced Cheese 200g", "Dairy", "SuperValu", 60, 2.49),
    ("SuperValu Cottage Cheese 300g", "Dairy", "SuperValu", 20, 2.19),
    ("Yoplait Petits Filous 6pk", "Dairy", "Yoplait", 25, 2.99),
    ("Glenisk Kefir 500ml", "Dairy", "Glenisk", 20, 2.79),
    ("Avonmore Fresh Cream 500ml", "Dairy", "Avonmore", 22, 2.99),
    ("SuperValu Salted Butter 454g", "Dairy", "SuperValu", 120, 4.49),
    ("SuperValu Unsalted Butter 227g", "Dairy", "SuperValu", 120, 2.99),
    ("Connacht Gold Butter 250g", "Dairy", "Connacht Gold", 100, 3.19),
    ("Glenisk Low Fat Natural Yogurt 500g", "Dairy", "Glenisk", 22, 2.29),
    ("SuperValu Fresh Custard 500g", "Dairy", "SuperValu", 30, 2.19),

    # Baby Food (8) — long-dated but pulled early
    ("Cow & Gate Stage 1 Baby Rice 100g", "Baby Food", "Cow & Gate", 400, 2.99),
    ("Cow & Gate Fruit Pouch Apple & Banana", "Baby Food", "Cow & Gate", 380, 1.19),
    ("HiPP Organic Baby Rice", "Baby Food", "HiPP", 400, 3.19),
    ("HiPP Organic Fruit Pouch", "Baby Food", "HiPP", 380, 1.29),
    ("Aptamil Follow-On Milk 800g", "Baby Food", "Aptamil", 540, 14.99),
    ("Cow & Gate Follow-On Milk 800g", "Baby Food", "Cow & Gate", 540, 13.99),
    ("HiPP Organic Vegetable Pouch", "Baby Food", "HiPP", 380, 1.29),
    ("Cow & Gate Baby Yogurt Pouch", "Baby Food", "Cow & Gate", 300, 1.39),

    # Tea/Coffee/Biscuits (15) — 120-180 days
    ("Barry's Tea 80 Bag", "Tea/Coffee/Biscuits", "Barry's Tea", 180, 4.49),
    ("Barry's Gold Blend Tea 40 Bag", "Tea/Coffee/Biscuits", "Barry's Tea", 180, 2.99),
    ("Lyons Tea 80 Bag", "Tea/Coffee/Biscuits", "Lyons", 180, 4.29),
    ("Bewley's Original Blend Tea 80 Bag", "Tea/Coffee/Biscuits", "Bewley's", 180, 4.49),
    ("Nescafe Gold Blend Coffee 200g", "Tea/Coffee/Biscuits", "Nescafe", 365, 6.99),
    ("Nescafe Original Coffee 100g", "Tea/Coffee/Biscuits", "Nescafe", 365, 4.49),
    ("Kenco Smooth Coffee 100g", "Tea/Coffee/Biscuits", "Kenco", 365, 4.29),
    ("Lavazza Qualita Oro Coffee 250g", "Tea/Coffee/Biscuits", "Lavazza", 365, 6.49),
    ("Jacob's Cream Crackers", "Tea/Coffee/Biscuits", "Jacob's", 150, 1.99),
    ("Jacob's Fig Rolls", "Tea/Coffee/Biscuits", "Jacob's", 150, 1.79),
    ("McVitie's Digestives", "Tea/Coffee/Biscuits", "McVitie's", 150, 1.89),
    ("McVitie's Rich Tea", "Tea/Coffee/Biscuits", "McVitie's", 150, 1.69),
    ("McVitie's Hobnobs", "Tea/Coffee/Biscuits", "McVitie's", 150, 1.99),
    ("Kimberley Coconut Creams", "Tea/Coffee/Biscuits", "Jacob's", 150, 1.79),
    ("Jacob's Chocolate Kimberley", "Tea/Coffee/Biscuits", "Jacob's", 150, 1.89),

    # Ambient Grocery (25) — 180-540 days
    ("Chef Brown Sauce 465g", "Ambient Grocery", "Chef", 365, 2.29),
    ("Heinz Tomato Ketchup 460g", "Ambient Grocery", "Heinz", 365, 2.99),
    ("Heinz Tomato Ketchup 910g", "Ambient Grocery", "Heinz", 365, 4.49),
    ("Ballymaloe Relish", "Ambient Grocery", "Ballymaloe", 400, 3.49),
    ("Hellmann's Real Mayonnaise 400g", "Ambient Grocery", "Hellmann's", 200, 2.99),
    ("Hellmann's Light Mayonnaise 400g", "Ambient Grocery", "Hellmann's", 200, 2.99),
    ("Chef Salad Cream 435g", "Ambient Grocery", "Chef", 300, 2.19),
    ("Knorr Chicken Stock Cubes", "Ambient Grocery", "Knorr", 540, 1.49),
    ("Colman's English Mustard", "Ambient Grocery", "Colman's", 540, 1.99),
    ("Maggi 2 Minute Noodles 5 Pack", "Ambient Grocery", "Maggi", 300, 2.29),
    ("Koka Instant Noodles", "Ambient Grocery", "Koka", 300, 0.79),
    ("Kellogg's Corn Flakes 500g", "Ambient Grocery", "Kellogg's", 270, 3.49),
    ("Kellogg's Coco Pops 375g", "Ambient Grocery", "Kellogg's", 270, 3.79),
    ("Weetabix 24 Pack", "Ambient Grocery", "Weetabix", 270, 3.29),
    ("Flahavan's Porridge Oats 1kg", "Ambient Grocery", "Flahavan's", 365, 2.99),
    ("Nestle Shreddies 500g", "Ambient Grocery", "Nestle", 270, 3.49),
    ("Bonne Maman Strawberry Jam 370g", "Ambient Grocery", "Bonne Maman", 540, 3.99),
    ("Chivers Raspberry Jam 340g", "Ambient Grocery", "Chivers", 540, 2.49),
    ("Robertson's Golden Shred Marmalade", "Ambient Grocery", "Robertson's", 540, 2.99),
    ("Odlums Plain Flour 2kg", "Ambient Grocery", "Odlums", 365, 2.49),
    ("Odlums Self Raising Flour 2kg", "Ambient Grocery", "Odlums", 365, 2.59),
    ("McDougall's Plain Flour 1.5kg", "Ambient Grocery", "McDougall's", 365, 2.29),
    ("Rank Hovis Strong White Flour 1.5kg", "Ambient Grocery", "Hovis", 365, 2.79),
    ("Homepride Pasta Sauce 500g", "Ambient Grocery", "Homepride", 400, 2.19),
    ("Napolina Passata 500g", "Ambient Grocery", "Napolina", 400, 1.49),

    # Chocolates (10) — 540-1000 days
    ("Cadbury Dairy Milk 200g", "Chocolates", "Cadbury", 540, 3.49),
    ("Cadbury Dairy Milk Buttons 119g", "Chocolates", "Cadbury", 540, 2.29),
    ("Cadbury Twirl 4 Pack", "Chocolates", "Cadbury", 400, 2.99),
    ("Cadbury Boost 4 Pack", "Chocolates", "Cadbury", 400, 2.99),
    ("Nestle KitKat 4 Finger 4 Pack", "Chocolates", "Nestle", 400, 2.79),
    ("Nestle Aero Bubbly 90g", "Chocolates", "Nestle", 400, 1.99),
    ("Lindt Excellence Dark 70% 100g", "Chocolates", "Lindt", 730, 3.99),
    ("Roses Chocolate Tin 600g", "Chocolates", "Cadbury", 900, 9.99),
    ("Celebrations Chocolate Bag 350g", "Chocolates", "Mars", 900, 6.49),
    ("Cadbury Roses Tub 550g", "Chocolates", "Cadbury", 900, 8.99),

    # Tins (10) — 730-1095 days
    ("Batchelors Baked Beans 420g", "Tins", "Batchelors", 900, 1.29),
    ("Heinz Baked Beans 415g", "Tins", "Heinz", 900, 1.79),
    ("Batchelors Marrowfat Peas 300g", "Tins", "Batchelors", 900, 0.99),
    ("John West Tuna Chunks in Brine 145g", "Tins", "John West", 1095, 1.99),
    ("John West Salmon 213g", "Tins", "John West", 1095, 3.49),
    ("Napolina Chopped Tomatoes 400g", "Tins", "Napolina", 900, 1.09),
    ("Napolina Plum Tomatoes 400g", "Tins", "Napolina", 900, 1.19),
    ("Batchelors Chickpeas 400g", "Tins", "Batchelors", 900, 0.89),
    ("Batchelors Butter Beans 400g", "Tins", "Batchelors", 900, 0.99),
    ("Erin Vegetable Soup 400g", "Tins", "Erin", 730, 1.49),

    # Pet Food (10) — 365-540 days
    ("Pedigree Adult Dry Dog Food Chicken 1.2kg", "Pet Food", "Pedigree", 450, 6.99),
    ("Pedigree Dentastix Medium 7 Pack", "Pet Food", "Pedigree", 450, 4.49),
    ("Whiskas Adult Dry Cat Food Tuna 1.2kg", "Pet Food", "Whiskas", 450, 6.49),
    ("Whiskas Cat Treats 60g", "Pet Food", "Whiskas", 400, 2.49),
    ("Bakers Complete Adult Dog Food 1kg", "Pet Food", "Bakers", 450, 4.99),
    ("Purina One Adult Cat Food 1.5kg", "Pet Food", "Purina", 450, 7.99),
    ("Felix As Good As It Looks 12 Pack", "Pet Food", "Felix", 730, 6.99),
    ("Pedigree Adult Wet Dog Food Tins 12 Pack", "Pet Food", "Pedigree", 730, 8.99),
    ("Whiskas Wet Cat Food Pouches 12 Pack", "Pet Food", "Whiskas", 730, 6.99),
    ("Harringtons Dry Dog Food 2kg", "Pet Food", "Harringtons", 450, 8.49),
]

assert len(PRODUCTS) == 118, f"expected 118 products, got {len(PRODUCTS)}"


def sql_str(s: str) -> str:
    """Escape a string for safe use inside a SQL literal."""
    return s.replace("'", "''")


def risk_status_for(days_to_expiry: int, shelf_life_days: int, green_pct: float, amber_pct: float) -> str:
    pct_remaining = days_to_expiry / shelf_life_days
    if pct_remaining > green_pct:
        return "Green"
    if pct_remaining > amber_pct:
        return "Amber"
    return "Red"


def discount_for(risk_status: str) -> float:
    return {"Green": 0.0, "Amber": 25.0, "Red": 50.0}[risk_status]


def main():
    lines = []
    lines.append("-- ============================================================")
    lines.append("-- SuperValu Navan — synthetic data population")
    lines.append(f"-- Generated {TODAY.isoformat()} | window {WINDOW_START.isoformat()} to {TODAY.isoformat()}")
    lines.append("-- Synthetic / illustrative data for a portfolio project —")
    lines.append("-- not real SuperValu Navan sales figures.")
    lines.append("-- ============================================================")
    lines.append("BEGIN;")
    lines.append("")

    # ---------------- products ----------------
    lines.append("-- STEP 1: products")
    lines.append("INSERT INTO products (product_name, category, brand, risk_tier, shelf_life_days, unit_cost, unit_price, supplier) VALUES")
    product_rows = []
    for name, category, brand, shelf_life, price in PRODUCTS:
        cfg = CATEGORY_CONFIG[category]
        cost = round(price * (1 - cfg["margin"]), 2)
        default_supplier = random.choice(cfg["suppliers"])
        product_rows.append(
            f"('{sql_str(name)}', '{category}', '{sql_str(brand)}', '{cfg['db_tier']}', "
            f"{shelf_life}, {cost}, {price}, '{sql_str(default_supplier)}')"
        )
    lines.append(",\n".join(product_rows) + ";")
    lines.append("")

    # product_id will be 1..118 in insertion order (fresh SERIAL sequence)
    product_records = []
    for idx, (name, category, brand, shelf_life, price) in enumerate(PRODUCTS, start=1):
        cfg = CATEGORY_CONFIG[category]
        cost = round(price * (1 - cfg["margin"]), 2)
        product_records.append({
            "product_id": idx, "name": name, "category": category,
            "shelf_life": shelf_life, "price": price, "cost": cost, "cfg": cfg,
        })

    # ---------------- deliveries + batches ----------------
    lines.append("-- STEP 2 & 3: deliveries + batches")
    delivery_rows = []          # (date, supplier) -> delivery_id
    delivery_lookup = {}
    delivery_id_counter = 1
    batch_rows = []
    batch_records = []          # for downstream sales/waste/snapshot simulation
    batch_id_counter = 1

    for prod in product_records:
        cfg = prod["cfg"]
        cadence_lo, cadence_hi = cfg["delivery_every_days"]
        d = WINDOW_START + timedelta(days=random.randint(0, cadence_hi))
        while d <= TODAY:
            supplier = random.choice(cfg["suppliers"])
            key = (d, supplier)
            if key not in delivery_lookup:
                delivery_lookup[key] = delivery_id_counter
                ref_no = f"DN-{d.strftime('%y%m%d')}-{delivery_id_counter:04d}"
                delivery_rows.append(
                    f"({delivery_id_counter}, '{d.isoformat()}', '{sql_str(supplier)}', '{ref_no}', 'Auto-generated delivery record')"
                )
                delivery_id_counter += 1
            delivery_id = delivery_lookup[key]

            units = random.randint(*cfg["units_range"])

            # ~6% of deliveries arrive "short-dated" — a real supply-chain
            # occurrence where a supplier ships stock that's already partway
            # through its shelf life. This is what lets even long-life
            # categories (Tins, Chocolates, Ambient Grocery...) occasionally
            # show real Amber/Red risk, rather than being structurally 100%
            # Green just because their normal shelf life outlasts the whole
            # 90-day generation window.
            short_dated = random.random() < 0.06
            if short_dated:
                effective_life = max(3, round(prod["shelf_life"] * random.uniform(0.05, 0.20)))
            else:
                effective_life = prod["shelf_life"]
            expiry = d + timedelta(days=effective_life)
            batch_rows.append(
                f"({batch_id_counter}, {delivery_id}, {prod['product_id']}, '{d.isoformat()}', "
                f"{units}, '{expiry.isoformat()}', {prod['cost']})"
            )
            batch_records.append({
                "batch_id": batch_id_counter, "product_id": prod["product_id"],
                "category": prod["category"], "delivery_date": d, "expiry_date": expiry,
                "units_received": units, "price": prod["price"], "cost": prod["cost"],
                "shelf_life": prod["shelf_life"], "cfg": cfg,
            })
            batch_id_counter += 1
            d = d + timedelta(days=random.randint(cadence_lo, cadence_hi))

    lines.append("INSERT INTO deliveries (delivery_id, delivery_date, supplier, reference_no, notes) VALUES")
    lines.append(",\n".join(delivery_rows) + ";")
    lines.append("SELECT setval('deliveries_delivery_id_seq', (SELECT MAX(delivery_id) FROM deliveries));")
    lines.append("")

    lines.append("INSERT INTO batches (batch_id, delivery_id, product_id, delivery_date, units_received, expiry_date, unit_cost_at_delivery) VALUES")
    lines.append(",\n".join(batch_rows) + ";")
    lines.append("SELECT setval('batches_batch_id_seq', (SELECT MAX(batch_id) FROM batches));")
    lines.append("")

    # ---------------- sales, waste, snapshots (simulated per PRODUCT, day by day) ----------------
    # This used to simulate each batch's sales completely independently of
    # its sibling batches, which meant two batches of the same product sold
    # down at the same time with zero regard for which one expired sooner —
    # that's a FEFO violation by definition, and it happened on almost every
    # multi-batch day. Simulating day-by-day per PRODUCT instead lets us
    # explicitly choose which batch a day's demand is drawn from, so most
    # days correctly draw from the oldest-expiring batch first (spilling
    # into the next-oldest if it runs out mid-day), and only a deliberate
    # slice of days (VIOLATION_RATE) draw from a newer batch instead —
    # modelling a real staff rotation mistake at a believable rate.
    VIOLATION_RATE = 0.15

    lines.append("-- STEP 4, 5 & 6: sales, waste, daily_stock_snapshot (simulated per product, day by day)")
    sale_rows = []
    waste_rows = []
    snapshot_rows = []
    sale_id = 1
    waste_id = 1
    snapshot_id = 1

    batches_by_product = defaultdict(list)
    for b in batch_records:
        batches_by_product[b["product_id"]].append(b)

    for prod in product_records:
        prod_batches = batches_by_product.get(prod["product_id"], [])
        if not prod_batches:
            continue
        cfg = prod["cfg"]

        for b in prod_batches:
            b["remaining"] = b["units_received"]
            # decided once per batch, same meaning as before: this batch is
            # destined to undersell for its whole life so some stock is left
            # over to expire into waste
            b["will_go_to_waste"] = random.random() < cfg["waste_chance"]

        sim_start = min(b["delivery_date"] for b in prod_batches)
        current_day = sim_start

        while current_day <= TODAY:
            # batches that exist yet, haven't passed their (capped) expiry
            # window, and still have stock — these are "on the shelf" today
            active = [
                b for b in prod_batches
                if b["delivery_date"] <= current_day <= min(b["expiry_date"], TODAY)
                and b["remaining"] > 0
            ]

            # snapshot every active batch's state before today's sale happens
            for b in active:
                days_to_expiry = (b["expiry_date"] - current_day).days
                status = risk_status_for(days_to_expiry, b["shelf_life"], cfg["green_pct"], cfg["amber_pct"])
                snapshot_rows.append(
                    f"({snapshot_id}, {b['batch_id']}, {b['product_id']}, '{current_day.isoformat()}', "
                    f"{b['remaining']}, {days_to_expiry}, '{status}')"
                )
                snapshot_id += 1

            if active:
                # oldest expiry first — this ordering IS the FEFO rule
                active_sorted = sorted(active, key=lambda x: x["expiry_date"])

                lo, hi = cfg["daily_sales_range"]
                # demand scales mildly with how many batches are currently
                # on the shelf — more concurrent stock genuinely does move
                # faster in a real shop (more facings, more visibility), so
                # a deep FEFO queue doesn't structurally starve every batch
                # behind the first one. Capped so it doesn't run away for
                # products with many small overlapping batches.
                concurrency = min(len(active_sorted), 4)
                demand_scale = 1 + 0.5 * (concurrency - 1)
                base = random.randint(lo, hi) * demand_scale
                quiet_day = random.random() < 0.35
                day_mult = 0.3 if quiet_day else 1.0

                # a violation can only happen when there's a wrong batch to
                # pick from in the first place
                violate = len(active_sorted) > 1 and random.random() < VIOLATION_RATE

                if violate:
                    # staff pull today's whole demand from a batch that ISN'T
                    # the oldest — the true oldest batch sits untouched today
                    # even though it still has stock. This is exactly what
                    # the fefo_violations SQL view is built to catch.
                    chosen = random.choice(active_sorted[1:])
                    days_to_expiry = (chosen["expiry_date"] - current_day).days
                    status = risk_status_for(days_to_expiry, chosen["shelf_life"], cfg["green_pct"], cfg["amber_pct"])
                    discount = discount_for(status)
                    status_mult = {"Green": 1.0, "Amber": 1.4, "Red": 1.9}[status]
                    daily_sale = round(base * day_mult * status_mult)
                    if chosen["will_go_to_waste"]:
                        daily_sale = round(daily_sale * 0.45)
                    units_sold = min(max(daily_sale, 0), chosen["remaining"])
                    if units_sold > 0:
                        sale_price = round(chosen["price"] * (1 - discount / 100), 2)
                        sale_rows.append(
                            f"({sale_id}, {chosen['batch_id']}, {chosen['product_id']}, '{current_day.isoformat()}', "
                            f"{units_sold}, {sale_price}, {discount})"
                        )
                        sale_id += 1
                        chosen["remaining"] -= units_sold
                else:
                    # correct FEFO: fill today's demand starting from the
                    # oldest batch, spilling into the next-oldest if the
                    # first one sells out partway through the day — this is
                    # genuinely correct shop behavior (sell out the old pack,
                    # then move to the next one), not a rotation mistake.
                    # The fefo_violations SQL view is written to recognise
                    # this: a sale from a non-oldest batch is only flagged
                    # as a violation if some OLDER batch was NOT fully sold
                    # out that same day (i.e. stock was genuinely skipped
                    # over, not just picked up after the prior batch ran dry).
                    remaining_demand = None
                    for b in active_sorted:
                        days_to_expiry = (b["expiry_date"] - current_day).days
                        status = risk_status_for(days_to_expiry, b["shelf_life"], cfg["green_pct"], cfg["amber_pct"])
                        discount = discount_for(status)
                        status_mult = {"Green": 1.0, "Amber": 1.4, "Red": 1.9}[status]

                        if remaining_demand is None:
                            remaining_demand = round(base * day_mult * status_mult)

                        this_take = round(remaining_demand * 0.45) if b["will_go_to_waste"] else remaining_demand
                        units_sold = min(max(this_take, 0), b["remaining"])

                        if units_sold > 0:
                            sale_price = round(b["price"] * (1 - discount / 100), 2)
                            sale_rows.append(
                                f"({sale_id}, {b['batch_id']}, {b['product_id']}, '{current_day.isoformat()}', "
                                f"{units_sold}, {sale_price}, {discount})"
                            )
                            sale_id += 1
                            b["remaining"] -= units_sold
                            remaining_demand -= units_sold

                        if remaining_demand is not None and remaining_demand <= 0:
                            break

            current_day += timedelta(days=1)

        # after the whole window, any batch that actually expired with
        # stock left over gets written off as waste
        for b in prod_batches:
            if b["expiry_date"] <= TODAY and b["remaining"] > 0:
                waste_rows.append(
                    f"({waste_id}, {b['batch_id']}, {b['product_id']}, '{b['expiry_date'].isoformat()}', "
                    f"{b['remaining']}, {round(b['remaining'] * b['cost'], 2)}, 'expired')"
                )
                waste_id += 1

    lines.append("INSERT INTO sales (sale_id, batch_id, product_id, sale_date, units_sold, unit_price_sold, discount_pct) VALUES")
    for i in range(0, len(sale_rows), 500):
        chunk = sale_rows[i:i + 500]
        lines.append(",\n".join(chunk) + (";" if i + 500 >= len(sale_rows) else ";\nINSERT INTO sales (sale_id, batch_id, product_id, sale_date, units_sold, unit_price_sold, discount_pct) VALUES"))
    lines.append("SELECT setval('sales_sale_id_seq', (SELECT MAX(sale_id) FROM sales));")
    lines.append("")

    if waste_rows:
        lines.append("INSERT INTO waste (waste_id, batch_id, product_id, waste_date, units_wasted, cost_lost, reason) VALUES")
        for i in range(0, len(waste_rows), 500):
            chunk = waste_rows[i:i + 500]
            lines.append(",\n".join(chunk) + (";" if i + 500 >= len(waste_rows) else ";\nINSERT INTO waste (waste_id, batch_id, product_id, waste_date, units_wasted, cost_lost, reason) VALUES"))
        lines.append("SELECT setval('waste_waste_id_seq', (SELECT MAX(waste_id) FROM waste));")
        lines.append("")

    lines.append("INSERT INTO daily_stock_snapshot (snapshot_id, batch_id, product_id, snapshot_date, units_remaining, days_to_expiry, risk_status) VALUES")
    for i in range(0, len(snapshot_rows), 500):
        chunk = snapshot_rows[i:i + 500]
        lines.append(",\n".join(chunk) + (";" if i + 500 >= len(snapshot_rows) else ";\nINSERT INTO daily_stock_snapshot (snapshot_id, batch_id, product_id, snapshot_date, units_remaining, days_to_expiry, risk_status) VALUES"))
    lines.append("SELECT setval('daily_stock_snapshot_snapshot_id_seq', (SELECT MAX(snapshot_id) FROM daily_stock_snapshot));")
    lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    lines.append("-- Row count sanity check:")
    lines.append("-- SELECT 'products' t, count(*) FROM products")
    lines.append("-- UNION ALL SELECT 'deliveries', count(*) FROM deliveries")
    lines.append("-- UNION ALL SELECT 'batches', count(*) FROM batches")
    lines.append("-- UNION ALL SELECT 'sales', count(*) FROM sales")
    lines.append("-- UNION ALL SELECT 'waste', count(*) FROM waste")
    lines.append("-- UNION ALL SELECT 'daily_stock_snapshot', count(*) FROM daily_stock_snapshot;")

    with open(OUT_PATH, "w") as f:
        f.write("\n".join(lines))

    print(f"Products:   {len(PRODUCTS)}")
    print(f"Deliveries: {len(delivery_rows)}")
    print(f"Batches:    {len(batch_rows)}")
    print(f"Sales:      {len(sale_rows)}")
    print(f"Waste:      {len(waste_rows)}")
    print(f"Snapshots:  {len(snapshot_rows)}")
    print(f"Written to: {OUT_PATH}")


if __name__ == "__main__":
    main()
