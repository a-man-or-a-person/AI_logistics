# D-07 independent Spec review — 16 October 2026

Reviewer `/root/sidebar_spec`, independent production-read-only review. Base `a843a2ab4d23c16f8a53d579e1e5be70288c8a9d`; reviewed the uncommitted D-07 implementation against the attached FINAL WORKSPACE CLEANUP request. Working-tree review; final commit/CI binding remains pending.

## Findings and disposition

- **MAJOR — doubled text leaves newly selected details below the visible inspector.** Task requires preservation of overview→cluster→point and 200% text behavior. Independent actual Edge at 1440×900, root font32px, 20 long saved Union origins: click cluster after scrolling its overview card into view. Back rectangle y860–900 exceeds panel y68–888; heading/details are below it. `selectCluster` still resets sidebar to0 while moved `#result-context` precedes details. Even the collapsed context is too tall (`details.open=false` after rendering). Reveal the selected section beneath the sticky comparison controls rather than resetting blindly to0; retain unrelated refresh scroll.
- **MINOR — Escape exits both comparison and its parent result drawer.** Narrow900×720 replay: drawer→Compare→Escape produces `{focus:'mobile-inspector-btn',compareVisible:false,panelOpen:false,comparisonOpen:false}`. Closing comparison with its button instead restores the open drawer and Compare button. Global Escape handler calls `closeComparison()` then `closePanel()`, immediately closing the drawer restored by the former. Consume this Escape after closing its top layer, retaining existing origin-options Escape priority.
- **MINOR, RESOLVED by implementer source change:** deleting methodology CSS left a dangling `.mode-cluster` before the next selector, preventing the ordinary value-help rule from matching. Implementer removed the residue. Initial suspicion of unused MODE_LABELS was retracted: unsupported Bear mode rendering still uses it.

## Independent checks

Read full task, affected HTML/CSS/controller/inspector/table paths, comparison close/open and keydown handlers, context rendering and new focused regressions. `REQUIRE_FRONTEND_BROWSER=1 python -m pytest -q -o addopts= -p no:cacheprovider tests/test_dashboard_workspace_cleanup.py` under escalated Edge: **7 passed in56.17s**, zero skips. Independently replayed the two uncovered cases above through `_table_script` and actual Edge DOM rectangles/focus. Desktop toolbar removal, right-only context, methodology UI deletion, retained fourteen columns/helps and moved Compare placement conform by source inspection. API/business definitions remain unchanged.

Verdict pending fixes: **changes requested**. Full suites, hosted final-HEAD CI, native zoom/text-size UI and human visual acceptance were not independently executed. Root-font32px is rendered doubled-text evidence, not native zoom UI evidence.

## Final independent replay — 16 October 2026

Reviewer `/root/d07_spec_final`; independent Spec follow-up, accountable implementer `/root`. Risk: frontend interaction/presentation (MEDIUM); saved-result/API mathematics remain frozen. Verified checkout `C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`, origin `https://github.com/a-man-or-a-person/AI_logistics.git`, branch `feature/balanced-ux-redesign`, base/HEAD `a843a2ab4d23c16f8a53d579e1e5be70288c8a9d` plus the uncommitted D-07 diff. Reviewed AGENTS/workflow, attached user request, domain pointers and Product contract/workflow. Scope: HTML/CSS, controller, inspector, table, changed contract/layout/summary/table tests and new workspace tests. No production or test edits by this reviewer.

**Disposition: all three prior findings resolved; no new blocking Spec finding.** `revealInspectorSelection()` reveals the selected back control after moved context and when reopening the drawer; unrelated rerenders retain scroll. Comparison Escape now returns after closing its own layer, restoring its parent drawer and Compare focus. Methodology CSS has no dangling prefix; metric value-help selector remains intact. The retracted MODE_LABELS suspicion remains retracted.

Independent execution with `C:/folder/Python/AI_logistics_clean/.venv/Scripts/python.exe`, actual headless Edge, `REQUIRE_FRONTEND_BROWSER=1`, escalated browser process access:

```text
python -m pytest -q -o addopts= -p no:cacheprovider tests/test_dashboard_workspace_cleanup.py tests/test_dashboard_layout.py::test_selection_reveals_details_after_scrolled_overview_without_resetting_rerenders
12 passed in 65.92s; zero skips
```

This independently replays all three desktop geometries, fourteen columns and retained help, absent methodology UI, relocated Compare close-button/Escape focus return at 1440×900, 1093×614 and 900×720, frozen result reference, doubled text/long context, and the prior D-06 selected-detail/parent-focus/scroll preservation regression.

Additional inline Python replay used the existing `_table_script` / `_run_browser_script` seam, root font `200%`, twenty named saved origins with the saved-list disclosure explicitly opened, one real fixture point and cluster zero. At **1440×900 and 900×720**, cluster→point Back controls were wholly below the sticky tools and inside the inspector; the twentieth saved origin remained in context; Compare→Escape restored Compare focus and a visible non-inert result panel. All five booleans true at both sizes. Initial probe assumptions were corrected: DOM references become detached after rerender, and a successful fresh Compare activates a result through existing `setResult`, clearing prior selection. Neither was reported as a defect.

