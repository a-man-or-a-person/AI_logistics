# D-06 independent Spec review — 16 October 2026

Reviewer: `/root/sidebar_spec`, independent of the implementer; production read-only.
Reviewed base/HEAD `cab287ff62840fc7b8de615f6e567330130899e1` plus the uncommitted D-06 diff. This is a working-tree review, not final-HEAD hosted-CI acceptance.

## Findings

**MAJOR — selecting a cluster can leave its details and return control outside the visible sidebar.** The task requires: “При выборе кластера правая панель должна показывать его детали.” The moved summary precedes overview cluster cards (`frontend/index.html:109`), while selection inserts details above that summary. `selectCluster` (`frontend/js/clustering/controller.js:579`) rerenders without revealing the new section. In independent actual Edge replay at 1440×900, scroll the eighth overview cluster into view then click it: selection becomes 7, panel scroll changes from 354 to 645; panel top is 68, but details/back button top is −480 (back bottom −460). The new section and return control are invisible. Reveal selected details on explicit selection; preserve scroll on unrelated refreshes. Verdict: **changes requested** until fixed and independently replayed.

## Independently checked

- Read task, D-06, Workflow v2 and full affected HTML/CSS/controller paths, inspector rendering, selection/origin/Pulse callbacks and existing drawer lifecycle.
- `git diff -- frontend tests CONTEXT.md docs/agents/development-workflow.md docs/clustering_product_v1_workflow.md`: only presentation/docking and corresponding assertions change; business readers, backend, ML, API and XLSX writer remain unchanged. Existing IDs occur once; frozen context remains central and full summary is owned by the right inspector.
- Parsed both `.scratch/sidebar-20261016/{before,after}-geometry.json`: all 24 physical/zoom/state identities match and all visible map areas increase. Nonzero-baseline gains are 1.376×–35.294×; three baselines have zero visible area.
- Escalated `REQUIRE_FRONTEND_BROWSER=1 python -m pytest -q -o addopts= -p no:cacheprovider tests/test_dashboard_layout.py::test_modal_panels_trap_focus_restore_opener_and_preserve_saved_state tests/test_dashboard_summary.py::test_saved_quality_and_status_are_in_the_sidebar_and_survive_draft_edits`: **4 passed**, no skips. Initial sandbox launches timed out; those are environment failures, not behavioral evidence.
- Independent synthetic replay used `_table_script`, eight cluster cards, `scrollIntoView({block:'center'})`, click and DOM rectangles; produced the finding above.

Source SHA256: index.html `ACE8A119BFD513E32A2394E1911C9B644D1FFB4C5BDE652667C170385E827176`; style.css `2311531FF82C9FD23D705E7547B980B148902E7C34184D3D9289655488FCD585`; controller.js `8DCCEE349D6267E9B02ACBF1819F6326D5FB9EA779CDA11D6DB5D032E9E30839`; unchanged inspector.js `D6A93FCDCDF09CEA3FDCEAB40E9EF957C0225298DCC3C280A0385F1AD9F39576`.

Not replayed: whole suites, independent numeric/XLSX oracle, native mouse/keyboard smoke (owner reports native tool access blocked), hosted final-HEAD CI or human visual acceptance. Production readiness remains UNVERIFIED.

## Selection-fix follow-up

Independent escalated Edge replay confirms the initial selection defect is fixed: explicit cluster selection resets sidebar scroll to 0 and Back is visible at y=165–185. The reset is outside rendering, so ordinary refreshes retain their position.

**MAJOR — drill-up restores invisible keyboard focus.** Current guarded reset (`clusterId/pointId != null`) still leaves the overview return target below the viewport. After selecting cluster 7 then activating Back, sidebar scroll is 0 and `document.activeElement.dataset.clusterId` is `7`, but its rectangle is y=1171–1211 against panel y=68–888. The existing return handler uses `focus({preventScroll:true})` (`controller.js:143`); summary relocation plus selection reset makes that focus invisible. Reveal the restored parent (ordinary focus or nearest scrolling), including the point-to-cluster path where applicable. The guarded change was independently replayed and produced the same result. Initial selection finding is resolved; review remains changes requested for this focus issue.

