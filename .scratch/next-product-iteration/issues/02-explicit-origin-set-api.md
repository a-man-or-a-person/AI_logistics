# 02: NPI-02 — Рассчитать origin union через API с точной frozen identity

ID: NPI-02
Status: implemented ? local gates passed; final review/PR CI pending
Priority: NEXT Product
Blocked by: P1

**What to build / Business purpose:** HTTP-клиент получает одну destination point из A+B, правильные веса и безопасный saved context.

## Scope and exclusions

Аддитивный explicit origin-set contract сквозь options/preview/run/compare/detail; repository union, aggregate перед coordinates по destination FIAS, row provenance/zero-match metadata и все cache keys. Full backend-to-HTTP slice; UI пока scalar.

Exclusions: All resolver/UI, XLSX, origin summary UI, nullable origin модель, новая graph topology, rewrite generic/Bear economics.

## Prerequisites and implementation boundary

Canonical sorted/deduplicated set, scalar=singleton; reject empty/null/conflicting/unknown selectors/region/parameters с заданными codes/status/X-Request-ID. Общие четыре filters, общий zero rows→NO_DATA. Preview без clustering; compare пять fixed modes/winner=null. Full SpatialGraph перед eligibility, induced subgraphs; Bear/no_bears и RESEARCH/LEGACY ограничения сохранены. Frozen set/intent/filters/mode+normalized params/source+coordinate snapshot/membership/exclusions; singleton legacy fields без ложного scalar label у union. Rich detail lookup точного cached result, eviction/restart RESULT_UNAVAILABLE409 без rerun, old point-rows сохраняет slice compatibility/max50. Generation races не смешивают success.

Read the approved specification and [shared execution/evidence requirements](../execution-requirements.md). This card owns the criterion IDs below. Downstream UI/workbook branches are verified at integration, not claimed PASS at an API-only stage. TDD is required for behavior changes; this decomposition does not start TDD or implementation.

## Approved dependency / reuse clarification

P1 is a mandatory prerequisite: complete rejected-snapshot invalidation/recovery before changing frozen identity and snapshot lifecycle. NPI-02 delivers working backend union/identity. NPI-06 follows this working slice; do not introduce a reverse dependency. Downstream metric consumers wait for NPI-06.

Authoritative backend contract: normalized frozen request, mode/parameters and source/coordinate generation bind normalized rows to the exact saved destination-to-cluster membership (NPI-02). NPI-07 uses the same frozen-row access for origin-to-point summary/detail. NPI-10 reuses that access and the existing metric-valid accumulator / saved backend table values. Origin-to-cluster attribution is a join of origin rows with saved destination membership, not separate clustering. Direction sheets remain source-row origin-region to saved cluster; grouping changes neither grain, weights nor membership. Export must not aggregate rounded UI summaries or add a separate calculator.

## Current code / contract references

ClusteringRequest; ClusteringRepository; aggregate_clustering_records/_Accumulator; build_location_dataset; ClusteringService request/location/graph/result caches, point_rows; Product API.

Symbol/API references refer to origin/main `db1ed6415ee84fec6837a1f7025e5d676fce83f8`; recheck candidate before implementation. NEXT API spelling and errors come from the approved spec, not deployed facts. No prescribed file layout or speculative framework.

## Observable acceptance criteria

- [ ] **R1-04**: A+B and B+A select same canonical dataset and metrics; no duplicate trips introduced by selection order or duplicate FIAS input.
- [ ] **R1-09**: changing mode uses graph from all pooled coordinate-resolved destinations before eligibility; Geo+Cost/Bear do not add spatial edges or route-duplicate nodes.
- [ ] **I-01**: same snapshot with different origins/filters/mode parameters never confuses result/rows/export identity; exact backend membership checked. All resolution alone does not mark unchanged form stale or corrupt selection-intent provenance through cache reuse.
- [ ] **I-04**: result-cache eviction/restart yields visible RESULT_UNAVAILABLE/recalculate for new detail/export contracts, no substitute result.
- [ ] **I-05**: legacy scalar run/preview/compare/detail callers retain success shape/status; singleton set is equivalent; LEGACY/RESEARCH still separate.
- [ ] **I-06**: five actual modes run on representative synthetic origin union; existing Bear positive/no_bears/threshold semantics remain functional, table unsupported unchanged.

## Regression and integration verification

TDD Flask/injected fixtures: shared X, A+B/B+A/duplicates, filters/NO_DATA, single-origin parity, invalid selectors, generation races, same snapshot different request/mode/params, cache eviction,5 реальных modes/graph semantics. RED→GREEN + full gates.

## Risks

Double count, cache collision, потеря provenance или сломанная research single-origin restriction. До изменений найти callers request/repository/dataset/location serializers, tests/fixtures.

## Required evidence and Definition of Done

