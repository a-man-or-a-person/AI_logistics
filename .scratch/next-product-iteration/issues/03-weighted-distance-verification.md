# 03: NPI-06 — Подтвердить weighted distance и coverage для origin union

ID: NPI-06
Status: backend verified; independent reviews passed; required PR verification tracked in PR #9 checks
Priority: NEXT Product
Blocked by: NPI-02

**What to build / Business purpose:** Логист получает длину пути средней машины и честное покрытие пропусков.

## Scope and exclusions

Регрессии существующей формулы/valid denominator propagation в point/table/методике; production changes только для обнаруженного конкретного gap.

Exclusions: Второй calculator/routing API, new distances, tonne/equal-origin weighting, rewrite Bear/regional economics.

## Prerequisites and implementation boundary

Reuse _Accumulator и table projection.10×100+30×300=250; ещё20 missing→250/40из60. Positive valid weight/length; zero denominator unavailable. Cluster=raw valid-row mean; price missing не убирает valid route. Min/median/max price/rate по destination-point values; filters/combined periods совместно меняют суммы; forecast external Pulse. UI/XLSX части owned criteria завершаются downstream и в NPI-12.

Read the approved specification and [shared execution/evidence requirements](../execution-requirements.md). This card owns the criterion IDs below. Downstream UI/workbook branches are verified at integration, not claimed PASS at an API-only stage. TDD is required for behavior changes; this decomposition does not start TDD or implementation.

## Approved dependency / reuse clarification

This is an explicit prerequisite for NPI-03, NPI-04, NPI-07 and NPI-10. Its prerequisite exit is verified backend union/point/table metric correctness and applicable current methodology. Future origin-summary, UI and XLSX branches remain UNVERIFIED until the consumer tickets and NPI-12 execute them. NPI-06 must not wait for those future consumers or introduce reverse dependencies.

## Current code / contract references

_Accumulator.add/_weighted; valid_route_length_trip_count; cluster_table weighted_mean/coverage; route tooltip/Product/Data contracts.

Symbol/API references refer to origin/main `db1ed6415ee84fec6837a1f7025e5d676fce83f8`; recheck candidate before implementation. NEXT API spelling and errors come from the approved spec, not deployed facts. No prescribed file layout or speculative framework.

## Observable acceptance criteria

- [ ] **R3-01**: A→X10 machines100km and B→X30 machines300km display250km at pooled X; same metric in workbook.
- [ ] **R3-02**: add20 machines with missing distance: mean stays250, coverage40/60; no zero imputation.
- [ ] **R3-03**: no valid positive lengths/weights → unavailable null/—/blank, not zero or divide-by-zero success.
- [ ] **R3-04**: cluster over multiple points with partial missing distances matches hand-calculated raw valid-row mean, not total-trip-weighted average of point means.
- [ ] **R3-06**: route tooltip/methodology identifies km, machine weights and valid denominator; price/rate missing does not remove a valid route contribution.
- [ ] **R3-07**: single-origin synthetic regression keeps existing point/table values, min/median/max semantics and valid coverage.
- [ ] **R3-08**: segment filters and combined selected periods affect numerator/denominator together; forecast label denotes supplied Pulse period.

## Regression and integration verification

Hand-calculated constants в dataset/location/table/Flask regressions. Conformant existing logic→GREEN evidence, без фиктивного RED; если найден gap→настоящий RED перед narrow fix. NPI-12 проверяет workbook/UI consumers.

## Risks

Total trips вместо metric-valid denominator или test копирует production calculation.

## Required evidence and Definition of Done

- [ ] Blockers complete; scope/criterion IDs confirmed against approved spec.
- [ ] Each owned criterion has action/input, expected/actual, evidence, environment, limitation and PASS/FAIL/UNVERIFIED; downstream branches delegated visibly to NPI-12.
- [ ] Behavior changes have actual RED → GREEN evidence; existing conformant behavior has regression evidence without fabricated RED.
- [ ] Applicable full verification and reviews in shared requirements complete; user-facing changes have observable live desktop evidence.
- [ ] Contract/CURRENT docs updated only for implemented behavior; all impacted callers/tests/fixtures/manifests addressed.
- [ ] No blocking integrity finding; unresolved external/capacity limitations explicitly retained.

