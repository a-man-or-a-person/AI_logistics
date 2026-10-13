# Balanced UX ticket 01 — typography and themes

Owner and criterion owner: `/root`. Risk: MEDIUM frontend presentation/keyboard help.
Base: `4d21b54259c1a34a9d098a34aa518f447b411b65` (`origin/main`).
Specification: local `.scratch/dashboard-redesign/issues/01-design-foundation.md`,
DS-01/02/03, and `design-tokens.md`. Preservation owner: `LEG-shell-theme`.

## Changes and boundaries

Product uses approved 24/18/14/13/12px typography, relative units for text resize,
tabular right-aligned numeric values, theme foregrounds and 3px focus outlines.
Essential nested Pulse FIAS and facet counts remain at least 13px. Dark solid
actions use a separate foreground; error toast uses error text/background roles.
Table help supports Enter/Space after Escape; inspector help uses native popovers.
The supported full table remains accessible at narrower widths. Layout dimensions,
persistent footer, contextual inspector and reflow integration remain ticket 02+.

Callers checked: app theme/navigation, controls, inspector, table and comparison.
Touched runtime seams: CSS, inspector help markup, table keyboard help. No request,
snapshot, cache, sort value, API, metric, membership, export writer or dependency
changes. Data Map keeps its own font sizes/formulas and receives shared theme/focus
corrections. Mandatory Quality workflow remains unchanged.

## RED and GREEN

- Baseline rendered essential table/Pulse values were 10/9px rather than 13px.
  `test_dashboard_foundation.py` failed both themes before CSS edits, then passed.
- Table Enter/Space did not reopen formula help after Escape. The existing public
  browser regression failed on `afterEnter`/`afterSpace`, then passed after the
  shared keyboard handler fix. An initial test f-string setup error was corrected
  before the behavioral RED; it is not counted as defect evidence.
- Independent reviewer measured dark error toast contrast 2.510806:1. The final
  rendered contrast regression checks light/dark toast and action/text pairs >=4.5.
- Independent reviewer reproduced faded facet count contrast (~3.27:1) and nested
  Pulse small text below 13px; final probes confirmed 13px/opacity 1 in both themes.

## Live functional evidence

Checkout: `C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`.
Branch: `feature/balanced-ux-redesign`. URL: `http://127.0.0.1:5086/`.
Entry point: existing synthetic `docs/design/dashboard-ux/evidence/audit_server.py`
calls `run.main()` with `--port 5086 --no-browser`; parent `.venv` Python 3.12.14,
Node 22.23.3, actual installed Edge. Synthetic input: 88 safe rows/12 destinations.
HTML and all changed CSS/JS bytes were compared with this checkout.

Actual headed Edge CDP mouse/keyboard smoke: origin selection, segment disclosure,
Geo+Cost calculation; 1366x768, 1440x900, 1920x1080 in both themes; all 14 table
columns retained with local scrolling. At 200% text resize values became 26px;
Calculate/export and the rightmost coverage column remained accessible. Native
inspector Escape/Enter/Space opened/dismissed help. Data Map dark navigation worked.
Actual browser zoom 125% was separately observed (DPR 1.2500000186, CSS viewport
1152x720 for a 1440x900 device viewport), using an isolated task-owned Edge profile.
No user's browser preference was changed.

Bulk local artifacts and reproduction drivers are retained in
`.scratch/balanced-foundation/` and `.scratch/foundation_edge.mjs`,
`.scratch/foundation_zoom_corrected.mjs`. Original research/evidence remains in the
original checkout, with a 100-file verified backup and manifest at
`.scratch/balanced-ux-backup-20261013/`. Screenshots contain synthetic data only.
Compact comparison: [baseline](screenshots/01-before-1440.png) and
[foundation candidate](screenshots/01-after-1440.png), both 1440x900/100%.
Baseline contains an external tile placeholder; candidate tile availability
differed. External basemap visual quality is UNVERIFIED, and this comparison does
not establish a tile improvement.

CSS/help do not alter failure/cache/cancellation identities: the existing full
frontend suite covers those transitions; the live smoke here is presentation/help
evidence, not a new claim of every lifecycle being manually replayed.

## Independent review

Reviewer `/root/foundation_spec`, independent read-only Spec review. Final CSS
SHA256 `bc7e05950c67429c6b52c0990ee2d4b4182e588e8b612acf6475cf2085084b9f`.
Inspector `78ed176c3d9b135f1790b0f4ddf79202a510e201cfb8aacf526fab6a6110c19b`;
table `67a775c77bfd3d7bb84453fda22e95fbb7c839591e8e91e51cc2a9c6b2e5aeb2`.
Reviewer ran three focused Edge checks and independent computed-style probes,
inspected resize/Data Map screenshots and connected source. Final verdict PASS for
ticket01 scope; all reported contrast/size/focus/help findings fixed. Standards is
N/A for this slice: no new ownership/infrastructure seam. Reviewer did not claim
independent full Quality, human acceptance or production readiness.

## Reproduction and readiness

Run the existing Quality sequence with `REQUIRE_FRONTEND_BROWSER=1`: locked
dependencies/pip check, Ruff, Node+Edge startup, frontend contracts with JUnit
zero-skipped assertion, then the remaining Python suite. Include
`tests/test_dashboard_foundation.py`; local pytest requires a NEW task-owned
`--basetemp` because the system `pytest-of-User` directory denies access.
Unrelated original research script lint failures were fixed only in local copied
scripts, which are outside the publication allowlist; originals remain untouched.

Final candidate test counts, exact commit SHA and hosted Quality run are recorded
in the timestamped Draft PR supplement after execution. No earlier run is credited
to a changed candidate. Human acceptance and production readiness are UNVERIFIED.
Main merge, Ready-for-Review promotion and cleanup require separate authorization.