- [ ] Blockers complete; scope/criterion IDs confirmed against approved spec.
- [ ] Each owned criterion has action/input, expected/actual, evidence, environment, limitation and PASS/FAIL/UNVERIFIED; downstream branches delegated visibly to NPI-12.
- [ ] Behavior changes have actual RED → GREEN evidence; existing conformant behavior has regression evidence without fabricated RED.
- [ ] Applicable full verification and reviews in shared requirements complete; user-facing changes have observable live desktop evidence.
- [ ] Contract/CURRENT docs updated only for implemented behavior; all impacted callers/tests/fixtures/manifests addressed.
- [ ] No blocking integrity finding; unresolved external/capacity limitations explicitly retained.

## Comments

Published locally on 2026-10-10 after explicit user approval and requested dependency corrections. Stable NPI ID retained; filename prefix is dependency order. No production work or execution evidence claimed.


### NPI-02 implementation evidence ? 2026-10-10 (Europe/Moscow)

Baseline: fetched protected origin/main `73bca251387d699bfb4613b4ec826df1289f5c1d`.
PR #7 is merged; its HEAD `9e5ade64991080d821530406743670e655292c62` has
Quality run 38072943912 completed/success, including required verification.
P1 PR #5 and P2 PR #6 are merged and ancestors of this baseline.
Original checkout HEAD f69e64c and unrelated local/untracked files were preserved.
Implementation is isolated in `.worktrees/npi02-origin-union`, branch
`feat/npi02-origin-union`. Approved card/spec/coverage/tracker/order/shared requirements
were read from the original untracked planning directory, not replaced by drafts.
Scope remains this card; filename-order differences in the chat do not change IDs.

Public seams: existing Product Flask API, ClusteringService/Repository, synthetic Pulse;
these seams are already approved in spec Testing Decisions. `/tdd`, local `/implement`,
`/code-review`, Ponytail/Ponytail review and `/pr` apply. No new testing framework.

Root changes: canonical tuple origins replace scalar request identity; scalar is a
singleton. Options union reuses indexed facet counts. Repository reads each selected
origin once and delegates raw-row destination pooling to the existing metric-valid
accumulator before coordinates/graph. Original duplicate observations retain distinct
source-row identities. Route/price/rate denominators remain independent.
Full graph remains shared across the five adapters; no mode/algorithm redesign.
Analysis adds resolved set, explicit selection intent, display and zero-match metadata,
and reusable normalized `frozen_request`. Multi-origin scalar labels are null.
New detail retrieves the exact request/mode/parameters/generation cache entry and saved
point membership/status; eviction/restart is RESULT_UNAVAILABLE409, no rerun.
Old scalar detail shape and cached-slice semantics remain. Rich rows add actual
origin/row-region/destination attribution and optional selected-origin restriction.
Checks around reads/calculation/serialization/cache publication reject generation races.
Exact FIAS display lookup avoids search-suggestion collisions.

RED ? GREEN evidence (commands use the existing `.codex-impl-env/Scripts/python.exe`):
1. `-m pytest tests/test_origin_union_api.py -ra`: initial public union tracer failed
HTTP400 INVALID_REQUEST because scalar origin was required; same test then passed.
2. Surface slice: 3 failed/3 passed ? compare rejected singleton set400, options lacked
union facets, detail returned UNKNOWN_DESTINATION_POINT422. After implementation,
98 API/repository checks passed.
3. Validation/race slice: 7 failed/40 passed ? empty preview returned200, six
source/coordinate races returned success200. After generation checks and NO_DATA,
146 union/API/dataset/location checks passed. Two existing tests deliberately updated:
old generation-race success and empty preview success now enforce the approved errors.
4. Frozen-request/injected union slice: 7 failed/47 passed ? five missing frozen_request,
injected union500 and incomplete rich context200. After repair,142 union/API checks passed.
5. Exact display lookup: origin b became literal label b when origin a's name contained
b; observed assertion failure. Exact catalog identity fixed it; final focused65 passed.
No RED manufactured for already-correct weighted accumulator/Bear algorithms.

Acceptance evidence: actual algorithms, Flask test client, safe synthetic CSV7 rows,
3 origins,4 resolved destinations; expanded paging fixture68 rows. All expected metric
values are hand-calculated constants. Production capacity remains UNVERIFIED.