## Final disposition — both findings resolved

Independently inspected the final controller changes: only explicit non-null selection resets sidebar scroll; point and cluster drill-up now use ordinary `focus()` so the browser reveals the restored parent. No reset was added to rendering or asynchronous/cache refresh paths.

Independently executed (escalated actual Edge, `REQUIRE_FRONTEND_BROWSER=1`):

`python -m pytest -q -o addopts= -p no:cacheprovider tests/test_dashboard_layout.py::test_selection_reveals_details_after_scrolled_overview_without_resetting_rerenders`

Result: **1 passed in 7.64s**, no skips. The regression replays the reported eighth-cluster scrolling scenario, verifies cluster and point detail return controls are visible, verifies ordinary rerender preserves scroll, and verifies both point→cluster and cluster→overview restore focus to a visible parent. Combined with the four prior independent drawer/frozen-summary checks, the affected behavior has five passing checks. Both MAJOR findings are **RESOLVED**; this disposition supersedes the earlier changes-requested verdict.

**Final Spec verdict: PASS for the reviewed D-06 working-tree implementation; no open Spec findings.** Source identity remains base/HEAD `cab287ff62840fc7b8de615f6e567330130899e1` plus reviewed uncommitted changes, rather than an as-yet-uncreated final candidate commit. Final source SHA256: controller.js `6EF160CEDF36768FA374ECEA6452FDF1CD4051D6D0A585BBF06F0A73262CF40B`; index.html `ACE8A119BFD513E32A2394E1911C9B644D1FFB4C5BDE652667C170385E827176`; style.css `2311531FF82C9FD23D705E7547B980B148902E7C34184D3D9289655488FCD585`; inspector.js `D6A93FCDCDF09CEA3FDCEAB40E9EF957C0225298DCC3C280A0385F1AD9F39576`.

No whole-suite or native smoke duplication was performed. Native Edge smoke, hosted final-HEAD CI, human visual acceptance and production readiness remain separate unverified gates in this review.

## Final responsive text refinement

Independently inspected the sole follow-up CSS rule: `.analysis-inspector .summary-quality{grid-template-columns:repeat(auto-fit,minmax(min(100%,7rem),1fr))}`. This preserves the normal two-column quality presentation and permits one column when text grows. Independent escalated actual Edge `_table_script` replay at 1440×900 measured grid tracks `133px 133px` at root font 16px and `268px` at 32px, with `scrollWidth <= clientWidth` in both states. This is rendered doubled-root-text evidence, not native browser zoom/text-size UI verification. No additional Spec finding; PASS remains valid for this scope.

Final style.css SHA256 supersedes the earlier hash: `6EE8AF69F50D2EB43EADAAC1EA02327F5F5F998A01BAFBAB071977AD858C35F2`. Other final production hashes remain as recorded above.

## Fixture supplement review

At candidate HEAD `3d78632946bf571a3b579cfed3f153b46b3b6151`, independently inspected the five added fixture lines in `tests/test_clustering_frontend_contract.py` and their three connected test bodies. The browser controller-only harness now supplies the real inspector element required by selection scrolling; two Node controller-only harnesses provide a stable panel object with `scrollTop`. Existing selection/map, lazy pagination/retry/cancellation, late-response and cache-invalidation assertions are unchanged. The stubs satisfy presentation setup while the tests retain their original business-lifecycle oracles. No production modification, test exclusion or weakened expectation is introduced. **Narrow supplement Spec verdict: PASS.**

Reviewed supplement file SHA256: `7894DDF43EB8D61DE61FFDEF04E73076147E9D2F2B45C8BA813631038C2CCA35`. This is independent source inspection; the owner's three passing focused executions and full mandatory rerun are not claimed as my executions. No additional runtime replay was needed for these fixture-only additions; final-HEAD CI and native/human gates remain separate.
