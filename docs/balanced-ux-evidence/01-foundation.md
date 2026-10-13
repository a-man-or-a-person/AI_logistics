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
Touched runtime seams: CSS, inspector help markup, table keyboard help and
controller Escape priority for an open native help popover. No request,
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
- First hosted Quality run `38387303328` at `14b81dbc` passed all 136 existing
  frontend cases/zero-skipped gate, but the two new resize oracles read 13px
  immediately after root mutation instead of 26px. Other 457 Python cases passed.
  Recovery candidate synchronizes measurement with two animation frames, preserves
  the 26px assertion and adds explicit root 16px/32px assertions. Production CSS
  remains the independently reviewed candidate; hosted recovery evidence is
  recorded in the later PR supplement rather than assumed from local success.
- Rerun `38388863949` at `6773700ce60c35f587670e754328e755ff1627f7` again passed
  136 frontend cases and 457 Python cases but failed both resize assertions;
  root32 assertions passed. Waiting animation frames alone was insufficient.
  The next test setup waits for inserted stylesheet completion and font readiness
  before initial measurement, preserving 13/26px assertions and capturing the
  font-size chain/UA if failure persists. A controlled empty delayed import did
  not reproduce the hosted symptom locally; no production defect is inferred.
- Run `38396169710` at `e625bb1a8fe69914c94f72975e5fa63d2374d36b` failed the
  same two assertions after resource readiness. Actual UA is Headless Edge152
  and document compatibility is CSS1Compat; root32 still passed. The next scoped
  CSS candidate assigns the same `.8125rem` directly to Product table/Pulse cells,
  retaining approved 13px/26px values instead of relying on table inheritance.
  The diagnostic assertion prints complete JSON rather than truncated dict repr.
  This candidate must pass a fresh hosted run; no environmental cause is asserted.
  Fourth hosted run54 (`38398675617`, job `115300351677`) at head
  `a1c4656cde9a898808e0cf6db7965b8f162236c1` also FAILED two resize cases;
  tested merge was `797d1b670bb2dc1d3ffe58ac9ef9a28022a0f630`.
  Complete JSON showed root32 while main14/table13/tbody13/tr13/td13 stayed
  unchanged in both themes (fonts loaded, standards mode, Edge152). This disproves
  the narrow table-inheritance explanation; direct cell rules did not solve it.
  A failure-only diagnostic now compares a freshly inserted inline rem element
  and loaded minimal iframe documents with implicit root versus relative100%
  root. Original26px assertion remains unchanged. Independent Spec reviewed and
  exercised the probes without file edits; local138 frontend/466 Python cases
  and Ruff passed. These diagnostics require hosted execution to establish a cause.
  Fifth run55 (`38400720015`, job `115307336930`) at
  `3ea8ab31853f9481a1f68b998d06b4e24db36282` again failed only both resize cases.
  Fresh inline rem computed26px/width32px; both minimal iframe roots (implicit
  and explicit100%) resized13px to26px; original existing rules stayed13px.
  Document was complete and fonts loaded. This ruled out root conversion, implicit root sizing and parser completion;
  existing nodes differed from newly inserted probes. The transition cause was
  established later, so this observation alone did not prove an engine defect.
  The next candidate moves the unchanged existing Google font URL/families/weights
  from CSS `@import` into a normal HTML stylesheet link and removes the ineffective
  direct-cell rule. The test loads that actual HTML font link too. Original
  assertions remain intact; hosted GREEN is required before attributing recovery
  to this change. An initial unescaped HTML-in-script fixture setup error was
  corrected using JSON `<` escaping; it is not behavioral RED evidence.
  Sixth run56 (`38408410995`, job `115333998366`) at
  `0ab9dd52edc57a12e9ceb8d26199015769e9e132` FAILED the same two resize cases,
  with136 frontend/457 other Python cases passing. Font-import placement was not
  the cause; the font-loading change was reverted to the original CSS import.
  The relative-body experiment at head `6cc25eee34a9323700c3fa48153547473626930d`
  also FAILED in run57 (`38411374557`, job `115344288813`). The fixed-body minimal
  control resized correctly, disproving the legacy fixed-body explanation.
