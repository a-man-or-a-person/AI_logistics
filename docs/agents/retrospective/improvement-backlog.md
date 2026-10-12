# TOP-10 улучшений и внедрение

Ниже proposed backlog; новые Product features не начаты, active issue files не переписываются. Размеры — инженерная оценка INFERRED, не замер: S ≤ половины дня, M около1–2дней с проверкой, L только после уточнения scope. Источник каждого action в [evidence-index](evidence-index.md).

| № / priority | Конкретное действие / owner | Evidence / WHY | EXPECTED IMPACT / стоимость | Как измерить |
|---|---|---|---|---|
|1 P0|Owner запуска: добавить revision/checkout/interpreter/port/served assets в handoff и onboarding checklist|E08 old5055/new5082|Устранить запуск чужой ревизии; S docs/procedure. Runtime revision endpoint — отдельно, только если процедура недостаточна|100% UI acceptance знает SHA и URL;0 stale-checkout incidents|
|2 P0|Contract owner: одна матрица cache states × Calculate/Compare/detail/export с recovery/cancel/restart|E03/E04/E05 missing transitions|Раннее обнаружение lifecycle defects; M для docs+reuse existing regressions|Каждый transition имеет owner/oracle; fewer later repair PRs|
|3 P0|Review owner: обязательные независимые metric/membership/completeness/security oracles|E05/E06 weighted coverage/provenance/literal/full rows|Не потерять integrity ради speed; S protocol, tests по задаче|0 silent truncation/provenance mix; independently reconciled outputs|
|4 P1|Coordinator: заменить universal triple review риск-матрицей из review-effectiveness|E01 mandates/E06 duplicate finding|Уменьшить dispatches на low-risk; S pilot. Экономия времени UNKNOWN|Unique findings per turn/minute и escaped defects на5 сравнимых tasks|
|5 P1|Executor: batch final report/evidence до публикации, focused checks в процессе, full final gate|E09 repeated report CI candidates|Сократить preventable reruns; S procedure|Количество report-only CI и local full per production revision|
|6 P1|Coordinator: stable criterion owner и CURRENT consumer-doc checklist|E02 ownerR3-05/E07/E08 stale readiness|Меньше late doc fixes/ambiguity; S|0 owner conflicts; current docs match public contracts при final review|
|7 P1|Evidence owner: manifest unique evidence, bounded bulk logs, durable summaries|E09 tracked315/71MB, #19 huge diff|Меньше archive/review overhead; M для policy+pilot. Старые файлы сохраняются|Новые evidence bytes/criterion и review time, все PASS sources durable|
|8 P1|Verification owner: interpreter/deps/temp/browser preflight|E03/E08/E09 startup/Temp/missing XlsxWriter|Меньше ложных application failures; S using existing startup helpers|Setup failures отдельно от test failures, time-to-first-valid-test|
|9 P1|Product owner + логист: human acceptance при first usable selection/table и first workbook|E05 checkpoint/E08 humanUV|Раньше подтвердить смысл/UI/business use; M календарно, engineer effort UNKNOWN|Recorded human result exact revision, fewer late business changes|
|10 P2|Product owner: определить All workload/latency/retention/worker goals; затем targeted export measurement|E08 90k21.27s/486.15MiB/30s|Capacity решение на evidence; S discovery, optimization M/L only if needed|p50/p95 на согласованных slices, memory ceiling, complete output; production gates закрыты|

Порядок:1→2→3 защищают доставку/данные;4→5→6 сокращают повторения;7→8 уменьшают overhead;9 нужен до production decision;10 не блокирует documentation PR, но блокирует обещание production SLA. Политика cleanup из workflow — отдельное согласованное внедрение, без удаления текущих artifacts.

## Ожидаемая экономия

CONFIRMED измерения:45 hosted jobs/101мин53с runner elapsed;315evidence files/~67.7MiB; минимум5 environments и19 historical registrations. Это baseline затрат, не доказательство waste. INFERRED opportunity: two reviews вместо three =33% меньше dispatches у допустимых задач; в retrospective counterfactual batching #19/#9 два ранних report runs каждой дали бы до699с меньше hosted execution. Эти величины не суммировать в процент общей разработки.

UNKNOWN: полный task elapsed/LLM tokens/$/cost of installations, доля expensive browser execution, человеческая цена ожидания merge/approval. Hypothesis для pilot: меньше review turns и report-only CI без роста escaped defects. Не обещаем численный end-to-end выигрыш до измерения. Сохранение full final candidate/main CI и независимой output correctness обязательно.

## Независимая критика

12 октября2026 отдельный субагент `retrospective_critique`, с чистым контекстом задачи, выполнил read-only review всех10 документов и выборочно первичных NPI07/12 и Graphify comparative/quantitative источников. Это независимый AI review, не self-review; production tests/GitHub API/private session ledger он заново не исполнял. **BLOCKER/MAJOR:0; MINOR:3; ADVISORY:1.**

| Возражение | Решение / результат |
|---|---|
|E10: «до начала работы» не воспроизводит exact251-record выборку|Принято: cutoff `2026-10-12T11:17:00Z`, буквальный cwd substring и categories записаны; private IDs/transcripts не публикуются|
|A9: конкретные artifact failures скрыты за aggregate omissions/setup|Принято: A7 artifact-log replacement, три B4 artifact-script failures, B7 replacement patch failure добавлены в inventory/scorecards; отделены от production defects|
|Обязательный independent acceptance executor создаёт новую роль/дорогой dispatch без measured benefit|Принято: owner исполняет runtime, independent reviewer проверяет matrix/evidence; independent executable replay только по риску/спорному PASS|
|Описание `retro` skill сильнее исходного «receives a diff, so no exploration needed»|Принято: это assumption о достаточном контексте, не запрет connected exploration; причинность historical misses UNKNOWN|

Reviewer независимо пересчитал45CI rows=6113seconds и103catalog rows, подтвердил Graphify68/70 vs66.2/70 и existence проверенных local links. Он согласился с N/A individual comparable scores, distinction skills/agents и counterfactual699s. Оптимизация reviews остаётся гипотезой; риск снижения качества контролируется pilot/escaped defects и сохранением data/security/contract oracles.

Final artifact audit parent:10Markdown files,35local links и30GitHub blob targets сверены; historical JUnit07/Freshness/10/11/12 разобран (0failures/errors/skips). Проверяются whitespace, scope10docs и pinned baseline; production/runtime rerun не выполнен для docs-only change. Independent critique не превращается в новое functional/human acceptance.
