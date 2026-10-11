# Newly repeated end-to-end scenarios

Environment for live scenarios: combined source596d9fb; Windows/Python3.12.14/Node22.23.3;
headed Edge155.0.4283.45; real Flask and actual Product algorithms; safe synthetic Pulse.
Expected behavior is the approved request/card. This is automated acceptance, not human acceptance.
Source API/algorithm/doc-only subbranches are labeled in the criterion matrix.

| Step | Input/action / expected behavior | Observed / status | Executed evidence |
|---|---|---|---|
|1|Documented run.py starts intended checkout|PASS: literal command on5082 and run.main on5078; expected frontend bytes|[startup](startup.json)|
|2|Open Product workspace in real Edge|PASS: «Кластеризация», current origin/All controls|[selection](selection/live-results.json), [navigation](navigation/live-observations.json)|
|3|Select one origin by keyboard/catalog identity|PASS: Arrow/Enter selects actual Alpha/Origin00 FIAS|[selection](selection/live-results.json), [All](all/live-observations.json)|
|4|Add multiple origins without duplicate trips|PASS: Alpha+Beta, pooled12 destinations/480 machines; Gamma zero-match explained|[selection](selection/live-results.json)|
|5|Select one destination region|PASS: A/B native selection and frozen region edits; shared scope retained|[All](all/live-network.json)|
|6|Explicit regional All without origin-region|PASS: region validation before run; explicit selector, no manual origin requirement|[All](all/live-observations.json)|
|7|All exceeds suggestion page|PASS:36 origins versus30 suggestions; foreign origin absent, zero-match retained|[All](all/live-network.json)|
|8|Configure periods/price/vehicle/tonnage|PASS: current/spot/tent/20 native controls; retro/current combine; supplied current/forecast branch|[All](all/live-network.json), [selection](selection/live-results.json), [export](network.json)|
|9|Calculate Geography|PASS: actual algorithm, map/table/rows and saved workbook|[medoid](medoid/live-network.json), [downloads](network.json)|
|10|Calculate Geo+Cost|PASS: actual eligibility/induced graph, excluded economics points, saved table/download|[medoid](medoid/live-network.json), [downloads](workbook-inspection.json)|
|11|Calculate Geo+Volume|PASS: actual graph/volume mode and saved table/download|[medoid](medoid/live-network.json), [downloads](workbook-inspection.json)|
|12|Calculate Bear Cost|PASS: positive singleton in medoid fixture; uniform All no_bears; unsupported export clear|[medoid](medoid/live-network.json), [All](all/live-network.json), [downloads](network.json)|
|13|Calculate Bear Volume|PASS: positive p0 singleton and uniform All no_bears; table/export unchanged|[medoid](medoid/live-network.json), [All](all/live-network.json)|
|14|Compare supported modes neutrally|PASS: five actual variants, same frozen dataset; winner null; request-free cached switch|[All](all/live-network.json), [freshness](freshness/network.json)|
|15|Inspect map and saved membership|PASS: real destination/map label clicks, member geometry and table/inspector consistency|[navigation](navigation/live-network.json), [medoid](medoid/live-observations.json)|
|16|Sort/collapse/reopen table|PASS: actual row order and collapsed download; drill-up preserves sort/collapse|[navigation](navigation/live-observations.json), [downloads](network.json)|
|17|Select cluster and destination|PASS: table and map selection expose correct saved point; late parent change clears descendants|[navigation](navigation/live-observations.json)|
|18|Open contributor summary|PASS: actual A/B contributions, null/conflicting source regions; bottom table unchanged|[navigation](navigation/live-network.json)|
|19|Open origin-specific Pulse rows|PASS: A50→61 newest-first unique rows; native Tab/Enter B gives onlyB rows|[navigation](navigation/live-network.json)|
|20|Drill up with native keyboard/focus|PASS: rows→summary→cluster→overview; original data/sort/map; no new requests, restored focus|[navigation](navigation/live-observations.json)|
|21|Inspect temporary medoid|PASS: same member/name/ID on map and inspector, non-city/missing explicit; no unresolved representative|[medoid](medoid/live-observations.json)|
|22|Download3 supported modes|PASS: real completed Geography/Cost/Volume attachments, saved intent and sorting|[downloads](network.json)|
|23|Independently open downloaded files|PASS: ZIP CRC/XML types/order/rows/membership/context; literal strings/no formulas/macros/external links|[inspection](workbook-inspection.json), [90k](capacity/reopened.json)|
|24|Typed errors and recovery|PASS: NO_DATA, NETWORK_TEST, STALE_DATA_SNAPSHOT, RESULT_UNAVAILABLE, EXPORT_FAILED/CONNECTION_ERROR; old result honest, retry/recalculate explicit|[navigation](navigation/live-network.json), [freshness](freshness/network.json), [downloads](network.json)|

| Extension | Expected | Observed / status | Evidence |
|---|---|---|---|
|Frozen edits and equivalent manual/All|Do not mutate old result or selection-intent provenance|PASS: old request/membership retained; equivalent selector provenance distinct|[downloads](network.json), [inspection](workbook-inspection.json)|
|Weekly CSV replacement with tab left open|Revision detects new metadata before accepting cached calculation|PASS: no reload; old generation rejected; failed display honest; All resolves new origin|[freshness](freshness/network.json)|
|Source changes inside real calculation|Reject generation race, preserve frozen display|PASS: held backend calculation + atomic replacement →409|[freshness](freshness/network.json)|
|Source changes during export|No mixed or partial successful artifact|PASS: real writer generation replacement →409, no download|[downloads](network.json)|
|Coordinate change|Reject known old source/coordinate identity and caches/export|PASS: different revision, available:false, export blocked, fresh success|[freshness](freshness/network.json)|
|Restart/eviction/old saved details|Explicit unavailable; no silent rerun|PASS: same-generation absence recognized; fresh explicit run recovers|[navigation](navigation/live-network.json), [downloads](network.json)|
|Cancellation/late transport|No replacement context or unintended download|PASS: native cancel/view exit/new run; existing mandatory Edge cases cover reset/pagehide/replacement|[downloads](network.json), [executed cases](executed-tests.md)|
|Network/export failure/retry|Retry same saved result without clustering|PASS: real transport reset and writer failure; unchanged run count; completed retry|[downloads](network.json)|
|Null/zero/precision/security/collision fixture|Unavailable dash/blank, zero numeric, literal prefixes/IDs, unique legal sheet map|PASS: actual browser file independently opened|[inspection](workbook-inspection.json)|
|Empty table|Explain unavailable export, preserve focus, no request/rerun|PASS at real Edge/controller seam; HTTP stub explicitly used, not a real-Flask claim|[empty guard](empty-guard.json)|
|Synthetic scaling|Full counts/timings/reopened rows, no invented SLA|PASS measurements; 90k complete actual browser file; production capacity UNVERIFIED|[measurement](measurements.json), [browser](capacity/timings.json)|
|Human acceptance|User independently accepts the Product workflow|UNVERIFIED; not replaced by browser automation|This report|
|Production capacity/operations|Representative authorized workload and targets|UNVERIFIED; requirements/data not supplied|[measurement](measurements.json), main report limitations|

All required desktop observations were independently repeated against the combined
candidate rather than inherited from prior reports. Historical temporal approval and
document-only/algorithm-only checks remain honestly attributed. Earlier execution setup
errors (missing dependency, occupied5055, obsolete driver selectors/source paths or
forecast-label selector) are not fabricated Product defects or RED/GREEN evidence.