## Comments

Published locally on 2026-10-10 after explicit user approval and requested dependency corrections. Stable NPI ID retained; filename prefix is dependency order. No production work or execution evidence claimed.

### NPI-06 backend verification — 2026-10-10 (Europe/Moscow)

Fetched main: `5923cd90b1ba483f673546a3b28091a9634ee379`, merge of PR #8.
PR #8 is merged; HEAD `7a95eb63857b44aceb282c9e73e2ff2ceb71798e` is an ancestor.
Required [verification job](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38074768102/job/114279333148)
completed SUCCESS. NPI-02 prerequisite is satisfied. Original checkout remains
`f69e64c` on `chore/automated-quality-guardrails`; all pre-existing local/untracked
work retained. Work is isolated in `.worktrees/npi06-weighted-verification`,
branch `test/npi06-weighted-verification`.

Authority: this exact approved card (dependency filename03, stable ID06), approved
spec R3, coverage matrix (R3-05 belongs to NPI-04), implementation order, shared
execution requirements, Product/data/workflow contracts, CONTEXT and current-state.
No ADR directory exists. `/implement`, `/code-review`, Ponytail full/Ponytail review
and `/pr` applied. No production defect verified in the tested cases, so no
production formula changes or manufactured TDD RED. Initial three new-test failures
were incorrect status/field assertions, corrected to existing public response names;
they are not evidence of a product defect.

#### Trace and exact formulas

1. `loader._pulse_record`: units→price, bid_count→integer machines, route_length→km;
   empty/null/NaN/unparseable values become None. Nonpositive metrics are not valid.
2. `ClusteringRepository.aggregate`: one indexed slice per canonical selected origin;
   common region/period/price/body/tonnage filters in `aggregate_clustering_records`.
   The destination-FIAS accumulator pools source rows before coordinates/graph.
   Selection order/duplicate FIAS never duplicate rows; distinct source observations stay.
3. `_Accumulator.add`: only positive machine counts contribute to total machines T.
   For metric m let V_m be selected rows with positive machines and a valid metric:
   N_m = Σ(m_i × machines_i); D_m = Σ(machines_i for i in V_m).
   Mean=N_m/D_m if D_m>0, otherwise None. Route valid iff length>0;
   price valid iff price>0; rate valid iff price>0 AND length>0, rate=price/length.
   Thus route, price and rate have independent numerators/denominators. Price/rate
   mean is not divided by T; rate mean is not mean price / mean route.
4. `locations_from_routes` preserves each mean and valid machine denominator.
   Product point JSON exposes these same values. Full SpatialGraph precedes eligibility.
5. `_cluster_table`: for saved members j, numerator=Σ(point_mean_j × D_m,j),
   denominator=Σ D_m,j. This reconstructs the raw valid-row mean, rather than
   weighting point route means by all machines. Price/rate min/median/max use the
   available destination-point means WITHOUT weights; even median averages middle two.
6. Coverage per metric: valid_points/total_points and D_m/T, independently. Backend
   returns integer counts; percentages below are their analytical ratios, not new
   backend fields. Zero total gives unavailable percentage. Existing frontend formats
   economic coverage to one decimal percent and missing means as —; it does not add
   a new route coverage column. Route/union UI and workbook consumers remain downstream.

Five modes retain existing semantics: Geography uses full graph/geography only;
Geo+Volume uses full graph and log1p volume; Geo+Cost uses economics-valid induced
graph; Bear Cost uses positive-volume valid-rate induced graph; Bear Volume uses
positive-volume induced graph. Regional/cluster/Bear economics retain their existing
point-trip-weighted paths (not replaced with table metric denominators). Bear tables
remain unsupported, thresholds/no_bears behavior unchanged. RESEARCH/LEGACY untouched.

#### Hand calculations and actual HTTP results

Safe synthetic CSV, origins A/B and unselected C, four coordinate-resolved destinations.
Baseline X rows: A10×100km/price1000; B30×300km/price6000; B20 missing both metrics.
W5×100/price1000, Y5×200/missing price, Z5×100/price1000.
No confidential source rows. Real adapters; Flask test-client public API responses.