- Controlled local `prefers-reduced-motion: reduce` reproduced the hosted symptom
  on installed Edge155: root32, existing table13, and 41 active CSSTransitions
  with duration0.01/currentTime0. The old global reduced-motion rule created
  transitions for font-size and other properties instead of disabling them.
  Saved RED observations: `.scratch/balanced-foundation/reduced-motion-red.json`.
  The expanded two-theme/system-or-forced-reduce test failed 2 cases and passed2
  before production edits. The final CSS uses `animation:none`/`transition:none`
  in that existing media rule; the ineffective relative-body rule was removed.
  All four strict 13-to26px cases then passed, including no CSSTransitions under
  forced reduction. Default test calls still retain actual system media settings.
  Earlier failure-only fresh-rem/iframe diagnostics were removed from the final
  test; their historical artifacts remain preserved. No CI assertion was weakened.
- Actual125% browser zoom with reduced motion exposed Escape dismissing both help
  and its parent inspector. A new regression genuinely failed with panelOpen=false
  while snapshot/UI/request count remained unchanged. The shared controller now
  lets native help dismissal take precedence. All five focused cases passed;
  actual keyboard Escape retained the panel/focus, Enter/Space reopened help,
  and a subsequent Escape without help closed the parent. Native smoke logs:
  `.scratch/balanced-foundation/motion-drawer.log` (RED) and
  `motion-drawer-green.log` (GREEN). Panel focus trapping/reflow remain ticket02.

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

Font-link candidate repeated full138 frontend/466 Python cases, zero frontend
skips, dependency/Ruff checks and explicit Node+Edge startup. Actual Inter and
JetBrains Mono faces loaded in headed Edge155; both-theme100% matrix/help/200%
resize passed. Blocking only Google font resources in an isolated test profile
also passed the fallback-font matrix/help/resize. All three device sizes in both
themes passed at actual125% browser zoom (DPR1.2500000186), retaining14 columns
and access to Calculate/export. Calculate access currently requires scrolling
the controls to their end; native scrollIntoView can expose only a sliver at
1366x768/125%. Persistent footer/focus visibility remains owned by ticket02;
this evidence does not claim its layout criterion. Named normal/fallback/zoom
observation JSON and drivers are retained in `.scratch/balanced-foundation/`
and `.scratch/foundation_font_link*.mjs`; source asset hashes matched served bytes.

Official Edge152 package SHA256 matched Microsoft metadata and was archive
extracted with existing7-Zip solely under `.scratch/resize-diagnosis-edge152/`.
No installer/global setting was changed. Actual offline browser UA was152, but
page CDP commands hung before CSS evaluation, including an immediate UA evaluation
without viewport/focus emulation. This is a local renderer/driver blocker with
unknown cause; it is not typography RED/GREEN. Package/probes are preserved.

The relative-body candidate repeated138 frontend cases (zero skips),466 Python
cases, dependencies/Ruff and live loaded-font/fallback matrices/help/200% resize.
The actual125% three-size/two-theme matrix also passed. Named `font-chain-*`
observation JSON, logs, screenshots and `.scratch/foundation_font_chain*.mjs`
drivers preserve this candidate separately from earlier font-link evidence.
Data Map's body/main were13px even after root32, both in independent probes and
the actual rendered navigation smoke. The persistent-footer limitation above
still belongs02; no skipped mandatory checks or changed workflow were introduced.

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

Reviewer `/root/foundation_spec`, independent read-only Spec review. Initial CSS
SHA256 `bc7e05950c67429c6b52c0990ee2d4b4182e588e8b612acf6475cf2085084b9f`.
Inspector `78ed176c3d9b135f1790b0f4ddf79202a510e201cfb8aacf526fab6a6110c19b`;
table `67a775c77bfd3d7bb84453fda22e95fbb7c839591e8e91e51cc2a9c6b2e5aeb2`.
Reviewer ran three focused Edge checks and independent computed-style probes,
inspected resize/Data Map screenshots and connected source. Final verdict PASS for
ticket01 scope; all reported contrast/size/focus/help findings fixed. Standards is
N/A for this slice: no new ownership/infrastructure seam. Reviewer did not claim
independent full Quality, human acceptance or production readiness.

