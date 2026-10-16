# D-06 independent Standards and targeted Ponytail review

Reviewer: `/root/sidebar_standards`, independent of implementer. Reviewed on
16 October 2026 in `.scratch/balanced-ux-worktree`, branch
`feature/balanced-ux-redesign`, remote
`https://github.com/a-man-or-a-person/AI_logistics.git`. Base and working HEAD:
`cab287ff62840fc7b8de615f6e567330130899e1`; candidate was uncommitted. Hashes below
pin the inspected candidate rather than claiming review of a future commit.

What this change does: moves the existing saved overview into the permanent
desktop inspector, retains the existing drawer below 1320px, and compacts the
frozen context above the map. Business readers and transport stay in their
existing modules.

## Scope and independent checks

Read the user task, Workflow v2, domain/issue discovery, Product contract and
workflow, CURRENT context/architecture, D-06, changed HTML/CSS/controller/tests,
and connected inspector, selection, table, panel/focus and export paths. Reviewed
only affected boundaries; did not replay the unchanged 294 obligations.

Own commands: `git diff -- frontend/index.html frontend/css/style.css
frontend/js/clustering/controller.js`, changed-test/doc diffs, caller searches,
`Get-FileHash -Algorithm SHA256`, `git diff --check`, and narrow real Edge browser
execution through `_run_browser_script(_table_script(...))`. Interpreter:
`C:/folder/Python/AI_logistics_clean/.venv/Scripts/python.exe`; viewport 1440x900,
reduced motion. First command quoting and missing-cluster fixture attempts were
setup failures; they are not behavioral evidence.

Independently read the before/after geometry JSON and viewed
`after-overview-1440.png` in `.scratch/sidebar-20261016`. Recalculation gives map
area gains of 51.9%, 41.5%, 38.8% at 1366x768, 1440x900, 1920x1080 respectively;
125% emulated viewport gains are 3429.4%, 174.5%, 37.6%. This is inspection of
owner-produced geometry, not independent acquisition or native browser zoom.

## Standards axis

No BLOCKER/MAJOR architecture or ownership violation found in the inspected
production diff. IDs move once; the existing renderer still owns business
readers; backend, formulas and writer remain untouched. Existing drawer inert,
focus trap and breakpoint behavior are reused rather than duplicated. Workflow
additions retain mandatory gates and require evidence before speculative CI fixes.

MINOR documentation correction requested: the changed CURRENT Product workflow
still calls mobile controls a bottom-sheet, whereas the existing
`.workspace .control-panel.panel-overlay` is a fixed left drawer. Owner notified;
update this description to match the actual UI.

Recommendation: architecture/maintainability PASS within inspected scope;
overall delivery awaits the finding below and required owner gates.

## Ponytail axis

1. **MAJOR — selecting a cluster below expanded analytics leaves its new details
   above the visible sidebar.** The persistent overview puts the cluster list
   after analytics. `selectCluster()` rerenders newly selected details before the
   overview without revealing them. This breaks the newly affected selection and
   native focus/scroll transition required by Workflow v2.

   Own reproducer uses `_table_script` and injects
   `result.clusters=[{cluster_id:0,point_count:1,trip_count:40,point_ids:['x']}]`,
   sets `result.points[0].cluster_id=0`, calls `workspace.show()`, opens
   `.result-diagnostics`, scrolls `#clustering-inspector` to `scrollHeight`, then
   clicks `#cluster-list [data-cluster-id]`. Observed selected cluster 0,
   scrollTop 512 → 1025; `#cluster-details-close` top −860 versus panel top 68,
   hence selected details/back action are invisible. Collapsed-diagnostics
   control: scrollTop 32 → 32 and details visible. The renderer's insertion and
   browser scroll anchoring make the expanded transition fail.

   Smallest fix: reveal the selected detail on the selection transition and
   preserve usable keyboard focus; add this specific regression. No new panel
   framework is needed. Owner notified before final gate completion.

Verdict: fix finding 1 before shipping. No unnecessary dependency, abstraction,
duplicated reader or business reinterpretation found.

## Reviewed source SHA256

| File | Hash |
|---|---|
| `frontend/index.html` | `ACE8A119BFD513E32A2394E1911C9B644D1FFB4C5BDE652667C170385E827176` |
| `frontend/css/style.css` | `2311531FF82C9FD23D705E7547B980B148902E7C34184D3D9289655488FCD585` |
| `frontend/js/clustering/controller.js` | `8DCCEE349D6267E9B02ACBF1819F6326D5FB9EA779CDA11D6DB5D032E9E30839` |
| `tests/test_dashboard_layout.py` | `160CAA9F2A95EE50AAADBB6998944C9270AE97D79ECF670DA2C476443A4C6380` |
| `tests/test_dashboard_summary.py` | `7FFBF7CD97D60F106C7FA64484CA3326787AB5215393E6C14E76C173329BD1E0` |

