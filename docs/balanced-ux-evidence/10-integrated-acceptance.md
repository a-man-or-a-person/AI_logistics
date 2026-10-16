# 10 — Integrated Balanced UX acceptance

Accountable implementer and IA01–04 owner: `/root`. RELEASE/HIGH risk.
Base/main: `4d21b54259c1a34a9d098a34aa518f447b411b65`.
Parent: `99abaddce51164e07af691a4b53ec315fd3d2212` (09, Quality66 SUCCESS).
This report concerns the isolated `feature/balanced-ux-redesign` checkout and
[Draft PR22](https://github.com/a-man-or-a-person/AI_logistics/pull/22).
The exact committed head and its hosted Quality result belong in the timestamped
PR supplement. Main merge, Ready promotion and cleanup are not authorized.

## Integration changes

Actual first Compare → cached mode → Show on map left the startup prompt over a
calculated map. Its regression returned `saved=true, hidden=false, visible=true`
on the parent; ordinary first Run already passed. `renderEmptyState` now hides
the startup prompt whenever a saved result exists, retaining the empty/error
branches. Both entry paths pass the original strict assertion after the fix.

Changing a draft method also hid the candidate-layer control for a saved Bear
map, or exposed it for a saved ordinary map. Three genuine failing cases cover
Geography, Bear Cost and Bear Volume. The layer control now follows the saved
map's mode; method parameter boxes continue to follow the draft. No request,
saved object, candidate population, metric or algorithm changes on draft edit.

Production changes are confined to these two shared presentation functions.
Five regression cases were added to the existing comparison/parameters tests.
Backend, ML, catalog, dependencies, Quality and workbook writer are unchanged.
An initial candidate-test selector syntax error is retained as setup failure,
separately from the genuine three-case RED run. The earlier expanded-methodology
mouse-target failure was resolved by closing the read disclosure before selecting
a table row; no hidden element was clicked and no production workaround added.

## Acceptance and preservation

The [294-record ledger](10-information-preservation.json) distinguishes raw
source/API arithmetic, actual downloaded disk cells, controlled renderer
fixtures, historical unchanged-source native evidence and final native routes.
It is not a claim of 294 fresh native sessions or human observations. Every ID
retains its source, access, method/population, expected/observed state and exact
evidence reference. Count equality alone does not establish preservation.

| Criteria | Scope and concrete evidence |
| --- | --- |
| DS01–03 | [Foundation](01-foundation.md): essential text, both themes, precision, contrast and keyboard help; typography/CSS unchanged by10. |
| WL01–03 | [Workspace](02-workspace.md): six desktop/zoom cases, native125%, drawer/dialog/scroll/focus; final routes use actual outer and table scrolling. |
| PM01–03 | [Parameters](03-parameters.md): single/union/All, catalog/defaults/presets; final All expands A/B/C including zero-match C and restores A/B. |
| EC01–03 | [Compatibility](04-economic-compatibility.md): independent denominators and canonical/compatible distinction; new15-context raw-source oracle below. |
| SR01–03 | [Saved summary](05-frozen-summary.md): frozen filters/counts/coverage, missing/zero and diagnostics; final draft-edit routes preserve saved identity. |
| MT01–03 | [Map/table](06-map-and-table.md):14 raw columns, sort/ties/nulls/help/layers;20 conditional field probes and saved-candidate control regression. |
| IN01–04 | [Inspector](07-contextual-inspector.md): exact members, own origin weights and lazy source rows; final point has64 pooled/A62/B2 rows, A50+12 pagination and return. |
| CX01–04 | [Compare/export](08-comparison-and-export.md): fixed five modes and frozen full workbook; actual final normal/adversarial/paired downloads reopened independently. |
| ST01–05 | [Recovery/accessibility](09-recovery-and-accessibility.md): cache/revision/cancel/retry/late responses, Data Map and record dialog; final typed failure/eviction/cancellation routes and unchanged lifecycle regressions. |
| IA01–04 | This report,294 per-ID records, independent integration review, final mandatory gates, served assets and baseline-first paired technical observations. Human gate remains separate. |

The35 criteria and294 obligations are technically reconciled only after the
final review/gates recorded below and exact-head hosted SUCCESS. Historical
01–09 evidence retains its original revision/scope; only two presentation paths
changed during10. Rare state fixtures are explicitly controlled: current plus
forecast, table empty/error, graph counts3/2/1/0, escaped origin/row warnings,
own economic coverage2/5 points and20/110 machines, raw cluster0 versus null,
missing coordinates, exact medoid, five OpenLayers visibility flags and LEGACY
disclosure/legends. These are rendered/public-function checks, not invented
observations from the ordinary89-row HTTP fixture.

## Independent numbers and actual workbooks

The independent raw CSV/HTTP oracle executes five modes × single A, union A/B
and All:15 contexts,22,111 assertions and147 directly checked field IDs. It checks
membership/source IDs, origin weights/pages, canonical distributions/means,
compatibility means, baselines/deltas/MAD/spread/Bear populations and independent
projected distances/P95/Geography validation formulas. Cluster membership follows
the actual saved algorithm outputs; clustering is not independently reimplemented.
Separate LEGACY replay checks47 aggregates and526 record values.

An additional exact value-pipeline oracle checks5,114 scalar/formatted outputs
across all147 numeric IDs using the production inspector/comparison/table,
LEGACY popup and record-cell functions fed actual saved HTTP/detail scalars.
Exact label/cell/ARIA extraction checks field mapping rather than global text
counts. This is controlled Node/function execution with a minimal DOM sink,
not Edge visibility or native input. Native access and controlled Edge visibility
are separately evidenced; API arithmetic alone is not called a UI-value check.

Actual Edge downloads, independently reopened as ZIP/XML against raw source:

| File/fixture | Bytes / SHA256 | Observed complete output |
| --- | --- | --- |
| Normal GeoCost/All |17381 / `7e0a9f7cbeb6dccc8da23aa0d535d08ee588553e8a42dbe373e5da0ac851769a`|86 unique source rows,570 machines,12 destinations,14 columns; saved price-weighted ASC despite child/first50/collapsed table/draft GeoVolume.|
| Adversarial |19380 / `a5c991ac576114db61b5c4a3a032cdb337a7be58f8e99dc57abd6f87326e49ea`|88 unique assigned rows; leading zeros, literal formula-like strings, numeric zero versus blank rate, timestamps and legal unique collision-safe sheet names.|
| Paired T08, each variant |Exact paths/hashes in retained paired oracle|86 own-generation IDs each;570 machines,12 destinations,14 table values; machine DESC250/160/160, full row order/context/membership.|

Normal plus adversarial disk ledger contains2,999 assertions across30 output IDs;
six workflow IDs rely on separate error/cancel/retry/eligibility evidence, not
successful files. Disk completeness does not by itself prove failure atomicity.
The existing complete-or-fail writer and generation-conflict regressions remain
mandatory. Both final books were captured through unchanged output code; later
presentation fixes receive separate fresh native evidence.

Paired raw ID sets intentionally differ: baseline snapshot `67240dfce6f6…`,
final snapshot `de15634942e7…`. Source restoration preserved bytes but changed its
generation fingerprint. Two independent CSV oracles compute each ID from its own
snapshot plus source record ordinal; both86-ID sets match exactly. Logical source
rows, values and membership match across generations. No equal-raw-ID claim is made.

## Baseline-first technical comparison

AS-IS is a read-only15-file frontend extraction of base4d21, served by actual
unchanged Flask on5087; TO-BE uses5086. All30 frontend byte comparisons pass.
AS-IS finished `2026-10-15T12:51:01.538Z`; its frozen14-record trace SHA256 is
`15f50b5dcb55dd7cd3e4fadfb4b8452bcf2be9493e9fd4783a306a77753bdc2f`.
Technical targets were declared at `12:52:57.752691Z`, before TO-BE, artifact
`10-before-to-be-targets.json`, SHA256
`cc7e6cd1b37ca4a4f4a094e408b169ddd887d4b5290c85d4ab860dfe362bd92d`.
Targets require exact context/value preservation and zero wrong-context output;
no human time/comprehension thresholds were invented or adopted.

AS-IS has14 task/subcase observations plus exact-largest-K4/expanded-All supplements.
Final fixed TO-BE has20 native routes with no helper/assertion failures; its trace
SHA256 is `6b6d19656015da520974820a5af8dbd6994874b8c812f6d589c6661165eb8f6b`.
Native mouse, keyboard and wheel actions, elapsed and client-observed HTTP wait
are recorded separately. Access-only driver adaptations use the new primary
table rather than the intentionally hidden old cluster list, and route scrolling
through the visible outer ancestor before the local table. Earlier failed helper
attempts remain retained and are not product defects or successful measurements.

Actual automated run count is one settled run per variant, plus named technical
supplements; human sessions **n=0**. Driver elapsed includes polling/automation,
and HTTP wait includes transport; neither is human task time or isolated server
CPU. There are no human assistance/comprehension scores or superiority claims.

Actual settled automated measurements (milliseconds; C/K/W = clicks/key/wheel actions).
These are assisted engineering routes, not unassisted human completion. Concurrent
verification and differing cache/generation conditions preclude performance conclusions.

| Task | AS-IS elapsed / C-K-W | TO-BE elapsed / C-K-W | HTTP wait AS-IS / TO-BE |
| --- | --- | --- | --- |
|T01|5341 / 6-4-6|4452 / 6-4-1|327 / 742|
|T02|1243 / 4-0-0|1474 / 4-0-1|0 / 0|
|T03|7339 / 10-5-7|6936 / 10-5-4|148 / 535|
|T04|7256 / 9-6-7|6168 / 9-6-3|332 / 159|
|T05|4636 / 5-3-7|2900 / 5-3-0|340 / 358|
|T06|12557 / 17-5-20|11711 / 17-5-18|631 / 187|
|T07|3346 / 7-2-0|3800 / 7-2-2|463 / 370|
|T08|3338 / 4-0-5|3961 / 4-0-8|449 / 390|
|T09|3247 / 4-0-4|2898 / 5-0-2|360 / 316|
|T10a|8455 / 12-5-10|6952 / 12-5-5|228 / 201|
|T10b|8613 / 11-5-9|7715 / 11-5-6|354 / 208|
|T10c|9350 / 12-5-9|8086 / 12-5-6|417 / 295|
|T10d|7161 / 10-5-5|7095 / 11-5-4|206 / 118|

Protocol qualifications: Auto initially gives3 clusters; a manualK4 supplement
selects the actual largest ID1/80 machines and returns. Catalog3 cannot establish
the >30 suggestion-overflow task (separate03 fixture covers108 origins). B has2
rows; equivalent A has62 and exercises50+12 pages. T03 human interpretation
remains UNVERIFIED; the exact missing/zero pair is checked separately through
numerical/conditional evidence. Draft
retro preserves current display/export; explicit retro Run returns real
INSUFFICIENT_POINTS on this fixture, so successful new-retro analysis is not
claimed. T10b injects a clearly labeled typed409 response; actual source/coordinate
generation proofs remain separately attributed to unchanged earlier native/test
evidence. T10c evicts the actual process cache and recovers through fresh Run.

Actual1440×900 light screenshots: [AS-IS](10-before-1440.png) and
[TO-BE](10-after-1440.png). They show the captured task states, including transient
external basemap tile loading; they are not retouched usability verdicts.

## Gates, review and delivery

Independent `/root/foundation_spec` owns the fresh20-route native replay, paired
book reopen and own-generation source-ID reconciliation. Independent
`/root/economics_standards` (Standards plus targeted Ponytail) reproduced both
integration defects, verified five strict GREEN regressions and independently
replayed all5,114 numeric value-pipeline observations. Separate
`/root/economics_spec` checks raw source/API/disk arithmetic and provenance.
The294-ledger content/source/value review passes; no BLOCKER/MAJOR remains.
Final publication allowlist, privacy, links, manifest and normalized byte mapping
are checked before commit. Exact-head hosted CI necessarily follows this commit;
its result and completed committed-byte verification belong in the timestamped
PR supplement, not a self-referential successful-CI claim inside the same commit.

Local mandatory full rerun on the final two-function/five-test candidate:
locked install, pip check,152 Python files/Ruff and Node/Edge startup PASS;
frontend136 PASS409.99s and Python633 PASS550.83s. Both nonempty JUnit reports
have zero errors, failures or skips; all five new regressions pass.
The earlier pre-fix full136/628 run passed but does not substitute for final gates.
One neighboring focused test hit Edge's unchanged20-second execution deadline
without a functional result; that exact case passes in the final full replay.
No test timeout/assertion was relaxed and no mandatory skip is accepted.

Runtime checkout is
`C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`, branch
`feature/balanced-ux-redesign`; original `.venv/Scripts/python.exe` launcher,
Python3.12.14/Node22.23.3/Edge155.0.4283.45. Current Flask5086 PID13960 starts
`.scratch/09_audit_server_retained.py.txt` through documented `run.main`; AS-IS5087
PID13736 starts the retained baseline wrapper. Both preserve approved synthetic
CSV/coordinates. Post-commit served HEAD/assets are recorded in the PR supplement.

Bulky drivers, all attempts/logs/AX traces/workbooks/JUnit and profiles remain in
the local `.scratch/balanced-foundation` archive and task-prefixed `.scratch`
files; a SHA256 manifest is recorded at final publication. No cleanup or profile
publication is authorized. Git contains compact summaries,294 trace records,
two safe screenshots, source/tests and CURRENT documentation only.

Local archive checkpoint `.scratch/balanced-foundation/10-runtime-manifest.json`
contains279 artifacts, SHA256
`f8025af155f09f013ff92c8268c95b30a98d73a931e59d696d78e046e15f1164`.
Profiles, the append-only server log, publication maps and the manifest itself
are explicitly excluded; all remain preserved. Later CI/review supplements do
not retroactively change this checkpoint.

Durable regression reproduction uses `REQUIRE_FRONTEND_BROWSER=1` and the
original Python launcher from this worktree: run
`pytest tests/test_dashboard_comparison.py -k first_saved_result_removes_the_initial_map_prompt`
and `pytest tests/test_dashboard_parameters.py -k candidate_layer_control_follows_saved_map`.
The full unchanged Quality commands run the frontend contract separately and
`pytest --ignore=tests/test_clustering_frontend_contract.py -ra`, with unique
basetemp directories. Local replay scripts and their input/observed artifacts
are pinned in the checkpoint; the ledger retains compact expected/observed values.

| Readiness | Verdict and boundary |
| --- | --- |
| IMPLEMENTED |PASS:01–10 implementation and per-criterion evidence present.|
| VERIFIED |Local gates/reviews PASS; exact-head hosted verdict and committed-byte mapping in the PR supplement.|
| READY TO MERGE |UNVERIFIED: PR stays Draft; required approvals/protection not established (protection API403).|
| MERGED & INTEGRATED |NOT MERGED; no main acceptance is claimed or authorized.|
| FUNCTIONALLY ACCEPTED |PASS for the reviewed feature candidate and qualified scenario matrix above; merged-main acceptance is not claimed.|
| HUMAN ACCEPTED |UNVERIFIED, n=0; named logistics user must accept exact revision/UI/workbooks.|
| PRODUCTION READY |UNVERIFIED; intended workload, latency/concurrency/memory, routing/retention/security/operations and human acceptance remain separate.|

Before any later authorized merge: confirm final-head CI/reviews and required
approvals/protection, complete named human walkthrough of parameters→result→14
columns→trace/pages→up→five-mode comparison→draft/frozen export→retry/cancel and
verify assistive-reader speech/announcements and open both workbook layouts in
the intended application. Existing long XLSX
headers may clip despite complete values/types. Merge/main smoke, main CI and
cleanup require their own later authorization; no automatic promotion follows CI.
