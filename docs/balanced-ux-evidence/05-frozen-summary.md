# Balanced UX05 — frozen summary and data quality

Accountable implementer and SR-01–SR-03 owner /root; risk HIGH for frozen
identity, metric populations and missing values. Parent
e5123ee6d79ef193ee22fab2ffb68364d553a413; dependencies02/03/04 VERIFIED with
exact-head hosted Quality60/61/59. Independent Spec, Standards plus targeted
Ponytail, and a separate numerical oracle reviewer.

## Behavior and owned information

Existing result/context/quality/metric IDs moved into a central saved-result
summary. The selected inspector, table, map, export and comparison retain their
existing readers and actions. One native disclosure opens all technical metrics;
each help button exposes its own formula/population. A sticky central action row
keeps panel actions reachable while the larger summary scrolls. Map/table minima
remain240/180px; no summary height cap hides content.

| Owned IDs | Access, expected and observed |
| --- | --- |
| FRZ-frozen-request, FRZ-selection-intent, FRZ-origins, FRZ-origin-coverage-zero-match, FRZ-source | Saved mode/parameters/four filters, region, Pulse label and saved origins render from analysis; frozen_request takes precedence over fallback fields. All retains its full named FIAS set in a disclosure and zero-match names remain visible. Draft edits do not change saved context or numbers. |
| FRZ-data-snapshot, FRZ-stale, FRZ-rejected-snapshot, FRZ-unavailable-result | Existing saved snapshot/cache identity retained, without exposing raw JSON as a KPI. Draft change, source/coordinate rejection and eviction have separate notices; existing detail/export guards remain authoritative. Failed refresh keeps the saved values; retry replaces them only on success. |
| SUM-analysis-mode, SUM-analysis-parameters-n-clusters, SUM-points-with-lat, SUM-trip-count-total, SUM-outliers-length | Saved mode, actual chosen K, existing lat-not-null population and outlier count retained. Machines use saved data_quality.trip_count_total, including unresolved destinations, rather than summed assigned clusters. |
| SUM-bear-zone-count, SUM-singleton-count, SUM-status, SUM-warnings | Actual cluster-type zone/singleton counts; candidates and covered points/machines retain saved values. Both no_bears modes are normal success-empty. Invalid connectedness, including nonzero violations with success status, remains visible outside analytics. Warning text is escaped. |
| QLT-resolved-points, QLT-destination-points-total, QLT-point-coverage-pct | Resolved/all destinations and saved data_quality point coverage. Algorithm-assignment coverage is a different population and never substitutes for it. |
| QLT-trip-count-resolved, QLT-trip-count-total, QLT-trip-weight-coverage-pct, QLT-economic-valid-points, QLT-excluded-missing-fias | Resolved/all machines, saved machine coverage, economic-valid/resolved points, excluded source rows. Nearby help explains each denominator. Unknown values render an em dash; real zero remains numeric zero. |
| MET-silhouette, MET-mean-distance-to-medoid-m, MET-p95-distance-to-medoid-m, MET-calinski-harabasz, MET-davies-bouldin | One analytics disclosure exposes all applicable values and individual definitions. Assigned-point unweighted projected distances convert meters to km; P95 uses linear interpolation. Silhouette includes singleton0; CH/DB mention installed sklearn degenerate conventions. |
| MET-within-cluster-weighted-rubkm-mad, MET-regional-weighted-rub-per-km | Existing algorithm rate MAD uses point total-machine weights then cluster-machine weights; regional mode-input baseline retains its original population. These are not a new canonical global mean or budget. |
| MET-within-cluster-trip-count-mad, MET-between-cluster-mean-trip-spread, MET-regional-volume-mean-trip-count-per-point | Existing assigned-point unweighted volume MAD, max-minus-min cluster means and regional mode-input mean including eligible unassigned points. |
| MET-candidate-count, MET-covered-point-count, MET-covered-trip-count | Saved candidate count and covered membership/machines, with mode-specific help and unavailable-versus-zero handling. |
| MET-graph-node-count, MET-graph-edge-count, MET-graph-graph-component-count, MET-graph-connectivity-violations | Saved graph populations/counts, disconnected cluster count and individual definitions; no second nested disclosure. |

