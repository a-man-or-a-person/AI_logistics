# Independent Spec review

Initial review18be91c: one P2. Successful revision followed by source change during /run or /compare returned409 without rejecting displayed generation. Old summary/row caches retained success. Violated spec5 frozen-visible-stale and obsolete detail blocking, and spec8 in-flight handling. Otherwise narrow implementation matched requirements; no scope creep.

Independent cache/network inspection confirmed unchanged reuse after revision, source replacement invalidation, All34→35, restart/eviction unavailable with unchanged revision, five-mode consistency and network/no-store revision responses. Independent Edge rerun was blocked by restricted sandbox startup timeout, not counted PASS.

Re-review dcfa3b23f890e3c6d6887abd27addd4d42b8daf6: initial P2 resolved; no remaining implementation findings.

Both /run and /compare generation-conflict catches now invalidate displayed snapshot using existing recovery, render stale and preserve frozen data. Aborted requests still exit before mutation.

Inspected genuine RED failures for both actions and GREEN28 relevant cases. Tests cover successful revision followed by calculation409, preserve old display, clear result/comparison caches and block saved summaries/rows.

Final full regression and appended real Flask/Edge checkpoint were running at re-review; reviewer did not independently rerun browser tests. Metadata identity and post-validation source/eviction limits remain documented.
