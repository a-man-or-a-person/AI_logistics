# D-07 independent Standards and targeted Ponytail review - 16 October 2026

What this change does: The desktop map starts directly below the menu. Saved context and Compare move into the existing inspector; narrow controls stay on the map. The methodology disclosure is deleted while individual metric helps retain its useful meanings.

## Identity, scope and risk

Independent reviewer/session: `/root/d07_standards_final`; no production or test edits. Accountable implementer: parent `/root`. Worktree `C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`, remote `https://github.com/a-man-or-a-person/AI_logistics.git`, isolated branch `feature/balanced-ux-redesign`. Fixed base and current HEAD `a843a2ab4d23c16f8a53d579e1e5be70288c8a9d`; this reviews the uncommitted candidate bound below, not a later commit.

Risk MEDIUM presentation/focus behavior; preserved snapshot/data contracts inspected with HIGH-risk care. Read supplied D-07 request, AGENTS, development workflow and domain/issue entry points. Affected seams: HTML context/selection/Compare ownership; CSS responsive thresholds and sticky inspector tools; controller panel/comparison focus and selection reveal; inspector saved context; table renderer/formula helps; dashboard layout/summary/table and frontend contract tests; new workspace cleanup regressions. Existing fixtures/API/exports/backend algorithms and mandatory CI config require preservation, not edits. CURRENT domain owners remain unchanged; this report and preservation ledger supply changed access-path evidence. Pre-existing backend/cache/coords_cache.json excluded.

## Findings and connected-path assessment

No BLOCKER/MAJOR production finding in inspected candidate. `methodologyHtml`, its call, disclosure markup/text and `.cluster-table-methodology` CSS are absent from frontend search. No dead substitute block or dangling prefix remains. MODE_LABELS remains needed for unsupported Bear messages. Price min/max helps now state unweighted destination points; median helps already state no weights; route/price/rate weighted helps retain metric-valid machine denominators and excluded-missing rules. Mode influence lives in existing weighted-price help. Saved period pills remain sourced from `table.period_types`. Backend `clustering_service.py` still owns methodology (unweighted_destination_points / metric_valid_trip_count); XLSX still reads it. No tracked backend/API/maths/config diff within scope.

`rawValue`, sorting (null-last, ID ties), formatting, row/cell/coverage generation, and all 14 column keys are unchanged. No new dependency, service seam, duplicated control panel or speculative abstraction. `revealInspectorSelection` is the one shared scroll action for cluster selection, point selection and opening the inspector drawer; it preserves ordinary rerenders. CSS sticky tools and centered selection are coupled through rendered geometry and now covered at doubled text. Compare stores the exact prior focus target separately from its parent drawer/opener, restores background inertness before reopening that drawer, and consumes Escape before the global panel close. This is the minimal required extra state for the relocated button.

**MINOR delivery obligation, pending owner integration:** historical preservation ledger still says "Central saved context strip above map" and "methodology disclosure". These are stale current access claims, not production regressions. Update the exact IDs below in a D-07 supplement/current projection, retain historical evidence as historical, and bind final source hashes/tests. FRZ-data-snapshot was never literally displayed by contextFor and must retain its API/request identity distinction. Do not infer 294 fresh UI passes or inherit old visibility claims wholesale.

## Independent checks

- Source: complete production diff and connected panel/comparison/selection/context/table paths, caller search, backend methodology/export anchors; `rg -n "methodologyHtml|cluster-table-methodology" frontend` returned no matches.
- `git diff --check`: PASS. Backend/config diff excluding known cache: no relevant change.
- Actual Edge through repository controlled public UI harness, `REQUIRE_FRONTEND_BROWSER=1`, interpreter `C:/folder/Python/AI_logistics_clean/.venv/Scripts/python.exe`: `python -m pytest -q -o addopts= -p no:cacheprovider tests/test_dashboard_workspace_cleanup.py tests/test_dashboard_table.py::test_all_fourteen_raw_sort_keys_keep_null_last_and_ascending_identity_ties tests/test_dashboard_table.py::test_each_metric_help_keeps_its_own_denominator_and_zero_is_not_missing tests/test_dashboard_layout.py::test_selection_reveals_details_after_scrolled_overview_without_resetting_rerenders` -> **14 passed in 84.41s, zero skips**. Covers three desktop areas/top68, narrow/docked Compare close and Escape focus return, frozen object retention, doubled-text cluster/point reveal, all raw sort keys, own coverage and real zero.

