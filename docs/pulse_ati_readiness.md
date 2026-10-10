# Pulse contract and ATI readiness

Status: CURRENT contract discovery / NEXT integration prerequisites. NPI-01,
2026-10-10. Verified against main `9f665ed07f01e341b21fa6d385458725e29217de`
(PRs #5 and #6 merged). This is documentation, not an ATI integration contract.
ATI integration is externally blocked; none of its mappings below is verified.

## CURRENT: ingestion and normalized fields

The Product repository reads a local CSV selected by `LOGISTICS_CSV_FILE`, otherwise
`v_pulse_prices.csv`. It does not fetch Pulse remotely. The loader uses
`csv.DictReader`, UTF-8 with BOM support and replacement of invalid encoding bytes;
missing required headers raise `ValueError`. `PULSE_COLUMNS` describes 25 source
columns, of which `REQUIRED_PULSE_COLUMNS` requires 11. Required headers do not
guarantee non-null or valid row values. The literal `PulseRawRecord` preserves
cleaned strings; Product uses normalized `LogisticsRecord` instead.
Evidence: [loader.py](../ml/data/loader.py) (`default_csv_path`, `iter_records`,
`_pulse_record`, column constants), [pulse_raw.py](../ml/data/pulse_raw.py).

| Pulse field | CURRENT normalized meaning / treatment |
|---|---|
| `shipment_point_locality_fias_id` | `origin_fias`: location identity, not region identity |
| `shipment_point_name_town`, `shipment_point_town_source` | `origin_name`: first non-null of these fields |
| `shipment_point_region` | `origin_region`: row attribution; catalog modal region must not replace it |
| `delivery_point_locality_fias_id` | `destination_fias`: aggregated point identity |
| `delivery_point_town`, `delivery_point_region_unified` | destination name and filtering region; source region retained separately |
| `period_id`, `period_type` | period string and selectable `retro` / `current` / `forecast`; validation checks six digits, not calendar validity |
| `units`, `bid_count` | `price` (rubles in Product), `trip_count` (integer machines, one machine = one transportation); also retained as raw numeric fields |
| `route_length` | distance in km in Product, supplied by Pulse; no routing computation |
| `price_type`, `vehicle_body_type`, `tonnage_id` | price / vehicle / tonnage segment labels; tonnage ID is not a numeric tonne weight |
| `currency`, `confidence`, `nanos` | retained in LogisticsRecord; Product repository rows omit them; no currency conversion, nanos addition or confidence weighting |
| `tech_load_ts` | parsed ISO-like `tech_ts`, used in row ordering; not the file generation token |
| point types, addresses, `route_type`, source town/region | retained provenance in LogisticsRecord; not Product graph identities/features |

These are the application's existing Pulse interpretations, not proof of ATI
equivalence or an upstream currency guarantee. In particular, the Product index
does not enforce currency homogeneity. Names/regions are labels, not identity
fallbacks. `latitude` / `longitude` can be parsed if present as extra columns;
they are outside the 25-column export, and the Product route pipeline resolves
coordinates separately.
Evidence: [schema.py](../ml/data/schema.py) (`LogisticsRecord`, parsers),
[validation.py](../ml/data/validation.py) (field policy and row errors),
[CONTEXT.md](../CONTEXT.md), [data contract](clustering_data_contract.md),
[repository](../ml/data/clustering_repository.py) (`ClusteringSourceRow`).

Null markers become `None`; malformed numeric/timestamp values become `None`
with validation errors rather than invented values. Floats accept decimal commas;
integers use integer parsing. Validation is diagnostic, not rejection of every
bad row or a complete finite-number/calendar/currency validator. Confidence is
diagnostic; `forecast` is external Pulse data, never a locally generated Product
prediction. Deferred prediction/evaluation code is a separate LEGACY/RESEARCH
surface. Evidence: schema/validation above and [project brief](project/project-brief.md).

## CURRENT: repository responsibilities and separation

| Responsibility | Actual owner / behavior |
|---|---|
| Catalog and scope | `ClusteringRepository.options`, `has_origin`, `destination_regions`, `has_destination_region`; lazy index keyed by `(origin_fias, destination_region)`; excludes records without origin or destination region |
| Catalog labels/facets | `_reload` selects modal non-null origin name and region independently; facets count rows, not machines; origin totals sum positive trips |
| Filtering/aggregate | `aggregate` delegates to `aggregate_clustering_records` on the indexed slice, preserving row diagnostics and metric-valid denominators |
| Detail | `source_rows` filters an explicit origin set/region/destination and the same four filter sets; returns the entire sorted normalized slice, not an HTTP page or raw CSV |
| Revision/cache token | `fingerprint` reloads on resolved path/size/mtime_ns change; `FileFingerprint.cache_token` returns that tuple; `source_rows(expected_fingerprint=...)` rejects mismatches under an RLock |
| Load observability | `load_count` increments on reload; service run logs use it for repository hit/miss, together with request ID, rows, points and timings; it is not a business revision or per-request read counter |
| Request validation/orchestration | `ClusteringRequest` and `ClusteringService`: canonical explicit origin set (scalar = singleton), normalized filters/parameters, typed errors, location/graph/result caches and API projection |
| Coordinates / algorithms | `resolve_location_routes` owns coordinate resolution; Product adapters own eligibility, parameters and mode semantics; repository owns neither coordinates nor clustering |

Evidence: [repository](../ml/data/clustering_repository.py) (named methods),
[service](../backend/services/clustering_service.py) (`_validate_scope`, `_locations`,
`run`, `point_rows`), [catalog](../backend/product_modes/catalog.py) (`ModeDataset`,
`ProductModeCatalog`), [architecture](architecture/current-state.md).

The injected repository seam already separates catalog/aggregation/detail from
service orchestration; it remains a concrete file-backed Pulse repository.
`records_factory` alone is **not a full source integration port**: with no explicit
repository it supplies catalog records and union aggregation, while scalar
`_locations` keeps the separate `dataset_builder`; `_source_token` still stats source and coordinate files, and
`point_rows` rejects unavailable repository detail. Passing `source=` to the
loader changes a record label, not its CSV mapping or runtime capabilities.
Pulse-specific CSV fields, contract report labels, file tokens, row numbering and
Pulse UI/error wording remain. No provider registry or source selector exists in
this change. Evidence: service constructor, `_records`, `_locations`, `_source_token`,
`point_rows`; [dataset](../ml/data/clustering_dataset.py) contract report;
[frontend state](../frontend/js/clustering/state.js) and
[controls](../frontend/js/clustering/controls.js),
[inspector](../frontend/js/clustering/inspector.js) (source label and rows).

## CURRENT: grain, weights and mode requirements

Product request filter lists are sorted/deduplicated. Defaults are `current` and
`spot`; periods/prices must be nonempty allowed lists, while empty vehicle/tonnage
lists mean unrestricted. Repository filtering itself treats empty sets as
unrestricted; that is not permission for API callers to submit empty periods/prices.
No matching data, insufficient spatial/economic data and invalid scope use existing
typed errors such as `NO_DATA`, `INSUFFICIENT_POINTS`, `INSUFFICIENT_ECONOMICS`,
`UNKNOWN_ORIGIN` and `UNKNOWN_DESTINATION_REGION`; no fabricated successful data.
Evidence: service `ClusteringRequest.from_payload`, `_validate_scope`,
`_prepare_mode_dataset`, adapters and [Product contract](clustering_product_v1_contract.md).

`aggregate_clustering_records` accepts a nonempty explicit origin set (or scalar)
and requires one destination region; RESEARCH builders still require scalar origin.
matching segments pool into one `ClusteringRoute` per destination FIAS before
coordinate resolution. No source-observation uniqueness key or revision deduplication
is applied here: repeated input rows contribute again. `LogisticsRecord.fingerprint`
is a separate duplicate-detection helper, not the repository's detail row ID.

For each metric, mean = sum(value × positive trips) / sum(positive trips on rows
valid for that metric). Route and price require positive values independently;
row rate = positive price / positive route length. Rate mean averages row rates,
not aggregate price divided by aggregate distance. Zero denominator means `None`.
All positive trips count towards total machines even when a metric is missing;
invalid trips get no artificial weight. Missing destination FIAS rows are counted
as excluded, not assigned a name-based identity.
Evidence: [dataset](../ml/data/clustering_dataset.py) (`_Accumulator.add`,
`aggregate_clustering_records`), schema fingerprint/rate.

The cluster table reconstructs means using the point's **metric-valid trip count**;
price/rate min, median and max describe destination-point values. Coverage reports
valid/total points and valid/total machines per metric. Machine share uses all
assigned cluster trips in that table, not all repository traffic. Generic cluster
JSON/regional/Bear economics have separate existing weighting paths; this document
does not claim every surface uses the table denominator or change those paths.
Evidence: [service](../backend/services/clustering_service.py) (`_cluster_table`,
`_cluster_json`, `_result_json`), [table regression](../tests/test_product_cluster_table.py).

| Product mode | Existing input dependency |
|---|---|
| Geography | resolved coordinates and full SpatialGraph; economics removed from algorithm input |
| Geo+Cost | spatial graph, positive trips, non-null weighted price and rate; eligible induced subgraph |
| Geo+Volume | spatial graph and trip volume; price/rate removed; volume affects partitioning |
| Bear Cost | positive trips and non-null weighted rate; induced subgraph; zones/singletons, successful `no_bears` allowed |
| Bear Volume | positive trips; price/rate removed; induced subgraph; zones/singletons, successful `no_bears` allowed |

All five adapters and their existing thresholds/parameters remain intact; table
support remains only the three Geography modes. Full graph precedes business
filtering; no source attribute can invent graph adjacency. Evidence:
[adapters](../backend/product_modes/), service `_prepare_mode_dataset`,
[Product contract](clustering_product_v1_contract.md).

## CURRENT: coordinates, snapshots and detail identity

FIAS is point identity, but `_resolve_coordinates` looks up `name::region`, then
normalized-name/region in local JSON, validates latitude/longitude ranges and
labels matches `unverified_cache` with `cache_exact` / `cache_normalized` provenance.
This is not a verified FIAS coordinate lookup. Missing coordinates stay unresolved;
there is no region-center fallback. WGS84 coordinates are projected to local AEQD
for algorithms. Evidence: [locations](../ml/data/locations.py)
(`_valid_coordinates`, `_resolve_coordinates`, `resolve_location_routes`).

Service generation concatenates source fingerprint and coordinate-cache
path/size/mtime_ns; `data_snapshot` hashes its representation with SHA-256. A
generation change clears location/graph/result caches. This detects file metadata
changes, not content hashes, upstream business revisions or an immutable external
snapshot. Same-size changes with restored mtime can be missed; tokens include
absolute paths and are not portable source revision IDs. `tech_load_ts` does not
provide snapshot isolation or deduplication. Evidence: repository fingerprint and
service `_source_token`, `_refresh_cache_generation`, `_data_snapshot`.

`point_rows` requires snapshot, destination, origin selection and explicit four filter
lists; pagination offset is a nonnegative integer, limit a positive integer
(booleans rejected), default/max 50. It checks generation, a matching cached result
**data slice** for old scalar payloads without mode/parameters, repository expected
source fingerprint and generation again after reading/serialization.
New origin-set or mode/parameter payloads require both mode and normalized parameters
and the exact saved request/cache entry. Use `analysis.frozen_request`, not diagnostic
algorithm parameters. Rows carry the saved point's membership/status and source-row
origin/name/region and destination/name/region. A point outside the saved result is
rejected; an unassigned point retains null cluster. Eviction/restart yields
`RESULT_UNAVAILABLE` (409) without rerun. Stale data yields `STALE_DATA_SNAPSHOT` (409); absent legacy cached slice yields
`INVALID_REQUEST` (400); no matching destination rows yields
`UNKNOWN_DESTINATION_POINT` (422). Snapshot alone is insufficient: result identity
includes generation, canonical origins/filters/region/mode/normalized parameters
and the cached result's actual membership/exclusions. Preview/run/compare also reject
generation races before success/cache publication. No export endpoint is implemented.
Evidence: service `point_rows`, `_location_cache_key`, `_assert_generation` and `run`.

Detail IDs are BLAKE2b (8-byte digest) of `snapshot:source_row_number`, with CSV
record numbering starting at 1 after the header. IDs persist within the same
generation, not across reloads/reorders/coordinate revisions. Newest-first sorting
uses valid six-digit period descending, parsed timestamp descending (naive assumed
UTC), then row number descending; missing/invalid keys sort after available ones.
Paging slices the full list; `total`, `offset`, capped `limit`, `has_more` accompany
normalized period/timestamp/segment/price/distance/rate/trip/warning fields. It does
not return all 25 source fields. New rich-context rows add actual origin-region
attribution; old scalar row fields remain unchanged.
Evidence: repository `_newest_first`, `_reload`, `source_rows`; service `point_rows`;
[repository regression](../tests/ml/test_clustering_repository.py),
[API regression](../tests/test_clustering_product_api.py).

Form edits preserve the displayed frozen result. PR #5 handles rejected-generation
recovery/invalidation; PR #6 synchronizes cached-mode form controls. These repairs
remain intact alongside the backend origin-set contract. Summary/export are deferred. Evidence:
[controller](../frontend/js/clustering/controller.js), [controls](../frontend/js/clustering/controls.js).

## CURRENT explicit origins / NEXT regional All and consumers

NPI-02 implements exactly one selector: legacy scalar origin or nonempty
`origin_fiases` with one destination region. Canonical origins are sorted and
deduplicated; empty/conflicting selection never means All. Frozen analysis retains
resolved origins, explicit selection intent, catalog labels and per-origin zero-match
row/trip counts. Regional `all_origins` is rejected until its own ticket.
NEXT All resolves the complete
region-serving catalog before segment filters, not the search page, in the same
source generation as the read. Keep intent, resolved origins and zero-match origins.

Pool selected rows by destination FIAS before coordinates/graph, retaining row
origin and actual origin region. Region is attribution, not graph grain. Future
result identity includes generation, normalized frozen request, mode/parameters
and saved membership; rich detail does not rerun clustering. NEXT summary/export
must reuse that binding without re-expanding All or trusting client membership.
Preserve additive metric-valid weights/coverage, five modes,
missing-data diagnostics and Product/RESEARCH/LEGACY separation. Implementation and
downstream UI/workbook evidence belong to NPI-02 onward and NPI-12, not NPI-01.
Authority: approved local `.scratch/next-product-iteration/spec.md`, sections
R1, R4, shared calculation contract and Product API extension; ownership in
`coverage-matrix.md`. These local planning files are intentionally not published
wholesale by this narrow documentation PR.

## ATI gap register: all UNKNOWN

No ATI owner, approved sample or authoritative integration contract was supplied
in this repository/task. A similarly named public product or field is not evidence
for this project's authorized dataset. No verified ATI mapping, endpoint, credential
or source-selection behavior is proposed here.

| Required fact / evidence to obtain | Status | Future work blocked |
|---|---|---|
| Accountable business/data owner and technical contact; approval process | UNKNOWN | requirements sign-off and escalation |
| Availability of the relevant dataset, geographic/segment/history coverage | UNKNOWN | feasibility and Product coverage claims |
| Access: API/file/other format, authorized account, authentication and environment | UNKNOWN | actual ingestion and access validation; credentials must stay outside commits |
| License, permitted storage/retention, redistribution/export and confidentiality | UNKNOWN | lawful persistence, samples and future workbook publication |
| Approved sanitized representative sample and authoritative versioned schema | UNKNOWN | parser and reproducible integration fixtures |
| Field mappings: origin/destination identity, names and row regions | UNKNOWN | normalized records, joins and region attribution |
| Observation grain, unique row key, duplicate/correction/deletion semantics | UNKNOWN | deduplication and reconcilable totals |
| Machine/volume definition, weight unit and integer/fractional behavior | UNKNOWN | mapping to trip_count and all volume/economic modes |
| Price meaning/unit, currency, tax basis and scale/precision | UNKNOWN | ruble economics and rate comparability; no guessed conversion |
| Distance meaning/unit, route type and availability | UNKNOWN | route mean and price/km; no invented distance |
| Period types/IDs, timezone, external forecast availability/meaning | UNKNOWN | period filters and honest forecast labels; local prediction stays separate |
| Vehicle, tonnage and price segment taxonomy/mappings | UNKNOWN | common segment filters and mixed-segment warnings |
| Nulls, malformed values, non-finite numbers, confidence and quality guarantees | UNKNOWN | validation/diagnostics and safe eligibility |
| Update frequency/latency, revision IDs, corrections and snapshot consistency | UNKNOWN | generation invalidation, frozen-result/detail safety |
| Paging/cursors, stable ordering/identity, full extraction and rate limits | UNKNOWN | complete detail pages and future exports without duplication/truncation |
| Coordinates: availability, CRS, provenance, accuracy, identity linkage/revision | UNKNOWN | spatial coverage, verified coordinate resolution and coordinate generation |
| Volume: row/origin/destination counts, growth, limits and operational SLA | UNKNOWN | capacity sizing and production performance acceptance |

## Conditions for safe future integration

1. Resolve the register with owner-approved documentation and sanitized samples;
   verify field meaning, grain, licensing and capabilities rather than borrowing
   Pulse names. Unsupported metrics must remain explicitly unavailable; never
   substitute zero, confidence weights, guessed currency or coordinates.
2. Establish stable source identity/revision and coordinate revision, consistent
   extraction across all pages, deterministic detail identity/order and explicit
   errors. Reconcile raw rows, machines and metric-valid sums/coverage on approved
   fixtures, including corrections, missing data and generation changes.
3. Confirm compatibility at the existing repository/service boundary: catalog,
   scope checks, facets, aggregate, full detail and generation must agree. A new
   records iterator alone cannot meet these responsibilities. Revisit the actual
   file-token coupling and Pulse labels only when a real source contract exists.
4. Verify each mode's data dependencies and frozen request/membership guarantees;
   keep external forecast separate from local prediction. Confirm workload before
   capacity claims. Obtain a separately approved implementation scope and tests;
   do not mix sources or expose a selector as a side effect of this document.

NPI-01 acceptance is a document/source review. It establishes these prerequisites,
not ATI feasibility or runtime readiness. No confidential transportation examples,
customer records or credentials are included.