Source inspection confirms right-only saved context, compact Union/All disclosure and single-origin FIAS, saved filters/method/K and source, integrated selection live region, sticky Compare, compact responsive controls, preserved warning/status content plus narrow-screen attention indicator, and unchanged backend methodology/API/definitions. Table rendering retains fourteen raw sort keys and metric-specific denominator/precision helps; removed UI is not recreated elsewhere. Existing OpenLayers implementation remains unchanged. Inspecting retained before/after geometry evidence (not a new Flask replay) confirms map top **196→68 px**, center width unchanged, and visible area **252736→339255**, **376435.125→447405.75**, **764849.625→878832.75 px²** at the three desktop sizes. Retained map-resize JSON records identical center/zoom and map size matching its target after resize.

Exact reviewed source identity (SHA256):

| File | SHA256 |
|---|---|
| `frontend/index.html` | `FF47D2295D52D9FDE858D75FB6517E4E0DB4826F0B76B4751F298A60D2E0B66C` |
| `frontend/css/style.css` | `5DAD2CA63FD736B92026E4DB2EBA3B82DC521288F08A153E0A3371909AB0BEFC` |
| `frontend/js/clustering/controller.js` | `558E607E46BFD58A23599570017C9C905331F17A72A427C860BFA0417E255928` |
| `frontend/js/clustering/inspector.js` | `1D679BE6AE53A141085791ED29840788031EC8066F00496E978D029901E60FB9` |
| `frontend/js/clustering/table.js` | `4846C780C8BC0A7CEB04F5544B48AF9246FEA36F6D616C4AE0B30CEF1B93DADE` |
| `tests/test_dashboard_workspace_cleanup.py` | `E4104C66F23E6C786E4D7BA3FC81F644DAD2E476D792C18CC90BAD272FEBD223` |
| `tests/test_dashboard_layout.py` | `0BB955A54BDC4812097BEBBAF55C46EC26E05A5CC01F36590EC3AB9546A5B155` |

**Verdict: PASS within the reviewed Spec scope and exact source hashes above.** This is automated functional evidence, not native Computer Use or human acceptance. Full suites are intentionally left to the owner to avoid duplicate mandatory runs. Final committed-HEAD/hosted CI binding, native browser zoom/text settings, all-five-mode/two-theme visual matrix, live Flask/map hit detection/Data Map and full 294-ID/35-criterion reconciliation were not independently replayed here; those require the owner's separate evidence. Human acceptance and production readiness remain UNVERIFIED by this review. Earlier findings/history above are retained.

### Final source-only supplement

Independently inspected the subsequent controller-only removal of the unused `clusterLabel` import. `rg -n 'clusterLabel' frontend/js/clustering/controller.js` returns no matches; the removed selection-label assignment was its last caller. No behavior changed and no new runtime replay was performed. Final controller SHA256 superseding its table entry above: `AD9DAE517B059AF48AAB5EBA7D6E7756D7C3A19E087D6E21D478815BA45BC9D4`. Spec verdict remains PASS within the same scope and limitations; the owner's final mandatory gates must bind this final source.

### Final test-only source supplement

Independently inspected `git diff a843a2ab4d23c16f8a53d579e1e5be70288c8a9d -- tests/test_clustering_frontend_contract.py` and the final D-07 test module. The DOM ownership checker now accepts literal IDs declared by renderers and explicitly requires dynamic `point-details-close`; it continues rejecting undeclared literal references. The weighted-price tooltip oracle retains exact formula/missing-value text, hover/focus/visibility/viewport/keyboard/scroll assertions and all 24 helps, while explicitly checking the three supported modes' influence descriptions. D-07 import ordering is nonbehavioral. Three additional narrow-control cases check visible attention marker and accessible warning label for draft, invalid-connectedness and result warnings. These changes match the approved UI move and preserve the meaningful assertions; no new Spec finding.

No duplicate runtime execution for this supplement. The owner's reported two targeted GREEN cases and three new attention GREEN cases are owner evidence, not independent replay. Reviewed final test SHA256: `tests/test_clustering_frontend_contract.py` = `9D887494EBC7648376F2ADB3C468905FB0C3F4B1590B405B2CB83C3EEFD125DB`; `tests/test_dashboard_workspace_cleanup.py` = `13E2B152A515B36F45214E8583CCF4FF7EE860376FD4F2B5F0FFF1B18205B9F3` (supersedes its earlier table entry). Controller hash independently rechecked unchanged at `AD9DAE517B059AF48AAB5EBA7D6E7756D7C3A19E087D6E21D478815BA45BC9D4`. Spec PASS and the earlier explicit scope limits remain; final local and hosted gates are owned separately.

### Inspector test ownership supplement

Independently inspected the final `tests/test_dashboard_inspector.py` diff against the fixed base. `test_selected_level_precedes_export_and_overview_content` now queries direct content sections plus sections within the new `#selection-context` wrapper, preserving DOM order and the exact expected first visible `cluster-details` assertion. This adapts the ownership query to the approved wrapper without dropping the selected-detail-before-export/overview requirement. Final file SHA256: `5F8EE7AAB3C4C32D47589532FF5EE9FB4E36E37C9EE59DC0C62A0497FB4F1E47`. Owner reports genuine RED and targeted GREEN; no independent runtime replay repeated for this test-only adjustment. Scoped Spec PASS unchanged; final suite and committed-source binding remain owner obligations.
