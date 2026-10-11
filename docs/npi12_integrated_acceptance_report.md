# NPI-12 — final integrated Product acceptance

Executed 2026-10-12, Europe/Moscow. Product source under acceptance:
`596d9fb4276db04c72c569b922c63e74d500035d`. Isolated branch
`test/npi12-integrated-acceptance`, worktree `.worktrees/npi12`.

**PRODUCT FUNCTIONAL ACCEPTANCE: PASS for the executed automated synthetic acceptance.**
**PRODUCT PRODUCTION READINESS: UNVERIFIED.** Human acceptance is **UNVERIFIED**.
**NPI-12 READY TO MERGE:** conditional on the acceptance PR's required verification
passing on its exact final HEAD. The final disposition, SHA, CI/job links and resolved
G-02 count are recorded in the PR/publication supplement, after execution.
No automatic merge or production release is authorized.

This report does not equate automated desktop interaction with human acceptance.
Production-capacity gates I-10/G-08 remain UNVERIFIED; the explicit release exception
is that this evidence/documentation PR can be reviewed independently of a production
release decision. No numerical SLA, arbitrary cap or truncation was introduced.

## Baseline and authority

Fetched protected `origin/main`; expected and actual SHA match exactly.
[Combined-main push Quality](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38179023381)
completed **success** on that SHA, rather than only on an individual PR branch.
[Baseline CI](npi12-evidence/main-ci.json) and
[main protection](npi12-evidence/main-branch.json) retain the read-only observation.
Merge ancestry independently confirms NPI-01 through NPI-11, P1, P2, Pulse Freshness
PR#14 and PR#18. [Merge inventory](npi12-evidence/baseline.txt).

Original workspace `.scratch/next-product-iteration/` issue12, approved specification,
coverage, tracker, order and execution requirements were read. The card owns I-02,
I-10 and G-01…08; release acceptance replays all78 criteria and43 stories. Historical
tracker blocked/proposed labels were preserved and reconciled with actual merged
ancestry, rather than silently rewritten. [Authority hashes](npi12-evidence/authority.json).
AGENTS/CONTEXT, architecture, Product/data/workflow contracts, current test/CI seams,
available NPI implementation reports and Pulse Freshness report were read.

The personal checkout remains on `chore/automated-quality-guardrails`, `f69e64c…`.
Its untracked planning/evidence, existing server and every other worktree were preserved.
Only this isolated worktree was edited. Safe deterministic synthetic CSV/coordinates
were used; no production Pulse was loaded or published.

## Exact acceptance and Definition of Done

[Verbatim78-criterion matrix](npi12-evidence/acceptance-matrix.md) and
[per-criterion inputs, expected wording, observations, environment and limits](npi12-evidence/criterion-evidence.json)
are the authoritative new acceptance record. Each PASS links executed evidence.
The approved coverage's43 user-story IDs are confirmed in the authority register;
their behavioral coverage is supplied by the associated R/I/P/G rows, not a newly
invented story checklist.

Tracked-report counts before publication CI:
**75 PASS / 0 FAIL / 0 BLOCKED / 3 UNVERIFIED / 0 NOT APPLICABLE.**
G-02 is pending the final documentation PR CI. With that exact-HEAD gate passed,
the final count is **76 PASS / 0 FAIL / 0 BLOCKED / 2 UNVERIFIED / 0 NOT APPLICABLE**,
with only I-10/G-08 retaining production-capacity UNVERIFIED. This conditional count
is not a claim that an unpublished commit passed CI.

Definition of Done disposition:

- Prerequisites/approved IDs confirmed; exact matrix and observable evidence recorded.
- No production behavior change was needed. Existing conformant behavior received
  regression evidence, without fabricated RED/GREEN. One obsolete CURRENT document
  was corrected after independent review; documentation does not need fictional TDD.
- Full local mandatory verification passed; required final-HEAD CI is a separate
  publication gate. Standards, Spec and Ponytail findings/dispositions are retained.
- No unresolved blocking integrity defect was reproduced. External capacity and human
  limitations remain explicit. No unrelated feature, dependency, framework or iteration.

## Executed walkthrough and observable seams

[Scenario matrix](npi12-evidence/scenario-matrix.md) covers the24 requested steps and
source/cache/error/performance extensions. All browser drivers used actual Flask and
headed Microsoft Edge155.0.4283.45, native CDP mouse/key input, rendered UI screenshots,
real Product algorithms and observed HTTP requests/responses. Python3.12.14,
Node22.23.3 and locked dependencies were used on Windows.