Independent extra Edge probe at 1440x900: geography / geo_cost / geo_volume each rendered saved Union names and leading-zero FIAS IDs under the inspector disclosure, current plus forecast period pills, preserved missing-value and mode-influence help, 14 columns and no methodology disclosure: PASS (3 mode observations). Initial scratch-probe assertions failed at the PowerShell stdin Unicode boundary; Unicode-escaped expectations passed without product edits.

## Exact affected preservation IDs and corrected paths

These are 48 individually named records (FRZ9/TBL14/TST9/COV16). Source inspection establishes the corrected route; targeted execution above establishes named tested behavior only. Historic numerical/API evidence may remain arithmetic evidence where code is unchanged, but does not prove relocated visibility. On narrow layouts first open `#mobile-inspector-btn` for inspector paths; wide desktop inspector is docked. Table paths use the table below map and its own scroll.

| ID | Current access path / retained distinction |
|---|---|
| `FRZ-frozen-request` | #clustering-inspector #result-context: route strong + saved method/K/weights/filter small elements; full request remains API/XLSX provenance, not literal UI JSON |
| `FRZ-selection-intent` | #clustering-inspector #result-context > strong: explicit All / Union count / single origin |
| `FRZ-origins` | #clustering-inspector #result-context details > summary then small names/FIAS for Union/All; single strong + FIAS small |
| `FRZ-origin-coverage-zero-match` | #clustering-inspector #result-context > small: zero-match saved origins notice |
| `FRZ-source` | #clustering-inspector #result-context > span: source attribution Pulse |
| `FRZ-data-snapshot` | Saved identity stays in state.result.data.data_snapshot and frozen detail/export requests; not visibly rendered by contextFor (old ledger must not imply visible snapshot) |
| `FRZ-stale` | #clustering-inspector #result-status: form-change notice; table .cluster-table-state; narrow #mobile-inspector-btn warning dot and accessible label |
| `FRZ-rejected-snapshot` | #clustering-inspector #result-status: changed Pulse/coordinates notice and blocked detail/XLSX; narrow result button warning dot |
| `FRZ-unavailable-result` | #clustering-inspector #result-status: saved result unavailable notice and blocked detail/XLSX; narrow result button warning dot |
| `TBL-cluster-id` | #cluster-table-panel thead [data-sort-key="cluster_id"] and matching tbody column; local horizontal/vertical scroll; row identity button for cluster ID |
| `TBL-point-count` | #cluster-table-panel thead [data-sort-key="point_count"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-trip-count` | #cluster-table-panel thead [data-sort-key="trip_count"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-trip-share` | #cluster-table-panel thead [data-sort-key="trip_share"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-weighted-route-length` | #cluster-table-panel thead [data-sort-key="weighted_route_length"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-price-min` | #cluster-table-panel thead [data-sort-key="price.min"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-price-median` | #cluster-table-panel thead [data-sort-key="price.median"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-price-weighted` | #cluster-table-panel thead [data-sort-key="price.weighted"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-price-max` | #cluster-table-panel thead [data-sort-key="price.max"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-rub-per-km-min` | #cluster-table-panel thead [data-sort-key="rub_per_km.min"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-rub-per-km-median` | #cluster-table-panel thead [data-sort-key="rub_per_km.median"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-rub-per-km-weighted` | #cluster-table-panel thead [data-sort-key="rub_per_km.weighted"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-rub-per-km-max` | #cluster-table-panel thead [data-sort-key="rub_per_km.max"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `TBL-economic-coverage` | #cluster-table-panel thead [data-sort-key="economic_coverage"] and matching tbody column; local horizontal/vertical scroll; focus/hover matching .cluster-value-help for raw precision/unit/coverage |
| `COV-coverage-route-length-valid-points` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-weighted_route_length"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-route-length-total-points` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-weighted_route_length"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-route-length-valid-trip-count` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-weighted_route_length"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-route-length-total-trip-count` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-weighted_route_length"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-price-valid-points` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-price.weighted"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-price-total-points` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-price.weighted"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-price-valid-trip-count` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-price.weighted"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-price-total-trip-count` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-price.weighted"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-rub-per-km-valid-points` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-rub_per_km.weighted"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-rub-per-km-total-points` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-rub_per_km.weighted"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-rub-per-km-valid-trip-count` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-rub_per_km.weighted"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-coverage-rub-per-km-total-trip-count` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-rub_per_km.weighted"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-economic-coverage-valid-points` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-economic_coverage"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-economic-coverage-total-points` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-economic_coverage"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-economic-coverage-valid-trip-count` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-economic_coverage"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `COV-economic-coverage-total-trip-count` | #cluster-table-panel tbody .cluster-value-help[aria-describedby="cluster-value-<cluster_id>-economic_coverage"] > .cluster-table-tooltip: own valid/total points and machines; focus/hover/click help; no methodology disclosure |
| `TST-table-sort` | #cluster-table-panel thead [data-sort-key]: all 14 headers, horizontal scroll where required; aria-sort and retained focus |
| `TST-table-open` | #cluster-table-panel [data-table-toggle]: collapse/reopen; local .cluster-table-scroll offsets |
| `TST-selected-hovered-cluster` | #cluster-table-panel tbody tr[data-cluster-id]: selected/hovered classes; row identity button opens inspector detail |
| `TST-period-types` | #cluster-table-panel .cluster-table-periods .cluster-table-period: saved table.period_types pills (including Pulse forecast); no methodology disclosure |
| `TST-methodology-distributions` | Existing column formula helps: #cluster-formula-price.min/.median/.max and #cluster-formula-rub_per_km.min/.median/.max; destination-point min/max and explicitly unweighted median retained; no replacement block |
| `TST-methodology-weighted-values` | Existing #cluster-formula-weighted_route_length, #cluster-formula-price.weighted, #cluster-formula-rub_per_km.weighted: metric-valid machine denominators; matching value helps expose metric coverage |
| `TST-missing-values` | Existing weighted metric formula helps say missing excluded / dash; per-value help distinguishes unavailable from true zero; coverage own denominators retained |
| `TST-supported` | #cluster-table-panel: supported ordinary 14-column table; Bear unsupported text and existing map/details, no fabricated ordinary rows |
| `TST-table-error-empty` | #cluster-table-panel .cluster-table-state[.error]: malformed/empty rows; independent of selected inspector detail |

## Reviewed candidate SHA256

- `frontend/index.html`: `ff47d2295d52d9fde858d75fb6517e4e0db4826f0b76b4751f298a60d2e0b66c`
- `frontend/css/style.css`: `5dad2ca63fd736b92026e4db2eba3b82dc521288f08a153e0a3371909ab0befc`
- `frontend/js/clustering/controller.js`: `558e607e46bfd58a23599570017c9c905331f17a72a427c860bfa0417e255928`
- `frontend/js/clustering/inspector.js`: `1d679be6ae53a141085791ed29840788031ec8066f00496e978d029901e60fb9`
- `frontend/js/clustering/table.js`: `4846c780c8bc0a7ceb04f5544b48af9246fea36f6d616c4ae0b30cef1b93dade`
- `tests/test_dashboard_workspace_cleanup.py`: `7a736d92e5951309ee7d3b1f3cff29fa298e51f6fbe03d7a37b778d535397007`

## Verdict and limitations

Standards/targeted Ponytail production scope: **PASS**. Delivery evidence: complete the explicit ledger update and final commit binding before claiming full D-07 readiness. Functional evidence above is controlled actual Edge, not native mouse/browser UI acceptance. Human acceptance remains UNVERIFIED; production/merge readiness remains UNVERIFIED pending owner's full local gates, exact-HEAD hosted CI and served revision evidence. No full suite duplicated, no merge, no cleanup.

Not checked: fresh native zoom/OS text UI, all five real Flask result routes, actual XLSX downloads, final hosted CI and human visual acceptance. Risk: later candidate changes invalidate these hashes and require affected replay.


## Final import-only supplement

Independently inspected final controller import change: removed unused `clusterLabel` from the formatters import. `rg -n "clusterLabel" frontend/js/clustering/controller.js` returns no occurrence after the selection-context assignment deletion. Remaining imports and call paths are unchanged; no behavior change or runtime replay required for this deletion. Final controller SHA256: `ad9dae517b059af48aab5eba7d6e7756d7c3a19e087d6e21d478815ba45bc9d4`. Earlier controller hash above records the runtime-tested candidate; this supplement binds the import-only final candidate. Standards/targeted Ponytail verdict remains PASS.


## Preservation-ledger disposition supplement

Independent read and assert-based document check of `13-workspace-evidence.json`: 294 unique record IDs and 35 unique criterion IDs; all 48 explicit paths equal this report exactly. Current access fields contain no central saved-context-strip/above-map claim or positive methodology-disclosure claim (remaining references explicitly say no disclosure). Owner projections put summary/quality in right inspector, technical metrics in its diagnostics and Compare entry in the right inspector. Historical obligations are separately labeled historical. The retained `10-information-preservation.json` SHA256 equals the ledger historical binding. The traceability method explicitly refuses 294 fresh native visibility claims; native/human/production limits remain UNVERIFIED.

Delivery MINOR stale-access obligation: **RESOLVED** by the D-07 current projection, with historical evidence retained. Inspected ledger SHA256: `25cd9e00d1fa309454fb5b47af2fd2e06841c5a44219dcd9056af51683f1f87a`. Final D-07 focused-test SHA256: `13e2b152a515b36f45214e8583ccf4ff7ee860376fd4f2b5f0fff1b18205b9f3` (Ruff import order and three new narrow attention-marker cases for draft/critical/warnings inspected by source; no reviewer runtime replay claimed for those added cases). Earlier runtime evidence remains bound to its tested candidate; owner final gates cover the final test file. Production source is unchanged from the import-only supplement.


## Final regenerated ledger and delivery-text check

Repeated independent document assertions after owner regenerated source bindings: 294 unique record IDs, 35 unique criterion IDs, exact equality of all 48 corrected paths, all ten worktree source hashes match disk, and historical ledger hash remains unchanged. No stale positive central-strip/above-map or methodology-disclosure access claim. Updated current ledger SHA256: `77e07f94cc5f4c79800adc0f4c6242cb19e3f8ee30109882108d929069301ac5` (supersedes the earlier inspected ledger hash for source-binding metadata only). Delivery MINOR remains RESOLVED.

Read `13-workspace.md` for claim scope. It labels actual Edge automation, synthetic retained data, Bear unsupported fixture states and unchanged numerical paths separately; it explicitly marks native 125% zoom, human acceptance and production readiness UNVERIFIED. Full local/hosted gates and committed/served revision binding are pending supplements, not claimed complete. No overclaim found within this document review. Ready for committed-blob binding; no runtime replay or production/test edit performed in this check.


## Final inspector-test fixture supplement

Inspected `git diff HEAD -- tests/test_dashboard_inspector.py`: first-visible-section query now includes sections nested directly under `#selection-context` as well as direct section children, preserving document order and exact `cluster-details` expectation. This corrects the DOM fixture assumption without weakening the selected-details-before-overview assertion. Inspector-test SHA256: `5f8ee7aab3c4c32d47589532ff5ee9fb4e36e37c9ee59dc0c62a0497fb4f1e47`. Owner RED/GREEN is reported separately; no independent runtime replay claimed here.

