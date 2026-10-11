# NPI-11 — saved Product XLSX frontend download

Executed 2026-10-11/12 Europe/Moscow in isolated `.worktrees/npi11-xlsx-frontend`,
branch `feat/npi11-xlsx-frontend`. Original checkout, branch and untracked approved
specification artifacts were preserved. NPI-12 was not started.

## Verified baseline and authority

Fetched protected origin/main: `e98eb2c02accb7a9252b919587e490748c2b64bb`.
[PR #16](https://github.com/a-man-or-a-person/AI_logistics/pull/16) and
[PR #17](https://github.com/a-man-or-a-person/AI_logistics/pull/17) are merged.
NPI-10 final integrated HEAD `d7778f76e6b004145eabcd1b19c4da7f0d42d9d1` passed
[required verification](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38173212403).
Combined main push passed
[Quality](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38173482318).

Read the original workspace `.scratch/next-product-iteration/` exact issue11,
approved spec, coverage matrix, implementation order, tracker and execution requirements;
AGENTS/CONTEXT, domain docs, Product architecture/contracts, NPI-07/08/09/10 and Pulse
freshness reports/code. Historical local blocked labels were reconciled with merged
implementation/CI rather than treated as current runtime facts. User-confirmed seams:
Product API, real Flask/synthetic Pulse, live desktop browser/downloaded XLSX and
existing Node/Edge frontend public transport/controller contracts.

## Exact owned acceptance matrix

Environment: Windows, Python3.12.14, Node22.23.3, headed Edge155, locked dependencies;
real Flask, deterministic synthetic Pulse only. PASS below means executed automated
browser acceptance and independent ZIP/OOXML inspection, not human desktop Excel.

| ID | Exact approved wording | Action / expected and actual | Evidence / limitation |
|---|---|---|---|
| R2-01 | sort actual active table, download/open XLSX: first sheet same columns/headers/all row IDs/order; no representative/origin column or viewport truncation. | Click route-length sort, collapse, keyboard download. First sheet has all14 actual UI headers and every saved cluster label in displayed order; comparison modes checked too. | PASS: 01 screenshot, network.json, workbook-inspection.json; synthetic2-cluster viewport with horizontally off-screen columns. |
| R2-07 | edit form after run, export: workbook uses original selected origins/filters/mode/parameters/periods/snapshot, not new form. | Change form to Bear after saved Geography; export original Geography. Cached Geo+Cost after Bear Volume edit exports its own table, membership and missing-metric assigned rows. All then equivalent manual set exports distinct observed intent. | PASS: 02/03/04 screenshots, request JSON and independently read workbook context. |
| R2-10 | conflict detected before export or generation changed during export: visible error/recalculate, no mixed or apparently successful partial workbook. | Change CSV before export; inject replacement during real backend workbook generation. Both yield409 STALE_DATA_SNAPSHOT, no browser download, old table stays visible, export blocked. Explicit fresh calculation recovers. | PASS: 07/08/09 screenshots, typed HTTP errors; P1 export invalidation and recovery checked. |
| R2-12 | download has real XLSX MIME/attachment and opens; collapsed table still exports full saved rows; invalid sort rejected and row order follows null/tie rules. | Real browser attachment bytes match server attachment hash;10 downloads reopened, table headers/all rows/order compared. Null/tie and invalid sort reuse actual backend endpoint regression tests; frontend transports supplied sort without substitution. | PASS: actual downloads/inspection plus test_xlsx_export_api.py sort tests and26 frontend checks. ZIP envelope test is not a full workbook validator. |
| R2-14 | keyboard initiates export; loading/error/retry visible; server result unavailable or empty/unsupported table explained; retry does not silently rerun clustering. | Native Enter downloads, held export displays preparing/cancel; writer500 and reset connection produce visible retry with unchanged run count. Bear is explicit unsupported. Restart gives RESULT_UNAVAILABLE; fresh run recovers. Empty supported table guard explains absence and refuses request. | PASS: live keyboard/loading/error/retry/Bear/restart and executed separate Edge empty-table check startup-empty.json. No human acceptance claim. |

I-07, P1-02/P2-03 export branches: cached Cost after Bear edit uses saved Cost;
form-only stale permits original export with warning; genuinely rejected source or
unavailable result invalidates existing caches, keeps old frozen display and blocks
export until successful fresh calculation. Original remediation identities retained.

## Download UX and transport

Inspector control sits immediately after saved context. Table layout, columns,
map, inspector selection, sort, collapse and NPI-08 navigation remain their existing
owners. Native button/live status shows preparing, cancel, safe errors/request ID,
retry and transfer-to-browser success. `aria-disabled` plus handler guard prevents
duplicates while retaining native focus. Bear/empty/rejected/unavailable cases have
explicit explanations. Ordinary point/cluster navigation uses the same frozen result.

`exportClustering` is a narrow POST JSON/binary path outside requestJson. It sends
cache:no-store, validates XLSX MIME/attachment and complete ZIP boundary records,
preserves the entire Blob, uses a safe server filename (UTF-8 filename* supported,
unsafe path/device/extension names fall back), retains backend typed code/message
and request ID, and handles connection/30s timeout/caller cancellation. No JS workbook
calculation or clustering request occurs during export/retry. Payload comes only from
displayed `analysis.frozen_request`, `data_snapshot`, explicit `selection_intent` and
copied current tableSort; All is never expanded again.

One in-flight controller; cancellation/new run/compare/reset/cached activation/view
exit/pagehide aborts and guards late response. Result replacement is checked again
before download. Hidden anchor is removed; object URL revoked after browser handoff.
Downloaded Blob is not cached. Success does not claim the user saved/opened the file.

## Actual downloaded workbook inspection

[Reproducible driver](npi11-evidence/live_download.py) starts real Flask and
[headed Edge](npi11-evidence/live_edge.mjs). Synthetic source:68 total rows,67 matched
Geography/Volume rows,65 Cost rows;3 resolved origins/4 destinations. All/manual/cache
variants download10 complete XLSX files. Server test-only attachment checksum retains
file position; actual browser-downloaded bytes equal that checksum. CDP returned empty
binary bodies, so no empty-CDP-body checksum is misrepresented as response evidence.

[Independent inspection](npi11-evidence/workbook-inspection.json) uses stdlib ZIP/XML,
checks CRC, headers/order, values/types, saved membership/context/snapshot/intent,
and absence of formulas/macros/external links. All60 missing-metric source rows of
assigned X are present once; original duplicate-value rows retain different IDs.
Geography/Volume export155 machines, Cost145 before fixture changes. X140 machines;
independent source numerators remain distance10000/valid40=250km,
price280000/valid60=4666.666666666667, rate700/valid40=17.5₽/km. Blank rows change
machine totals without changing valid denominators. Grouping preserves row-region
attribution and saved destination-to-cluster membership. No detail page was loaded
before downloads. Production Pulse was never loaded or published.

[Network](npi11-evidence/network.json) records JSON payloads, MIME/attachment/no-store,
typed failures and browser download events. [Live observations](npi11-evidence/live-observations.json)
and screenshots show native actions/states. Driver cancellations cover user cancel,
Data Map navigation and new calculation; real-Edge regressions cover reset/pagehide,
cached comparison/replacement and cancelled late successful fetch response.

## Verification and reviews

[RED/GREEN observations](npi11-evidence/red-green.md): genuine missing transport and
connection-error RED, then GREEN; environment-only controller timeout not claimed RED.
26 focused Node/Edge checks passed. Initial full suite591PASS/2FAIL; required DOM fixture
methods repaired, targeted2PASS. Final full suite: **593 passed,136 mandatory frontend
Node/Edge checks,0 skipped,0 failed**,304.65s. [Full log](npi11-evidence/full.txt) and
[JUnit results](npi11-evidence/pytest-results.xml) retain complete counts.
[Separate startup/empty-table Edge check](npi11-evidence/startup-empty.json): PASS,
no export request or repeated run, focus retained. Empty guard is executed regression
evidence, not merely code inspection.
Locked install/pip check, Ruff, all frontend JS syntax, driver syntax and diff check
executed. [Locked install](npi11-evidence/locked-install.txt) revalidated the existing
manifest. No dependency or manifest change was needed.

[Independent Standards](npi11-evidence/standards-review.md):0 blockers.
[Independent Spec](npi11-evidence/spec-review.md): CURRENT-doc finding resolved;
no production blocker/scope creep. [Ponytail](npi11-evidence/ponytail-review.md): no
concrete code finding; minimal existing architecture retained. Final results and exact
PR/required-CI links and exact final HEAD are provided in the task's final response
only after actual publication and verification.

## Limitations

Production All capacity/SLA and human Excel acceptance remain UNVERIFIED. Browser
buffers Blob plus ArrayBuffer and retains the existing30s timeout; no arbitrary row
cap/truncation is added. Backend metadata fingerprint, in-memory result lifetime and
multiworker/source-after-final-check limits are unchanged. No merge or NPI-12 work.
