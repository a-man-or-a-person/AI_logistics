# 04: NPI-03 — Разрешать «Все отправления» одного региона на backend

ID: NPI-03
Status: backend implemented; final independent reviews passed; required final-HEAD verification tracked in PR checks
Priority: NEXT Product
Blocked by: NPI-02, NPI-06

**What to build / Business purpose:** HTTP-клиент выбирает полный regional origin set независимо от лимита поиска.

## Scope and exclusions

all_origins selector, destination-scoped origin catalog/options, generation-safe resolution для preview/run/compare.

Exclusions: Frontend All, guessed capacity/SLA, implicit All для пустого selector.

## Prerequisites and implementation boundary

Полный R-serving set ДО segment filters, включая origins за q/limit/search page; zero-match origins disclosed. Каталог и read rows в одном generation, source race/catalog error→typed failure, без partial union. Compare разрешает All один раз для5 modes. Saved set не re-expand; cache reuse сохраняет explicit/All selection intent.

Read the approved specification and [shared execution/evidence requirements](../execution-requirements.md). This card owns the criterion IDs below. Downstream UI/workbook branches are verified at integration, not claimed PASS at an API-only stage. TDD is required for behavior changes; this decomposition does not start TDD or implementation.

## Approved dependency / reuse clarification

NPI-06 must supply backend regression evidence for valid multi-origin weighted route and coverage before All consumes these metrics. All reuses the common aggregation.

## Current code / contract references

ClusteringRepository options/destination_regions/fingerprint; ClusteringRequest; ClusteringService origins/options/preview/run/compare; frozen analysis.

Symbol/API references refer to origin/main `db1ed6415ee84fec6837a1f7025e5d676fce83f8`; recheck candidate before implementation. NEXT API spelling and errors come from the approved spec, not deployed facts. No prescribed file layout or speculative framework.

## Observable acceptance criteria

- [ ] **I-03**: compare resolves All once at one generation, five modes share same frozen dataset; mode switch no hidden run and winner remains null.

## Regression and integration verification

TDD HTTP fixture с origin за search limit, чужим регионом, zero-match, race, same-set explicit/All cache reuse и общей compare generation.

## Risks

Search page ошибочно становится complete catalog; пере-разрешение saved All.

## Required evidence and Definition of Done

- [ ] Blockers complete; scope/criterion IDs confirmed against approved spec.
- [ ] Each owned criterion has action/input, expected/actual, evidence, environment, limitation and PASS/FAIL/UNVERIFIED; downstream branches delegated visibly to NPI-12.
- [ ] Behavior changes have actual RED → GREEN evidence; existing conformant behavior has regression evidence without fabricated RED.
- [ ] Applicable full verification and reviews in shared requirements complete; user-facing changes have observable live desktop evidence.
- [ ] Contract/CURRENT docs updated only for implemented behavior; all impacted callers/tests/fixtures/manifests addressed.
- [ ] No blocking integrity finding; unresolved external/capacity limitations explicitly retained.

## Comments

Published locally on 2026-10-10 after explicit user approval and requested dependency corrections. Stable NPI ID retained; filename prefix is dependency order. No production work or execution evidence claimed.

### NPI-03 execution evidence — 2026-10-10 (Europe/Moscow)

Approved authority: this exact stable-ID NPI-03 card (dependency filename04),
spec.md, coverage-matrix.md, tracker.md, implementation-order.md and shared
execution-requirements.md. Approved testing seams are Product HTTP and the existing
Flask/synthetic Pulse fixture. `/tdd`, `/implement`, `/code-review`, Ponytail full,
independent Ponytail review and `/pr` applied. No extra implementation approval needed:
the current user explicitly authorized implementation and PR publication.

#### Prerequisites and isolation

- Latest fetched origin/main: `ca89a681ed644d6c18d34d2c90bb7580d3415aef`.
  Main is protected (GitHub branch API verified). PR #9 is merged at this SHA.
- PR #9 final HEAD `8048d449a4ea63eaa06267bf6d5aefe48d2aeb70` has required
  [verification SUCCESS](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38075896540/job/114282655399).
  NPI-02 PR #8 and NPI-06 results/contracts were read; both prerequisites satisfied.
- Branch `feat/npi03-regional-all`, isolated `.worktrees/npi03-regional-all`.
  Original checkout `f69e64c`, branch and pre-existing untracked artifacts preserved.
  No confidential source rows or generated test data committed.

