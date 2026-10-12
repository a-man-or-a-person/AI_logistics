# Agent Development Workflow v2

Owner: the accountable implementer maintains task delivery; this file owns development, review, readiness and evidence policy. AGENTS owns entry points; domain.md owns domain discovery; issue-tracker.md owns ticket layout; Product contracts own behavior; quality.yml owns executable CI. Historical reports remain evidence.

Source: development retrospective (publication PR linked in the PR body), original commit `b5abd6c35479fced48c13cae4d223e08e7b66b32`. The evidence links below target files already present in merged main at `f95b9bb9253fa6ca6333ef7c2a2244a6740e6928`, so this workflow can merge independently of the retrospective. Recommendations about efficiency are hypotheses pending a five-task pilot.

## Before development

1. Print absolute repository/worktree path, remote URL, branch, HEAD and status. Fetch main in a safe clone; record origin/main SHA and confirm the intended base and clean tracked state. Preserve existing changes; create an isolated task branch, adding a worktree only when isolation requires one. Never switch someone else's checkout.
2. Read the ticket/spec and domain pointers. Record observable inputs/outputs, acceptance IDs, source identity, failure/recovery and frozen/editable boundaries. Assign one accountable implementer and criterion owner. Check adjacent callers, tests, fixtures, configuration, exports and CURRENT documents; retain approved Product/RESEARCH/LEGACY boundaries.
3. Classify the highest affected risk below and select gates. Resolve contract/ADR conflicts explicitly. An approved ticket's stronger obligations and repository required checks override the default matrix. Missing reviewer/tool access is UNVERIFIED, not an independent PASS.

## Review routing

| Risk | Scope | Review and applicable checks |
|---|---|---|
| LOW | Documentation or isolated edit without behavior change | One accountable implementer; one lightweight content reviewer plus narrow conventions, links, privacy and diff checks; unchanged mandatory CI. |
| MEDIUM | Frontend/API behavior and interactions | Independent Spec; targeted public-contract and neighbor tests; early real Flask smoke, real Edge mouse/keyboard smoke for UI. Add Standards for new ownership/infrastructure seams. |
| HIGH | Architecture, data, metrics, caches, snapshot consistency, export completeness, security | Independent Spec and Standards; targeted Ponytail axis for implementation/failure/load risks. Separate third agent when it adds independent expertise or the ticket requires it. Independent numerical/output oracles, integration checks and full mandatory CI. |
| RELEASE / FINAL ACCEPTANCE | Cross-feature delivery | Owner executes the approved acceptance matrix on actual merged main, confirms main CI and served revision; independent reviewer checks integration evidence and verdict, replaying disputed/high-risk scenarios when needed. Human and production gates stay separate. |

Cache/focus UI changes are HIGH when they affect saved identity or snapshot consistency; focus-only presentation can remain MEDIUM. Required tests do not become optional because fewer reviewers are dispatched. Architecture-only HIGH keeps Standards and Spec; data/security HIGH retains all three axes, even when a targeted Ponytail pass shares a reviewer with a clearly labeled scope.

Existing NPI shared execution requirements require Standards, Spec and Ponytail. That obligation is preserved for those published tickets and dedicated P1/P2 remediations. The matrix governs new work without a stronger approved contract; replacing an existing mandatory gate requires an explicit, separately justified contract amendment. Global skills and branch protection are not edited by this policy.

## Reviewer protocol

| Axis | Responsibility |
|---|---|
| Standards | Architecture boundaries, ownership, dependency direction, maintainability, infrastructure conventions, cross-component invariants. |
| Spec | Observable behavior, contracts, acceptance criteria, edge cases, invariants, behavioral regression. |
| Ponytail | Connected implementation paths, hidden coupling, failure handling, operational/load risks, unnecessary complexity and risky gaps in tests. |

Give each reviewer fixed base/head SHAs, ticket/contract pointers, changed scope and completion criteria. Each verdict records: reviewer/session and independent or self-review; scope reviewed; exact reviewed SHA; independently inspected/reproduced facts and commands; evidence references; findings with BLOCKER/MAJOR/MINOR/ADVISORY severity; what was NOT verified; final recommendation.

PASS requires the reviewer's own source/evidence inspection or execution within that stated scope. Reading another PASS alone is insufficient. Evidence inspection is not runtime replay. Merge duplicate findings by root cause in one PR ledger, preserving authors, independent checks, severity, fix/disposition and repeat-check. BLOCKER/MAJOR findings remain merge blockers until fixed or explicitly adjudicated by the authorized owner with evidence. Three headings in one agent response are self-review, not three independent agents.

## Implementation and verification

Use the smallest complete change and existing seams. Keep validation, error handling, cancellation and supported callers during extraction. Preserve a working increment before broad changes. Disjoint ready tasks may be delegated with a file owner and allowed scope; shared state is edited by one owner.

