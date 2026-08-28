# Predictive ML contract v0 — DEFERRED

> **STATUS: DEFERRED. NOT PART OF THE CURRENT CLUSTERING MILESTONE.**
> The active Clustering Contract v1 defines `units` as trip price and `bid_count` as
> trip count. This historical document does not override the active clustering contract.

This document preserves the earlier price-prediction investigation for historical context.
It is not an active roadmap.

## Current status

The repository can ingest and audit the complete 25-column Pulse export without replacing
malformed values with zero. Model training is blocked until the target and point-in-time
semantics are confirmed.

## Candidate row grain

Until the source owner confirms it, the candidate business key is:

```text
origin_fias × destination_fias × period_id × period_type × price_type
× route_type × tonnage_id × vehicle_type × currency
```

`tech_load_ts` is a snapshot/availability timestamp, not a model feature. Multiple rows on
the candidate key may be legitimate revisions; the audit reports them instead of silently
deduplicating them.

## Target and temporal policy

- `units` is price under Clustering Contract v1; predictive PIT evaluation stays deferred.
- `period_type=forecast` is never accepted as an ordinary training label.
- `tech_load_ts` establishes what was available at prediction time.
- Random train/test splitting is prohibited.
- Any later historical or aggregate feature must be computed strictly before the row's
  prediction timestamp.

## Feature policy before semantic confirmation

| Source field | Status | Reason |
|---|---|---|
| `units` | deferred price target | Active clustering semantics say price; predictive validation is separate. |
| `period_type` | split control | Forecast rows can be external predictions. |
| `confidence` | blocked | It may be derived from the external price calculation. |
| `bid_count` | blocked | Availability at prediction time is unknown. |
| `tech_load_ts` | point-in-time control | It is used for ordering and revision checks. |

Base route, geography, vehicle, tonnage, price type, currency, and calendar fields remain
candidates, not automatically approved production features.

## Required answers before dataset building or training

1. What separate source supplies a realized price target?
2. What point-in-time product scenario would a future price model serve?
3. Which fields are truly available at that prediction time?

## Stage-0 artifacts

`python -m ml.data.audit` writes:

- schema and full-column null coverage;
- malformed-value counters separate from source nulls;
- exact and candidate-business-key duplicates;
- price, distance, and RUB/km distributions;
- categorical cardinalities and distributions;
- route history measured in records and distinct months;
- the conservative leakage policy and current training blocker.

No predictive model should be trained merely because these artifacts exist.
