# Индекс доказательств

Срез: 12 октября 2026 (Europe/Moscow). GitHub проверен через connected GET API; origin/main получен git fetch. База f95b9bb9253fa6ca6333ef7c2a2244a6740e6928. Отчётная ветка docs/development-retrospective, исходный root checkout не менялся. Десять final документов — единственный publishable scope; локальный research note не включается.

## Метод и confidence

- **CONFIRMED:** наблюдение в первичном artifact/API/Git/structured metadata; для historical report это подтверждение записанного результата, а не новое исполнение.
- **INFERRED:** причинный/оптимизационный вывод, который допускает другие объяснения.
- **UNKNOWN/N/A:** источник отсутствует, выборка неполна или измерение несопоставимо.

Git author не атрибутирует AI действия. Role не равен person/thread. Skill не равен агент; CLI/test/CI не являются независимыми reviewers. Raw prompts/datasets/browser profiles не публикуются. Read attempt skill body не означает successful invocation. Работа этой ретроспективы не включена в historical agent/worktree/CI counts.

## Реестр источников

| ID | Источник | Что доказывает / граница |
|---|---|---|
| E01 | [AGENTS](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/AGENTS.md), [domain](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/agents/domain.md), [issue tracker](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/agents/issue-tracker.md); local .scratch/next-product-iteration/{spec,execution-requirements,implementation-order,coverage-matrix,tracker}.md | Действующие conventions, утверждённые dependencies и obligations. Local history не публикуется wholesale; stale status не заменяет Git ancestry |
| E02 | [PR collection](https://api.github.com/repos/a-man-or-a-person/AI_logistics/pulls?state=all&per_page=100), PR #1–19 и Git log | Titles/body/merge/head/stats. PR body mutable; observed state сохранён текстом ниже, merge commits immutable |
| E03 | [PR5](https://github.com/a-man-or-a-person/AI_logistics/pull/5), [PR6](https://github.com/a-man-or-a-person/AI_logistics/pull/6); local .scratch/product-final-acceptance/report.md, issues/01-refresh-rejected-snapshot.md, issues/02-sync-cached-mode-controls.md, p2-verification/report.md | Initial13PASS/3FAIL, root causes и reacceptance; local-only scripts/screenshots referenced внутри этих reports, не все перепроверены здесь |
| E04 | [Freshness report](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/pulse_freshness_implementation_report.md), [Spec](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/pulse-freshness-evidence/spec-review.md), [RED race](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/pulse-freshness-evidence/red-calculation-race.txt) | Source revision/presence, in-flight409, genuine baseline RED; metadata не content hash |
| E05 | [NPI07](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi07_implementation_report.md), [Ponytail](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi07-evidence/ponytail-review.md), [NPI08 Spec](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi08-evidence/spec-review.md), [NPI09](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi09_implementation_report.md), [NPI06 card](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/.scratch/next-product-iteration/issues/03-weighted-distance-verification.md) | Cached/focus/summary findings, human medoid decision и metric oracle. 06 card специально committed, большинство scratch files только local |
| E06 | [NPI10](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi10_implementation_report.md), [Spec](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi10-evidence/spec-review.md), [Standards](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi10-evidence/standards-review.md), [Ponytail](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi10-evidence/ponytail-review.md), [reopened HTTP](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi10-evidence/http-download.json) | Complete literal frozen XLSX, duplicate apostrophe finding, provenance; no human Excel claim |
| E07 | [NPI11](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi11_implementation_report.md), [RED/GREEN](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi11-evidence/red-green.md), [inspection](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi11-evidence/workbook-inspection.json) | Native download + independent reopening; two fixture failures distinguish from production |
| E08 | [NPI12](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi12_integrated_acceptance_report.md), [matrix](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi12-evidence/acceptance-matrix.md), [startup](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi12-evidence/startup.json), [measurements](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi12-evidence/measurements.json), [90k timings](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi12-evidence/capacity/timings.json), [review supplement](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi12-evidence/review-supplement.md), [branch observation](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/npi12-evidence/main-branch.json), [PR19](https://github.com/a-man-or-a-person/AI_logistics/pull/19) | Actual candidate596d9fb, old5055, capacity fixture, independent review limits; PR supplement closes G02 after final CI,76PASS/2UV |
| E09 | [Quality workflow](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/.github/workflows/quality.yml), [runs API](https://api.github.com/repos/a-man-or-a-person/AI_logistics/actions/runs?per_page=100), jobs GET per run; local .scratch/product-mode-refactor/ticket09-implementation-report.md | 45 jobs, failure steps, durations; source git ls-files/stat даёт artifact sizes. Required-check effective rule не прочитан |
| E10 | Local Codex sessions: session_meta first-line source.subagent.thread_spawn, cwd filter по project, before current retrospective; relevant named tool-call skill paths | Отдельные threads и read attempts; raw transcripts/IDs не копируются.251 records=49root/92guardian/110spawn, limited local sample, Temp cwd excluded. Private actor/runtime content не является публичным source |
| E11 | [CONTEXT](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/CONTEXT.md), [current architecture](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/architecture/current-state.md), [freeze report](https://github.com/a-man-or-a-person/AI_logistics/blob/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928/docs/clustering_contract_v1_freeze_report.md); Git ccbf086→3ab9c7a (см. timeline); local .scratch/product-mode-refactor/issues/01…09 | Historical architecture/domain, preserved boundaries, refactor plan; no personal attribution by author |
| E12 | Local .scratch/graphify-evaluation/{report,protocol,ground-truth,comparative-review,quantitative-audit,setup-failures,research}.md + A-T1…7/B-T1…7 | Saved controlled navigation experiment, rubric,24graph processes20.368s; no full task token/cost ledger. Not public Git sources |

E10 воспроизводим только на машине владельца: перечислить `$CODEX_HOME/sessions/**/*.jsonl`, прочитать первую строку `session_meta`, включить запись если `timestamp < "2026-10-12T11:17:00Z"` и буквальная подстрока `"Проект ИИ Логистика"` содержится в `cwd`; затем разделить по `source` (root/guardian/subagent.thread_spawn). Это точный cutoff/predicate исследованной выборки, а не календарный итог всех сессий 12 октября. Не считать guardian Product reviewer; named agents сопоставить с saved review artifacts. Session files изменяемы/удаляемы; aggregate snapshot не даёт публично воспроизводимого полного actor ledger. E12 scoring сохранённого эксперимента — historical assessment, не новая runtime проверка.

## PR/merge roster

Все19 PR observed closed+merged; дата/время в следующей таблице UTC. Точный head для #17 включает integration merge main. PR#1 merge SHA совпадает с head; не все integration события обязаны создавать отдельный merge commit.

| PR | Результат | Merged UTC | Head / merge |
|---|---|---|---|
| [#1](https://github.com/a-man-or-a-person/AI_logistics/pull/1) | feat: deliver Product cluster table and Pulse destination drill-down | 2026-10-08T06:53:46Z | `4e74b17` / [`4e74b17`](https://github.com/a-man-or-a-person/AI_logistics/commit/4e74b17dc63928635e0796ae377c2ddcce67fcb7) |
| [#2](https://github.com/a-man-or-a-person/AI_logistics/pull/2) | ci: enforce pytest ruff and frontend verification | 2026-10-10T12:32:06Z | `f69e64c` / [`396bee5`](https://github.com/a-man-or-a-person/AI_logistics/commit/396bee51188482de913254de45f12a2d3e341300) |
| [#3](https://github.com/a-man-or-a-person/AI_logistics/pull/3) | fix: make Product formula tooltips readable on hover and focus | 2026-10-10T13:12:06Z | `fd92a86` / [`0787367`](https://github.com/a-man-or-a-person/AI_logistics/commit/078736702f2d5f5fbf39e9634e5222a72f44a418) |
| [#4](https://github.com/a-man-or-a-person/AI_logistics/pull/4) | fix: Product point detail selected periods and missing economic metrics | 2026-10-10T13:28:17Z | `d5199e5` / [`db1ed64`](https://github.com/a-man-or-a-person/AI_logistics/commit/db1ed6415ee84fec6837a1f7025e5d676fce83f8) |
| [#5](https://github.com/a-man-or-a-person/AI_logistics/pull/5) | fix: recover Product results after rejected snapshots | 2026-10-10T17:15:28Z | `ed28fe6` / [`3e27230`](https://github.com/a-man-or-a-person/AI_logistics/commit/3e27230ed61bfb84d7b45452aa7512652c23c474) |
| [#6](https://github.com/a-man-or-a-person/AI_logistics/pull/6) | fix: keep cached comparison mode and form controls synchronized | 2026-10-10T17:34:32Z | `830d14a` / [`9f665ed`](https://github.com/a-man-or-a-person/AI_logistics/commit/9f665ed07f01e341b21fa6d385458725e29217de) |
| [#7](https://github.com/a-man-or-a-person/AI_logistics/pull/7) | docs: document Pulse contract and ATI unknowns (NPI-01) | 2026-10-10T17:49:56Z | `9e5ade6` / [`73bca25`](https://github.com/a-man-or-a-person/AI_logistics/commit/73bca251387d699bfb4613b4ec826df1289f5c1d) |
| [#8](https://github.com/a-man-or-a-person/AI_logistics/pull/8) | feat: canonical origin union and frozen Product identity (NPI-02) | 2026-10-10T18:17:38Z | `7a95eb6` / [`5923cd9`](https://github.com/a-man-or-a-person/AI_logistics/commit/5923cd90b1ba483f673546a3b28091a9634ee379) |
| [#9](https://github.com/a-man-or-a-person/AI_logistics/pull/9) | test: verify machine-weighted distance and coverage (NPI-06) | 2026-10-10T18:33:43Z | `8048d44` / [`ca89a68`](https://github.com/a-man-or-a-person/AI_logistics/commit/ca89a681ed644d6c18d34d2c90bb7580d3415aef) |
| [#10](https://github.com/a-man-or-a-person/AI_logistics/pull/10) | feat: add generation-safe regional All API (NPI-03) | 2026-10-11T06:10:31Z | `0312959` / [`8fda966`](https://github.com/a-man-or-a-person/AI_logistics/commit/8fda966c1d33288a80d727f7c2ac8f2298a68fe1) |
| [#11](https://github.com/a-man-or-a-person/AI_logistics/pull/11) | feat: multi-origin frontend and shared Product map (NPI-04) | 2026-10-11T11:55:26Z | `fce0b2c` / [`9e77a7d`](https://github.com/a-man-or-a-person/AI_logistics/commit/9e77a7de34cacf52628423b0b83bccbcf9aa8c89) |
| [#12](https://github.com/a-man-or-a-person/AI_logistics/pull/12) | feat: explicit regional All frontend (NPI-05) | 2026-10-11T12:32:27Z | `1958f60` / [`d27d799`](https://github.com/a-man-or-a-person/AI_logistics/commit/d27d799d870cae8012b7c6a42b71c6df761852bd) |
| [#13](https://github.com/a-man-or-a-person/AI_logistics/pull/13) | feat: frozen point origin summary and detail (NPI-07) | 2026-10-11T13:52:26Z | `1a7f91c` / [`e4ec549`](https://github.com/a-man-or-a-person/AI_logistics/commit/e4ec54951d37f10b1c607788bee263fda200911c) |
| [#14](https://github.com/a-man-or-a-person/AI_logistics/pull/14) | fix: validate Pulse freshness before frontend Product cache reuse | 2026-10-11T14:40:25Z | `98ec1a0` / [`6cb7fd8`](https://github.com/a-man-or-a-person/AI_logistics/commit/6cb7fd8e1e488bcde75c927cb41e67ee6bc1d68e) |
| [#15](https://github.com/a-man-or-a-person/AI_logistics/pull/15) | feat: frozen Product drill-up navigation (NPI-08) | 2026-10-11T19:57:30Z | `49ba3ad` / [`53c0037`](https://github.com/a-man-or-a-person/AI_logistics/commit/53c003797961c31c8160b0bfc1b69ea2cfa6c15b) |
| [#16](https://github.com/a-man-or-a-person/AI_logistics/pull/16) | feat: temporary cluster medoid representative (NPI-09) | 2026-10-11T20:40:21Z | `0ff7876` / [`b5df418`](https://github.com/a-man-or-a-person/AI_logistics/commit/b5df41885712a76ee74bbfe6e2fd74cd04771eb8) |
| [#17](https://github.com/a-man-or-a-person/AI_logistics/pull/17) | feat: safe saved Product XLSX export backend (NPI-10) | 2026-10-11T20:44:38Z | `d7778f7` / [`e98eb2c`](https://github.com/a-man-or-a-person/AI_logistics/commit/e98eb2c02accb7a9252b919587e490748c2b64bb) |
| [#18](https://github.com/a-man-or-a-person/AI_logistics/pull/18) | feat: download saved Product XLSX with frozen context (NPI-11) | 2026-10-11T22:05:32Z | `887c07d` / [`596d9fb`](https://github.com/a-man-or-a-person/AI_logistics/commit/596d9fb4276db04c72c569b922c63e74d500035d) |
| [#19](https://github.com/a-man-or-a-person/AI_logistics/pull/19) | docs: complete NPI-12 integrated acceptance and release assessment | 2026-10-11T23:10:48Z | `09e08a6` / [`f95b9bb`](https://github.com/a-man-or-a-person/AI_logistics/commit/f95b9bb9253fa6ca6333ef7c2a2244a6740e6928) |

## GitHub discussion evidence

GET issues/{n}/comments, pulls/{n}/reviews, pulls/{n}/comments для каждого n=1…19 вернул []. Это57 endpoints. Review artifacts и threads существуют вне GitHub review objects; нельзя приписать independent approval GitHub reviewer account по одному PR body.

## CI ledger

45 runs,43success/2failure,27PR/18push-main. Каждый jobs endpoint прочитан. Job elapsed = completed_at−started_at; сумма6113s, медиана88s. Run lifecycle updated−created сумма6284s. Это elapsed, не billing duration/LLM cost. Ни rerun-attempt history, ни deleted runs не восстановлены отдельно. Latest main f95b9bb9253fa6ca6333ef7c2a2244a6740e6928 — success.

| Run | Event | Head | Job elapsed s | Result |
|---|---|---|---:|---|
| [38050412351](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38050412351/job/114208227831) | pull_request | `87430f2` | 71 | failure: Python suite |
| [38051104241](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38051104241/job/114210235521) | pull_request | `f69e64c` | 62 | success |
| [38052310935](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38052310935/job/114213730174) | push | `396bee5` | 62 | success |
| [38054586889](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38054586889/job/114220329117) | pull_request | `fd92a86` | 81 | success |
| [38054813166](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38054813166/job/114220980474) | push | `0787367` | 63 | success |
| [38055575908](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38055575908/job/114223211662) | pull_request | `d5199e5` | 74 | success |
| [38055834910](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38055834910/job/114224095543) | push | `db1ed64` | 59 | success |
| [38069752424](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38069752424/job/114264575235) | pull_request | `a6c27c4` | 79 | success |
| [38069925711](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38069925711/job/114265084652) | pull_request | `ed28fe6` | 88 | success |
| [38070995343](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38070995343/job/114268192332) | push | `3e27230` | 74 | success |
| [38071825760](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38071825760/job/114270612595) | pull_request | `830d14a` | 79 | success |
| [38072298352](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38072298352/job/114272042105) | push | `9f665ed` | 86 | success |
| [38072943912](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38072943912/job/114273946064) | pull_request | `9e5ade6` | 76 | success |
| [38073338408](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38073338408/job/114275099751) | push | `73bca25` | 79 | success |
| [38074728243](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38074728243/job/114279205298) | pull_request | `a32a1f3` | 84 | success |
| [38074768102](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38074768102/job/114279333148) | pull_request | `7a95eb6` | 72 | success |
| [38075193375](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38075193375/job/114280591888) | push | `5923cd9` | 73 | success |
| [38075778507](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38075778507/job/114282314052) | pull_request | `9a78c99` | 74 | success |
| [38075810955](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38075810955/job/114282410126) | pull_request | `abd5b9c` | 75 | success |
| [38075896540](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38075896540/job/114282655399) | pull_request | `8048d44` | 87 | success |
| [38076277035](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38076277035/job/114283763472) | push | `ca89a68` | 73 | success |
| [38082530230](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38082530230/job/114302217167) | pull_request | `0312959` | 77 | success |
| [38117200612](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38117200612/job/114404351076) | push | `8fda966` | 85 | success |
| [38136824505](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38136824505/job/114462290640) | pull_request | `aeafc79` | 104 | failure: Frontend contracts (Node and Edge) |
| [38137091846](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38137091846/job/114463074955) | pull_request | `fce0b2c` | 96 | success |
| [38137338911](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38137338911/job/114463795012) | push | `9e77a7d` | 93 | success |
| [38139177429](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38139177429/job/114469285218) | pull_request | `1958f60` | 123 | success |
| [38139652600](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38139652600/job/114470687098) | push | `d27d799` | 130 | success |
| [38141437996](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38141437996/job/114475950379) | pull_request | `1a7f91c` | 129 | success |
| [38144908987](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38144908987/job/114486122718) | push | `e4ec549` | 100 | success |
| [38146937061](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38146937061/job/114492169621) | pull_request | `98ec1a0` | 174 | success |
| [38148137989](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38148137989/job/114495708736) | push | `6cb7fd8` | 180 | success |
| [38157762448](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38157762448/job/114524156012) | pull_request | `49ba3ad` | 205 | success |
| [38170184262](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38170184262/job/114560979855) | push | `53c0037` | 188 | success |
| [38172123947](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38172123947/job/114566724523) | pull_request | `0ff7876` | 226 | success |
| [38172145456](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38172145456/job/114566789368) | pull_request | `fb9b92f` | 188 | success |
| [38173189356](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38173189356/job/114569947531) | push | `b5df418` | 224 | success |
| [38173212403](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38173212403/job/114570011438) | pull_request | `d7778f7` | 219 | success |
| [38173482318](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38173482318/job/114570837089) | push | `e98eb2c` | 237 | success |
| [38177611267](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38177611267/job/114583212076) | pull_request | `887c07d` | 339 | success |
| [38179023381](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38179023381/job/114587418307) | push | `596d9fb` | 271 | success |
| [38181923754](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38181923754/job/114596123065) | pull_request | `b496f79` | 277 | success |
| [38182156432](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38182156432/job/114596800786) | pull_request | `7e6bdcf` | 273 | success |
| [38182529031](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38182529031/job/114597944872) | pull_request | `09e08a6` | 322 | success |
| [38183300676](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38183300676/job/114600241225) | push | `f95b9bb` | 282 | success |

## Artifact/resource measurements

At pinned main: git rev-list --count HEAD =138. git diff --shortstat ccbf086 HEAD:616files,+372177/−1; baseline is empty initial commit. NPI span git diff --shortstat 9f665ed HEAD:364files,+310078/−254. These contain tests/docs/evidence and binary changes, not production LOC/productivity.

`git log ccbf086..HEAD --no-merges --format=%s`:117 non-merge commits,20 с case-insensitive prefix `fix`; span9f665ed..HEAD:45 non-merge commits,10fix-prefixed. Это reproducible **именование исправлений**, не число distinct bugs, escaped defects или review cycles: один fix может устранять несколько причин, часть repairs называется test/docs/feat. Saved JUnit independently parsed здесь:07 464,Freshness485,10 531,11/12 593 testcases; у каждого0failures/errors/skips. Это чтение historical results, не новый execution.

Tracked docs/*-evidence files measured with git ls-files followed by byte stat (not recursive private profiles):315files/71036036bytes. Groups:04 13/2067135;05 22/4596926;07 24/3801795;08 40/11743163;09 35/9027650;10 19/108804;11 35/13761957;12 92/18544173;Freshness35/7384433. Units: file count/bytes. Git object-compression/storage costs not measured.

Before report worktree, git worktree list returned19registrations including original root, graphify baseline,12NPI and remediation/Temp paths. Directory check found root .codex-impl-env/.codex-test-env/.venv and .venv in10/11:minimum5. No disk-wide inspection or deletion. New report worktree excluded. Full historic creation/removal ledger UNKNOWN.

Source-level reproduction commands:

```powershell
 git log origin/main --reverse --oneline
 git rev-list --count origin/main
 git diff --shortstat ccbf086 origin/main
 git diff --shortstat 9f665ed origin/main
 git ls-files 'docs/*-evidence/*'
 git worktree list
```

For byte stats resolve only returned tracked paths under pinned checkout. CI totals sum job timestamps in jobs endpoints above; preserve event/head/conclusion. Private artifacts need owner access, not export into a public PR.

## Неизвестное и ограничения

Полный unique agent/skill invocation count, actor-per-change attribution, deleted sessions, complete tool calls/tokens/$/latency ledger, local test/install counts, all worktrees/envs ever created, exact effective required-check configuration, human acceptance и production SLA — UNKNOWN/UNVERIFIED. Current physical103 SKILL.md includes cache copies;27 historical names are read attempts. Catalog описания прочитаны, relevant process bodies исследованы; unrelated installed skills нельзя считать исторически применёнными.

В этой работе сохранены local-only source references вместо публикации приватных журналов. Публикация10 итоговых docs допустима, но existing remote branches не изменяются; PR не создаётся без нового remote ref. Итоговый local report удовлетворяет разрешённому stopping point report/PR. Нет merge/cleanup/новой Product iteration.