The replay runner reuses existing NPI-04/05/08/09/Freshness drivers. It updates only
fixture/output paths, free ports, current visible hierarchy selectors and current
origin-summary rejection observations. Drivers written for the pre-NPI-08 hidden DOM
needed visible-control checks; a stale driver expecting point-row rejection now
observes the earlier frozen-summary rejection. No production assertion was weakened.
The map click replay toggles the existing label layer off before selecting the real
destination marker; dense medoid labels otherwise cover the marker. Labels and actual
representative geometry are separately verified in the medoid replay.

API/algorithm-only arithmetic, malformed payloads, equal-distance medoid and legacy
compatibility cases are labeled as such. R4 is document/source review. Temporal
NPI-09 reaffirmation is inspected historical approval evidence, not a new approval.
No unit/controller callback is called a human or real-Flask walkthrough.

Executed browser evidence:

- [Selection](npi12-evidence/selection/live-results.json): one/multiple origins,
  combined periods, frozen edits, zero-match/NO_DATA, P1 recovery, native selection/removal.
- [All](npi12-evidence/all/live-network.json):36 origins versus30 suggestions,
  foreign-region exclusion, current/spot/tent/20, equivalent manual selection,
  regional changes,35/36 zero-match attribution, Space/Enter and reset.
- [Navigation](npi12-evidence/navigation/live-network.json):34 origins/12 destinations,
  contributor paging50→61, focus restoration, map/table selection, request-free drill-up,
  late responses, summary/row retry, sort/collapse/help and separate historical repeats.
- [Freshness](npi12-evidence/freshness/network.json): atomic weekly replacement with
  tab left open, revision/no-store, failed/fresh calculation, comparison reuse,
  eviction/restart/network validation, in-flight source change, coordinate rejection/recovery.
- [Medoid](npi12-evidence/medoid/live-network.json): five actual modes, member geometry,
  non-city and missing-name representatives, unresolved exclusion, temporary semantics.
- [Downloads](npi12-evidence/network.json): actual completed attachments, byte checksum,
  saved sort/intent, edited forms, cancellation, failure/retry, generation conflicts,
  restarted result and quality/forecast fixtures; independently reopened workbooks.

## Independent mathematical reconciliation

The following expectations were hand-calculated before inspecting output; they are
not copied from production aggregate functions. [Independent arithmetic and scaling](npi12-evidence/measurements.json),
[newly executed literal-constant regression cases](npi12-evidence/executed-tests.md).

Shared X rows: A10 machines/100km/price1000; B30/300/6000; B20 missing both metrics;
B20 price4500/missing distance. Machines80. Valid route weight40, price60, rate40.

| Metric | Raw numerator / valid machines | Expected and observed |
|---|---|---|
| Route km | (10×100 +30×300)/40 =10000/40 |250|
| Price rubles | (10×1000 +30×6000 +20×4500)/60 =280000/60 |4666.666666666667|
| Rubles/km | (10×10 +30×20)/40 =700/40 |17.5|

The original union case with only the first missing-distance20 has total60 and
valid40, preserving250 and coverage40/60. The separately executed HTTP regression
checks those exact constants. Adding60 distinct equal-value missing-metric rows
for browser export changes X to140 machines while valid weights/numerators remain
40/60/40 and10000/280000/700. The actual workbook retains every one of those rows,
including duplicate values with distinct source IDs. Geography/Volume total155
machines and67 assigned rows; Cost145/65, excluding unassigned destinations.

Contributor A remains100km/10 valid machines; B300km/30 valid route machines, price
weight50 before the60-row addition. Actual B source-region null/conflict is retained.
Null/zero values receive no invented weight. The quality fixture proves true numeric
zero versus blank missing values and route-null → UI dash → blank XLSX.

Navigation fixture independently extends X: +60 machines at100km/price1000 and
31 one-machine origins at200km/price2000, plus40 missing-route machines. X171,
valid route131, numerator22200 →169.46564885496184km. Cluster0 includes X and three
40-machine destinations: total291, valid route251, numerator52200 →207.96812749003985km,
display208.0. A total-trip-weighted average of point means would be wrong.
Price valid weight271 and rate251 differ, demonstrating independent coverage.
All other base clusters retain250km. Region regrouping preserves row identity,
membership and valid weights; it does not produce another clustering.

