# Preservation and independent validation

Date: 12 October 2026, Europe/Moscow. Original retrospective: `b5abd6c35479fced48c13cae4d223e08e7b66b32`; source branch `docs/development-retrospective`, source worktree under the historical repository's `.worktrees/development-retrospective`. All ten documents were committed; no tracked/untracked additions were present in that worktree. This supplement and one confirmed correction are a separate follow-up commit; original history is retained.

## Preservation

An independent local archive named `AI_logistics-retrospective-preservation-20261012-v2` beside the historical repository holds the exact ten files under `original-git-bytes`, `original-git-sha256-manifest.json`, the earlier ZIP/CRLF export and `retrospective.bundle`. `git bundle verify` confirms complete history and the original branch ref. An independent bare clone of that bundle contains the full original SHA and passed `git fsck --full`. Raw Git blob exports and re-read restore blobs are checked against the original Git blobs and manifest. The initial Windows ZIP export converted LF to CRLF; it is retained, but the authoritative file export is the separately verified raw Git blob export. The archive remains local and is not published; historical repositories, backups and worktrees are retained.

The older stage1 bundle lacks the retrospective branch/ref and was created before it; it is not relied upon for this preservation. A clean independent clone exists. Both publication branches use main baseline `f95b9bb9253fa6ca6333ef7c2a2244a6740e6928`; PR #19 is confirmed merged. Neither the old main checkout nor the historical retrospective worktree is edited.

| Original file | SHA-256 of original Git bytes |
|---|---|
| agent-inventory.md | `80898785b7f946499372c1ccad52114bfbf0770f7b2ffc880f7c97771fe1e257` |
| agent-scorecards.md | `2c8bd9352ed7377d920d41d8e079f3ff2ae89abc528ba673922bee4aa10eafbd` |
| evidence-index.md | `41de6de00bd0fd28a3cbdd6b30a34304fe78a73d8cb691cf3a768520f178b27a` |
| executive-summary.md | `4de97a05284cda98e3010bf9f5050c22a86b2ef474f78749499de362f740bbcb` |
| improvement-backlog.md | `895d60c54cc32e4d3b0432acb22bec4a52791165047f92d5f0089f8347719be5` |
| iteration-timeline.md | `496afa45993cb4c462d4c0484492adc1431b573678fd183084c315cede4c7311` |
| process-failures.md | `30c00b2878e297f4bebd9d62db9662f1b0eff89e8908990c6de864e0b684a3af` |
| review-effectiveness.md | `114c6b599569aa5a121ccabf0cbd275ed4bf8fdfbe7a5842941c89439ff9f33d` |
| testing-and-ci.md | `d90020df4edb0b61b4e62898605050f0dd0b7437a3cc78ab9f461c0ec5b847b2` |
| workflow-v2.md | `696bd017f6acc9e9f43ab7eea2955b59b0de3e03b826773f4e41c53cd2806c15` |

These hashes describe the preserved original, not the corrected publication version.

## Significant claims and independent critique

The separate read-only agent `retrospective_review` read all ten documents and primary AGENTS/domain/tracker/NPI execution requirements, initial acceptance, NPI07/NPI10 reviews, NPI12 startup/capacity/supplement/report and Graphify comparative/quantitative evidence. Private metadata was inspected locally without copying transcripts or IDs into publication.

| Claim | Classification / evidence and limit |
|---|---|
| Nine role groups | CONFIRMED analytical groups in inventory; unique agent headcount UNKNOWN. |
| 110 spawn records | CONFIRMED documented cutoff/predicate: 49 root + 92 guardian + 110 spawn = 251 records; complete lifetime census UNKNOWN. |
| 103 current/cache skills, 27 historical names | CONFIRMED physical/catalog rows and historical read attempts; enabled providers and successful invocation totals UNKNOWN. |
| 45 CI jobs, 101 minutes 53 seconds | CONFIRMED fresh GET collection and all 45 jobs: 6113 seconds from started/completed timestamps; 27 PR / 18 push, 43 success / 2 failure. Not whole-task time or cost. |
| Standards / Spec / Ponytail independence | CONFIRMED existence of separate role threads and sampled primary review findings; exhaustive independent runtime replay UNKNOWN. |
| P1/P2/Freshness and later cache/focus/export repairs | CONFIRMED historical reports/reviews/commits; no claim that production tests were freshly replayed for this documentation task. |
| Risk routing reduces duplicate work | INFERRED proposal supported by overlapping findings; real time/token/cost savings UNKNOWN. |
| Worktree/evidence accumulation | CONFIRMED historical recorded registrations and independently counted 315 tracked evidence files / 71,036,036 bytes; waste magnitude INFERRED. |
| Functional versus human/production acceptance | CONFIRMED recorded functional scope and explicit UNVERIFIED human/production gates; no new business acceptance. |

Review findings: **BLOCKER 0 / MAJOR 0 / MINOR 1**. The MINOR arithmetic error in [testing-and-ci](testing-and-ci.md) is corrected from 837 to **872 seconds** for the three PR #19 jobs: 277 + 273 + 322. The early-pair 550 seconds and combined counterfactual 699 seconds remain correct. The reviewer independently verified the ledger; the implementer also recollected the hosted jobs through GitHub GET API. No historical fact or role score is reconstructed.

## Publication checks and limits

All 35 original local links exist; all 30 unique pinned GitHub blob targets resolve in local Git. Historical PR references match the fresh 19-merged-PR collection; referenced CI run/job IDs and results are checked through the hosted API. Git revision targets are checked locally. Document contents and links were reviewed for private rows, credentials, mappings and authentication profiles; none observed in the publication allowlist. The only additional file is this compact supplement. Markdown fences/table structure, scope and `git diff --check` are checked before commit.

Baseline main [Quality run](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38183300676/job/114600241225) succeeded, including frontend zero-skip rejection. Final publication-HEAD CI is pending at commit time and will be recorded in the PR after completion. Existing CI is unchanged. Effective branch protection is UNKNOWN: the connected app's protection GET returns 403 (administration permission unavailable); settings are preserved.

Active VS Code workspace could not be established from sandbox process/workspace-state access. The supplied task workspace is the historical repository; Git paths/branches/HEADs and independent clones are established directly. No claim is made about a current editor window or running server. No browser/product suite is rerun locally for these docs-only changes; mandatory hosted Quality still applies to final HEAD. Full external website availability and exhaustive historical actor attribution remain UNKNOWN.
