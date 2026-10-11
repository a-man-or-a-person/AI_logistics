What this change does: Calculate and Compare confirm the current source generation and exact saved-result availability before accepting frontend cache hits. Existing invalidation keeps obsolete summaries/pages blocked while the old map/table remains frozen.

Looks good. Ship conditional on final exact-HEAD required verification.

Checked connected API/service/repository/frontend state/controller callers, public-boundary RED/GREEN, cancellation/conflict recovery, metadata stat cost, bounded six-context validation, no-store and live Edge request counts. Existing helpers and immutable request normalization reused; no dependency, process UUID, persistent store, polling, duplicated invalidation, algorithm or formula change. Assumed current local Flask desktop Product, no multi-worker retention/SLA promise.

Not checked: production workload/capacity and human acceptance. Metadata same-path/size/mtime rewrite and later result eviction remain documented limits.

Rechecked dcfa3b2 calculation409 handling and genuine RED→GREEN. Existing helper reuse and cancellation ordering preserved; no extra abstraction warranted. Real in-flight source replacement checkpoint12 independently exercises final error path through Flask and Edge. Verdict remains Ship conditional on exact-HEAD CI.
