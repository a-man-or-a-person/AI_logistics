# D-06 independent numerical and information-preservation review

Reviewer: independent `sidebar_oracle` agent, 16 October 2026. Accountable
implementer: root agent. Scope: preservation and numeric/output semantics only;
desktop/drawer visibility is the implementer's separate runtime gate. No production,
test, fixture or configuration edits by this reviewer.

Reviewed checkout: `C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`,
branch `feature/balanced-ux-redesign`, origin
`https://github.com/a-man-or-a-person/AI_logistics.git`, HEAD
`cab287ff62840fc7b8de615f6e567330130899e1` plus the D-06 working diff.
Historical semantic comparison: `ddbeeb4`. This is a source-hash-pinned working
candidate review, not final-HEAD CI or merged acceptance. The inherited workflow,
D-06 decision and original ledger were inspected.

## Verdict

PASS within the stated preservation/numerical scope. No BLOCKER, MAJOR or MINOR
finding. ADVISORY: moving the summary changes the user's access path; historical
center placement assertions do not establish current visibility. Fresh native
sidebar/drawer/focus evidence remains required from the implementation owner.

The ledger still contains **35 criteria, 294 records, 294 unique record IDs**;
every record's `acceptance_ids` resolves to those criteria. Its SHA-256 is
`e87115a8b3b0da44d70781ecd10b916a3c41c1da139982fde03cccbfc14d8c39`.
The ledger is unchanged from `ddbeeb4`. This verifies retention and valid links,
not 294 new runtime PASS observations. Prior API, controlled-renderer, disk and
native evidence retains its original qualification and date.

## Changed access and unchanged readers

An independent Python `HTMLParser` walk confirmed exactly one instance of each
of `result-summary`, `result-status`, `result-title`, `result-subtitle`,
`result-total-trips`, `result-outliers`, `result-warnings`, `result-quality`,
`result-metrics`. All nine moved from `clustering-center` to
`clustering-inspector > inspector-result`; the entire summary section text is
identical to `git show cab287f:frontend/index.html`.

`renderInspector(state)` still reads `state.result.data`, toggles `inspector-result`
by saved-result existence, then writes these same IDs. Selection is not a
precondition for populating the summary. `qualityFor` still reads saved
`data_quality`; `metricsFor` reads saved metrics/graph fields. Null and zero
handling, percentage scaling and units are unchanged. `contextFor` still prefers
`analysis.frozen_request` and reads `selection_intent`; its compact context remains
in the center. Cluster/point details use their existing siblings before the moved
overview. All SUM/QLT metric obligations retain readers and values; their current
visual access is the right overview or existing responsive drawer. MT diagnostics
retain the existing expandable details access. FRZ source/snapshot/request fields
retain their context reader and saved identity.

The final controller diff against both `cab287f` and `ddbeeb4` contains two changed
docking conditions, two guarded scroll assignments and two focus-call changes: right-panel docking at
`innerWidth >= 1320` no longer requires selected details; `selectCluster` and
`selectPoint` reset the inspector's `scrollTop` after rendering non-null newly selected
details. Returning from cluster or point details now calls the same parent's
`focus()` without `preventScroll`, allowing the browser to reveal the focused
parent below the moved overview. Null selection does not trigger either added
scroll reset. Independent source inspection confirms that ordinary inspector rerenders
contain no added scroll reset. The focused regression
`test_selection_reveals_details_after_scrolled_overview_without_resetting_rerenders`
checks cluster and point close controls are in view after selection, an ordinary
rerender preserves scroll position 100, and return focus lands on the expected
visible point or cluster parent. Its reported RED/GREEN execution belongs
to the implementer's evidence; this reviewer inspected the test and final diff
without replaying it. These additions affect access to saved details, not metric
readers or saved identity. `downloadExport` is untouched: it still sends saved `frozen_request`,
`data_snapshot`, `selection_intent` and table sort, preserves abort/current-result
checks, and invokes the unchanged API path. No table membership, row order, metric
formula, frozen-input or workbook projection change is introduced by D-06.

`git diff --name-only ddbeeb4 -- backend ml frontend/js` and the same comparison
against `cab287f` returned only `frontend/js/clustering/controller.js`;
`git diff --numstat` reported 6 added / 4 removed lines. Thus business code, ML,
API and XLSX writer are source-unchanged. The pre-existing coordinate cache working
change is explicitly outside this audit; Git reports no semantic content diff for
it in those comparisons. The additional actual downloaded-workbook check below
independently verifies the ordinary Geography export success path.

## Independent fresh checks

Environment: Python 3.12.14, existing repository `.venv`, working directory above.

```powershell
C:/folder/Python/AI_logistics_clean/.venv/Scripts/python.exe -m pytest tests/test_dashboard_economic_compatibility.py -q -p no:cacheprovider --basetemp=.scratch/12-independent-numeric-tmp
```

Observed: **7 passed, zero skipped** (exit 0). The test constants were independently
inspected: partial coverage retains canonical weighted price 200 and rate 20 from
20 valid trips while the historical 110-trip denominator retains legacy
118.18181818181819 and 11.818181818181818. Distinct metric denominators preserve
250 / 25 / 10 in the weighted case; the equal-trip example preserves rate 12.5,
which differs from 200 / 15. Missing/nonpositive values and nonpositive trip weights
remain unavailable rather than zero. These are synthetic service executions with
hand constants, not production-data verification.

The ledger/count/link and HTML parent/uniqueness/section-equality assertions were
executed using Python standard-library JSON, `HTMLParser`, `re` and `subprocess`
against current files and `git show cab287f:frontend/index.html`; all passed.
Their essential reproduction is: parse both HTML files, collect ID ancestor paths,
require all nine current paths contain `clustering-inspector` and `inspector-result`,
require each ID occurs once, compare the `result-summary` section text, and assert
all ledger record acceptance IDs are members of its criteria IDs.