#### Request/response contract and saved-result safety

POST preview/run/compare requires exactly one selector: nonempty scalar origin_fias,
nonempty origin_fiases string list, or JSON all_origins=true; one destination_region,
four common filter lists, existing modes/parameters/defaults. False/null/string/number
All, missing/empty/conflicting selections remain INVALID_REQUEST400. Unknown explicit
origin=UNKNOWN_ORIGIN422; unknown regional catalog=UNKNOWN_DESTINATION_REGION422;
all zero-match after common filters=NO_DATA422. Catalog read failure=INTERNAL_ERROR500;
source/coordinate race=STALE_DATA_SNAPSHOT409. X-Request-ID preserved.

GET origins keeps q/limit (1..100), adding destination_region scoping. GET options
supports repeated origin_fiases or all_origins=true plus destination_region; returns
full regional origins and union facets. Surrounding region whitespace is normalized
consistently on All resolution, validation, catalog and facets, including records_factory.
Resolution never calls paginated suggestions: 108 regional origins resolve despite
100 maximum suggestions; other-region origin excluded. Canonical resolved set is
sorted/deduplicated before filters; zero-match origins stay in origin_coverage.

Each result/preview retains analysis.selection_intent={all_origins:true} and actual
analysis.origin_fiases. analysis.frozen_request deliberately contains explicit resolved
origin_fiases, region, four lists and normalized mode/parameters, with no All selector.
Same-set explicit/All requests reuse calculation/cache while each response keeps its
own selection intent. Existing source/coordinate generation, normalized request and
actual saved membership bind rich detail. POST point-rows requires saved explicit
context+snapshot+destination; optional detail_origin_fias only narrows it. All in detail
is INVALID_REQUEST400; changed exact context or restart/eviction=RESULT_UNAVAILABLE409;
changed generation=STALE_DATA_SNAPSHOT409. It never expands All, reruns or substitutes
membership. New successful All recalculation may resolve new origins/new snapshot;
old response/detail remains frozen and is rejected after generation changes.

All resolution and reads share checked generation. Compare resolves once before
five fixed modes; same full pooled geographic graph/generation/set, winner=null.
Common accumulator, destination FIAS pooling and independent valid-machine denominators
remain unchanged: X60 machines, route250km with valid40/60, price4750/rate17.5 with
valid40. All default filtered union has6 source rows/4 destinations/75 machines;
zero-match c remains selected. Bear Cost no_bears and Bear Volume x singleton/table
unsupported remain; Geo+Cost y economic_unavailable, full graph w/x/y/z preserved.

#### Genuine TDD evidence

No production edits preceded the first public HTTP test. Commands use repository
`.codex-impl-env/Scripts/python.exe`, worktree cwd, pytest `-p no:cacheprovider`.

| Cycle / command suffix | Genuine RED before fix | GREEN evidence |
|---|---|---|
| tests/test_regional_all_api.py, basetemp all-red1 | complete-regional run400 INVALID_REQUEST: "Regional All is not supported yet" | same test200, set a/b/c, route250/40/60; all-green1 1PASS |
| regional suite, all-red2 | preview422; suggestions wrongly include outside-region origin (2FAIL) | preview/search/options regional contract passes |
| test_compare_resolves_all_once_for_five_modes, all-red3 |5 regional resolutions versus expected1 | one resolution, five results, winner null; all-green2 89PASS including union |
| injected options regression, all-red-review | foreign-region origin leaked in options | scoped catalog + spot6/tender1 facets; focused166PASS |
| normalized options regression, all-red-normalization | repo422 and injected empty200 for padded region (2FAIL) | both200 with correct catalog/facets; final focused168PASS |

The first full run's fixture-registration errors and injected manifest-only options
missing-file regression were repaired. They are not fabricated feature RED evidence.
Regression-only additional safety cases passed without claiming every case was RED.

#### Exact acceptance coverage

Windows; Python3.12.14, pytest8.3.5, Ruff0.9.10, Node22.23.3, real Edge.
Safe synthetic Pulse CSV/coordinates, real mode adapters, actual HTTP JSON/status checks.

