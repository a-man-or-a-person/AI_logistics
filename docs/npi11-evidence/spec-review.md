# Independent Spec review

Reviewed baseline `e98eb2c02accb7a9252b919587e490748c2b64bb` through candidate `5ab13b636e0bfe7265555de3f094276b5012c6bf`, plus the pending two DOM-fixture `setAttribute` additions and live mouse-coordinate correction. Commit: `5ab13b6 feat: download saved Product XLSX with frozen context (NPI-11)`.

Sources: original workspace approved NPI-11 card, spec R2-01/07/10/12/14, I-07, P1/P2 export branches, coverage matrix, execution requirements and pasted implementation request. Inspected production diff, callers, state rejection/cache logic, table sorting, existing actual export endpoint and frontend/live evidence tests.

## Findings

1. **Resolved: CURRENT documentation.** NPI-11 Definition of Done requires “Contract/CURRENT docs updated only for implemented behavior”. The initial review found CURRENT docs still describing download UI as NEXT. Independently rereviewed the subsequent diff in `CONTEXT.md`, `docs/architecture/current-state.md`, `docs/clustering_product_v1_workflow.md` and `docs/clustering_product_v1_contract.md`: all now describe the implemented saved-result download, explicit frozen intent/current sort, form-only stale warning, rejection/retry and cancellation behavior consistently with production code. No unresolved finding remains.

No concrete production correctness blocker or scope creep found. The request uses the displayed result’s frozen request, snapshot and explicit intent, with a copied current sort. It never expands All or calculates a workbook in JavaScript. Form edits leave saved membership intact. Source/result rejections reuse existing invalidation, preserve the display and block export; fresh recovery retains the existing calculation path. Cancellation checks both abort and result/controller identity after transport, including late successful responses. The transport preserves exact response bytes, typed diagnostics/request ID and no-store, cleans DOM/object URLs, and rejects bad MIME/attachment/truncated ZIP envelopes. Bear and empty results have explicit explanations.

## Evidence boundary

Final artifact rereview observed `full.txt` and `pytest-results.xml`: 593 passing tests, including 136 frontend cases, zero skipped/failing. `startup-empty.json` records startup Node/Edge success and the explained empty-table guard without an export request. `live-observations.json` records headed Edge 155 actions and required download/error/recovery states. `network.json` contains ten successful exports/downloads; all ten `workbook-inspection.json` hashes match their captured server attachment checksum headers. Inspection records report ZIP CRC/XML reopen, exact headers/order/context/membership and supported mode source-row counts. I inspected these outputs; I did not independently rerun tests or reopen workbooks.

The driver-only checksum hook reads the generated Flask attachment and restores its file position before transmission. This resolves CDP's empty binary response-body limitation without changing production transport/workbook bytes. No additional blocking finding. Final required CI remains pending and is not claimed PASS by this review.

Skipped production-scale capacity measurement and final CI; capacity and final-HEAD verification remain release-report obligations.
