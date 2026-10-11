# Ponytail review

What this change does: Shows each contributing origin inside a saved destination point. Selecting an origin opens only its frozen source rows; clustering membership and the bottom table stay the same.

Reviewed final source `d85f275` against protected baseline `d27d799`, connected request normalization, repository source rows, canonical accumulator, result-cache lookup, controller selection/cancellation, P1/P2 invalidation and inspector/table callers. Assumed the documented local Flask desktop application; production capacity requirements are unknown.

Must-fix findings resolved:

1. Completed cached origin pages returned before rendering. A→B→A could keep B visible. Genuine Edge RED reproduced the wrong aria-pressed/context. The handler now renders selected cached pages and avoids fetching a later page on reselection; GREEN and real live cached A61/B3 assertions pass.
2. Rerender removed the focused native origin button, preventing normal Tab/Enter continuation. Genuine focus RED reproduced this. Inspector restores the same origin's focus across async/cached rendering. GREEN and real Edge Tab/Enter pass.
3. Shared frozen-row access allowed the row-only detail selector to narrow summary. HTTP RED returned a partial200; summary now returns INVALID_REQUEST400 for that field. Full API regression passes.

Independent Standards advisory resolved by renaming cancellation to `cancelPointDetailRequests` at every caller. No new abstraction, provider, dependency, formula, clustering mode or lower-table column. Grouping and aggregation are linear over one frozen point's source rows; all contributors are returned without a guessed cap. Existing typed snapshot/eviction errors and generation checks retained. No production data writes or migrations.

Verdict: Ship, conditional on required GitHub verification on the exact final PR HEAD.

Not checked: human acceptance, confidential live data, production load/SLA, future drill-up/XLSX/ATI.
