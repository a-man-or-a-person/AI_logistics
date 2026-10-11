# REMEDIATION — Pulse Source Freshness and Frontend Cache Safety

Repository: `a-man-or-a-person/AI_logistics`

Workflow:
`/tdd` → `/implement` → `/code-review` → Ponytail → `/pr`

## Preconditions

1. Fetch latest protected origin/main.
2. Confirm PR #13 / NPI-07 has been merged and required verification passed.
3. Read CONTEXT.md, Product API contract, current architecture and the implementation/evidence for P1, P2, NPI-02, NPI-03, NPI-04, NPI-05 and NPI-07.
4. Preserve all existing worktrees, untracked files, skills and hooks.
5. Create an isolated remediation ticket and branch. Do not alter approved NPI-07 acceptance history.

## Problem

Pulse CSV is expected to be updated approximately weekly.

Currently the frontend can reuse locally cached Product results or comparisons by request signature without contacting the backend.

Consequently, a user with an open browser tab may click Calculate after a CSV replacement and unknowingly receive a result based on the previous data generation.

Frontend cache keys do not independently guarantee source freshness.

## Objective

Ensure that initiating a new Product calculation or comparison cannot silently reuse a stale frontend result after the Pulse source generation changes.

Preserve fast cache reuse when the current source generation is confirmed unchanged.

Maintain strict frozen-result and detail consistency.

## Investigation

Trace:

- Source fingerprint and generation handling.
- ClusteringService result/graph/location caches.
- Frontend result and comparison caches.
- Saved origin summaries and origin-specific point-row caches.
- P1 rejected-snapshot recovery.
- NPI-07 stale/eviction behavior.
- Backend restart and lost in-memory result behavior.

Design the smallest coherent solution supported by these existing contracts.

## Implementation requirements

1. Provide an inexpensive, read-only way to validate the current source generation before accepting a frontend cache hit.

2. Prefer existing source-generation logic. Avoid repeated full CSV parsing or hashing for every click.

3. Return an opaque revision identifier. Do not expose private filesystem paths or confidential source metadata.

4. Prevent HTTP intermediary/browser caching of the revision check.

5. When source generation differs:
   - invalidate affected frontend result/comparison caches;
   - prevent obsolete origin summaries and point-row pages from being reused;
   - retain the old map/table as a visibly stale, frozen result;
   - allow explicit recalculation;
   - resolve regional All again for the new generation.

6. Do not silently rerun clustering for an old detail request.

7. When revision validation fails due to network/server error, do not present an unverified cached result as freshly calculated.

8. Handle race conditions, cancelled requests and rapid repeated clicks without publishing mixed generations.

9. Consider backend restart and in-memory result eviction explicitly. If source revision alone is insufficient, document and implement the narrowest safe result-lifetime validation strategy.

10. Preserve scalar, explicit multi-origin, regional All and all five Product modes.

11. Preserve existing P1/P2/NPI-04/NPI-05/NPI-07 semantics.

12. The detection scheme must be explicit about limitations of current file-metadata fingerprints. Do not claim cryptographic content identity if it is not implemented.

## TDD

Begin with genuine RED reproductions for:

- Same request and unchanged CSV: valid cache reuse.
- Same request after CSV replacement: stale cache rejected.
- Cached comparison after source update.
- Updated All catalog includes a newly added origin.
- Frozen displayed context remains unchanged until successful recalculation.
- Origin summary and detail cannot mix generations.
- Source update during an in-flight operation.
- Revision-check network failure.
- Server restart / lost saved result.
- Existing P1/P2 recovery.

Use synthetic CSV fixtures and real Flask/Edge requests.

Independently inspect actual cache hit/miss and network behavior.

## Scope restrictions

No new Product features.
No origin drill-up navigation.
No XLSX.
No ATI.
No clustering algorithm or weighted formula changes.
No speculative database or external cache infrastructure.

Do not remove caching entirely.

## Quality gates

Run focused RED → GREEN tests and full pytest with mandatory Node/Edge.

Run Ruff, locked dependency checks, JS syntax checks and git diff --check.

Perform independent Standards and Spec reviews and Ponytail.

Verify a real browser scenario in Edge where Pulse changes without reloading the browser page.

Open a narrow PR targeting protected main.

Verify GitHub Actions verification on its exact final HEAD.

Do not merge automatically.

## Final report

Provide:

- Root cause and exact affected cache paths.
- Current and new freshness contract.
- API and revision identity design.
- Cache reuse and invalidation evidence.
- Weekly CSV replacement scenario.
- All origin-set refresh scenario.
- Restart/eviction limitations.
- Browser screenshots/network evidence.
- RED → GREEN and regression results.
- Independent reviews.
- PR URL and final CI.
- READY TO MERGE YES/NO.

STOP.