# Ponytail review

What this change does: This change records independent integrated acceptance of the
combined Product iteration. It corrects obsolete CURRENT readiness wording and adds
reproducible synthetic evidence; no production logic, dependency or architecture changes.

Reviewed connected repository/accumulator/service/export/adapter and frontend
state/controller/inspector/table flows, affected consumers, README/startup/quality gates,
the independent reviews and new executed evidence. Assumed workload: local desktop
Product using safe synthetic CSV; intended production load is unknown.

Should fix after workload requirements are supplied:

1. **Large export approaches the existing timeout** (`clustering_service.py:1024`).
   What this is: Export repeatedly scans the regional rows for each assigned point.
   Problem: 90,000 rows/300 destinations took21.27s at the API and19.52s through
   actual Edge, with process peak486.15MiB in the sequential measurement run.
   Fix: First obtain intended workload/targets; if needed, group or index rows once
   under the existing generation checks. Keep complete row output and saved membership.
   If skipped: Larger/slower slices may repeatedly time out; no production capacity
   promise is supported by these one-shot measurements.

No must-fix production correctness/security finding was reproduced. Frozen identity,
weights, full exports, cancellation, source races and typed recovery were exercised.
Existing metadata and in-memory/multiworker shortcuts remain explicit. Evidence drivers
reuse prior harnesses; temporary profiles/binary workbooks stay local. No extra source
framework, persistence, background job platform or new user feature was added.

Verdict: Ship the acceptance/documentation PR after exact-HEAD CI; production readiness
remains UNVERIFIED. Not checked: human acceptance and authorized production-scale load.
