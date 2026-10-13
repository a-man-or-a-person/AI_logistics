# 04 — economic compatibility guard

Date: 2026-10-13. Accountable implementer and EC-01/02/03 criterion owner: `/root`; preparation contributor: `/root/economic_guard`. Risk: HIGH (business metrics); independent Spec, Standards and targeted Ponytail scope reviews passed; final-head CI remains a gate. This is local source/API evidence, not ticket DONE/VERIFIED, hosted CI, human acceptance or production readiness.

## Scope and identity

Checkout: `C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`; remote `https://github.com/a-man-or-a-person/AI_logistics.git`; branch `feature/balanced-ux-redesign`; base/preparation HEAD `4d21b54259c1a34a9d098a34aa518f447b411b65`; integration parent `1c180f35486d3fe87e59fd0e12c343c49f3431a8`. Concurrent frontend edits were preserved. Owned additions only: this report and [numerical guard](../../tests/test_dashboard_economic_compatibility.py). No backend/config/fixture/CURRENT documentation edits or private source mutation. Publication adds only this report and the numerical guard; final commit/CI are recorded in the PR supplement.

Read ownership: local `.scratch/dashboard-redesign/issues/04-economic-compatibility.md`, local `.scratch/dashboard-redesign/economic-compatibility.md`, spec and D-02/03/04; CONTEXT, architecture current-state, Product contract/workflow and Agent Workflow v2. Inspected callers: dataset aggregation → location metrics → Product adapters/algorithms → service point/cluster/table serializers → run/compare/point-origins/point-rows/export; frontend inspector/table/comparison; XLSX writer. Catalog owns mode support/defaults; existing test-local synthetic Pulse/coordinate fixtures suffice. RESEARCH/LEGACY formulas are unaffected.

`git diff --exit-code 4d21b54259c1a34a9d098a34aa518f447b411b65 -- backend ml` returned 0 with empty output. Both complete tracked production trees are therefore unchanged: backend tree `4a5b8c72ef9d1ccbc4d1c731359482f87910e631`, ml tree `ead9c5dca3594d8c1d76d19767a89f3096a7d4cc`.

| Source | Git blob (base = inspected working source) |
| --- | --- |
| backend/services/clustering_service.py | `43e72d36837b873144cee7e4bff46a06cf363843` |
| ml/data/clustering_dataset.py | `52f9f29d59c2e58cee973026f3982a57fb5a6531` |
| ml/clustering/economics.py | `21e3b79d493a0f700c00c0344b6e2a92169b821a` |
| backend/services/xlsx_export.py | `c50ff771edad19463e14bf22eb6429e3aa2992a3` |
| backend/clustering_api.py | `393d0166d4f4926f8aa8a7c2aa9c4b0edf68792e` |

## EC-01 — independent constants, expected = observed

Constants are derived from synthetic rows, independent of formatter/API output. The new test exercises the existing service serializer with the existing fixed-membership clusterer; neighboring tests exercise actual Flask endpoints and algorithms.

| Input | Canonical price / route / rate | Metric-valid machines (price / route / rate); total |
| --- | --- | --- |
| A: 10 machines at100/10 +90 missing; B:10 at300/10 | 200 /10 /20 | 20 /20 /20;110 |
| (100,10,1), (300,30,3) | 250 /25 /10 | 4 /4 /4;4 |
| (100,10,1), (300,20,1) | 200 /15 /12.5 | 2 /2 /2;2 |
| (100,10,1), (300,missing,3) | 250 /10 /10 | 4 /1 /1;4 |
| missing/bad metrics with positive2+3 machines | null /null /null | 0 /0 /0;5 |
| zero/negative metrics with positive2+3 machines | null /null /null | 0 /0 /0;5 |
| valid metrics with zero/negative/bad weights | null /null /null | 0 /0 /0;0 (share null) |

First case: A has100 machines and B10. Canonical price numerator100×10+300×10=4000 and denominator20; rate numerator10×10+30×10=400 and denominator20. Legacy means remain (100×100+300×10)/110=`118.18181818181819` and (10×100+30×10)/110=`11.818181818181818`. Route10; min/median/max price100/200/300, rate10/20/30. All three coverage objects and economic coverage contain2/2 points and20/110 machines. Two distinct populations are preserved. Unequal-route case rate12.5 is distinct from aggregate ratio200/15=`13.333333333333334`.

Existing independent neighbor oracles passed: `test_product_cluster_table` even destination median, missing-price-with-valid-route, metric weights and exact membership; `tests/ml/test_clustering_dataset.py` positive/missing/invalid raw weights and row-level numerators; `test_origin_union_api` pooled x route10000/40=250, price190000/40=4750, rate700/40=17.5 despite60 total machines; `test_regional_all_api` complete regional resolution before common filters and frozen All intent. Export tests independently reopen HTTP XLSX bytes using ZIP/XML, reconcile source IDs (6 unique assigned rows,75 machines in base union fixture), coverage, all14 columns, types, precision, exclusions, current sort and complete-or-fail output. Browser file-download realization belongs08.

## EC-02/03 — preserved seams and downstream lookup

