# 09 — Recovery and accessibility

Accountable implementer and ST01–05 owner: `/root`. HIGH risk: shared cancellation,
revision validation, cached detail identity and focus. Parent is
`7361f2d22e7c9c8d50b273195fbb9ae86c3205db` (08, Quality65 SUCCESS).
This is feature-branch functional evidence, not merged-main, human or production
acceptance. Final local/hosted gates are recorded separately below.

## Behavior and boundaries

Pending, failed and cancelled revision checks guard new detail activation and
export. Cancelling a check retains uncertainty until a successful check; an
aborted old response cannot validate a newer operation. Draft edits retain the
validated saved result. Source/coordinate stale and unavailable causes retain
their existing distinct states and recovery paths.

Run and Compare expose explicit cancellation for both initial and refresh work.
Cancellation aborts the owned request, retains the last display, announces the
operation and returns focus. Comparison completion removes both pending Cancel
actions. Product exit/pagehide now abort pending detail requests as well as
calculation/export; completed cached details remain available on valid reentry.

The LEGACY record dialog owns one abortable request, guards late success/error,
clears old rows during loading, and distinguishes empty from error. Background
surfaces are inert while open; Escape and close restore a valid opener. Its named
table region receives keyboard scrolling and remains inside the viewport at
320px and doubled root text size, with an accessible close action.

Data Map offers a native closed point selector using the current displayed
dataset, preserving shipment/delivery identity even for equal town names. It
opens the same existing popup as the mouse. The drawer closes before popup
focus; Escape returns to the visible opener or mobile controls. Popup text and
period counts scale from 13px to 26px at doubled root size, with theme contrast.
Mouse popup content, legacy formulas and the nine record fields are retained.

Only the existing frontend seams change: app owns modal requests; controller
owns Product requests and guards; map owns popup presentation. `fetchRecords`
retains its first four arguments and accepts an optional fifth signal argument.
The existing `closePanel` is exposed to the app for drawer dismissal. No backend,
writer, catalog, calculation, dependency, new store or Quality changes.

## Reproduction and genuine regression evidence

New deterministic safe browser cases are in
[`test_dashboard_recovery.py`](../../tests/test_dashboard_recovery.py).
The first42 pass (112.02s), independently repeated42 by Spec, zero skips.
Two additional real OpenLayers group cases and two disabled-action focus cases
bring the set to46; one escaped typed-target accessible-name case brings the
set to47 (47 PASS278.34s). Filter pressed-state/tag focus and error-toast cases
bring the final set to49. Nine affected accessibility/lifecycle neighbors pass
8.27s and independently8.85s; the complete final49 are in full gates.
The retained RED/GREEN files below are relative to the local archive
`.scratch/balanced-foundation/`; test setup failures are not product RED evidence.

| Defect and expected behavior | Baseline RED → observed GREEN |
| --- | --- |
| Failed/malformed revision blocks details until validation | `09-revision-red-resumed.log`:4 failures →4 pass |
| Record ownership, focus, loading/empty/error | `09-records-red.log`:7 failures →7 pass |
| Pending checks and cached origin activation | `09-pending-cache-red.log`:3 failures → affected cases pass |
| Exit/pagehide aborts late detail success and error | `09-exit-red-verified.log`:4 failures →4 pass; exact result dictionaries reject helper-error false positives |
| Modal fits viewport, scrolls and retains close | `09-record-reflow-red.log`:6 failures →6 pass |
| Keyboard entry and narrow noninert popup | `09-map-keyboard-red-verified.log`, `09-map-keyboard-narrow-red.log`: real behavioral failures →2 entry cases pass |
| Popup minimum font and period contrast | `09-popup-a11y-red.log`:4 failures →4 pass; native discovery found one11px count among19 essential text leaves; native GREEN has zero undersized leaves |
| Initial/refresh Run/Compare explicit cancel, late success/error | `09-explicit-cancel-red.log`:8 failures →8 pass |
| Completed comparison removes pending cancel actions | `09-cancel-completion-red.log`:error path fails, success already passes →both pass |
| Cancelled revision is not successful validation | `09-aborted-check-red.log`:2 failures →2 pass |
| Keyboard reaches coincident and max-zoom inseparable group | `09-group-keyboard-red-verified.log`:2 failures (no group count/details/bulk action) →2 real OpenLayers cases pass; shared mouse formatter/actions preserved |
| Disabled group action retains Escape/focus | Native `09-native-group-settled.log` loses focus after disabling bulk action; `09-group-action-focus-red.log`:2 failures →6 connected cases pass after all three individual/bulk handlers focus the closer. New grouped fixture explicitly settles maximum zoom before asserting group actions, matching the existing group fixture |
| Group action names identify action and target | Independent AX audit finds icon-only regeocode name and indistinguishable Details names; `09-action-name-red.log`:1 failure →5 connected cases pass14.97s. Names include action, shipment/delivery type, town and region, safely escaping quotes and markup |
| Filter selection and removed-tag focus | `09-filter-state-red.log`:1 failure → pressed false/true for region/period/price at creation/click/reset and focus on the matching deselected region after tag removal; canonical filter arrays unchanged |
| Error notification semantics | `09-toast-alert-red.log`:1 failure → error alert/assertive before content; normal status/polite restored. Six original Data Map lifecycle assertions remain unchanged; fake DOM adds setAttribute support only |

