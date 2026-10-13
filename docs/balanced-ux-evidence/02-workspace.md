# Balanced UX02 - persistent actions and responsive workspace

Accountable implementer and WL01-WL03 criterion owner: /root. Risk HIGH: view-exit
request ownership affects shared map/loading and saved result/cache publication.
Independent Spec and Standards plus targeted Ponytail. Task parent b07706f5f5613b5809fae83517016feb1a69dfc7,
original base4d21b54259c1a34a9d098a34aa518f447b411b65. Dependency01 and integration04
were VERIFIED on successful exact-head CI58/59 before this slice.

## Scope and expected/observed

WL01: one Calculate is associated with its original form using native form=,
while Calculate/Reset/current draft caption occupy a wrapping footer outside the
form scroller (min72px). Saved context is rendered once in the center, min64px,
independent of selected-inspector visibility. The map/table use70/30 remainder
with240/180px minima; the center scrolls vertically instead of dropping the table.

WL02: approved56px shell,12px padding/gap,280px controls and320px inspector.
Selected inspector docks atCSS>=1320, otherwise opens as an overlay; overview
has no docked inspector. Its previous overview metrics/list/export remain reachable
through Result pending05's summary extraction. Controls become a closed drawer
below1040. Native dialogs have entry/trap/inert/Escape/close/backdrop and return to
opener; previously inert values are restored, one panel owns presentation at a time.
Opening comparison closes a drawer; full comparison background modality remains
NEXT08/CX02 and receives no PASS from this ticket.

WL03 and owned LEG-shell-view/base-layer: actual Product/Data Map navigation,
legacy filters/Apply/Reset and base-layer keyboard selection work. Reentry retains
selected identity and issues no implicit clustering run. Hiding Product closes its
comparison presentation without clearing saved comparison results/cache or stealing
navigation focus. Existing Product cancellation guards suppress late run/compare
publication. Data Map cancels on replacement, view exit and Reset; request-local
abort/owner/view guards suppress late success/error and foreign loading cleanup.
Pending Product detail reads retain their existing frozen-cache/invalidation semantics;
this change does not claim cancellation of every detail request.
Old action IDs/handlers/catalog/config/API/export writer remain.
Backend/ml and economic formulas are unchanged.

Affected callers: index DOM, app navigation, controller init/show/hide/selection/
comparison/panel presentation, inspector render callbacks and table/map actions.
Panel sync is an optional existing-pattern renderer callback; standalone/stubbed
renderers retain their old contract. The backdrop has a static HTML ID. No new
framework/store/dependency, copied business state or generic configuration.
CURRENT CONTEXT documents the implemented layout; remaining summaries/details are
not claimed as complete. Fixtures are safe Product workspace and88-row synthetic
Flask input; tests and external-font evidence are distinguished below.

## Genuine failures and disposition

- Baseline rendered tests failed: actions were inside the form and context inside
  inspector; overview reserved an inspector and controls width320. Both failures
  became GREEN after structural/CSS changes.
- Independent Standards reproduced Compare remaining visible after hide -> Data Map.
  hide now closes presentation with restoreFocus=false; independent repeat plus
  regression passed, with saved result/results/cache/noRequests preserved.
- Independent Spec reproduced a narrow Data Map drawer as flex row: Apply85px.
  Common overlay column correction gave full279px filter area/Apply239px.
- Native narrow Data Map exposed the old grid selector outranking the breakpoint:
  map280px atviewport900. The explicit mode-data breakpoint now gives876px;
  independent focused/full native tests check full useful center width.
- Initial full suites caught new panel DOM work leaking into stubbed business
  renderers. Moving sync into the real renderer callback restored existing
  lifecycle tests without weaker assertions or artificial DOM implementations.
- An inactive CDP page deferred resize/media events and produced a focus failure;
  diagnostics showed no such events. Active-page replay (bringToFront/focus
  emulation) passed unchanged focus assertions. Presentation also tracks the
  previously focused panel and handles resize plus both media breakpoints.
- The layout fixture now removes only the existing external font import, preserving
  production CSS and testing deterministic fallback geometry. Actual loaded Inter/
  JetBrains Mono are independently observed in the real-server native runs.
- Genuine baseline Product run/compare view-exit RED replaced saved identity,
  grew caches and repainted the map after hide. Reusing cancelCalculation in hide
  made both GREEN; independent reviewers restored the old call in memory and
  reproduced RED. Tests preserve saved identity, UI, map and both cache contents.
- Baseline Data Map late success/error/replacement/Reset RED published old data,
  exposed an old error or cleared newer loading. Replacement failed even with an
  aborted signal. Local request ownership and central cancellation made four GREEN;
  active success and error/retry also pass, proving normal publication still works.
- Actual loaded-font form search fields also overflowed at normal text (266/263px):
  the older tagged selector outranked its width rule. A scoped width correction
  restores the intended margin-aware width; headings and preset wrapping retain
  all controls at 200% text without clipping fields.