All five modes were exercised by the focused tests against unchanged baseline production bytes. Geography/Geo+Cost/Geo+Volume retain public keys/values, exact eligible/assigned membership and existing canonical methodology (`product_cluster_table_v1`, `unweighted_destination_points`, `metric_valid_trip_count`). Geo+Cost keeps economic eligibility and induced full spatial graph; Geo+Volume keeps positive-volume semantics. Bear Cost/Bear Volume preserve threshold presets, candidate/zones/singletons, baselines/deltas, no_bears and typed errors; both retain `cluster_table={supported:false}` and unsupported XLSX. Source identity covers full serializers and algorithm implementations, not merely selected assertions. This is a baseline source-equivalence proof plus behavioral regression replay; no separate copied baseline executable or external-consumer audit was run.

Diagnostics retain distinct formulas/populations: regional rate and legacy cluster means use available destination metric values weighted by total destination machines; rate delta=value/baseline−1; rate MAD weights absolute deviations with its own existing center/population; volume baseline is arithmetic machines-per-eligible-point, volume delta compares that baseline, and spreads compare cluster summaries. No diagnostic is relabeled as canonical table mean or recomputed in the browser. Bear eligible sets and RESEARCH/LEGACY remain separate.

Frozen lookup contract for07: in the current saved result only, join `cluster_table.rows` to selected cluster by raw `cluster_id` (identity0 is valid; presentation number=id+1). Read route=`weighted_route_length`, price=`price.weighted`, rate=`rub_per_km.weighted`, metric coverage=`coverage.*` and economic coverage=`economic_coverage`. Match identity rather than sorted array index. Missing/unsupported row or null value means unavailable with explanation; never fall back to `clusters[].weighted_*`, another result, draft request or browser Pulse aggregation. Legacy cluster values remain accessible under their own total-volume-weight label; each regional/diagnostic field keeps its own name. Old saved results without canonical rows degrade explicitly. This report specifies the contract;07 owns implemented DOM/browser proof.

No required backend/API extension: all primary means and per-metric numerator population/coverage are already represented by frozen row values and valid/total point/machine counts. `/run`, `/compare`, `/point-origins`, `/point-rows`, `/export`, frozen request/selection intent/snapshot and source identity stay intact. No invented fields, store, cache version or serializer rewrite. Unknown external callers remain UNKNOWN; unchanged interfaces minimize change risk without proving their audit.

## Reproduction and limits

Python `C:/folder/Python/AI_logistics_clean/.venv/Scripts/python.exe` 3.12.14; existing parent locked environment. Run from checkout:

```powershell
C:\folder\Python\AI_logistics_clean\.venv\Scripts\python.exe -m pytest tests/test_dashboard_economic_compatibility.py tests/test_product_cluster_table.py tests/test_bear_product_modes.py tests/test_business_product_modes.py tests/test_point_origins_api.py tests/test_origin_union_api.py tests/test_regional_all_api.py tests/test_xlsx_export_api.py tests/ml/test_clustering_dataset.py -q -o addopts='' -p no:cacheprovider -k 'not unchanged_recalculation' --basetemp=.scratch/ec04-pytest-20261013-b
```

Observed: **267 passed, 1 deselected in9.77s**, exit0. The one deselected existing live Flask→Node snapshot/cache recovery test (`test_unchanged_recalculation_recovers_after_real_snapshot_conflict`) belongs parent full gates; this focused run does not claim zero skipped mandatory final gates. First identical focused run passed but emitted two Windows pytest-cache write warnings; cache-disabled rerun above passed cleanly with fresh task-owned basetemp. Ruff on new test: all checks passed. No artificial RED: backend conforms already; added constants are a preservation guard. UI loading/cache/stale/cancel/retry/focus transitions N/A to this guard's production change (none), and remain mandatory in downstream UI slices/full gates. Downloaded disk workbook belongs08. Final-head hosted Quality, full UI preservation, human and production gates remain UNVERIFIED here; independent source/API reviews are recorded below.

## Independent review and integration evidence

Guard SHA256: `5acad4542ef4feaca7f07d13c2e3f5de915bd3a226198b66f8edb310115a0af9`.
Independent Spec `/root/economics_spec`: source, constant arithmetic and frozen-row
lookup contract PASS; independently replayed267 focused cases plus15 neighbors.
Independent Standards and targeted Ponytail `/root/economics_standards`: ownership,
unchanged source/API semantics, distinct denominator populations, invalid/missing
cases and scope sufficiency PASS. Independently replayed all268 focused cases,
including the real Flask-to-Node unchanged-recalculation conflict/cache case;
no deselection in that replay. No BLOCKER/MAJOR finding remains in this guard scope.

Parent final integration on unchanged guard bytes at the preparation stage:
469 Python cases and141 frontend cases PASS, zero frontend skips, locked deps,
Ruff and explicit Node/Edge startup PASS. The local Python count includes this
seven-case unpublished guard. Hosted CI before guard publication does not contain
those seven cases; guard's own final-head hosted CI remains required separately.
The full baseline backend/ml production trees still match base byte-for-byte.
Source/API compatibility evidence covers135 affected IDs; the guard owns no UI
preservation IDs. It does not assert that downstream redesigned DOM is implemented.