Not checked: broad suites, independent full numerical/XLSX oracle, actual native
Edge mouse/keyboard or 125% browser zoom, hosted CI and final served revision.
Human acceptance and production readiness remain UNVERIFIED; this report cannot
promote them. Runtime cache/private data are outside the publication allowlist.

## Fix disposition and independent repeat-check

Both findings above are resolved in the final inspected working candidate.
The CURRENT Product workflow now describes the right analytics drawer and left
controls drawer correctly. `selectCluster` and `selectPoint` now reset inspector
scroll only for a non-null selection, after rendering, leaving ordinary renderer
refresh and drill-up return behavior in their existing owners. This is two small
lines at the existing selection seams, without a new abstraction.

Independently repeated the expanded-diagnostics reproducer on the final guarded
source, additionally checking point selection and ordinary rerender preservation:
observed `{before:512, cluster:true, kept:true, point:true, scroll:0}`. `cluster`
and `point` mean their back controls lie fully inside inspector bounds; `kept`
means `workspace.show()` preserves a user-set scrollTop of 100. Assertions passed.
The new focused regression was inspected; owner RED/GREEN is separately recorded
by the implementer. `git diff --check` passed; runtime coordinate-cache line-ending
warning does not belong to this review's publication scope.

Final changed hashes supersede corresponding initial rows above:

| File | SHA256 |
|---|---|
| `frontend/js/clustering/controller.js` | `379B0D4266D5E5FA81A91E6CE853DD1E0F940994D3046C6D05C28F9B2DBABE95` |
| `tests/test_dashboard_layout.py` | `7399602C80994DF6061550E391A2D3AAF4FA4126863B7E6E607490C75E92AE0B` |
| `docs/clustering_product_v1_workflow.md` | `31E1D7DF570E3EFC6244036ACACF5DF5F13A12B7316ACA9B41E6F83367FC4D3F` |

Final verdict: **Standards PASS; targeted Ponytail PASS**, no open findings in
the reviewed scope. Required final local/hosted checks, served-revision proof,
human acceptance and production readiness remain outside this verdict.

### Final drill-up follow-up

The independent Spec review identified an additional reverse-transition case:
restored cluster focus could remain below the visible overview. Inspected the
two-line correction: point/cluster close handlers now use native `.focus()` on
the existing parent rather than `.focus({preventScroll:true})`. Native focus
reveals that parent without introducing new scroll tracking; the null-selection
guards above remain. Inspected the extended focused regression.

Own final repeat uses eight clusters, expanded diagnostics, last-cluster
selection, point selection, point return and cluster return. Real Edge observed
`{cluster:true, point:true, kept:true, pointReturn:true, clusterReturn:true}`;
all assertions passed. Both return flags require the correct focused parent to
lie fully within inspector bounds. This supplements, rather than replaces, the
initial RED observation and previous forward-transition checks.

Final frozen production/test hashes supersede the corresponding previous rows:

| File | SHA256 |
|---|---|
| `frontend/js/clustering/controller.js` | `6EF160CEDF36768FA374ECEA6452FDF1CD4051D6D0A585BBF06F0A73262CF40B` |
| `tests/test_dashboard_layout.py` | `72E2C15B7439F824D1E305916DF9A8CB98B8B764DEA4A66B089E6E7B6B97D9AF` |

Verdict remains **Standards PASS; targeted Ponytail PASS** for this final scope.
No broad suites were duplicated; native acceptance and final CI are still not
claimed by this independent review.

### Text-size grid refinement

Inspected the last CSS change to
`repeat(auto-fit,minmax(min(100%,7rem),1fr))`. It reuses the existing responsive
grid pattern so the narrow inspector can use one column when text doubles.
Independent narrow Edge execution on the final CSS confirmed, at 1440x900:
root 16px → columns `133px 133px`, scroll/client width 278/278; root 32px → one
column `268px`, scroll/client width 268/268. Assertions for column count and no
quality-grid horizontal overflow passed. The earlier 200% screenshot was
inspected as the reason for this refinement, not claimed as final-source proof.

Final CSS SHA256: `6EE8AF69F50D2EB43EADAAC1EA02327F5F5F998A01BAFBAB071977AD858C35F2`,
superseding the initial CSS hash. Standards and targeted Ponytail remain PASS
within scope; final mandatory gates remain the implementer's responsibility.