| ID | Input/action and expected | Actual/evidence | Status/limits |
|---|---|---|---|
| R1-04 | A+B/B+A/repeated/whitespace origins; pooled X once,60 machines,route250(valid40),price4750(valid40),rate17.5(valid40) | `test_union_is_canonical_and_pools_raw_valid_weights`; identical complete responses; distinct duplicate source observations preserved | PASS API |
| R1-09 | Compare five actual modes; graph must include pooled X/Y/Z/W before economics eligibility | `test_real_modes_share_pooled_full_graph_and_keep_bear_semantics`; one build, same full graph for five datasets, Y economic_unavailable; existing induced-subgraph adapter regressions | PASS backend |
| I-01 | Same snapshot different origins/filters/mode/K; retrieve only exact saved context and actual destination membership | `test_rich_detail_is_bound_to_saved_mode_and_rows`, `test_detail_uses_exact_membership_and_generation`, normalized-request five-mode roundtrip, paging/filter tests | PASS owned explicit API; All intent/UI/export branches UNVERIFIED, delegated to NPI-03/04/10/11/12 |
| I-04 | Clear result LRU / new service at same generation; detail must409 without evaluate | `test_detail_restart_and_stale_snapshot_fail_without_reclustering`, rich-detail eviction test: RESULT_UNAVAILABLE; generation change STALE_DATA_SNAPSHOT | PASS detail; export branch UNVERIFIED until NPI-10/11/12 |
| I-05 | Scalar versus singleton on preview/run/compare; existing scalar detail schema/status; RESEARCH scalar guards | `test_union_surfaces_and_scalar_parity`; existing Product API, ML dataset/location/research tests; scalar source-row exact-field assertions | PASS compatibility; error-state race/empty-preview tightened per approved contract |
| I-06 | Five real union modes; cost positive/no_bears,volume positive/no_bears,presets; Bear table unsupported | two actual-mode union tests plus Bear/business adapter regressions; X volume singleton,Z cost singleton; .2/.35/.5 thresholds | PASS backend; no new UI/Bear semantics |

Other contract coverage: invalid/empty/null/conflicting/unknown selectors and region,
omitted origin != All, common filters/NO_DATA and X-Request-ID; zero-match C retained;
missing metric rows and independently valid route weights; 50+13 newest-first detail
pages with63 distinct IDs, selected-origin narrowing, generation races across
preview/run/compare/detail, restart/eviction, cached response normalization.
Cluster wx:65 machines,route233.33333333333333/valid45,price4333.333333333333/rate16.666666666666667;
cluster yz:10 machines,route150/valid10,price1000/valid5. No UI rounding in backend.

Verification in progress; final commands, review dispositions, PR/CI will be appended
here. All resolver, multi-origin frontend, summaries/navigation,XLSX,ATI,new modes,
unrelated Bear/RESEARCH/LEGACY changes are excluded. Existing file metadata tokens
and in-memory result lifetime remain; no production capacity or durable snapshot claim.


Final local gates after review fixes (Python3.12.14, Node22.23.3,
Edge155.0.4283.45, pytest8.3.5, Ruff0.9.10; Windows desktop):
- Locked install: `python -m pip install -r requirements-lock.txt` ? all exact pins installed;
  `python -m pip check` ? No broken requirements found. No dependency changes.
- Mandatory startup: workflow's runpy Node JSON assertion + Edge dataset assertion ? PASS.
- Full: `REQUIRE_FRONTEND_BROWSER=1 python -m pytest -ra -p no:cacheprovider
  --basetemp=.scratch/npi02-reviewed-temp --junitxml=.scratch/npi02-reviewed-results.xml`
  ? **343 passed in19.47s, zero skips** (43frontend+300other).
  XML assertion confirmed no skipped testcase and43 frontend cases.
- `python -m pytest tests/test_origin_union_api.py -ra` ? **68 passed in3.14s**.
- `python -m ruff check .` ? PASS. `node --check` on all12 frontend JS files ? PASS.
  `git diff --check` ? PASS.
- Initial sandbox browser failures were interrupted and are not PASS evidence.
  Authorized normal Edge/process execution succeeded. Earlier full339/340 passes
  preceded subsequent review fixes; final343 is authoritative. Cacheprovider was
  disabled to avoid host filesystem cache warnings, not to skip any tests.

P1 regressions: `test_unchanged_recalculation_recovers_after_real_snapshot_conflict`
uses actual live Flask HTTP+Node controller, mutates the synthetic CSV, observes409,
verifies rejected cache bypass, failed refresh preserving display, new snapshot/rows
and safe comparison recovery. Selective rejected-snapshot cache tests PASS.
P2: `test_cached_comparison_keeps_form_mode_and_presets_after_filter_edit` uses real
Edge DOM mode/K/preset/radio controls, cached switch then period edit and next submitted
Geography; frozen membership/metrics and request-free switching PASS.
No frontend production edits. Fresh human desktop walkthrough of historical whole
scenarios10/12/16 is not claimed; it remains NPI-12 integration evidence.

Reviews: independent Standards at b4fb40a:0 blockers; advisory graph collaborator
assertions retained because R1-09 explicitly requires full graph sharing/eligibility.
Independent Spec found injected scalar options region regression; reproduced RED
(empty region list) and repaired canonical-origin collection, new HTTP test GREEN.
Ponytail review (local desktop app load, no capacity assumption) found source change
during cached/new result deepcopy could return success; both cases reproduced RED200
versus expected409. Copy now precedes generation validation/cache publication, both
GREEN. Union logs now record all canonical origins; audit grain label reflects union.
No remaining known blocker; independent re-review is requested on final source.
Ponytail verdict: Ship after these fixes. No dependency, new mode or speculative layer.

All six owned criterion rows have PASS backend evidence above; future All intent,
UI and export branches remain explicitly UNVERIFIED/delegated. Production capacity,
metadata-token hash limitations and in-memory result lifetime remain documented.
Publication/actual-head CI result will be recorded after GitHub verification completes;
no automatic merge authorized or performed.