For reproducible defects, execute a minimal public-seam regression on unchanged baseline (RED), then fix and rerun it and affected neighbors (GREEN). Separate setup/fixture failures from behavioral failures. Documentation and already conformant behavior need verification, not artificial RED. Reuse approved test seams; a new business meaning needs an explicit decision.

During development use focused tests. Run early real Flask smoke at the first usable changed API/UI transition; UI behavior also needs native Edge rendered state, mouse/keyboard, focus and observed HTTP. Keep unit, API, browser, integration and human evidence labeled separately.

For affected lifecycle contracts, record expected → observed for: fresh/cache hit and A→B→A reentry; form edits versus frozen display/export; stale source/coordinate generation and in-flight conflict; failed refresh → retry → successful fresh rows; cancel/late success/error; eviction/restart; parent selection/removal; native focus/scroll restoration. Mark genuinely unaffected transitions N/A with a reason; retain ticket-mandated branches.

Metrics/data require independently hand-calculated constants with metric-valid denominators, membership and source-row reconciliation. Export requires an actual downloaded XLSX independently reopened: full row IDs/count/order, saved request/provenance/membership, types, missing versus zero, literal formula-like strings, leading-zero IDs, legal unique sheet names and generation/error completeness. HTTP 200 alone is insufficient.

After the last production/test change, run the full required local suite when the environment is available; preserve every stronger ticket requirement. Report-only edits need focused document checks locally, while final-HEAD hosted CI stays full. New code/test/environment changes, integration conflicts or unresolved concerns require renewed affected checks. Record interpreter, locked dependencies, Node/Edge and temp paths before diagnosing a test failure.

The existing [Quality workflow](../../.github/workflows/quality.yml) remains unchanged: locked install, dependency check, Ruff, Node/Edge startup, frontend tests with empty/skipped-case rejection, Python suite. A missing browser, skipped mandatory test or failed gate blocks readiness. Record the exact PR head and successful run/job links; verify that the PR run belongs to that head (including the tested merge SHA when applicable). A new HEAD invalidates previous final-HEAD CI. Preserve effective branch-protection checks; unavailable protection reads remain UNKNOWN.

Batch report/evidence before publishing the final candidate. CI results arriving later belong in a timestamped PR supplement with exact head/run/job, rather than a self-referential claim inside the commit awaiting CI.

## Definition of Done

Record these statuses separately, with PASS/FAIL/UNVERIFIED and evidence. CI never automatically promotes later statuses.

| Status | Evidence required | Accountable owner |
|---|---|---|
| IMPLEMENTED | Owned criteria implemented; callers/tests/fixtures/docs consistent; base/head recorded | Implementer |
| VERIFIED | All applicable required checks executed; genuine defect RED/GREEN, applicable live/output oracles and limitations recorded | Implementer |
| READY TO MERGE | VERIFIED; required reviews/dispositions, privacy/scope/link checks, full successful final-HEAD CI and applicable required approvals | PR owner |
| MERGED & INTEGRATED | Authorized merge; actual merged-main SHA, main CI and affected integration smoke | Integration owner |
| FUNCTIONALLY ACCEPTED | Exact revision/URL, approved scenario matrix and real observed actions/outputs with open limitations | Acceptance owner |
| HUMAN ACCEPTED | Named responsible human completes the prescribed manual walkthrough and explicitly accepts the exact revision/UI/workbook for intended business use; record actions and result | Product owner and accepting логист |
| PRODUCTION READY | Human acceptance plus intended workload, latency, concurrency, memory, retention, worker routing, security and operations evidenced, or explicit authorized exceptions | Product/operations owner |

Automated headed Edge remains automated functional evidence. Synthetic capacity results establish the tested fixture only. Unknown human acceptance or production requirements remain UNVERIFIED even after merge.

## Delivery and worktree lifecycle

Fetch main → verify clean base → isolated branch/worktree if needed → implement → verify → open PR → final-HEAD CI → authorized merge → verify integrated main → archive unique artifacts → confirm cleanup eligibility.

Before handing off a running application, record absolute checkout, branch/HEAD, remote revision, interpreter/entry point, approved input source, process/listening port and exact URL. Fetch `/` and changed frontend assets and compare their bytes/hashes with the intended checkout. Use the documented `run.py` with an explicit free port; observe a changed native UI transition. Identify a busy port's owner and preserve unrelated processes. A URL or successful test in another worktree does not prove which revision the user sees.

Cleanup is a separate authorized action after confirming the branch is integrated, owned processes stopped and worktree no longer needed. Inspect tracked, untracked AND ignored files; archive unique evidence and private/user files with verified manifest/recovery before any removal. Confirm resolved paths belong to the task. Never use automatic `git clean -fdx`. This implementation task preserves every old repository, backup and worktree.

