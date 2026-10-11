# Independent Spec review — NPI-07

Reviewed `git diff d27d799d870cae8012b7c6a42b71c6df761852bd...d85f275ab91afe1b6a976a03a345af659d431946` and connected service/repository/accumulator, frontend selection/cache/invalidation and tests against the approved original-workspace NPI-07 card, spec, coverage matrix and execution requirements.

**One finding, resolved:** on initial `8c56181`, cached A → B → A reselection left B displayed while state selected A; incomplete cached pages also advanced unnecessarily. This violated **R5-02**, “choose origin A by click/keyboard: first page contains only A→X frozen rows; source context labels visible and correct,” and the card's “cache key result/point/origin” contract. Re-reviewed correction: handler opens and renders successful cached detail immediately, fetching only idle/error pages. It preserves contributor focus across rerenders. Dedicated cached-selection/focus RED→GREEN evidence and final real-CDP cached A61/B3 Tab/Enter assertions cover the correction. Disposition: resolved; zero remaining blocking Spec findings.

No other missing or incorrectly implemented owned criterion found. Summary grain is one contributing origin FIAS per destination; actual row regions remain attributes, and zero-match selections remain in saved analysis instead of fabricated contributor rows. Shared frozen-row access validates exact canonical request/mode/parameters, generation and saved destination membership; typed snapshot/eviction errors retain recalculation recovery. Aggregation reuses existing independent valid-machine denominators, while detail preserves source IDs/newest-first/max50. Form edits preserve frozen context; lower-table formulas and membership are unchanged. No NPI-08/09/10/11, ATI, new mode or formula scope creep found.

The summary now rejects row-only `detail_origin_fias`, preserving the spec's complete per-point contributor summary; a dedicated HTTP RED→GREEN test covers this boundary.

Checks: source/diff review, hand-constant HTTP test inspection, Node/Edge and real Flask/CDP evidence inspection. Full-suite/live counts are implementer evidence, not independently rerun here. Automated native-button/CDP interaction is not human acceptance; downstream workbook grouping and production capacity remain unverified.

Skipped: production data/load and human acceptance. Risk: final required CI must still pass on the publication HEAD.