## Pinned source hashes

SHA-256 of reviewed file bytes; semantic equality comparison normalizes CRLF/LF.

| File | SHA-256 | Equal to ddbeeb4 |
|---|---|---|
| frontend/js/clustering/inspector.js | d6a93fcdcdf09cea3fdceab40e9ef957c0225298dcc3c280a0385f1ad9f39576 | Yes |
| frontend/js/clustering/formatters.js | cb7d918d935b7df61a2bf5de12f7c7294c0688daa081c40cd661769355cb4679 | Yes |
| frontend/js/clustering/table.js | 3457d0a6164d2ee954425d9c5092289b0b44292c87273166e34267711f6b562f | Yes |
| frontend/js/clustering/comparison.js | c637d31a91ca21cbbc358830a780986bb9de35430083ca77f65846767cccd23c | Yes |
| frontend/js/clustering/state.js | cce83dff4a98d8872ff4356460011c9f5c2792ccf9de1f3536ae9b46887dc6da | Yes |
| backend/services/clustering_service.py | febef672f788004c3e5265b70270d90bbfffbd4a07ac5a902e5ce737e50b53cb | Yes |
| backend/services/xlsx_export.py | 6e9893437352a3fb2c6759ec01e08ddb29702c5406ebc20f6d506486c3388518 | Yes |
| frontend/js/clustering/controller.js | 6ef160cedf36768fa374ecea6452fdf1cd4051d6d0a585bbf06f0a73262cf40b | Docking conditions, guarded selection scroll resets and parent focus reveal |
| frontend/index.html | ace8a119bfd513e32a2394e1911c9b644d1ffb4c5bde652667c170385e827176 | Summary placement |
| frontend/css/style.css | 2311531ff82c9fd23d705e7547b980b148902e7c34184d3d9289655488fcd585 | Layout styling |

## Additional actual browser-downloaded workbook oracle

Independently executed after the implementer's actual headless Edge
`btn-export-clustering` click completed a browser download. Browser action evidence:
`.scratch/sidebar-20261016/delivery-download.json`; this reviewer independently
opened the completed disk file, rather than treating its HTTP status or UI message
as successful output. The click itself was not independently replayed.

File: `.scratch/sidebar-20261016/delivery-downloads/product-geography-de15634942e7.xlsx`,
16,052 bytes, SHA-256
`c284e9a38aa9323fa921e20e3661b4a32f2f4df7e7bc0147884a98eafbbe29ba`.
Approved synthetic source: `.scratch/dashboard-ux-runtime/synthetic.csv`, 89 data
rows, SHA-256 `50a70f8c017d94f97daf10326c5e72e1ced5583ac7caefc0c0b40b45cc403f1f`.
Saved snapshot: `de15634942e7a41edc1c8230c375d682fb284a57aec59c3eec97adef4584e877`.

Command: standard-library Python here-string piped to
`C:/folder/Python/AI_logistics_clean/.venv/Scripts/python.exe -` in the reviewed
checkout. It opened ZIP/OOXML using `zipfile` and `xml.etree.ElementTree`, read the
CSV using `csv.DictReader`, independently selected origin `a`, destination Region A,
period `current`, price `spot`, and asserted the following. Actual result: **PASS,
exit 0**. No production parser, metric helper or XLSX writer was used as the oracle.

- ZIP integrity passed; all five worksheets parsed; no worksheet formula nodes.
- Exactly 73 unique exported `source_row_id` values equal the independently
  selected 73 source rows. IDs were reconstructed from their original 1-based CSV
  row positions with `blake2b(f'{snapshot}:{i}', digest_size=8).hexdigest()`.
  No duplicate, missing or extra row IDs. Every destination ID, origin, period,
  price segment, period ID, tonnage ID, raw price, route, derived price/route and
  trip count reconciled to the selected CSV record.
- Exactly 12 destination IDs, 190 machines, three cluster rows, and all 14 table
  columns. Detail rows / unique destinations / machines are respectively
  **65 / 4 / 110**, **4 / 4 / 40**, **4 / 4 / 40**. Each detail row's visible cluster
  agrees with its table row and sheet mapping. Machine sorting is descending.
- All table values reconciled: point counts 4 each, machine counts 110/40/40,
  shares 110/190 and 40/190, route 100, all four price distribution/mean cells
  1000, all four rate cells 10, and both displayed economic coverage percentages
  100%. Per-metric coverage context agrees with the 4 valid points and respective
  110/40/40 valid and total machines.
- Complete detail order reconciled independently: destination IDs ascending, with
  each destination's selected original source rows newest first. All sheet mapping
  source-row counts agree with actual rows. The context's source count is 73.
- Frozen request exactly matches Geography / Auto K / origin `a` / Region A /
  current / spot / unrestricted vehicle and tonnage filters. Context table sort
  is `trip_count desc`. CSV selection is driven by those approved constants,
  independently of exported detail membership.

This fresh successful output check supersedes the earlier scope exclusion for an
actual workbook reopen. It does not replay adversarial strings, missing/zero
fixtures, cancellation/failure/retry, other modes, or human Excel acceptance.
The recorded workbook export timestamp is its runtime metadata; it does not
independently establish host clock accuracy or a later source revision.

Skipped: duplicate full suites, fresh 294-record runtime replay, adversarial XLSX
replay, and native/human visual acceptance. Risk: unchanged numeric and
writer source does not establish visibility, final-HEAD CI, human acceptance or
production readiness; those remain separately evidenced or UNVERIFIED.
