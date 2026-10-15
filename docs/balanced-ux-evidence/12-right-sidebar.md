# 12 — Restore persistent right analytics

Accountable implementer and criterion owner: `/root`. Presentation risk MEDIUM;
the task's stronger cross-feature gates and independent Spec/Standards/Ponytail
requirements are retained. Repository/worktree:
`C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`;
remote `https://github.com/a-man-or-a-person/AI_logistics.git`;
branch `feature/balanced-ux-redesign`; starting HEAD
`cab287ff62840fc7b8de615f6e567330130899e1`, UI baseline
`ddbeeb466d5d79557e79a88fcd345a6782ad1408`.
Fetched main remains `4d21b54259c1a34a9d098a34aa518f447b411b65`.
The existing feature worktree is reused by explicit user direction. Pre-existing
`backend/cache/coords_cache.json` modification and untracked/ignored private or
historical materials are preserved and excluded from publication.

## Decision and implementation

[D-06](12-right-sidebar-decision.md) supersedes only the top placement of the main
overview. Parameters remain left; compact frozen context, larger map and complete
table remain central; the existing overview/quality/warnings/diagnostics move once
into the persistent inspector. Selected cluster and point/origin/Pulse details
precede that overview. Below 1320 CSS pixels the existing right modal drawer
preserves center width, focus trapping, Escape and opener return.

HTML IDs and business readers remain intact. Controller changes only docking and
selection/return presentation. Explicit selection reveals details; ordinary
rerenders retain reading position; drill-up reveals the focused parent.
OpenLayers already owns `ResizeObserver -> updateSize()`: a live resize preserved
center `[4129953.10843045,7381298.312185911]` and zoom `11`, and reported map size
`[762,240]` matching the resized target. A second observer was unnecessary.
Backend, ML, API, metric formulas, state/cache modules and XLSX writer are unchanged.

Scope includes HTML/CSS/controller, existing layout/summary tests, CURRENT context
and Product workflow, the two Workflow policy additions and this evidence.
Callers include Run/Compare render, map/table selection, parent navigation and
panel resize; existing fixtures, mode catalog, transport and exports retain their
contracts. No new dependency or agent infrastructure was added.

Workflow v2 now requires an **Early Visual Workspace Gate** using identical saved
states and measured workspace areas, and **Repeated CI Failure Diagnosis** using
environment/media/animation/network/readiness fingerprints and a minimal reproducer
before another production fix. Existing CI split and mandatory gates stay intact.

## Actual geometry and visual trade-off

Same live Flask synthetic saved Geography result (origin a, current/spot, Region A,
190 machines, 12 destinations, Auto K3), same viewport and states before/after.
Baseline was captured before CSS edits. Dimensions below are CSS pixels; visible
map height accounts for viewport clipping. Desktop center becomes narrower, while
the map becomes much taller and its visible area grows. The full table keeps all
14 columns and local horizontal scrolling.

| Viewport | Visible map height before → after | Visible area before → after | Gain |
|---|---:|---:|---:|
| 1366×768 | 160.8 → 352 | 166,460 → 252,736 | +51.8% |
| 1440×900 | 240 → 475.3 | 266,112 → 376,435 | +41.5% |
| 1920×1080 | 343.6 → 601.3 | 551,134 → 764,850 | +38.8% |

At 1440 the center narrows from1124 to792, context shrinks107.6→64, table
height grows196→204.7, and inspector is320×820. Expanded diagnostics no longer
consume central height. All24 viewport/state pairs improve visible area, including
overview, expanded diagnostics, cluster and point. Three old expanded-state
baselines had zero visible map area. At the smallest 125%-equivalent viewport the
new map is fully visible at240px, while the table still needs central vertical
scrolling; this compact-screen limit is retained explicitly.

125% was measured through equivalent CSS viewport/DPR pairs (1092×614,
1152×720,1536×864), **not native browser zoom**. Before screenshots use headed
Edge; final screenshots use headless Edge after native Computer Use became blocked.
These are real browser renders, not mockups or human usability evidence.

