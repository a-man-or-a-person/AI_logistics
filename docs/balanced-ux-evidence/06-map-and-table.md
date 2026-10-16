# Balanced UX06 — map and all fourteen columns

Accountable implementer and MT01–03 owner /root. Risk MEDIUM presentation,
with independent Spec and Standards plus targeted Ponytail for connected
render/focus boundaries. Parent e56a35b858aaf6e095d7ecee30bd63d1ccb7e8b7;
05 exact-head Quality62 SUCCESS before edits; dependencies01/02/04 verified.
Original base4d21b54259c1a34a9d098a34aa518f447b411b65, isolated
feature/balanced-ux-redesign. No backend/API/metric/catalog/config/state/export
writer changes; existing numerical compatibility guards remain binding.

## Owned preservation and behavior

| Owned IDs | Expected and observed access / oracle |
| --- | --- |
| TBL-cluster-id, TBL-point-count, TBL-trip-count, TBL-trip-share | Four original columns/keys/labels/counts and assigned-machine share retained. Sticky identity/header, raw0 selected identity and default trip_count descending; all14 keys sort both directions, missing last and raw cluster_id ascending ties. |
| TBL-weighted-route-length, TBL-price-min, TBL-price-median, TBL-price-weighted, TBL-price-max, TBL-rub-per-km-min, TBL-rub-per-km-median, TBL-rub-per-km-weighted, TBL-rub-per-km-max, TBL-economic-coverage | Ten original values/labels/formulas retained. Destination-mean min/median/max stay unweighted, even median stays the two central means; weighted metrics use their own valid machines. Cell help exposes unrounded saved value/unit and its coverage; displayed rounding never becomes the sort source. Missing count/value stays unavailable, numeric0 stays0. |
| COV-coverage-route-length-valid-points, COV-coverage-route-length-total-points, COV-coverage-route-length-valid-trip-count, COV-coverage-route-length-total-trip-count | Route cell's accessible help exposes exact saved route-valid/all points and machines. Fixture2/5 points and20/110 machines. |
| COV-coverage-price-valid-points, COV-coverage-price-total-points, COV-coverage-price-valid-trip-count, COV-coverage-price-total-trip-count | Each price cell uses its saved price coverage, fixture3/5 and30/110. Never uses route/rate or total-machine weights as its denominator. |
| COV-coverage-rub-per-km-valid-points, COV-coverage-rub-per-km-total-points, COV-coverage-rub-per-km-valid-trip-count, COV-coverage-rub-per-km-total-trip-count | Each rate cell uses its saved rate coverage, fixture2/5 and20/110. Header retains row-level rate-before-weighting definition; no ratio of mean price and mean distance. |
| COV-economic-coverage-valid-points, COV-economic-coverage-total-points, COV-economic-coverage-valid-trip-count, COV-economic-coverage-total-trip-count | Saved economic coverage preserves both populations and existing conditional price-versus-rate title. Unknown numerator is unavailable in display and raw sorting; true zero remains a numeric zero. |
| TST-table-sort, TST-table-open, TST-selected-hovered-cluster | Native sort/toggle/identity focus retained after DOM replacement, including0. Collapse/reopen restores horizontal and vertical local offsets. Help click opens its tooltip without selecting the row; row button still selects map/table/inspector together. |
| TST-period-types, TST-methodology-distributions, TST-methodology-weighted-values, TST-missing-values | Existing period chips, header formulas and methodology text retained. Methodology disclosure has its own bounded scroll; actual header/content layout accommodates text growth without a fixed52px subtraction. |
| TST-supported, TST-table-error-empty | Both saved Bear modes show an explicit unsupported ordinary-table reason, with no fabricated rows. Supported empty/error branches remain distinct. No ordinary export support is added to Bear. |
| MAP-points, MAP-labels, MAP-centers, MAP-outliers, MAP-candidates | Existing points-only renderer, labels/medoid, center marks, outliers and Bear candidates/layers preserved. Actual OpenLayers regression proves selecting/hovering0 does not highlight a null-cluster outlier or include it in the fitted member extent. |
| MAP-base-layer, MAP-legend | Existing usable basemap and separate Data Map legend retained; no Product polygon/hub meaning introduced. Existing Data Map/navigation contracts and native layer evidence remain separate from Product membership proof. |

These46 owned IDs are scoped checks. Full294 integration remains ticket10.
DOM-local scroll offsets belong to presentation and are cleared when no supported
table remains; no new saved-result store/cache or snapshot key. Re-rendered
keyboard controls restore their matching raw identity with preventScroll.
Existing header help interaction/escaping/top-layer placement is reused for
value help. Fine targets remain24px and coarse targets44px.

## Genuine RED → GREEN and independent checks

Unchanged baseline browser RED: sort focus moved to BODY, collapse reset160/90
scroll offsets to0/0, identity scrolled out, values lacked precision/population
help, unsupported Bear panel silently disappeared, and real OpenLayers treated
null as cluster0 for highlighting/fitted extent. Small renderer/CSS/map fixes
make these GREEN through the existing browser and real bundled OpenLayers seam.