## Real Flask and Edge

Running checkout is the isolated `.scratch/balanced-ux-worktree`, branch
`feature/balanced-ux-redesign`, parent7361 plus the reviewed09 files. URL is
`http://127.0.0.1:5086`; Flask process6756 uses original checkout venv Python3.12.14.
Entry `.scratch/09_audit_server_retained.py.txt` executes the approved audit
server without overwriting its retained synthetic source at startup. Only safe
synthetic89 rows and12 destination coordinates are used; no private Pulse rows.
Node22.23.3, Edge155.0.4283.45 and locked scikit-learn1.4.0. Unique task profiles
and logs are retained. The user-authorized Node CDP fallback supplies actual
mouse/keyboard events; DOM fixture tests and evidence inspection are separately
labeled. This is automated functional evidence, not human screen-reader speech.

| Executed driver in `.scratch/` | Expected → observed |
| --- | --- |
| `09-revision-native-early-retained.mjs` | Actual revision ConnectionReset; unknown notice, zero new unsafe detail HTTP; successful check enables actual details |
| `09-native-cancel-final.mjs` |10 cases:8 held actual Flask Run/Compare responses across initial/refresh × success/error;2 cancelled revision checks. Native Cancel aborts, retains displayed identity, announces, restores focus; late responses do not change display/error; subsequent successful check recovers export |
| `09-native-legacy-keyboard-final-settled.mjs` | Native keyboard selector→popup→Escape; actual64 records ×9 fields match Records API;28 viewport/theme/root-size cases; ShiftTab/Tab scrolling region/close; named AX dialog/table; held old success/error cannot overwrite next town; real ConnectionReset→reopen; real empty filter result |
| `09-native-legacy-zoom125-final-settled.mjs` | Actual browser DPR1.2500000186; same legacy transitions plus12 desktop/theme/root-size layouts. Driver waits for actual target town and OpenLayers singleclick/autopan completion before strict mouse hit checks |
| `09-native-popup-font-green.mjs` |19 visible essential popup leaves, none below13px; source formatter tests independently verify both themes at16/32px root and period contrast≥4.5 |
| `09-native-legacy-status-verified.mjs` | Actual filtered counts2 shipments/12 deliveries/14 geocoded; search/tags/reset/empty/base layer/theme. Controlled status3/10→30%, done→hidden and exact regeocode town/region request; real external geocoder is deliberately not launched. Four rendered theme/root-size font checks have minimum13/26px |
| `09-native-group-focus-final.mjs` | Actual mouse and native keyboard open identical group HTML/count2; per-point actions and bulk membership retained; after disabling bulk action, focus moves to closer and Escape returns to opener. Controlled actual HTTP response copy adds one safe coincident point; source/coordinate files unchanged. OpenLayers member order is not asserted as a business order |
| `09-native-group-label-final.mjs` | Same actual mouse/keyboard/group/action/Escape replay after named-target fix; real full AX tree contains both action names with each town and region. AX capture is retained; no human speech claim |
| `09-native-alert-filter-final.mjs` | Actual AX pressed true/false for current/spot/tender; native tag removal restores region-button focus. Actual Points ConnectionReset appears as nonempty alert/assertive in DOM and AX, retry recovers actual map; other status/geocode/theme/font checks remain PASS |
| `09-export-native-lifecycle-final.mjs` |7 cancel groups, no late file/error; drill-up retains same-result export; real network error retries identical frozen payload; actual Page.navigate pagehide abort retained into new document, no late file |

