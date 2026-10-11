# NPI-11 RED/GREEN observations

Executed before API implementation:

`python -m pytest tests/test_clustering_frontend_contract.py -k xlsx_transport -q`

RED: `test_xlsx_transport_returns_exact_binary_and_safe_attachment` failed with
`ReferenceError: exportClustering is not defined`. After adding the narrow binary
transport, the same test passed (1 passed).

Next transport failure slice:

`python -m pytest tests/test_clustering_frontend_contract.py -k xlsx_transport_failures -q -p no:cacheprovider`

RED: network failure exposed raw `TypeError`, expected `EXPORT_CONNECTION_ERROR`.
The caller-cancel checks also initially compared DOMException's numeric legacy
`code=20` to its name; that test assertion was corrected, not counted as a production
defect. Added the user-facing connection error; transport/filename slice GREEN:
15 passed. Timeout, already-aborted caller, typed JSON error, bad MIME/attachment,
partial ZIP, unsafe paths and UTF-8 filename covered.

Controller test was written before its production implementation. Its initial
sandboxed Edge run timed out because CDP local access was blocked; this is an
environment failure, **not claimed as a genuine behavioral RED**. The authorized
Edge run then passed. Controller cases added afterward are regression evidence,
not fabricated RED: frozen context, selection/sort/collapse/focus, rapid duplicate
activation, cancellation/reset/pagehide/hide/new run/comparison/replacement and
late response, typed writer/source/unavailable errors and retry/cache invalidation.
Focused mandatory Node/Edge run: 26 passed.

Initial full suite: 591 passed, 2 failed. Both existing lightweight DOM fixtures
omitted `setAttribute`, now used by the export live-region controls. Added that
platform method to the fixtures without relaxing any assertions; both targeted
checks passed. The final full-suite result is in full.txt/pytest-results.xml.

Raw first RED outputs were observed in the task tool transcript; this file records
those observations, not a reconstructed execution log. Full GREEN logs are retained.
