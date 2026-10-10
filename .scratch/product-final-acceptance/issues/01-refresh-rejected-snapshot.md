# Refresh a result whose snapshot was rejected

Status: implemented ? PR #5 open; not merged
Priority: P1 — blocks final acceptance
Blocked by: none

## Reproduction

Verified on main `db1ed6415ee84fec6837a1f7025e5d676fce83f8`, real Flask server and Edge 155 desktop viewport.

1. Run Geography for synthetic-origin → Region A, current/spot.
2. Change only the synthetic CSV generation after the result is saved.
3. Select a destination and expand Pulse rows. Observe “Данные Pulse изменились. Пересчитайте результат.”
4. Press “Рассчитать” with unchanged filters and parameters.
5. Select the destination again. The same stale message remains; no new `/api/clustering/run` request occurs.

Evidence: [before](../defect-stale-before.png), [after recalculation and reselection](../defect-stale-after-reselect.png), [browser log](../browser-log.jsonl), [network log](../network.jsonl).

## Expected / actual

The instructed recalculation obtains a fresh snapshot, then permits source-row loading. Actual: `executeRun()` accepts its request-signature cache entry; the rejected snapshot and stale detail survive. Source-generation isolation works, but recovery does not.

## Proposed narrow remediation

Invalidate or bypass entries associated with the rejected snapshot when recalculating, including comparison entries that could reactivate it. Preserve the displayed result until a fresh request succeeds. Do not remove ordinary cached comparison switching.

Add a small regression covering an unchanged-filter recalculation after a real snapshot conflict: one fresh `/run`, a different snapshot, and successful subsequent point rows. Repeat acceptance scenarios 10 and 16.

Scope: frontend cache/recovery transition in controller/state and its existing regression infrastructure. No implementation was performed.


## Comments

### P1 implementation ? 2026-10-10

Baseline: fetched origin/main `db1ed6415ee84fec6837a1f7025e5d676fce83f8`. Existing tracked work and untracked .scratch preserved; isolated worktree/branch `fix/product-rejected-snapshot-recovery`. Search found no existing P1 implementation PR. The reproduction and proposed remediation above are retained as historical acceptance evidence.

Confirmed root cause: point-row HTTP 409 only changed detail.status; request-signature result cache and saved comparison still held the rejected data_snapshot. Unchanged Calculate reused it without /run.

Changes: record rejected snapshots for the current workspace; evict only matching result/comparison cache entries and saved comparison variants; clear and mark all matching loaded source-row pages stale. New point selections under that snapshot also remain stale. Preserve frozen displayed map/table until a valid result succeeds. setResult and incoming comparison responses reject known rejected snapshots. Ordinary valid/unrelated snapshots remain cacheable.

Cancellation: each run/compare owns its AbortController; new calculations, cached activations and reset cancel previous work. Aborted successes/errors cannot update state or clear newer loading UI. Point-row selection/result cancellation guards remain in force. Comparison loading clears old selectable variants before installing a new context; invalid forms do not relabel saved comparison context. No backend metrics, modes, pagination, Bear, ProductModeCatalog, RESEARCH/LEGACY or P2 changes.

TDD evidence:
- RED: `test_unchanged_recalculation_recovers_after_real_snapshot_conflict` received actual Flask HTTP 409 after synthetic CSV mutation, then failed `rejected cache must force refresh`: actual success versus expected error (no attempted refresh).
- GREEN: same test verifies initial/valid cached run, real conflict, removal of previously loaded rows, failed refresh preserving stale frozen display, retry/new snapshot/successful rows, safe saved comparison and fresh cached comparison.
- Race RED: four run?cached/reset cases left Calculate disabled; GREEN after shared cancellation cleanup.
- Review RED: two `comparison_tab` cases failed `old tab cannot cancel new comparison`; GREEN after clearing loading variants. Deferred success/error tests cover run/compare replacement by fresh/cache/reset; selective invalidation test preserves unrelated snapshots.
- Final local full suite: **274 passed in 17.38s, zero skips**, REQUIRE_FRONTEND_BROWSER=1. Ruff, all12 JS syntax checks, git diff --check PASS. Focused Product/Node/Edge checks PASS. Early sandbox/temp permission failures were rerun with isolated temp directories and normal browser sandbox; they are not counted as PASS.

Observed desktop acceptance: real run.py on localhost:5064, Edge155 headless desktop1600?1000, actual Product algorithms, same71 synthetic Pulse rows/12 destinations, no private source loaded or published.
- Scenario10 recovery: load50 rows, mutate CSV generation, Show more receives409; stale message, zero obsolete rendered rows, prior map/table retained. Unchanged Calculate sends fresh /run; snapshot3764bb02? becomes ae8cf494?; reselected point loads50 rows, next page completes60. PASS.
- Original first-page scenario and comparison: new generation, select previously unloaded synthetic-01, expand?409; reopening comparison sends new /compare, reselected point loads1 row with snapshot4eb6d01c?. PASS.
- Scenario16 recovery on final source: fresh application, run, mutate CSV, select synthetic-01, expand?409; native Shift+Tab focuses Calculate, native Enter with text activates it; fresh /run changes snapshot b095796b??8291eee8?; reselect/expand loads1 valid row. PASS. An earlier Enter probe omitted native text and did not activate Calculate; it was superseded by this corrected input, not claimed successful.
- This repeats the P1 recovery portions of scenarios10/16. Existing keyboard/table/tooltip tests pass; the whole prior16-scenario matrix, headed/human walkthrough, other browsers and production-scale/private Pulse remain UNVERIFIED. P2 is still a separate open ticket.

Local-only desktop artifacts: [stale rows cleared](../p1-verification/03-rejected.png), [fresh rows](../p1-verification/05-recovered.png), [keyboard focus](../p1-verification/17-native-focus.png), [keyboard recovery](../p1-verification/19-native-recovered.png), [browser log](../p1-verification/browser-log.jsonl), [network log](../p1-verification/network.jsonl), [full pytest](../p1-verification/final-pytest.txt). These synthetic artifacts are retained locally, not added to the PR.

Reviews at source HEAD a6c27c4: Standards0 hard violations/0 actionable smells. Spec1 blocking frozen-context race found and fixed; re-review0 remaining blockers, independent17focused regressions PASS plus canceled conflict/rejected incoming comparison checks. Ponytail review: Ship; existing helpers/AbortController reused, no new dependency or speculative abstraction. Assumed one desktop workspace; no production capacity promise.

Publication: [PR #5](https://github.com/a-man-or-a-person/AI_logistics/pull/5), target protected main; no automatic merge. Required `verification` is checked on the final PR HEAD; its final outcome is recorded in the PR checks and completion report. This implementation does not mark the entire Product iteration ready.