All14 raw-key oracle uses near-equal values2.00004/2.00003 that round together,
ties and a missing value. Expected ascending IDs1,2,0,3 and descending0,1,2,3;
identity itself sorts0,1,2,3 /3,2,1,0. Missing economic numerator originally
coerced to0 during division; raw-value guard restores unavailable-last sorting.
This deliberately missing frontend fixture is not a claim that the current
backend emits null valid-machine counts.

Independent reviewers reproduced missing coverage as0% despite unavailable
help (MAJOR), and keyboard toggle/row activation losing focus (MINOR). Owner
regressions reproduce RED then GREEN: numerator guards, null-safe exact titles
and focused-control restoration. Both reviewers independently repeated fixes.
Native strict hit testing also failed: the first value help lay behind the
88px sticky identity and58px header after scrolling. Scaled scroll padding and
a text-sensitive minimum preserve the180px lower bound and make native access
GREEN. At text200%, a fixed52px header subtraction left20px content overflow;
the final flex layout uses actual header height, and methodology scrolls locally.
The05 minimum-height oracle now checks the approved >=180px lower bound rather
than forbidding this required text-growth accommodation.

13 focused table cases cover the failures plus14 raw keys, distinct coverage,
missing/zero and expanded methodology. Existing numerical expected values are
unchanged: an existing visible-cell test uses innerText to exclude new hidden
tooltip prose. Existing all-help clipping checks expand from12 to24 targets
for their deliberately coverage-missing one-row fixture; real rows expose25.
Existing Bear test now expects the approved visible reason and no tooltips/rows.
72 Product table/Bear/medoid/XLSX API/economic guard neighbors PASS; this is API
evidence, not the actual downloaded/reopened workbook required in ticket08.

## Runtime, review and gates

Task checkout C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree,
existing run.main via local audit_server.py, http://127.0.0.1:5086, PID11092.
Python3.12.14, Node22.23.3, Edge155, locked sklearn1.4.0. Safe synthetic89 Pulse
rows/12 destinations, retained after the explicit05 source-change replay.
Both Product and legacy coordinates stay in the task runtime; tracked cache
and original private inputs remain byte-preserved.

Native actual five-mode responses, all14 sort keys in both directions/focus,
12 formula helps plus13 first-row value helps/Escape/viewport bounds, normal
both-theme six-viewports, actual125% both-theme three-device sizes, text200%
and320px reflow are recorded in unique06 drivers/logs/screenshots. Product
layer checkbox/restoration, both Bear reasons/candidates and raw0 selection
have a separate native replay. Region/K setup uses dispatched changes, not
native typing. Basemap screenshots prove the tested scene, not tile-provider
availability at other times. Failed local driver selector quoting is setup
failure, separate from genuine strict native-hit and layout failures.

Independent Spec /root/foundation_spec and Standards/targeted Ponytail
/root/economics_standards approve the source fixes within their stated scopes.
Final flex-layout source/content Spec and Standards/Ponytail PASS. Spec independently
ran13 cases plus the affected summary neighbor; Standards independently removed
the last CSS fix in memory and reproduced overflow20/unscrollable methodology RED,
then current GREEN. Reviewed CSS6cd7d9870aed65f1e094a83d8f94e2f345e6e8f28815a6ed21920bfa991f8cb6
and testsf55c3675182c0e19293632217f6b6b3f024c193d4a65279b50c93efd32cad205.
Final Python550 PASS in274.89s, JUnit zero skipped/error/failure inspected;
dependencies,149 published candidate Python files Ruff, unchanged Node/real Edge
startup PASS. Five HTML/CSS/table/map/controller served assets match checkout
bytes in06-final-served.json; listening process remains11092.

Native real wheel/collapse/Enter reopen preserves both observed offsets exactly:
160px horizontal and85.599998px vertical. Final real125% both-theme matrix and
Product layers/Bear explanations/cluster0 selection PASS. Fresh-profile normal
renewal PASS for both-theme six viewports plus all14 sort/25-help text200% and
320px reflow; final table overflow is0 in both enlarged/narrow observations.
After interruption, frontend execution ended221PASS/one process
timeout; the isolated unchanged case repeated PASS in5.73s. Full frontend is
renewed without changing source or timeout limits. A native compositor screenshot
stalled after successful1440 interactions; the owned Node/browser was interrupted,
with profile/logs preserved. Fresh-profile replay uses view capture for bulky
intermediate images; those display-sized/dimmed captures are not visual acceptance
evidence. The correct final-source [1366px screenshot](screenshots/06-after-1366.png)
uses the earlier successful compositor capture and shows local scroll/sticky identity.

Final repeated frontend222 PASS in479.80s; JUnit zero skipped/error/failure
inspected. table06-runtime-manifest.json retains17 stable final-source drivers,
logs, observations, served hashes, safe screenshot, table tests and both JUnit
records locally. Successful exact-head hosted Quality remains pending publication.
Earlier runs interrupted/superseded by the proven text-growth fix
are retained and not credited as final gates. Final numerical semantics/API keys,
saved/export identity and all14 columns remain unchanged.

Full functional integration, human acceptance and production readiness remain
UNVERIFIED; Draft PR stays open/unmerged. Merge/promotion/cleanup require later
authorization. Existing selected-inspector text200% limitations remain07/09;
this table slice does not assert full accessibility acceptance.
