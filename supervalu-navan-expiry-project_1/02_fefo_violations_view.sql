-- ============================================================
-- SuperValu Navan — Stock Expiry Management
-- Step 2: FEFO violation detection view (v2)
--
-- A "FEFO violation" = a sale was made against a batch while an
-- OLDER-expiry batch of the same product genuinely still had
-- stock sitting unsold that day. Selling from a newer batch after
-- the older one sold out THAT SAME DAY is normal, correct shop
-- behavior, not a violation — this view tells the two apart.
-- ============================================================

CREATE OR REPLACE VIEW fefo_violations AS

-- ------------------------------------------------------------
-- STEP A — active_batches
-- daily_stock_snapshot.units_remaining for a given snapshot_date
-- is recorded BEFORE that date's sale happens (see generate_sql.py:
-- the snapshot is appended, then the day's sale runs). So a
-- snapshot row for date D already IS the true start-of-day-D
-- stock — no date shift needed, we just read it as-is.
-- ------------------------------------------------------------
WITH active_batches AS (
    SELECT
        dss.batch_id,
        dss.product_id,
        dss.snapshot_date            AS available_on_date,
        dss.units_remaining          AS remaining_start_of_day
    FROM daily_stock_snapshot dss
    WHERE dss.units_remaining > 0
),

-- ------------------------------------------------------------
-- STEP B — ranked_batches
-- Same as before: rank each product's active batches per day,
-- oldest expiry first. Unchanged.
-- ------------------------------------------------------------
ranked_batches AS (
    SELECT
        ab.product_id,
        ab.available_on_date,
        ab.batch_id,
        ab.remaining_start_of_day,
        b.expiry_date,
        RANK() OVER (
            PARTITION BY ab.product_id, ab.available_on_date
            ORDER BY b.expiry_date ASC
        ) AS fefo_rank
    FROM active_batches ab
    JOIN batches b ON b.batch_id = ab.batch_id
),

-- ------------------------------------------------------------
-- STEP C — daily_batch_sales
-- How many units did each batch actually sell on each specific
-- day? (Normally one sale row per batch per day in our data, but
-- SUM handles it even if there were several.)
-- ------------------------------------------------------------
daily_batch_sales AS (
    SELECT
        batch_id,
        sale_date,
        SUM(units_sold) AS units_sold_that_day
    FROM sales
    GROUP BY batch_id, sale_date
),

-- ------------------------------------------------------------
-- STEP D — batch_day_status
-- The new piece: for every active batch on every day, work out
-- whether it was FULLY CLEARED that day — did the amount sold
-- that day account for everything it had at the start of the day?
-- If yes, it's fine for a newer batch to have picked up any
-- leftover demand that same day.
-- ------------------------------------------------------------
batch_day_status AS (
    SELECT
        rb.product_id,
        rb.available_on_date,
        rb.batch_id,
        rb.fefo_rank,
        rb.remaining_start_of_day,
        COALESCE(dbs.units_sold_that_day, 0) AS units_sold_that_day,
        COALESCE(dbs.units_sold_that_day, 0) >= rb.remaining_start_of_day AS fully_cleared
    FROM ranked_batches rb
    LEFT JOIN daily_batch_sales dbs
        ON dbs.batch_id = rb.batch_id
       AND dbs.sale_date = rb.available_on_date
)

-- ------------------------------------------------------------
-- STEP E — the final result
-- For every sale, check: is there ANY older batch (lower
-- fefo_rank), active the same product/day, that was NOT fully
-- cleared? If so, real stock was genuinely skipped over — a
-- true violation. If every older batch was fully cleared, this
-- sale is legitimate same-day spillover, not a violation.
-- ------------------------------------------------------------
SELECT
    s.sale_id,
    s.product_id,
    s.batch_id            AS sold_batch_id,
    s.sale_date,
    s.units_sold,
    sold.expiry_date      AS sold_batch_expiry_date,
    bds.fefo_rank          AS sold_batch_fefo_rank,
    (
        SELECT older.batch_id
        FROM batch_day_status older
        WHERE older.product_id = bds.product_id
          AND older.available_on_date = bds.available_on_date
          AND older.fefo_rank < bds.fefo_rank
          AND NOT older.fully_cleared
        ORDER BY older.fefo_rank ASC
        LIMIT 1
    ) AS skipped_over_batch_id,
    EXISTS (
        SELECT 1
        FROM batch_day_status older
        WHERE older.product_id = bds.product_id
          AND older.available_on_date = bds.available_on_date
          AND older.fefo_rank < bds.fefo_rank
          AND NOT older.fully_cleared
    ) AS is_violation
FROM sales s
JOIN batches sold
    ON sold.batch_id = s.batch_id
JOIN batch_day_status bds
    ON bds.product_id = s.product_id
   AND bds.available_on_date = s.sale_date
   AND bds.batch_id = s.batch_id;

COMMENT ON VIEW fefo_violations IS
    'One row per sale — flags a genuine FEFO violation only when some older-expiry batch, active the same day, was NOT fully sold out that day (legitimate same-day spillover is excluded)';


-- ============================================================
-- Sanity checks
-- ============================================================

-- 1. Overall violation rate
-- SELECT
--     COUNT(*) FILTER (WHERE is_violation) AS violations,
--     COUNT(*) AS total_sales,
--     ROUND(100.0 * COUNT(*) FILTER (WHERE is_violation) / COUNT(*), 2) AS violation_pct
-- FROM fefo_violations;

-- 2. Violation rate by category
-- SELECT
--     p.category,
--     COUNT(*) FILTER (WHERE fv.is_violation) AS violations,
--     COUNT(*) AS total_sales,
--     ROUND(100.0 * COUNT(*) FILTER (WHERE fv.is_violation) / COUNT(*), 2) AS violation_pct
-- FROM fefo_violations fv
-- JOIN products p ON p.product_id = fv.product_id
-- GROUP BY p.category
-- ORDER BY violation_pct DESC;

-- 3. Spot-check a handful of actual violation rows
-- SELECT * FROM fefo_violations WHERE is_violation LIMIT 20;