1440px [before](12-before-1440.png) / [after](12-after-1440.png),
[dark theme](12-dark-1440.png), [200% root text](12-text200-1440.png).
The quality grid adapts from two columns to one at doubled text, independently
checked without horizontal overflow. Complete rectangles, source fingerprints,
resize oracle and retained local artifact manifest:
[compact evidence ledger](12-right-sidebar-evidence.json).

## Verification and independent review

Genuine baseline RED: persistent-overview regression returned `hidden:true`.
GREEN returns a visible docked panel. Review found two additional defects:
selected details stayed above a scrolled inspector, then restored cluster focus
stayed below the viewport. The final combined regression was RED first for
cluster/point visibility, RED again for `clusterReturn:false`, then GREEN for
`cluster`, `point`, `kept`, `pointReturn`, `clusterReturn`. Both independent
reviewers repeated the fixed paths. Six geometry regressions compare against
measured baseline areas and retain14 columns and invariant map geometry when
diagnostics expand. Existing modal/frozen-summary assertions were updated for D-06.

Independent [Spec](12-spec-review.md) and [Standards/targeted Ponytail](12-standards-review.md)
PASS within their source/renderer scope; both MAJORs are resolved. Their final
source hashes bind to this candidate. [Independent preservation/numeric/workbook
review](12-preservation-review.md) retains35 criteria/294 unique obligations,
checks the moved IDs/readers and executes seven numerical tests. It also reopens
an actual browser-downloaded XLSX:73 exact source IDs,12 destinations,190 machines,
14 columns, three clusters, ordering, types, values, shares, coverage and frozen
context reconcile. Historical adversarial evidence is inherited, not relabeled
as a new replay. The ledger groups every original ID with its current access path.

Required local commands use the existing split: locked dependency install,
`pip check`, tracked Python Ruff, Node/Edge startup,
`pytest tests/test_clustering_frontend_contract.py -ra`, then
`pytest --ignore=tests/test_clustering_frontend_contract.py -ra`.
`REQUIRE_FRONTEND_BROWSER=1` and JUnit reject empty/skipped mandatory suites.
The latter suite owns dashboard checks, including both themes, text sizing,
all modes, frozen/draft/cache, selection/origin/Pulse, sorting, comparison,
XLSX, Data Map, stale/cancel/retry/late responses and independent numeric checks.
Full final local/hosted outcomes and exact committed HEAD belong in the timestamped
PR supplement once runs finish; this report does not claim pending checks passed.

## Running checkout and readiness

The retained synthetic server is PID13960, parent1840, port5086, entry
`.scratch/09_audit_server_retained.py.txt -> run.main`, using the root repository's
`.venv/Scripts/python.exe` and this worktree's approved synthetic CSV/coordinates.
URL `http://127.0.0.1:5086`. `/`, CSS, controller and inspector bytes match this
checkout; source hashes are recorded in the ledger. Other processes/ports are
preserved. This URL serves the synthetic acceptance fixture, not private data.

IMPLEMENTED: PASS. Automated verification is subject to the final gate supplement.
Required native Edge mouse/keyboard smoke: **UNVERIFIED**. Computer Use ended with
“could not determine the current browser URL on Windows with enough confidence to
enforce policy”; no further native input was attempted. Headless DOM/keyboard
regressions and synthetic live HTTP evidence are separately labeled and do not
replace this gate. VERIFIED / READY TO MERGE therefore remain UNVERIFIED even if
CI succeeds. No merge, Ready promotion or cleanup is authorized.

Human acceptance n=0 / UNVERIFIED; production readiness UNVERIFIED. The Product
owner must inspect the exact published candidate at all three desktop sizes,
actual125% browser zoom and200% text, both themes, map/table proportions, drawer
keyboard/focus and the intended Excel application. After publication the agent
stops for that visual acceptance.