## Evidence retention

Keep in Git compact acceptance summaries, findings/dispositions, pinned source references, deterministic safe fixtures, essential reproduction commands and small unique critical evidence. Each substantial PASS includes criterion, base/head, environment, input/action, expected/observed, command/result and a durable reproduction/source path.

Keep bulky traces, full browser logs, repeated screenshots, generated datasets/workbooks and necessary runtime profiles in CI artifacts or a local archive with a manifest. Record storage/availability at creation; no arbitrary universal expiry. Before artifacts expire or are removed, preserve enough durable critical evidence to verify the claim. A deleted/expired artifact cannot be the only PASS source. Refer to unchanged earlier evidence once, replay changed transitions, retain historical evidence.

Publish no private Pulse/actual rows, credentials, confidential mappings/business data or temporary authentication profiles. Scan the explicit publication allowlist and links before push; a local source reference does not authorize exporting its contents.

## PR verification record

Use the existing PR writing format and include: risk/why; implementer and reviewers/scopes; base and final head; criteria/expected→observed; commands/results/environment; unique findings/dispositions; UI served revision/URL/smoke when applicable; metric reconciliation and reopened workbook when applicable; exact CI run/job; human/production status and limits. Mark N/A with reasons. Check Markdown, local/pinned external targets, `git diff --check`, private-data absence and production scope before publication.

## Change rationale and ownership

| Owner / BEFORE → AFTER | Retrospective evidence on merged main | Expected impact |
|---|---|---|
| AGENTS: two discovery pointers → brief preflight/development/delivery rules with one policy pointer | [NPI-12 startup](../npi12-evidence/startup.json) | Deliver the intended checkout instead of old port 5055 UI. |
| This policy, review: repeated three broad passes → risk routing with stronger-ticket override and explicit independence | [NPI-10 Spec](../npi10-evidence/spec-review.md), [Ponytail](../npi10-evidence/ponytail-review.md), [NPI-12 review limits](../npi12-evidence/review-supplement.md) | Reduce duplicate dispatches while retaining data/security oracles; time savings unmeasured. |
| This policy, verification/DoD: scattered statuses → explicit owners, lifecycle checks and separate readiness evidence | [Freshness Spec](../pulse-freshness-evidence/spec-review.md), [NPI-07 Ponytail](../npi07-evidence/ponytail-review.md), [NPI-12 matrix](../npi12-evidence/acceptance-matrix.md) | Find state failures early; avoid conflating green CI with human/production acceptance. |
| This policy, evidence: bulk committed logs → compact durable proof and archived bulk; preserve existing evidence | [NPI-12 manifest](../npi12-evidence/artifact-manifest.json) and [reproduction](../npi12-evidence/README.md) | Smaller new review artifacts without unverifiable PASS claims. |

No canonical general development/review/DoD policy or PR template existed in main; one policy owns these rules instead of modifying historical review verdicts. Product workflow remains the Product behavior owner. Domain discovery and executable CI already cover their scopes and need no duplicate policy edits.

## Paper walkthroughs

| Task | Risk / implementer / reviewers | Required tests and merge gate | Evidence and worktree disposition |
|---|---|---|---|
| A. Fix a broken documentation link | LOW; one implementer, one content reviewer | Resolve target, Markdown/privacy/diff checks; existing full final-head Quality and required approvals. No fictional RED/browser replay. | Before/after link, base/head, reviewer scope, CI job; reuse isolated branch, cleanup only after authorized merge and file/archive checks. |
| B. Cached UI reentry loses focus | HIGH for shared cache lifecycle (MEDIUM only if demonstrated focus-only); one implementer, independent Spec/Standards, targeted Ponytail axis | Genuine baseline RED; Node state + real Flask/Edge cached A→B→A, edit/frozen/retry/cancel/late-response/focus regressions as affected; full local/hosted gates, no mandatory skips. Published NPI obligation retains all three reviewers. | Observed requests/DOM/focus, served path/SHA/URL, findings and exact CI; archive unique replay evidence, preserve ignored files, cleanup separately authorized. |
| C. Change complete saved XLSX export | HIGH; one implementer, independent Spec/Standards and targeted Ponytail | Independent source IDs/weights/provenance oracle, reopened downloaded workbook, literal/type/name/completeness checks, generation conflict and failed/cancelled output; integration/full CI and resolved blockers. | Reconciliation constants/counts, inspection summary/reproduction, review limits, exact HEAD/job; archive bulky safe workbook locally; cleanup only after integrated-main and preservation checks. |

Run the five-task pilot using comparable risk: review turns/unique findings/duplicates, repeated full runs, CI minutes, new evidence bytes and escaped defects. Extra independent replay follows observed gaps. No elapsed-time or token savings are claimed before measurement.
