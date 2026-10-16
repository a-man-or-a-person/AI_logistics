# D-06 — Persistent Right Analytics Sidebar

Accepted by the Product owner in the 16 October 2026 task. This replaces only
D-01's placement of the main analytical overview above the map; D-01–D-05 retain
their other requirements, including all 294 information obligations.

Desktop keeps analysis parameters and calculation on the left, a compact frozen
context, map and complete 14-column table in the center, and persistent analytics
on the right. The existing summary, coverage, warnings and diagnostics move into
the inspector once. Cluster and point/origin/Pulse details precede the overview
when selected; returning restores the saved overview. All readers, saved identity,
sorting, pagination, cancellation, cache and XLSX semantics remain unchanged.

The sidebar uses the existing accessible right drawer below 1320 CSS pixels.
This breakpoint preserves at least 660px of center space on docked desktops:
1320 minus 24px outer padding, 24px gaps, 280px controls and 320px analytics.
The trade-off is a narrower desktop map and horizontal table scrolling. Accept
that trade-off only against measured gains in visible map area on identical
saved states; preserve the full table and its columns. No business reinterpretation,
backend, ML, API, economic formula or writer change is authorized by D-06.

Human visual acceptance and production readiness remain UNVERIFIED until separately
accepted. Historical reports and D-01–D-05 are retained.