The subsequent direct-cell candidate was independently reviewed at CSS SHA256
`4cbcebdd784accf065df2859c52633a21beb6a9c9b61e7bf3ce18b04c7808852`
and test SHA256
`cc30decec5b7068bdf85b733079175b82f7bf37e245f96b9d329483ef890b1b3`.
The reviewer reported PASS with two focused browser cases, zero skips; approved
13/18px and resized 26/36px values and Data Map/business isolation were retained.
Repeated local gates passed 138 frontend cases and 466 Python cases (including
seven prepared, unpublished ticket04 guard cases), Ruff and dependency checks.
Fresh live matrix/help/200% text smoke passed in both themes. Hosted verification
is still required; local evidence does not establish the hosted failure cause.

Font-link candidate independent Spec PASS: CSS
`fe331cbeb898ffe2464f1331e7f3b2a3855d426950d4b1c5681264554c271cfc`, HTML
`bbba1d3559705589eb2639547b722ef655117af7b52e4a9f5ecf792c2e803881`, test
`0c45fb8b9a5980883108e0a63ef7419767fce31b808dd26b8e7f8f65b162271f`.
Reviewer independently inspected exact decoded font URL/resource placement,
assertion/fixture preservation and replayed both browser cases with zero skips.
Loaded font coverage comes from the separately observed live evidence above;
successful test cases can legitimately use the existing fallback.

Relative-body candidate independent Spec PASS: CSS
`de06cf1b95bb2e9371704e6172d218145bb784d80ba9c1d2406641cb0011927f`, test
`f7e0a0009ccdc566ca44824a74887bc262f7dca2569e8cbd4a1472273b2844e2`.
Reviewer independently ran both cases, verified `:has()` support, Product26px
body/28px main at root32, Data Map13px at both roots and after reentry, and visible
comparison relative sizing. Narrow source/probe verdict PASS; hosted recovery
and broader delivery readiness were not claimed.

Final motion candidate independent Standards PASS (`/root/economics_standards`):
CSS `89c5dd6b3ede233f7aca5702812dd3bd114d9db8e10a7b4d301280cc912d90f2`,
helper `00bdd4e503ac4d30d437ff4f40abadacf5d83cd627230a477aa297102425302e`.
Reviewer independently ran four motion cases, checked the default-system setting
and unchanged CI, and found no animation/transition completion listeners affected.
Restricted browser startup timed out before assertions; escalated replay passed.

Final independent Spec PASS (`/root/foundation_spec`): same CSS/helper plus
controller `25b5223c2f3ed13fc64d927dc3f77e96ecccfc1256ec65b85facc994156bfE9b`
and tests `45663e56cf95855c30f479c94d87d708150062e67709f25b991ace986ffc486b`.
Reviewer ran five cases without skips and independently restored the old reduced
motion rule and removed the Escape guard in memory to reproduce both defects.
Native keyboard evidence above is the implementer's separately observed smoke.

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

Latest full local gate on the final motion/Escape source: other Python469 PASS,
locked dependencies and Ruff PASS. The frontend141 PASS/zero skips (JUnit verified), explicit Node/Edge startup and
served asset byte equality PASS. Hosted exact-head result remains pending; this is not hosted GREEN yet.
Normal and forced-reduction live matrices on final source both passed three device
sizes/two themes, 14 columns, strict200% text resize, native help and Data Map.
Current logs: `.scratch/balanced-foundation/motion-final-{normal,reduce}.log`.

Final actual125% zoom with forced reduced motion also passed all three device sizes
and both themes, all14 columns and Calculate/export access. Evidence: local
`.scratch/balanced-foundation/motion-final-zoom.log` and named observation JSON.
