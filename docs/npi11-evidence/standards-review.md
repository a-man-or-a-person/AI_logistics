# NPI-11 Standards review

Reviewed `git diff e98eb2c02accb7a9252b919587e490748c2b64bb...HEAD` at `5ab13b636e0bfe7265555de3f094276b5012c6bf` (`feat: download saved Product XLSX with frozen context (NPI-11)`), plus the working-tree DOM fixture `setAttribute()` additions and live-driver pointer-coordinate correction.

**Hard documented violations: none found.** The applicable sources were `AGENTS.md`, `docs/agents/domain.md`, `CONTEXT.md`, the Product contract/workflow, architecture/project brief, `pyproject.toml`, and the original shared execution requirements. Tool-enforced formatting/lint rules were excluded.

`frontend/js/clustering/controller.js` respects the shared architecture rule “Backend owns aggregation ... XLSX values. Frontend owns ... download”: it forwards the saved `analysis.frozen_request`, snapshot, saved intent and current table sort rather than rebuilding values from editable form state. Bear availability follows backend `cluster_table.supported`; existing stale/unavailable invalidation helpers are reused. `frontend/js/app.js` adds cancellation to the existing view boundary. Product/RESEARCH/LEGACY boundaries and backend semantics remain unchanged.

The binary API path has a justified separate implementation from the JSON client: attachment/MIME checks, typed JSON failures, timeout, safe filename and complete-body checks require different success handling. I found no actionable baseline smell warranting abstraction. Tests cover the new nontrivial branches and update affected DOM fixtures without weakening existing assertions.

**Lifecycle/accessibility assessment:** no actionable defect found by inspection. Duplicate activation is guarded even though `aria-disabled` preserves focus; status is a live region; cancellation, page hiding, reset, replacement and calculation prevent late downloads. The object URL is released, and success accurately says the file was handed to the browser.

**Final rereview:** working-tree CURRENT documentation, DOM fixture changes and test-only checksum hook are consistent with production behavior. The hook hashes the real attachment and restores its position, preserving response bytes. The implementation report records 593 full tests passed, 136 frontend checks with zero skips, and ten actual Edge downloads independently inspected. No blocker found; the earlier NEXT-documentation limitation is resolved.

**Remaining limitations, not violations:** the client buffers Blob plus ArrayBuffer and retains the 30-second timeout; production capacity is unverified. ZIP boundary checks are not full workbook validation. I inspected the final report rather than independently rerunning its tests; human Excel acceptance and actual candidate CI remain separately reported gates.

Standards findings: 0 hard violations, 0 actionable smell findings.
