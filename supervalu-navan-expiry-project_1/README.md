# SuperValu Navan - Retail Stock Expiry Management

A data analytics portfolio project modeling and solving a real problem from
my part-time job as a shop floor assistant at SuperValu Navan: stock
rotation and near-expiry markdowns are tracked manually on paper, so
near-expiry stock often gets discounted too late (or not at all) and ends
up wasted.

This project builds a realistic PostgreSQL data model of a store's
deliveries, batches, sales and waste, detects genuine FEFO (First-Expiry-
First-Out) rotation mistakes in the sales data, and surfaces all of it
through a set of Tableau dashboards and a daily alert script.

## Problem

Store staff are supposed to always sell the oldest-expiring batch of a
product first. In practice this doesn't always happen - a newer batch
gets picked up while an older one still has stock - which quietly drives
up waste. There was no way to measure how often this was actually
happening, or to systematically catch stock before it expired.

### What is FEFO?

FEFO stands for **First-Expiry-First-Out**: when a product has multiple
batches on the shelf with different expiry dates (e.g. one delivery from
Monday and another from Wednesday), the batch expiring soonest should
always be sold first, regardless of which one arrived first. This is
standard practice in any business handling perishable stock — get it
wrong and stock that could have sold quietly expires behind a newer batch
that gets picked up instead.

## Tech stack

- **PostgreSQL** — schema design, views, window functions
- **Tableau** — dashboards

## Project components

1. **Synthetic data generator** (`generate_sql.py`) — generates a
   realistic dataset (~118 products, ~900 deliveries, ~2,000 batches,
   ~12,700 sales, ~190 waste events, ~24,000 daily stock snapshots),
   with sales deliberately biased toward — but not perfectly following —
   correct FEFO order, so genuine rotation mistakes exist in the data at
   a believable rate.

2. **Database schema + FEFO violation detection** (`01_create_schema.sql`,
   `02_fefo_violations_view.sql`, `03_fefo_linked_waste_view.sql`) — the
   core logic of the project. A sale is only flagged as a genuine FEFO
   violation if an older-expiry batch of the same product still had
   real, uncleared stock that same day — legitimate same-day spillover
   (selling from the next batch after the oldest one sells out) is
   correctly excluded. A second view then links waste back to violations,
   turning "25% of sales violate FEFO" into a euro figure: how much of
   the store's actual waste bill is a direct result of that behavior.

3. **Tableau dashboards**:
   - *Stock Risk and Financial Impact* — an overview combining a
     category × risk-status heatmap, a weekly waste cost trend, FEFO
     violation rate by category, FEFO-linked vs. other waste cost, and
     revenue lost to discounting.
   - *What to Discount Today* — an actionable list of every batch
     currently at Amber/Red risk, with suggested discount and value at
     risk.
   - *Reorder Suggestions* — flags products with low days-of-cover based
     on current stock and recent sales velocity.


## Key design decisions

- **Snapshot-based, not just transactional** — a `daily_stock_snapshot`
  table records units remaining and risk status per batch per day, which
  every dashboard, view, and the alert script all read from as a single
  source of truth.
- **FEFO violations required two rounds of debugging to get right** —
  the first version over-counted violations because it didn't account
  for legitimate same-day spillover; a second bug (a snapshot date-shift
  assumption) was found and fixed by tracing exactly when snapshots are
  written relative to each day's sales. Final calibrated violation rate:
  ~25%.

## Possible extensions (not built, scoped out deliberately)

- Tracking how many consecutive days a batch stays flagged (to catch
  markdowns that aren't working) — a SQL "gaps and islands" pattern,
  scoped out to keep the project focused and fully explainable.
- A Claude API-generated weekly narrative insight report summarizing
  trends in plain English.
