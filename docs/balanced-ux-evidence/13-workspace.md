# D-07 delivery: map-first workspace

Owner/accountable implementer: root agent. Risk: MEDIUM, presentation and focus
behavior. Worktree: `C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`;
branch `feature/balanced-ux-redesign`; remote `a-man-or-a-person/AI_logistics`.
Base before edits: `a843a2ab4d23c16f8a53d579e1e5be70288c8a9d` (D-06).
Main is not changed. User authorized feature commit/push, not merge or cleanup.

## Result and placement

The desktop center contains only the map and full fourteen-column table. Saved
context moves to the right inspector below its sticky Compare control. Existing
summary, quality, technical diagnostics and selected cluster/point details remain
in that inspector. Selection uses the existing detail headings without a duplicate
name strip. Single/Union/All contexts retain full saved names and FIAS identities,
Pulse period/source, mode, K, weights and filter details. Draft/stale status still
describes the frozen saved result separately from editable parameters on the left.

Desktop Parameters/Result openers disappear. At existing responsive breakpoints,
compact map-overlay controls open the same accessible drawers. The Result control
flags draft/critical/warning attention. Compare close/Escape restores its parent
drawer and keyboard focus; selected details scroll into view at enlarged text.

The calculation-methodology disclosure, renderer and CSS are deleted, with no
replacement block. Individual metric helps retain definitions, including mode
influence in the existing weighted-price help. All fourteen keys, sorting, raw
precision, coverage, backend methodology metadata, formulas and XLSX paths remain.
No backend, API, fixture, dependency or export-writer changes were needed.

## Same-data desktop geometry

Actual Edge renders of the same retained synthetic saved result, matched before
and after. Map top moves from 196 to 68 CSS px at all three desktop sizes: a 56 px
menu plus the existing 12 px spacing. Center width is unchanged.

| Viewport | Center width | Visible map area before -> after (px2) | Gain | Table height before -> after |
|---|---:|---:|---:|---:|
| 1366x768 | 718 | 252736 -> 339255 | 34.23% | 196 -> 203.5 |
| 1440x900 | 792 | 376435.125 -> 447405.75 | 18.85% | 204.703 -> 243.094 |
| 1920x1080 | 1272 | 764849.625 -> 878832.75 | 14.90% | 258.703 -> 297.094 |

[Before, 1440x900](13-before-1440.png), [after, same data/viewport](13-after-1440.png),
[dark theme](13-dark-1440.png), [dark with 200% root text](13-text200-1440.png).
[Machine evidence](13-workspace-evidence.json) contains all 24 matched geometry
pairs, resize center/zoom preservation and live route results. Local raw artifacts
remain under `.scratch/d07-workspace`; none were deleted.

## Verification and independent review

Focused RED reproduced the old desktop map offset, nested Compare focus loss and
200%-text hidden selected details. GREEN covers the new placement, deletion,
fourteen columns/helps, drawers, frozen identity, Compare button/Escape focus and
narrow attention states. Affected-neighbor run: 88 passed. The new module has 14
cases. Independent [Spec](13-spec-review.md) and
[Standards/targeted Ponytail](13-standards-review.md) reviews pass within their
explicit scopes; earlier findings and repeat checks remain in those reports.

Live Flask/Edge checks exercised all five modes (including the fixture's honest
Bear unsupported states), overview/cluster/point/origin, Compare, Data Map,
OpenLayers resize and an actual browser XLSX download. This is functional browser
evidence, not a fresh independent numerical XLSX oracle. Business paths are
unchanged and remain covered by mandatory suites.

The current ledger explicitly projects 294 unique information IDs and 35 unique
criteria. It includes the reviewer's 48 corrected paths and owner corrections for
right-side summary/status/Compare access. Historical ledgers remain unchanged;
this does not claim 294 new native visibility passes.

Mandatory final local gates are running on this source candidate: locked install,
dependency check, Ruff and Node/Edge startup have passed; full frontend: 136 passed,
zero skips. Earlier lint ordering, two frontend expectations and one inspector
direct-child expectation were corrected; failed attempts remain local. The latter
retains the exact selected-section-first assertion through the new wrapper and
passed its targeted GREEN. The completed Python attempt reported 652 passed and
two fixture failures: that ordering check and a Node DOM mock missing
`scrollIntoView`. Adding the no-op DOM method retained all real HTTP 409, frozen
identity, cache and recovery assertions; targeted GREEN passed. The already
queued Python repeat was stopped on this known-invalid fixture revision; final
Python is repeated after both test-only corrections. Production bytes are unchanged.
Final suite totals, exact committed HEAD, hosted run/jobs and served asset binding
are recorded in the timestamped Draft PR #22 supplement after completion, avoiding
a self-referential evidence commit. No pending gate is claimed as passed here.

## Handoff and limits

Live preview: `http://127.0.0.1:5086`, retained synthetic fixture, worktree above;
entry `.scratch/09_audit_server_retained.py.txt`, explicit `--no-browser` server.
Final listener/asset hashes are checked separately at handoff.

Native Computer Use stopped because it could not determine the browser URL
confidently; no further native input was sent. Actual browser 125% zoom is
UNVERIFIED: the recorded 125% matrix uses equivalent viewport/DPR. The 200% check
uses root text sizing. Human visual acceptance and production readiness remain
UNVERIFIED. Functional automation is reported separately. Draft PR stays Draft;
no merge, main change, private-cache modification or cleanup is part of D-07.
