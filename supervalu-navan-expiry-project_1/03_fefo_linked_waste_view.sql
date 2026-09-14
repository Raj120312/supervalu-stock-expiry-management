-- ============================================================
-- SuperValu Navan — Stock Expiry Management
-- Step 3: FEFO-linked waste view
--
-- Connects waste back to the FEFO violations that caused it. A
-- waste row is "FEFO-linked" if that exact batch was, at some
-- point, a batch that got skipped over while a newer batch sold
-- instead (skipped_over_batch_id in fefo_violations). This turns
-- "25% of sales violate FEFO" into a euro figure: how much of our
-- actual waste bill is a direct result of that behavior.
-- ============================================================

CREATE VIEW fefo_linked_waste AS
SELECT
    w.waste_id,
    w.batch_id,
    w.product_id,
    w.waste_date,
    w.units_wasted,
    w.cost_lost,
    (w.batch_id IN (
        SELECT DISTINCT skipped_over_batch_id
        FROM fefo_violations
        WHERE skipped_over_batch_id IS NOT NULL
    )) AS is_fefo_linked
FROM waste w;

COMMENT ON VIEW fefo_linked_waste IS
    'Waste rows flagged with whether that batch was ever skipped over by a FEFO violation before it expired';

-- ============================================================
-- Sanity check
-- ============================================================
-- SELECT
--     COUNT(*) FILTER (WHERE is_fefo_linked) AS fefo_linked_batches,
--     COUNT(*) AS total_waste_batches,
--     SUM(cost_lost) FILTER (WHERE is_fefo_linked) AS fefo_linked_cost,
--     SUM(cost_lost) AS total_waste_cost,
--     ROUND(100.0 * SUM(cost_lost) FILTER (WHERE is_fefo_linked) / SUM(cost_lost), 2) AS fefo_linked_cost_pct
-- FROM fefo_linked_waste;
