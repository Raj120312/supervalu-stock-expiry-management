-- ============================================================
-- SuperValu Navan — Stock Expiry Management
-- Step 1: Database + schema creation (PostgreSQL)
-- ============================================================

-- ------------------------------------------------------------
-- STEP 0 — Create the database
-- Run this line on its own first, connected to the default
-- "postgres" database (psql or pgAdmin's query tool).
-- You cannot create a database and then use it in the same
-- transaction/script, so this line is separate from the rest.
-- ------------------------------------------------------------
CREATE DATABASE supervalu_navan_expiry;

-- Now switch your connection to the new database before running
-- anything below. In psql:  \c supervalu_navan_expiry
-- In pgAdmin: click the new database in the left tree first,
-- then open a new Query Tool against it.


-- ============================================================
-- STEP 1 — products
-- The master list. One row per SKU. Static — doesn't change
-- day to day, everything else (batches, sales, waste) hangs
-- off this via product_id.
-- ============================================================
CREATE TABLE products (
    product_id       SERIAL PRIMARY KEY,
    product_name     VARCHAR(120)   NOT NULL,
    category         VARCHAR(40)    NOT NULL
        CHECK (category IN (
            'Fresh Meat', 'Dairy', 'Ambient Grocery',
            'Tea/Coffee/Biscuits', 'Chocolates', 'Tins',
            'Pet Food', 'Baby Food'
        )),
    brand            VARCHAR(60),
    risk_tier        VARCHAR(20)    NOT NULL
        CHECK (risk_tier IN ('Critical', 'High', 'Medium', 'Low')),
    shelf_life_days  INTEGER        NOT NULL CHECK (shelf_life_days > 0),
    unit_cost        NUMERIC(8,2)   NOT NULL CHECK (unit_cost >= 0),
    unit_price       NUMERIC(8,2)   NOT NULL CHECK (unit_price >= 0),
    supplier         VARCHAR(80),
    created_at       TIMESTAMP      NOT NULL DEFAULT now()
);

COMMENT ON TABLE products IS 'Master SKU list — ~118 products across 8 categories';


-- ============================================================
-- STEP 2 — deliveries
-- One row per real-world truck / drop-off from a supplier.
-- A single delivery covers many products at once, which is
-- the macro-level unit: "how did Tuesday's Musgrave truck
-- perform" rather than "how did this one product do".
-- ============================================================
CREATE TABLE deliveries (
    delivery_id      SERIAL PRIMARY KEY,
    delivery_date    DATE    NOT NULL,
    supplier         VARCHAR(80) NOT NULL,
    reference_no     VARCHAR(40),
    notes            VARCHAR(200)
);

COMMENT ON TABLE deliveries IS 'One row per truck/drop-off — the macro-level delivery event that batches belong to';


-- ============================================================
-- STEP 3 — batches
-- One row per product within a delivery. Each batch has its
-- own expiry_date, which is what makes FEFO (first-expiry-
-- first-out) rotation logic possible — two deliveries of the
-- same product can have different expiry dates. Every batch
-- belongs to exactly one delivery (the truck it came off).
-- ============================================================
CREATE TABLE batches (
    batch_id               SERIAL PRIMARY KEY,
    delivery_id             INTEGER NOT NULL REFERENCES deliveries(delivery_id),
    product_id              INTEGER NOT NULL REFERENCES products(product_id),
    delivery_date            DATE   NOT NULL,
    units_received           INTEGER NOT NULL CHECK (units_received > 0),
    expiry_date              DATE   NOT NULL,
    unit_cost_at_delivery    NUMERIC(8,2) NOT NULL CHECK (unit_cost_at_delivery >= 0),

    CHECK (expiry_date > delivery_date)
);

COMMENT ON TABLE batches IS 'One row per product within a delivery — the unit that expiry tracking is really done on';


-- ============================================================
-- STEP 4 — sales
-- Daily units sold, allocated against a specific batch (FEFO:
-- always sell down the oldest-expiring batch first).
-- ============================================================
CREATE TABLE sales (
    sale_id            SERIAL PRIMARY KEY,
    batch_id           INTEGER NOT NULL REFERENCES batches(batch_id),
    product_id         INTEGER NOT NULL REFERENCES products(product_id),
    sale_date          DATE    NOT NULL,
    units_sold         INTEGER NOT NULL CHECK (units_sold > 0),
    unit_price_sold    NUMERIC(8,2) NOT NULL CHECK (unit_price_sold >= 0),
    discount_pct       NUMERIC(5,2) NOT NULL DEFAULT 0
        CHECK (discount_pct >= 0 AND discount_pct <= 100)
);

COMMENT ON TABLE sales IS 'Daily sales transactions, allocated against a batch';


-- ============================================================
-- STEP 5 — waste
-- Units that expired before being sold — the actual loss
-- events your project measures.
-- ============================================================
CREATE TABLE waste (
    waste_id       SERIAL PRIMARY KEY,
    batch_id       INTEGER NOT NULL REFERENCES batches(batch_id),
    product_id     INTEGER NOT NULL REFERENCES products(product_id),
    waste_date     DATE    NOT NULL,
    units_wasted   INTEGER NOT NULL CHECK (units_wasted > 0),
    cost_lost      NUMERIC(10,2) NOT NULL CHECK (cost_lost >= 0),
    reason         VARCHAR(30) NOT NULL DEFAULT 'expired'
        CHECK (reason IN ('expired', 'damaged', 'other'))
);

COMMENT ON TABLE waste IS 'Units written off — the waste/loss events the whole project is built to reduce';


-- ============================================================
-- STEP 6 — daily_stock_snapshot
-- One row per batch per day: units remaining, days to expiry,
-- and a Red/Amber/Green risk status. This is the table the
-- dashboard, the alert script and the Claude API report all
-- read from — it's the daily "photograph" of shelf state,
-- computed from batches minus sales minus waste.
-- ============================================================
CREATE TABLE daily_stock_snapshot (
    snapshot_id      SERIAL PRIMARY KEY,
    batch_id         INTEGER NOT NULL REFERENCES batches(batch_id),
    product_id       INTEGER NOT NULL REFERENCES products(product_id),
    snapshot_date    DATE    NOT NULL,
    units_remaining  INTEGER NOT NULL CHECK (units_remaining >= 0),
    days_to_expiry   INTEGER NOT NULL,
    risk_status      VARCHAR(10) NOT NULL
        CHECK (risk_status IN ('Green', 'Amber', 'Red')),

    UNIQUE (batch_id, snapshot_date)
);

COMMENT ON TABLE daily_stock_snapshot IS 'Daily computed shelf state per batch — source for the dashboard, alerts and weekly report';


-- ============================================================
-- STEP 7 — indexes
-- Speeds up the lookups every downstream component will do:
-- "today's snapshot", "this product's history", "this batch's
-- activity", "everything from this delivery".
-- ============================================================
CREATE INDEX idx_batches_delivery       ON batches(delivery_id);
CREATE INDEX idx_batches_product        ON batches(product_id);
CREATE INDEX idx_sales_batch            ON sales(batch_id);
CREATE INDEX idx_sales_date             ON sales(sale_date);
CREATE INDEX idx_waste_batch            ON waste(batch_id);
CREATE INDEX idx_waste_date             ON waste(waste_date);
CREATE INDEX idx_snapshot_date          ON daily_stock_snapshot(snapshot_date);
CREATE INDEX idx_snapshot_batch         ON daily_stock_snapshot(batch_id);
CREATE INDEX idx_snapshot_risk          ON daily_stock_snapshot(risk_status);


-- ============================================================
-- Sanity check — run this after all steps above to confirm
-- everything was created.
-- ============================================================
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' ORDER BY table_name;
