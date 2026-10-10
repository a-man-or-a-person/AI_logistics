# NPI-01 Implementation Report

Date: 2026-10-10 (Europe/Moscow). Scope: documentation and contract discovery only.
Publication/review evidence is appended after verification; this is not acceptance
of the entire NEXT Product iteration or readiness to integrate ATI.

## Verified baseline and preserved workspace

- Fetched `origin/main`: `9f665ed07f01e341b21fa6d385458725e29217de`.
- [PR #5](https://github.com/a-man-or-a-person/AI_logistics/pull/5): merged,
  merge SHA `3e27230ed61bfb84d7b45452aa7512652c23c474`.
- [PR #6](https://github.com/a-man-or-a-person/AI_logistics/pull/6): merged,
  merge SHA `9f665ed07f01e341b21fa6d385458725e29217de`.
- Both merge commits verified as ancestors of fetched main. Clean isolated
  branch `docs/npi01-pulse-ati-contract`, worktree `.worktrees/npi01` started there.
  Original checkout and existing untracked artifacts preserved.
- Read existing issue, approved spec, tracker, implementation order, coverage matrix,
  shared execution requirements and root CONTEXT.md. There is no iteration-local
  CONTEXT.md. Historical baseline/P1/P2 statements in the approved planning files
  are not rewritten as current evidence.

## Exact change scope

Published files:

- `docs/pulse_ati_readiness.md`: actual ingestion, repository, dataset, coordinate,
  snapshot/detail and mode contracts; separate NEXT origin-set requirements;
  ATI UNKNOWN register and prerequisites.
- `docs/architecture/current-state.md`: one navigation link to the contract.
- `docs/clustering_product_v1_contract.md`: clarify the existing point-row slice
  validation, avoiding an unsupported exact-membership guarantee.
- `docs/npi01_implementation_report.md`: acceptance, checks and review evidence.

Local tracker updates (existing untracked planning artifacts, not published wholesale):
`.scratch/next-product-iteration/issues/01-pulse-ati-readiness.md`, `tracker.md`.
No changed production code, tests, fixtures, exports, dependencies, manifests or CI
configuration. No confidential input/derived data, credential or source sample added.

## Contract findings

Pulse is a local CSV input, not a remote ingest client. `units` maps to Product
ruble price; `bid_count` to integer machine weights; supplied route length is km.
Scalar origin/region rows pool by destination FIAS. Each metric has its own valid
positive-trip denominator and coverage. Price/rate table distributions are over
destination points; generic/Bear/regional summaries have separate weighting paths.

Repository already owns lazy catalog/scope/facets/aggregate/detail and file revision;
service owns orchestration/caches, coordinates are separate, adapters own mode
semantics. `records_factory` does not replace dataset building, revisions or detail.
FIAS is identity, but coordinates use name/region lookup and `unverified_cache`.
File metadata tokens are not upstream immutable snapshots. Detail IDs bind snapshot
to row ordinal, not cross-revision business identity. Current point rows validate a
cached data slice, not exact active mode membership. NEXT origin-set/exact saved
membership/export contracts remain deferred.

ATI availability, owner, access/license/sample/schema, field mappings/grain/identity,
machine volume, currency/units, periods/forecast, quality, revisions/update cadence,
paging, coordinates and capacity are explicitly UNKNOWN with blocked activities.
Safe integration needs approved evidence, stable consistent revisions/rows,
reconciliation and capability/frozen-result validation; no invented ATI interface.
Full traceability is in [readiness document](pulse_ati_readiness.md).

## Exact acceptance coverage

Environment for every row: source/document inspection at the verified baseline in
the isolated Windows worktree, using safe existing synthetic contract tests.
Expected/actual below establish documentation correctness, not ATI runtime behavior.

| ID | Action/input | Expected | Actual/evidence | Result / limitation |
|---|---|---|---|---|
| R4-01 | Trace loader → repository → service → dataset/adapters | Actual ownership and Pulse assumptions; factory not a full source port | Readiness CURRENT ingestion/responsibilities/grain sections cite named code symbols and describe separate factory/dataset/token/detail paths | PASS; repository source only, no remote Pulse audit |
| R4-02 | Compare spec/issue gap lists with register | Every mapping/access/owner/schema/unit/period/revision/paging gap UNKNOWN and blocked work named | ATI register explicitly covers all requested items, including availability, access/license/sample, quality/cadence/volume | PASS; no ATI facts or mappings verified |
| R4-03 | Trace accumulator, coordinate resolver, tokens and paged detail | Grain/weights/revisions/identity/paging/capability prerequisites correct | CURRENT weights/modes/snapshots sections; separate NEXT origin-set section; independent metric weights, metadata limitations and row ordinal identity explicit | PASS; NEXT multi-origin/detail/export runtime not executed |
| R4-04 | Inspect complete file scope and runtime labels | Documentation only; runtime still Pulse; no selector/interface/provider | Only four Markdown files published; referenced service/UI retain Pulse wording | PASS; no new browser walkthrough needed for unchanged UI |
| R4-05 | Review prerequisites, forecast language and published content | Required integration evidence; external forecast separate; safe content | Preconditions section, period/forecast treatment and UNKNOWN register; no customer rows/credentials/examples included | PASS; ATI access/licensing/capacity remain unknown |

All five exact NPI-01 criteria covered. US-41 is addressed. Downstream runtime/UI/XLSX
criteria remain with their owners and NPI-12; no integrated release PASS inferred.

## Lightweight verification

- Python 3.12.14, existing `.codex-impl-env` interpreter.
- `python -m pytest tests/ml/test_clustering_repository.py tests/ml/test_pulse_semantics.py tests/test_product_cluster_table.py tests/test_clustering_product_api.py -q --basetemp=.codex-pytest-tmp-npi01`
  completed successfully: 104 tests, no skips. Existing synthetic tests only.
- `git diff --check`: passed.
- Inline assertion check: all local Markdown targets exist, all five R4 criterion
  IDs are present, all 17 ATI register entries explicitly say UNKNOWN and name
  blocked work, changed scope contains only the four listed Markdown files.
- Documentation links/source symbols, exact criterion coverage and documentation-only
  scope checked against code. Publication has the existing GitHub Actions
  `verification` gate, including locked dependencies, Ruff, Python and mandatory
  Node/Edge checks; result recorded after it completes.
- No `/tdd`, manufactured RED/GREEN or test additions. No local full runtime/browser
  acceptance for a documentation-only change; GitHub CI runs the existing full gate.

## Review and publication

Independent Standards review: PASS, no blocking violations. One optional consistency
suggestion was resolved by clarifying the canonical Product point-row contract.
Independent Spec review: PASS, zero findings against exact R4-01 through R4-05.
Both reviews use fixed baseline `9f665ed` and reviewed implementation through
`712741e`; subsequent report edits record evidence only.

Ponytail technical review: this change documents the actual Pulse flow and names
the prerequisites for future ATI work. Checked connected ingestion, aggregation,
coordinates, cache/detail validation, adapters and synthetic regression coverage.
No correctness, confidentiality, scope or speculative-abstraction blockers found.
Verdict: Ship, subject to required CI. Existing metadata-token, currency and
slice-validation limits are documented; repairing them is outside this ticket.

Publication: narrow documentation PR against main, no automatic merge. The PR body
and existing local ticket evidence record the final candidate SHA, actual GitHub
Actions verification run/job URL and final READY TO MERGE decision after CI. This
committed report does not claim that an as-yet-unpublished commit passed its own CI.
ATI integration and production capacity remain UNKNOWN/UNVERIFIED.