| ID / ownership | Input/action and expected | Actual/evidence / limits |
|---|---|---|
| I-03, owned | explicit All compare resolves once; five variants same frozen region dataset/graph/snapshot; winner null; cached switching sends no run | PASS backend: test_compare_resolves_all_once_for_five_modes, test_all_preview_and_compare_keep_resolved_context, test_all_compare_shares_full_graph_and_keeps_mode_semantics. Existing Node/Edge cache/mode switching regressions PASS; new All UI remains NPI-05, no human All UI walkthrough claimed |
| R1-02, support NPI-05 | All with no origin-region includes full catalog beyond q/limit, excludes foreign region | PASS API: complete catalog, options/scoped suggestions,108-versus100 tests; rendered All UI UNVERIFIED downstream |
| R1-03/R1-06, support NPI-04 | common filters leave c zero-match, all absent vehicle rows NO_DATA | PASS API context/errors with unchanged frozen result; new UI explanations UNVERIFIED downstream |
| R1-04/R1-05/I-05, support | deterministic sorted set/no duplicate rows, scalar=singleton, empty/missing/conflict never All | PASS existing84 union tests + strict All invalid POST/query matrix; current frontend43 checks PASS |
| R1-08, support NPI-05 | append d after saved All; old detail409; new recalculation set a/b/c/d; old response a/b/c | PASS test_all_recalculation_resolves_new_generation_without_expanding_saved_detail; future All UI UNVERIFIED |
| I-01, supporting All-intent branch | explicit/All same resolved dataset reused without intent loss; rich detail exact saved membership | PASS both cache orderings, no evaluate allowed,3 x rows a/b exact cluster; detail widened set409/All400 |
| I-02/I-04, support | resolution/evaluation source/coordinate race, catalog failure, restart/eviction | PASS All race matrix and existing union detail/cache tests; typed409/500, no partial successful response or rerun |
| R1-09/I-06, support | full graph before eligibility, five actual adapters/Bear semantics unchanged | PASS All full graph identity and union/Bear suites, no frontend/mode redesign |
| R3-01/02/04/06/07/08, support NPI-06 | X250 valid40/60, additive raw-row table means, independent denominators/period filtering/scalar parity | PASS existing NPI-06 regressions plus All X constants; downstream UI/workbook remain UNVERIFIED |

#### Final local gates and independent reviews

- `python -m pip install -r requirements-lock.txt`: exact pins already satisfied;
  `python -m pip check`: no broken requirements. No dependencies added.
- Focused: `python -m pytest tests/test_regional_all_api.py tests/test_origin_union_api.py
  tests/test_product_cluster_table.py tests/ml/test_clustering_repository.py -ra
  -p no:cacheprovider --basetemp=.scratch/all-normalized-green`: **168PASS**.
- Required workflow runpy Node JSON + Edge dataset startup assertions: PASS.
- Final source `e6b2de5e3b807954bafd9aba08c61a431d000cd2`:
  `REQUIRE_FRONTEND_BROWSER=1 python -m pytest -ra -p no:cacheprovider
  --basetemp=.scratch/all-final-normalized --junitxml=.scratch/all-final-normalized.xml`:
  **429PASS in26.00s**, including70 new All cases and43 mandatory Node/Edge cases.
  XML assertions:429 testcases,43 frontend cases,0 skips.
- `python -m ruff check .`: PASS; all12 frontend JS files `node --check`: PASS;
  `git diff ca89a681...HEAD --check`: PASS. Restricted generated-temp directory warnings
  did not omit tracked files; tracked Python files separately checked successfully.
- Independent Standards final: **0 findings**, original CONTEXT discrepancy fixed.
- Independent Spec final: **0 remaining findings**; normalized-options finding resolved;
  independently154 All+union tests PASS.
- Independent Ponytail final: **Ship,0 remaining findings**; foreign-region injected
  options resolved, normalized options verified; independently70 All tests PASS.

Final publication adds this existing approved card only; no test/source change after
the authoritative final gates. Final PR HEAD/checks will be verified on GitHub after
publication, never inferred from previous HEAD. No automatic merge.

Excluded: NPI-04 multi-select UI, NPI-05 All UI, origin summary, XLSX, ATI, changes
to modes/Bear/RESEARCH/LEGACY. Live confidential data, human All UI acceptance and
production load/capacity/SLA are UNVERIFIED. Existing metadata fingerprints and
in-memory result lifetime remain; this PR does not promise durable historical snapshots.