Native screenshot: [record dialog1440px](09-after-1440.png). Source/coordinate
generation mutation, eviction, parent removal, source IDs, numerical oracles,
complete XLSX and unchanged output types retain the independently verified
[07](07-contextual-inspector.md) and [08](08-comparison-and-export.md) evidence;
changed exit/export transitions were replayed here. Full294-ID integration is10.

## Preservation and independent review

09 owns62 information obligations:9 STA,53 LEG; all56 LEG IDs are affected.
STA states use the controller tests/native revision/cancel evidence above plus
the retained typed stale/unavailable recovery tests. LEG shell/status/counts,
filters/search/tags/periods/types, popup values/periods/legend and records use
actual HTTP/DOM evidence above. Geocode running/done/progress uses explicitly
controlled transport, not a claim about a real worker. Cluster popup formatter
and mouse actions retain their existing code, extracted into a shared presentation
function. Keyboard selection also opens the actual current OpenLayers group when
coincident or inseparable at maximum zoom; its count, per-point details and bulk
regeocode event are available with Escape/return focus. Separable groups retain
individual point entry and the existing mouse zoom behavior.

Separate `/root/economics_spec` independently reconciled6 real HTTP filter cases,
47 point aggregates and526 record values plus unknown-town empty. CurrentSpot
synthetic00 has64 records: legacy price1079, route103.2, bids2, paired-valid
rate10.5 (68000/6500), independently distinct from Product weighted rate12.7272.
Oracle `.scratch/09_independent_legacy_values.py.txt` SHA256
`B55CA8D78E08297B42AC38B17D830C500BD1098CF2506C626E4C812C6ABD12F3`;
summary `09-independent-legacy-values.json`. Own data-processor2 tests pass.
The separate reviewer also executes both unchanged popup formatters against real
HTTP values:15 individual popups,19 period entries and15 grouped items. Town,
region/type, means/min/max/rates/counts/period labels and details identity match.
Oracle `.scratch/09_independent_popup_values.py.txt` SHA256
`1BE45934C191DC6539CF5A247D188CCFE2C37C97E2A67C2A23E635EE051F2565`;
summary `09-independent-popup-values.json`. Final label-delta replay is
`.scratch/09_independent_popup_values_final.py.txt`, SHA256
`5E61771C7EED2DEEEFC077322D3F5AEEC7F708477068D2A3D84983E7D18EDDD6`;
summary `09-independent-popup-values-final.json`, again15/19/15 PASS.
Individual formatter and all nine record-cell templates remain identical to
parent7361; grouped formatter differs only by escaped target-label declaration
and two accessibility attributes. Numerical fields/formulas/identity stay equal.

Independent `/root/foundation_spec` source Spec PASS and own42 cases pass.
Narrow inert popup MAJOR fixed/replayed with actual bundled OpenLayers;
hidden opener MINOR fixed/replayed, returning mobile controls. Pending revision,
explicit cancel and completion cleanup independently verified. Independent
`/root/economics_standards` Standards + targeted Ponytail source PASS; own24
recovery+9 neighbors,5 selector/font checks, final12 cancel/completion/uncertainty
checks. No unresolved source findings. Reviewer native evidence inspection is
not misrepresented as their native replay.

Final reviewed source SHA256: controller
`747F7A9A4137C50FADE0D69D89D7BEF6918103CD563FF5B32E9D3DD6CCE1E3BA`;
map `A45BF567ED084F789C20380A65DEE8C18578AD70438D88FBEBCDF4C841E38C28`;
tests `DCBBF8CA3742300C7BA2492033CA5EA31191D4F957328ADE30A497AC3656EBF6`.
Both reviewers independently pass the group extraction and final six action/focus
cases (Standards12.32s, Spec zero skips). Native group/action/focus PASS is above;
document/artifact closure is recorded with the final gates.

## Final gates and readiness