Single-origin API regression independently retains120km (valid5/total9), raw
price28000.05/9, point min/median/max distributions and unavailable values. These
diagnostic distribution semantics remain over destination points. Generic/Bear
diagnostic economics retain their separately documented semantics; the saved cluster
table and XLSX use the metric-valid denominators required by this iteration.

## Five modes, multi-origin and All

Geography, Geo+Cost and Geo+Volume run and download their own saved membership/table.
All five compare variants share one frozen dataset/snapshot; winner remains null.
Internal cached activation is request-free and resets overview/default trip sort.
Full SpatialGraph precedes business eligibility; induced-subgraph invariants and
scalar/singleton compatibility pass newly executed algorithm/API tests.

The uniform regional All fixture gives normal `no_bears` for both Bear modes.
The separate medoid fixture produces one real Bear Cost singleton p1 and one
Bear Volume singleton p0, with expected high-cost/high-volume semantics. Both retain
explicit unsupported table/export behavior. No RESEARCH/LEGACY restriction was moved
into Product or vice versa; full regression and real Data Map view exit were exercised.

## Navigation, frozen context and historical failures

Native navigation rows→summary→cluster→overview restores origin/point/cluster focus.
Same saved request, map center/zoom, membership, sort/collapse and loaded pages remain;
no new clustering or detail request occurs during cached drill-up/reentry.
Selecting a different cluster clears descendants; released late rows cannot reopen them.
Form-only edits leave the old result usable, with warning. Rejected generations and
unavailable results require explicit successful recalculation.

Three separate historical repeats are present in
[navigation observations](npi12-evidence/navigation/live-observations.json):

| Historical scenario | New execution record | Observed outcome |
|---|---|---|
|10 / D01/P1|10-p1-source-rejected,11-p1-refresh-failure,12-p1-fresh-recovery|Real409; failed refresh retains old display; unchanged Calculate sends fresh run, new snapshot/35 origins, working source rows.|
|12 / D02/P2|09-cached-comparison-p2, historical-12-p2-next-submitted-mode|Bear Volume→Geography→Archive retains checked/form Geography; next actual submitted run is Geography.|
|16 / D01/P1 keyboard|historical-16-keyboard-fresh-recovery|A second source conflict; native Enter on Calculate gives a new snapshot and reselected50 working origin rows.|

All six P1/P2 criteria include export branches in actual downloaded workbooks/errors.
Ordinary valid cached switching is preserved. Revision validation does not promise
future retention: later eviction/change still fails safely. Cancellation and late
success/error responses cannot replace new result/context or start unwanted downloads.

## Medoid acceptance

Actual representative remains an unweighted projected-distance medoid in the assigned,
coordinate-resolved member set. The x0/2/10 independent case selects2 (distance sums
12/10/18), not centroid4 or largest-volume10. Tie/coincident/singleton cases repeat the
same member for identical ordering. Map and inspector expose identical saved name/FIAS
and member geometry across five modes, including non-city and missing-name labels.
Unresolved p12 is never representative. Table columns remain unchanged.
**НАВЕРНО / ВРЕМЕННО** and the recorded user reaffirmation are retained; no warehouse,
centroid-city, reverse-geocoding or new Bear rule is implied.

## Actual downloaded XLSX inspection

[Workbook inspection](npi12-evidence/workbook-inspection.json) reopens the actual
browser-downloaded bytes with an independent stdlib ZIP/OOXML reader. CRC, sheet
structure/names,14 first-sheet headers/all row labels/order, source-row uniqueness,
saved membership, request/provenance/selection intent, units/coverage and cells are checked.
Successful attachments match the fixture server's SHA256. This is file opening and
content inspection, not a claim of human desktop Microsoft Excel acceptance.

Sheets are «Кластеры», actual row-origin-region→saved cluster directions, «Контекст».
Null regions stay explicit; collision-safe legal names reconstruct full labels in context.
No formulas/macros/external links were found. Literal =,+,-,@ source strings, leading-zero
000123,1000.05,zero and blanks are exercised by an actual browser download. All assigned
source rows export before paging; missing economic rows remain if their destination is
assigned, while unassigned rows are excluded with counts/reasons. Cancellation/writer500/
connection reset/source409/restart409 produce no apparently successful partial download.
Retry does not rerun clustering. Bear stays explicitly unsupported.

## Reproduced startup discrepancy