| Input/action | Analytical expected | Actual result |
|---|---|---|
| Scalar A vs singleton A, X | route100, D10/T10; price1000, rate10 | identical complete HTTP responses; exact values |
| Scalar B vs singleton B, X | route9000/30=300, D30/T50=60%; price6000, rate20 | identical complete HTTP responses; exact values |
| Explicit A+B, B+A, duplicate origins, X | route(1000+9000)/40=250; D40/T60=66.6667%; one X | exact250/40/60, 4 distinct destination points, complete canonical response parity |
| Baseline X price/rate | price190000/40=4750; rate700/40=17.5 | exact4750 and17.5; denominators40 |
| Add price2000 to B20 missing-route row | route250/D40; price230000/60=3833.333333; rate17.5/D40 | matched in Geography, Geo+Cost, Geo+Volume |
| W+X cluster with that price-only row | route10500/45=233.333333; price235000/65=3615.384615; rate750/45=16.666667 | HTTP table matches; route/rate45/65=69.2308%, price65/65=100%; valid points2/2 |
| W+X distributions with price-only row | price min1000, median2416.666667, max3833.333333; rate min10, median13.75, max17.5 | matched; medians are point distributions, not raw rows or weighted medians |
| Baseline Y+Z | route(1000+500)/10=150; route10/10=100%, price/rate5/10=50%; available price1000/rate10 | matched; price-missing Y contributes its route |
| All lengths empty/0/negative/unparseable/NaN, or all weights empty/0/negative/unparseable | route None, D0; no zero mean/divide by zero | all4 HTTP points and table rows None/valid0; rate also None |
| Tent20, current | X10000/40=250, T60; W+X10500/45=233.333333, T65 | matched |
| Tent20, current+forecast (+B10×400) | X14000/50=280, T70; W+X14500/55=263.636364, T75 | matched; contains_forecast true; frozen table periods current/forecast |
| Tent20, current+retro, spot+tender (+A5×500) | X12500/45=277.777778, T65; W+X13000/50=260, T70 | matched; contains_forecast false |
| Current, include van10 (+A100×900) | X100000/140=714.285714, T160; W+X100500/145=693.103448, T165 | matched; filtering changes numerator and denominator together |

The wrong total-machine-weighted W+X route would be (250×60+100×5)/65=
238.461538, distinguishable from actual233.333333. Unequal origins are not equally
weighted (that would give200 at X). Missing lengths never add a zero contribution.

#### Acceptance coverage

| ID | Action/expected and evidence | Actual/status and limits |
|---|---|---|
| R3-01 | baseline A+B, analytical250; `test_union_is_canonical_and_pools_raw_valid_weights`, `test_scalar_and_union_route_constants` | PASS backend; multi-origin rendered UI/workbook UNVERIFIED NPI-04/10/11/12 |
| R3-02 | B20 missing:250,40/60; same tests + independent-denominator test | PASS backend counts (66.6667% analytical); downstream display/export UNVERIFIED |
| R3-03 | nine invalid route/weight cases; `test_union_unavailable_route_is_null_with_zero_valid_weight` + existing zero-weight table test | PASS backend None/D0; current missing-value Node/Edge regressions PASS; future workbook blank UNVERIFIED |
| R3-04 | W+X/Y+Z analytical raw valid means; `test_union_cluster_table_reconstructs_metric_valid_weights`, new denominator/period tests | PASS backend actual saved membership and table, no formula rewrite |
| R3-06 | price-only X and route-only Y; new three-mode independent-denominator regression; current table tooltip/methodology/formatting frontend regressions | PASS current backend/contracts; existing route cells show km, tooltip identifies valid machines/exclusion/—; new consumers UNVERIFIED |
| R3-07 | scalar/singleton exact complete response parity, A/B constants; existing `test_run_exposes_hand_calculated_cluster_table_from_cached_assignments` (table test) and point-distribution checks | PASS API and current table regressions; fresh human walkthrough not claimed |
| R3-08 | four combined-period/segment cases; `test_union_periods_and_segments_change_route_numerator_and_denominator`; current frontend saved-period/Прогноз Pulse label checks | PASS backend and current automated rendering; future union UI/workbook UNVERIFIED |

