# Predictive ML contract v0

This document defines the implementation boundary for the price-prediction plan. It does
not declare that `units` is a realized shipment price; that business meaning remains open.

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

- `units` is only a target candidate.
- `period_type=forecast` is never accepted as an ordinary training label.
- `tech_load_ts` establishes what was available at prediction time.
- Random train/test splitting is prohibited.
- Any later historical or aggregate feature must be computed strictly before the row's
  prediction timestamp.

## Feature policy before semantic confirmation

| Source field | Status | Reason |
|---|---|---|
| `units` | target candidate only | Its exact business meaning is not confirmed. |
| `period_type` | split control | Forecast rows can be external predictions. |
| `confidence` | blocked | It may be derived from the external price calculation. |
| `bid_count` | blocked | Availability at prediction time is unknown. |
| `tech_load_ts` | point-in-time control | It is used for ordering and revision checks. |

Base route, geography, vehicle, tonnage, price type, currency, and calendar fields remain
candidates, not automatically approved production features.

## Required answers before dataset building or training

1. What does one Pulse row represent, and what exactly does `units` measure?
2. How is `period_type=forecast` produced?
3. Are `bid_count` and `confidence` known at prediction time?
4. Is the first product a monthly batch forecast or an on-demand route quotation?

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