## Runtime and live evidence

Checkout C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree;
branch feature/balanced-ux-redesign; URL http://127.0.0.1:5086.
Existing run.main via copied local audit_server.py; parent .venv Python3.12.14,
Node22.23.3 and installed Edge155. Input88 synthetic Pulse rows/12 destinations.
Listening PID25736 executes the existing venv/base interpreter via audit_server.py
--port5086 --no-browser. Final HTML/CSS/app/controller/inspector HTTP bytes equal
this checkout exactly; retained 02-final-served.json records hashes and URLs.
The local fixture now seeds a separate legacy-coords.json under task runtime:
legacy UI smoke had added synthetic entries to this worktree's tracked runtime
cache. Those generated bytes were retained with SHA manifest locally, and tracked
cache bytes restored exactly to HEAD. Original checkout/data were untouched; no
cache/profile/large runtime artifact is included in the publication allowlist.

Native active-page mouse/keyboard: six logical desktop/zoom viewports in both themes;
Calculate outside scroll, saved context, all14 columns, panel Tab/ShiftTab/Escape,
background inert/return, ID0 docking and resize focus. Actual125% browser zoom
(DPR1.25), three device sizes in both themes, separately checked using new owned
profiles; no user browser preference changed. Also200% text, reflow320, legacy
Apply/Reset/base layer and Product selected reentry/no implicit run. Earlier named
logs/captures are preserved; latest final-source runtime repetition is recorded in
local 02-native-race-final.log and 02-zoom125-final-confirmed.log. The former
holds an actual Flask Data Map response after parsing it, navigates via native
mouse back to Product, then releases the late response: signal aborted, legacy
info remains hidden, and a Product loading sentinel stays untouched. The sentinel
is fixture instrumentation, not a claim that a business calculation was running.
The first fresh zoom profile was 100%; its setup assertion failed and was retained.
A new isolated profile explicitly seeded 125% before startup, then passed at DPR1.25.

Existing lifecycle oracles retain loading/cache/reentry/form-vs-frozen/stale/retry/
cancel/late-response coverage. New panel tests assert exact saved object, UI sort/
selection and request count preservation. No export/download meaning was changed;
actual disk workbook completeness belongs08. No new business metric oracle needed:
04's independent numerical guards and unchanged backend/ml apply.

## Review, gates and readiness

Independent Spec /root/foundation_spec reproduced/corrected Data Map geometry,
ran16 focused cases/zero skips and inspected native matrix/actual125 drivers,
logs and screenshots. Scoped WL01-WL03 PASS; initial footer height observation was
fixed by explicit row direction while retaining wrapping.
Independent Standards /root/economics_standards inspected ownership/callback,
inert restoration/resize/media, deterministic fixture loading and original business
assertions, independently replayed focus/navigation regressions and closed its
MAJOR navigation finding. Both reviewers independently reproduced Product and
reverse Data Map late-publication RED and replayed current GREEN. Spec six active/
late/retry Node cases and two Product cache cases PASS; Standards independently
replayed four reverse cases, positive error/retry and two strengthened Product cases.
Standards also supplies the targeted Ponytail HIGH axis. Source-scope PASS;
final delivery gates remain required. Final file/commit mapping is recorded in
PR supplement after publication; no self-review substitutes those checks.

Full renewed mandatory local gates, startup/served bytes and exact-head hosted CI
must be completed on final production/test bytes before VERIFIED. Final results
are added from execution, not inferred from earlier passes. Human acceptance,
production readiness and full294-ID integration are UNVERIFIED. No main merge,
Draft promotion, automatic merge or cleanup is authorized.

Compact visual comparison: [foundation before](screenshots/01-after-1440.png) and
[workspace after](screenshots/02-after-1440.png),1440x900/100%, synthetic data only.
External tile availability varies; no basemap quality improvement is inferred.
Local bulky evidence: layout02-high-final-manifest.json lists retained final driver/
log/served-byte/test/screenshot hashes; earlier manifests remain historical evidence.
Final candidate full local frontend175 PASS in311.92s/zero skips (136 existing
contracts, five foundation and34 layout/transition cases); XML checked for no
skipped test cases. Full local Python503 PASS in122.06s/zero skips; dependency,
Ruff and unchanged Node/Edge startup checks PASS. Independent final Spec and
Standards plus targeted Ponytail source/evidence review PASS; no unresolved
material finding. Exact-head hosted CI remains pending publication.

Final visual reflow regression: at200% text the parameter form initially had
scrollWidth401 vsclient263 (genuine RED). Scoped wrapping headings/badges and
relative preset grid now preserve all five mode controls without horizontal form
scroll at normal/200% sizes (ten cases). Native loaded-font assertions are repeated
on this final CSS; no clipping/hidden-field workaround was used.