These43 owned IDs are scoped preservation checks. Full294 integration acceptance
belongs to ticket10. No API/backend/ML/config/catalog/export writer changes,
new store, dependency, invented budget or global canonical economic mean.
General silhouette/CH/DB definitions were checked against the
[official sklearn1.4 documentation](https://scikit-learn.org/1.4/modules/clustering.html);
repository algorithms and installed1.4.0 source determine actual populations.

## Genuine RED → GREEN and independent oracle

Baseline failures: saved quality remained in the inspector; missing counts and
meters became numeric zero; saved parameters were absent from context. Initial
candidate failures: diagnostics required two opens; null parameters produced
NaN; central scrolling hid panel actions. Fixed by existing-ID relocation,
local null guards, frozen parameters, one disclosure and sticky actions.
Repeated unchanged saved-status renders replaced the live-region node;
conditional markup replacement and a polite status role preserve the node.
Independent Spec and Standards also reproduced quoted error text replacing the
same paragraph because DOM serialization normalizes quotes. Genuine regression
RED then GREEN: compare the exact DOM-local assigned markup string, preserving
escaping of quotes, apostrophes, ampersands and literal input-like text.
Setup mistakes (a wrong expected null-distance suffix and shell text encoding)
were not product RED. Earlier failed logs/profiles remain archived.

Independent real Flask oracle: four destinations carry10/10/40/50 machines;
only the first two resolve, only the first has valid economics. Expected and
observed:2/4 points50%,20/110 machines18.1818%, economics1/2; two singleton
clusters total20 machines but the summary must show110. Algorithm coverage100%
does not replace data-quality50%. Real zero medoid distances remain0;
silhouette/CH/DB unavailable remain missing. Both Bear modes return HTTP200
no_bears with zero coverage. Separate Bear hand oracles verify zone/singleton
counts and baselines: Cost7200/66=109.090909 and10300/101=101.980198;
Volume25 and40, with covered points/machines2/6,1/1,2/80,1/100 respectively.
Durable existing API/Bear tests and the19 summary tests reproduce the safe
public-seam assertions; the independent oracle script and JSON are retained
locally under .scratch/summary05-independent-oracle/ and
.scratch/summary05_independent_oracle.py.

## Runtime evidence and gates

Isolated feature/balanced-ux-redesign checkout:
C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree.
Existing run.main via task-local audit_server.py, http://127.0.0.1:5086,
PID11092; Python3.12.14, Node22.23.3, Edge155, locked sklearn1.4.0.
Safe synthetic88 Pulse rows/12 destinations, then89 after the deliberate
task-only source-change replay; both Product and legacy coordinates
stay inside the owned runtime. Private inputs and original checkout preserved.

Native five actual Flask requests verify rendered quality/machine totals against
each response; both Bear modes exercised. Mouse/keyboard disclosures and help,
All/manual restoration, invalid Compare repair, frozen edits, failed refresh,
successful retry and eviction notices passed. A real task-only source append,
failed refresh and retry also preserve old values, show the distinct rejected
snapshot cause and publish fresh values only after success. Before-change CSV
bytes are retained locally. K/region setup assigns values with
dispatched change; it is not native typing evidence. Controlled browser response
fixtures cover critical connectivity warnings and the distinct rejection cause;
they do not establish a newly reproduced backend connectivity defect.

Both-theme normal six-viewport, text200%,320px reflow and Data Map apply/reset/
base-layer/reentry/held-late-response matrix PASS; actual125% three-device matrix
PASS. Larger summary uses center scrolling. Existing selected-inspector overflow
at text200% remains a later07/09 integration obligation; this is not a full
accessibility or human acceptance claim.

Native logs/drivers/screenshots stay in .scratch/balanced-foundation/ with unique
05 prefixes; 05-final-served.json verifies exact HTML/CSS/controller/inspector
served bytes and summary05-final-manifest.json hashes11 retained artifacts.
[After](screenshots/05-after-1440.png) shows the safe fresh190-machine scene
after the deliberate source append and successful retry. A residual hidden
form error is absent from rendered output; raw observations retain its text.
Independent Spec /root/foundation_spec SR01–03/43IDs source/content PASS:
own19 summary cases plus a separate current strengthened quoted-status replay.
Independent Standards plus targeted Ponytail /root/economics_standards PASS,
including its own quoted regression. Reviewed inspector SHA256
0a50b52d5277ee848b90970d25996a316ef793ac01c0fa1a2997bdff3ffa866b
and tests97b6bbf2be98232636bea5d721bdd7be0b80e02922f005cac4a062abe7c152a4.
No unresolved material finding. Numerical reviewer /root/economics_spec independently
executed62 API/Bear/neighbor cases and checked installed formula sources;
this is numerical/source evidence rather than DOM or full-gate approval.
Full Ruff initially included an unpublished local independent-oracle scratch
script and reported its formatting errors; all published source passes Ruff
with task scratch excluded. Hosted full Ruff remains unchanged and mandatory.
Dependencies and unchanged Node/real Edge startup PASS.
Final Python537 PASS in197.25s, zero skipped/error/failure cases; JUnit inspected.
Final frontend209 PASS in401.63s, zero skipped/error/failure cases; JUnit inspected.
Successful exact-head hosted Quality remains pending publication. Independent
reviewed-byte to staged-blob mapping permits only Git LF normalization;
summary05-reviewed-staged-map.json retains the exact mapping.
Functional full-feature acceptance, human
acceptance and production readiness remain UNVERIFIED. Draft PR stays unmerged;
main merge, promotion and cleanup require later authorization.
