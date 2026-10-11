# NPI-10 — saved Product XLSX backend

Baseline: fetched protected `origin/main` `53c003797961c31c8160b0bfc1b69ea2cfa6c15b`,
2026-10-11 Europe/Moscow. Isolated `.worktrees/npi10`, `feat/npi10-xlsx-backend`.
NPI-07/#13, Pulse Freshness/#14 and NPI-08/#15 are merged ancestors. Required
Quality runs on exact prerequisite heads succeeded:
[NPI-07](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38141437996),
[Freshness](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38146937061),
[NPI-08](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38157762448).
Existing NPI-02/06 contracts/evidence are retained through that baseline.
NPI-09 and all other worktrees/environments/configuration were not changed.

Authority read from ORIGINAL workspace: exact NPI-10 card, approved spec, coverage,
tracker, order and execution requirements; AGENTS/CONTEXT, architecture, current
Product, origin-set/weighted/summary contracts, Pulse readiness and freshness code.
Historical local blocked labels were checked against actual merged ancestry/CI.

## Exact owned acceptance matrix

Environment: isolated Windows Python3.12.14, Node22.23.3, XlsxWriter3.2.9; synthetic
Pulse only. Tests observe Flask HTTP and independently reopen generated ZIP/OOXML.
Live evidence uses real localhost Flask, an HTTP attachment and saved XLSX reopening.
No download UI or human desktop Excel acceptance is claimed.

| Owned criterion | Exact approved requirement | Action/input, expected and actual | Evidence / status / limitation |
|---|---|---|---|
| R2-02 | workbook direction sheets identify source origin region→saved cluster; no independent origin-region clustering or new run occurs. | Export saved Geography/Cost/Volume; directions join row region to exact saved membership; table values copied, no calculation called. | HTTP mode/compare tests; live download. PASS backend; UI delegated. |
| R2-03 | source fixture with60 matched rows, browser has loaded0/50: export contains all60 once, with existing normalized fields plus origin/region/destination/cluster. | Append60 distinct duplicate-value rows; export before any detail page. All60 plus6 base rows present, unique IDs66; live60 plus126=186. | full-pages test and http-download.json. PASS backend; browser button delegated. |
| R2-04 | origin with two row region labels groups each row by its actual region; catalog modal value never rewrites it; discrepancy disclosed. | Multiple actual labels on same origin; distinct groups and context conflicting_origin_regions. | reopened direction records and mappings. PASS. |
| R2-05 | null origin region appears in explicit unknown-region direction group, not dropped/guessed. | Null and real literal «Регион погрузки не определён» both included with different sheet identities; mapping retains null versus text. | literal/collision test. PASS. |
| R2-06 | assigned destination with missing-price individual row exports that row; economic-invalid unassigned destination absent; exclusion counts/reasons disclosed. | Shared X missing-price rows retained; Geo+Cost Y economic_unavailable and Z spatial_outlier omitted with point/row/machine counts. | mode reconciliation, context exclusions. PASS. |
| R2-08 | numeric1000.05 retains value with UI price format; unavailable blank and zero numeric; units/denominators/coverage documented. | Independently read1000.05/59 zero cells and null cells; styles contain numeric display formats, context metric rules/counts, coverage text Russian decimal comma. | precision/styles/coverage and reconciliation tests. PASS. |
| R2-09 | source strings beginning =,+,-,@ remain literal text with no executed formulas/links; IDs retain leading zeros/text identity. | Export all4 prefixes and URL-like text; XML inlineStr, no formula/hyperlink/externalLink/vba; IDs000123/007 retained as text. | ZIP/XML literal-cell test. PASS. |
| R2-11 | same region but unselected origin rows absent; cached comparison variant export uses only its own saved membership/mode. | Base c tender excluded by spot;5 actual comparison variants (3 exports,2 explicit unsupported); frozen identity/sort tests. | comparison/scalar and stale identity tests. PASS backend; UI edits delegated. |
| R2-13 | direction names long/invalid/colliding remain distinct/legal and full labels reconstructable from context; no silently overwritten sheet. | Long Cyrillic, invalid chars, truncation collision, null/literal collision, apostrophe at cutoff. Numeric prefixes distinguish identities; full label mapping reopened. | RED-sheet → GREEN; independent review reproduction. PASS. |
| R2-15 | union exported source-row IDs exactly equals filtered source records for saved assigned destinations; counts/weighted metrics reconcile per validity rules, no source-page cap or fabricated values. | Workbook ID union equals point-detail IDs; full count66/126/186; independently worked valid weights below; missing/partial/duplicate rows cannot succeed. | reopened workbook, detail equality, manual constants, safe-failure tests. PASS synthetic; production capacity UNVERIFIED. |

NPI-11 owns R2-01/07/10/12/14 observable UI branches; API coverage here supports them
without claiming their desktop acceptance. NPI-12 owns integrated replay/release.

## Workbook and frozen lifecycle

`POST /api/clustering/export`: complete normalized frozen request + snapshot +
allowlisted table_sort. Optional selection_intent must be backend-observed;
ambiguous All/manual cache reuse requires it. Scalar singleton, explicit unions
and resolved All sets use exact saved membership; All is never re-expanded.
Snapshot alone cannot select a result; cache eviction/restart gives RESULT_UNAVAILABLE.