[Bounded startup/hash evidence](npi12-evidence/startup.json) proves the equivalent
outdated-frontend symptom is **REPRODUCED**, not merely inferred from an old branch.
The existing localhost5055 server returns HTML without multi-origin/All. Its HTML,
state.js and controller.js match the old personal checkout **byte for byte**.
An independent literal `python run.py --port 5082 --no-browser` with synthetic CSV
returns candidate HTML/scripts byte for byte, including both current controls.
Navigation also runs through the candidate's documented `run.main()` at5078.
Existing5055 process was observed, preserved and never killed.

Classification: local checkout/old-server mismatch, not an integrated Product defect.
The original user's exact historical tab/session was not independently observed;
the presently reproduced equivalent symptom and static checkout identity are proven.
Static responses use Cache-Control:no-cache and conditional ETag304; there is no
evidence here of a caching rule overriding the supplied checkout. An old live tab
can still retain already-loaded JS; that is a separate unobserved historical possibility.
Product workspace must be selected rather than «Карта данных».

Precise local diagnosis checklist:

1. In the terminal used to launch, print `Get-Location`, `git branch --show-current`
   and `git rev-parse HEAD`; compare with the intended checkout/SHA. Preserve changes.
2. Check which port the terminal reports and which URL/tab is open. `run.py` defaults
   to5055; direct `backend/app.py` defaults to5000. The existing `--help` description
   incorrectly says5000 despite the parser's5055 default; this pre-existing help typo
   is documented, not silently changed in a verification ticket.
3. Identify existing listeners with `Get-NetTCPConnection -State Listen -LocalPort 5055,5000`.
   Do not kill an unidentified process. Use an unused explicit port for a bounded check.
4. From the intended checkout and locked environment, set `LOGISTICS_CSV_FILE` to an
   authorized local CSV, then launch `python run.py --port <unused-port> --no-browser`.
   Missing CSV causes startup failure; a worktree does not copy private data automatically.
5. Open that exact URL in a new tab, select «Кластеризация», inspect HTML for
   `selected-origins` and `all-origins`, and confirm static JS comes from that checkout.
   Reload the old tab only after confirming the server identity/URL.

## Safe capacity and operational observations

These are single observations, not percentiles, stress-test guarantees or production SLAs.
API timings use real Flask client, actual algorithms/export and independently opened files.
Catalog timing includes lazy CSV index load. Browser90k timing includes actual UI/network
handoff. Memory is process working-set/peak from Win32 during sequential runs, not
isolated per-case allocations or total browser memory.

| Origins | Destinations | Raw rows | Assigned/exported rows | Catalog/load s | Run s | API export s | XLSX bytes | Process peak MiB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|34|12|408|374|0.060|0.117|0.207|40,778|140.86|
|100|100|20,000|20,000|1.025|0.617|4.089|1,522,284|207.76|
|150|300|90,000|90,000|3.891|1.212|21.266|6,695,463|486.15|

Use [measurement JSON](npi12-evidence/measurements.json) for full precision;
the smallest collinear fixture legitimately excludes one spatial outlier (34 rows),
and those rows are explained rather than silently truncated. Actual standalone
run.py startup time is recorded in [startup JSON](npi12-evidence/startup.json).
The90k actual Edge run/handoff took1.667s/19.522s; independently reopened
**90,000 unique rows/90,000 machines**,6,695,466 browser bytes (context timestamp differs).
[Browser timing](npi12-evidence/capacity/timings.json),
[opened-file proof](npi12-evidence/capacity/reopened.json).

Export scans the regional selected slice for each destination: approximately P×R
candidate checks. Constant-memory workbook writing does not remove repository/source
and per-point lists. Browser transport retains Blob plus ArrayBuffer; the existing30s
timeout remains. Larger/slower/realistic slices can exceed it. Backend cancellation
does not establish a job platform or guarantee stopped computation; frontend correctly
prevents cancelled late results from being presented/downloaded.

In-memory LRU:64 saved results,32 location entries,32 graphs; there is no time-based
retention lease. Eviction/restart loses saved membership and returns explicit recovery.
Different workers cannot share those process-local caches, so production deployment
requires separately verified worker routing/state behavior. Metadata identity is
path/size/mtime for source and coordinates, not a content hash; same-size/same-mtime
rewrites are undetectable. File replacement must change metadata. Updates after the
last generation check are not protected by a streaming lease, though completed
workbook bytes themselves stay frozen. Coordinate lookups remain name/region cache
provenance, not verified FIAS geocoding; no real-coordinate accuracy claim is made.