Final local required Quality PASS:136 frontend cases in403.75s and628 Python
cases in687.80s, including all49 recovery cases. Both nonempty JUnit files have
zero skipped/error/failure cases. Final-HEAD hosted Quality remains PENDING.
Ruff152 candidate Python files, pip check and unchanged Quality Node/Edge startup
PASS. First full attempts lacked browser/runtime access. The second run exposed
six deterministic old Data Map Node-fixture failures: its modal incorrectly
started open and its fake DOM lacked selector/event primitives. The fixture now
matches actual initial HTML and supports those primitives; all original six
business assertions remain unchanged, six PASS1.51s and independent six PASS0.90s.
Independent Standards verified the narrow fixture diff. Earlier logs are retained
and confirmed owned process trees were stopped. Full suites restarted after the
last test change. Final3 was superseded by the reviewed conditional group fix;
final4 by trailing whitespace cleanup; final5 by the native disabled-action focus
fix and stable fixture setup. Final6 executes all625 Python cases:623 pass and
two reduced-motion foundation pages produce no result before the existing helper
poll deadline. They fail before any product assertion; the exact two pass unchanged
in an independent14.87s repeat. Exact font/resource/scheduling cause remains
unproven. Full required Quality suites now run sequentially, avoiding duplicated
concurrent dashboard-browser coverage: original frontend contracts136, then all
remaining Python cases625 including every dashboard/recovery test. That run's artifacts
are `recovery09-final7-frontend.xml` and `recovery09-final7-python.xml`, with matching
unique basetemps/logs. No assertion or timeout was weakened, and no skipped or
failed mandatory case is accepted as PASS.

Final7 frontend136 PASS221.96s; its Python log also contains two foundation
no-result cases before the interrupted session ended. Repeated execution alone
did not establish readiness. Independent controlled CDP diagnostics retained in
`.scratch/std09_font_diagnostic.py` and `std09-font-diagnostic.{log,json}` show
held Google CSS requests blocking stylesheet readiness on both parent/current
CSS, and held font-file requests blocking fonts.ready. The exact network phase
of historical natural failures remains unobserved.

The foundation fixture now uses the existing layout-test pattern: strip only
the remote CSS import and append the unchanged remaining stylesheet directly;
force layout and await fonts.ready. All size, contrast, doubled text, media and
zero-transition assertions remain. Production font loading and global helper
timeouts are unchanged. Independent all four cases plus help neighbor PASS with
both font domains held; owner five PASS17.74s. Foundation SHA256
`B968B7D0200C4309533676736A9A20E531ABCEEBFCF7FCEF1972B0A5AC09B1F0`.
Native real Inter/JetBrains loaded-font observations are retained separately.
Final8 was superseded by the targeted filter/alert accessibility fixes. Renewed
sequential Quality9 PASS on these bytes:136 original frontend contracts and628
remaining Python cases, no skips. Final JUnit files are
`.scratch/recovery09-final9-frontend.xml` and `.scratch/recovery09-final9-python.xml`;
commands are the unchanged Quality frontend/Python commands with
REQUIRE_FRONTEND_BROWSER=1 and unique recovery09-final9 basetemps. Locked
dependencies are already satisfied using pip --no-index --no-deps against the
unchanged lockfile; pip check, Ruff152 candidates and unchanged Node/Edge startup
all PASS. Production Google Fonts loading remains unchanged.

Final app SHA256 `25ACD3D19984623236C183D0A1F306ADE311F3C8842DC447F42E1311D1E45118`;
filters `C24C0222AD970205DB28219927AB5B92BB0AE6E64D89AF4629B0EB8F93087255`;
recovery tests `DCBBF8CA3742300C7BA2492033CA5EA31191D4F957328ADE30A497AC3656EBF6`;
layout fixture `2405ECF4FD3EA5800499A2595674E09E486307260D526FC1633B8BF56E59D9BB`.
These supersede earlier incremental hashes. Independent Spec own rendered AX
closes group-name MAJOR/Details MINOR, selected-state/tag-focus and error-alert
MAJOR; own three tests pass. Remaining inspected LEG controls have meaningful
names, native state or disclosure aria-expanded; no additional material finding
in that targeted audit. Standards/Ponytail own final nine cases pass, no open
source finding. This does not claim a complete human WCAG/screen-reader audit.

All10 changed served assets independently match local source bytes after final
tests. Source CSV and Product coordinate bytes match their retained08 backups;
tracked private coordinate cache matches parent bytes and is excluded from the
explicit16-file publication allowlist. Only10 frontend files,3 test files,
CONTEXT, this report and one safe PNG are candidates. Local archive manifest,
reviewed staged-blob mapping and final-HEAD CI are checked before strict closure;
CI facts arriving after commit belong in the timestamped PR supplement.

The synthetic server was restored after the user resumed on15 October; current
Flask PID13960, same5086 URL/retained entry/source/coords. Earlier process6756
identifies historical native replays, not the current running process.

Human screen-reader/business walkthrough, native Excel layout acceptance and
production workload/operations remain UNVERIFIED. Existing XLSX long-header
clipping advisory from08 remains. No merge, Ready promotion or cleanup.