Sheets: «Кластеры» first (14 existing headers, all rows, numeric/null-last/ID-tie sort),
nonempty actual row-region→saved cluster directions next, «Контекст» last.
Direction columns: source_row_id, period_id, source_timestamp, period_type, price_type,
vehicle_type, tonnage_id, price, route_length, rub_per_km, trip_count, warnings,
origin_fias/name/region, destination_fias/name, visible cluster_id.
Context maps canonical IDs to visible labels and sheet names to full labels;
records full origins/intent/zero-match/region/4filters/source/mode/normalized parameters/
snapshot, units, valid weights, coverage, exclusions and export creation time.
No invented calculation timestamp or private source metadata.

Reuse: `_frozen_point_rows`, repository `source_rows`, shared `_source_row_json`,
and existing saved backend table values. No second economic calculator, no clusters
from client. Additive point `source_row_count` checks complete source retrieval;
distinct original duplicate rows retain distinct IDs. Unassigned includes null/-1.
Source+coordinate generation is checked before read, during frozen reads and after
complete file. Source replacement in either phase discards the whole download.
Generation token remains existing metadata fingerprint, not content hash or HTTP lease.

## Independent mathematical reconciliation

Shared X: A10×100km, B30×300km, B20 missing both metrics, B20 price4500/no distance.
Machines80; distance numerator10000/valid40 =250km; price numerator280000/valid60
=4666.666666666667; rate numerator700/valid40 =17.5 ₽/км. Origin valid price weights
are10/50, route/rate10/30. Tests assert literal independently worked constants from
exported rows and cross-check existing summary, pooled point and saved table.
Geo+Cost excludes unassigned Y/Z: exported/table machines85; Geography/Volume95.
Regrouping by row region changes neither values nor source-row union.

## Serialization and structural evidence

Pinned dependency-free XlsxWriter3.2.9 in both manifests. Explicit write_string,
formula/url inference disabled, IDs/timestamps literal, timezone preserved, floats
unrounded with formats, blank missing, numeric zero. Long32768-character cells and
nonfinite numeric values fail the whole export; recognized source null markers
remain blank. Writer/resource errors produce safe EXPORT_FAILED JSON and request ID.
Workbook row/cell writer return codes checked; no arbitrary cap/truncation.
Constant-memory worksheet rows and disk-backed complete attachment limit additional
serialization memory; existing index and per-point rows remain in memory.

[Real HTTP observations](npi10-evidence/http-download.json), reproducible
[driver](npi10-evidence/http_download.py): 123 origins,4 destinations,186 unique
source rows,255 machines. Full XLSX saved locally under `.scratch/npi10-runtime/`,
then independently reopened using stdlib ZIP/XML reader. CRC, cell values/types,
sheet order and formula/macro/external-link absence inspected. Sizes/timings/hash
recorded in JSON; binary workbook is not published. Synthetic evidence only.

Engine behavior checked against primary [XlsxWriter workbook documentation](https://xlsxwriter.readthedocs.io/workbook.html)
and [worksheet limits](https://xlsxwriter.readthedocs.io/worksheet.html).

## Verification and independent reviews

Genuine RED logs: endpoint404, invalid sort500, wrong cache provenance, partial-row
success, illegal truncated apostrophe, coverage-text mismatch. GREEN export suite
and full verification logs accompany this report. Initial full suite:529 passed; final full suite after review fixes: **531 passed,
80 frontend tests,0 skipped** (178.74s). Two pytest cache-directory permission
warnings affect caching only; all checks executed. See full.txt/pytest-results.xml.

Commands use this worktree's `.venv/Scripts/python.exe`:

- `-m pytest tests/test_xlsx_export_api.py --basetemp=.tmp-npi10-greenreview -ra`
- `REQUIRE_FRONTEND_BROWSER=1 -m pytest --basetemp=.tmp-npi10-full-final --junitxml=docs/npi10-evidence/pytest-results.xml -ra`
- `-m pip install -r requirements-lock.txt`, `-m pip check`
- `-m ruff check` on every `git ls-files -- *.py` plus the new HTTP evidence driver
  (all tracked Python source; local runtime artifacts excluded)
- Mandatory existing Node/Edge startup; every frontend JS `node --check`; `git diff --check`
- `docs/npi10-evidence/http_download.py` against real localhost Flask.

[Standards](npi10-evidence/standards-review.md): no blocking findings, both observations
addressed. [Spec](npi10-evidence/spec-review.md):2 P2 findings resolved/re-reviewed.
[Ponytail](npi10-evidence/ponytail-review.md): naming fix validated, final Ship verdict.
Reviewed final code `426729ca66a82b69a165aa1ce8704408f1dac24f`.

## Publication and limitations

One focused PR against main; no merge, NPI-11 or NPI-12 work started. Publication/CI
links and exact final HEAD are recorded in the final response after actual execution.

Production regional-All capacity/SLA remains UNKNOWN/UNVERIFIED; existing repository
access scans the regional source slice for each destination. No capacity promise.
In-memory result lifetime/multiworker behavior and metadata-fingerprint limitations
are unchanged. Source update after final check does not alter already-frozen workbook
bytes but is not covered by a streaming-generation lease. Human desktop Excel and
frontend download interaction remain unverified at this API-only stage.