**PRODUCTION CAPACITY: UNVERIFIED**: no authorized representative production input,
target rows/origins/destinations, concurrency, latency, memory or retention SLA was supplied.

## Findings, independent reviews and remediation proposals

[Standards](npi12-evidence/standards-review.md) and
[Spec](npi12-evidence/spec-review.md) were separate read-only agents, followed by
[Ponytail review](npi12-evidence/ponytail-review.md). They are separate axes:
Standards0 hard violations,1 operational advisory; Spec1 MINOR CURRENT-doc mismatch
resolved,2 evidence/freshness advisories. Reviewers did not independently run the
parent's full desktop suite. Final evidence/doc review is retained separately.

| Finding | Severity / affected criteria | Reproducibility/evidence | Disposition |
|---|---|---|---|
|Old server/check-out at5055|MINOR operational/startup|Three static resources match personal f69e64c bytes; startup JSON|Root cause captured; checklist; personal process preserved.|
|Obsolete readiness CURRENT All/export statements|MINOR R4-01/R4-03|Independent Spec cites old lines173/191/194–209|Focused documentation correction, no production/TDD fiction.|
|Repeated source traversal and30s timeout|ADVISORY I-10/G-08; production impact unverified|300×90k,21.27s API/19.52s browser,486.15MiB peak|Measured; focused proposal; no unapproved architecture.|
|Metadata identity/in-memory retention/workers|ADVISORY I-02/I-04/operational|Source+coordinate/restart/eviction replay; documented boundary|Retained explicitly, no content-hash/coherence guarantee.|
|Dense representative labels overlay markers|ADVISORY map/medoid usability|12-point navigation screenshot; existing label toggle exposes destination|Temporary labels verified; no decluttering redesign.|

No unresolved BLOCKER/MAJOR integrity defect was found in executed scope.
Suggested post-iteration tickets, **proposals only, not started**:

- Obtain production workload, latency/memory/retention/concurrency and authorized
  sanitized representative fixtures; measure intended All slices. Acceptance: requirements
  recorded and observed workload reconciles, with no guessed SLA or confidential evidence.
- If measurements justify it, reuse one generation-validated destination grouping/index
  for export instead of repeated regional scanning. Preserve exact source-row IDs,
  membership, completeness, cancellation/error behavior and current writer; compare
  before/after on identical approved fixtures.
- Define production process/result lifetime and weekly publication/coordinate provenance
  operating procedure. Retain explicit RESULT_UNAVAILABLE and rejection recovery; choose
  persistence/coherence/content revisions only after an approved need, outside NPI-12.

## Full regression, security and publication

Final local full suite: **593 passed / 0 failed / 0 skipped**,136 mandatory Node/Edge
frontend checks,328.96s. [JUnit](npi12-evidence/pytest-results.xml),
[complete log](npi12-evidence/pytest-clean.txt),
[executed case inventory](npi12-evidence/executed-tests.md).
Two pytest cache-directory permission warnings did not skip or fail tests; new fixtures
and basetemp are isolated. Initial old-environment collection failed on missing
XlsxWriter; isolated full locked installation corrected it, without editing existing envs.

Locked install/pip check, Ruff, all frontend JS syntax (including vendored ol.js),
driver syntax, diff whitespace, exact mandatory Node/Edge startup and literal run.py smoke
were executed. [Quality record](npi12-evidence/quality-gates.json). No production code,
dependency/manifest/CI change. New evidence scripts contain executable assertions and
were actually run, not merely added as unexecuted tooling.

Only synthetic IDs, rows and coordinates may enter the publication allowlist. Private
CSV, XLSX binaries, virtualenvs, profiles and all other workspace files remain local.
Text logs are redacted for local checkout/user paths before publication. The
[artifact manifest](npi12-evidence/artifact-manifest.json) inventories the published set.
Spreadsheet strings remain literal; no formulas/macros/external links found; typed
error responses do not deliver partial workbook artifacts. Local default loopback
Flask startup is reproducible; production hosting/security/coordinate/data quality
acceptance is not implied by this local workflow.

One focused PR targets protected main. No merge, production operation or next iteration.
Final recommendation: accept the evidenced functional iteration and review this
documentation PR after exact-HEAD CI. Obtain human and production operational/capacity
acceptance before claiming a production-ready release. The final PR supplement resolves
the publication gate without creating a self-referential claim inside its own commit.