Repeated document assertions after regeneration: exact 48 paths, 294 unique record IDs, 35 unique criteria, all 11 source/test worktree bindings match disk, unchanged historical ledger hash, no stale positive central-strip/above-map/disclosure access claims. Current ledger SHA256: `1b915026cbdfffd8669daeeb11be8dc0eb06a05fb8073c3a3932412385d52e57` supersedes prior generated ledger bindings. `13-workspace.md` now explicitly records frontend 136 passed with zero skips and final Python repeat pending; no pending Python/hosted gate is promoted to PASS. Production unchanged; Standards/targeted Ponytail PASS and resolved delivery MINOR remain valid. Ready for committed-blob binding.


## Snapshot-conflict fake-DOM fixture supplement

Inspected the sole `tests/test_product_cluster_table.py` change: existing fake DOM elements gain a no-op `scrollIntoView()` method to support the presentation call. The real HTTP 409, unchanged recalculation, frozen result and cache assertions are untouched. Test-file SHA256: `11cc13ce06a09a02cb6512ed0952b22af137494d79eb7c45e7e39c9824e2189f`. Scoped source review PASS; targeted GREEN belongs to owner evidence, with no independent runtime replay claimed. Production files remain unchanged.

Regenerated ledger validation PASS: exact equality of 48 corrected paths, 294 unique record IDs, 35 unique criterion IDs, all 12 source/test worktree bindings current, historical ledger hash unchanged, no stale positive central-strip/above-map/disclosure claims. Current ledger SHA256: `1e6c72dd3bf13b016eac7064e44d11589a65e77b1ed7eb2a1465e8fc928f87a8` supersedes earlier generated ledger bindings. Standards/targeted Ponytail PASS and resolved delivery MINOR remain valid; final follow-up commit/blob and mandatory-gate binding remain pending.