Backend prerequisite exit is verified. Full integrated acceptance is NOT claimed;
NPI-12 owns closure with NPI-04/07/10/11 evidence. No reverse dependency introduced.
Source capacity/SLA and real-data quality prevalence remain UNKNOWN/UNVERIFIED.

#### Files and local verification

- `tests/test_origin_union_api.py`: 16 new deterministic HTTP regression cases using
  existing fixture/helper and actual adapters, hand constants; no dependency/config/export edits.
- This exact existing approved Ticket06 card: published with trace/acceptance/gate evidence.
  Approved criteria wording and original planning comment preserved; status updated.
- Production formulas, callers, fixtures outside this test, UI, modes and contract docs unchanged.

Windows, Python3.12.14, pytest8.3.5, Ruff0.9.10, Node22.23.3, real Edge.
Python executable: repository `.codex-impl-env/Scripts/python.exe`; cwd isolated worktree.

- `python -m pip install -r requirements-lock.txt`: exact pins satisfied.
  `python -m pip check`: no broken requirements.
- `python -m pytest tests/test_origin_union_api.py tests/test_product_cluster_table.py tests/ml/test_clustering_dataset.py tests/ml/test_locations.py tests/ml/test_pulse_semantics.py tests/test_business_product_modes.py tests/test_bear_product_modes.py -ra -p no:cacheprovider --basetemp=.scratch/npi06-focused2`: **137 PASS**.
- `python -m pytest tests/test_origin_union_api.py -ra -p no:cacheprovider --basetemp=.scratch/npi06-table`: **84 PASS**, after adding combined-period cluster assertions.
- Workflow runpy Node/Edge startup assertions: PASS.
- `REQUIRE_FRONTEND_BROWSER=1 python -m pytest -ra -p no:cacheprovider --basetemp=.scratch/npi06-full --junitxml=.scratch/npi06-results.xml`: **359 PASS, zero skips**, 43 Node/Edge frontend cases,20.29s. This precedes final extra table assertions; final gates recorded below.
- XML assert:359 testcases, zero skipped,43 frontend cases.
- `python -m ruff check .`, `node --check` for all12 frontend JS files,
  `git diff --check`: PASS. No optional framework or source data committed.

Independent Standards/Spec/Ponytail findings, final candidate and PR/CI links follow
after execution. No merge authorized or performed. Ticket03/04/XLSX excluded.

Final local gates after combined-period cluster assertions: **359 PASS in22.75s,
zero skips,43 frontend cases** with `REQUIRE_FRONTEND_BROWSER=1`, same command using
`--basetemp=.scratch/npi06-final --junitxml=.scratch/npi06-final-results.xml`.
XML count/skip assertions passed. Ruff over every tracked Python file passed;
`ruff check .` also passed (host warning for generated restricted pytest-temp directory,
no tracked source omitted). All12 JS syntax checks and full baseline diff check PASS.

Independent reviews at code commit `9a78c998db58389f1cf4824c52377206cebb3f1d`:
- Standards: **0 hard violations/blockers**. One optional duplicated CSV setup
  observation; retained explicit setup at two uses, avoiding an unnecessary helper.
- Spec: **PASS,0 findings**. Independently ran union/table suites:94 PASS.
- Ponytail: **Ship,0 findings**. Independently ran union/table suites:94 PASS;
  connected normalization/filter/accumulator/location/table/five-mode paths checked.
Review limitations: no fresh human whole-scenario walkthrough, workbook, live confidential
data or production capacity check. Scope and downstream UNVERIFIED branches unchanged.

Published [PR #9](https://github.com/a-man-or-a-person/AI_logistics/pull/9),
base main `5923cd90`, branch `test/npi06-weighted-verification`.
The final documentation commit adds only this gate/review record. Required GitHub Actions
`verification` must succeed on its exact HEAD; the authoritative final status/run is
available in [PR checks](https://github.com/a-man-or-a-person/AI_logistics/pull/9/checks)
and the completion report. A previous-HEAD green is insufficient. No automatic merge.
