# История и повторная работа

Источники: [E01–E09](evidence-index.md). Даты ниже — Europe/Moscow; GitHub timestamps в индексе сохранены UTC. Названия этапов описывают результат, а не личность автора. Участие отдельных historical agents подтверждается отдельно в [inventory](agent-inventory.md).

## До NPI

| Этап / Git evidence | Цель и фактический объём | Изменение курса / дефекты | Проверка и остаток |
|---|---|---|---|
| `ccbf086` → `e70b6b4` | Карта, геокодирование, ML-кластеризация, проекции, агрегация | Fix агрегации подтверждён коммитом; исходный prompt/ответственный UNKNOWN | Git доказывает последовательность, но не качество handoff или autonomous работу |
| `3037c6f` → `da3aac5` | Research data/evaluation/forecast pipeline, boundary QA | Затем цель смещена к clustering quality; это подтверждённая смена фокуса, не доказательство ошибки каждого раннего feature | Research отделён от Product; цена раннего разведочного труда UNKNOWN |
| `04dab52` → `58d139a` | Freeze clustering contract, weighted economics, graph и режимы | `d0e89e5`/`83fa53f` исправляют семантику/contract; нельзя считать каждый fix одинаковым escaped defect | Freeze/research reports; coordinate cache разрешён с ограничениями |
| `3445236` → `8dafa2a` | Repository/service/API/UI, территориальная Product workspace, volume modes | Сохраняются LEGACY/RESEARCH; новые Product contracts | Characterization tests стали базой рефакторинга |
| `37609ac` → `3ab9c7a`, затем `8470a9e`/`c44a6dc` | Каталог пяти mode adapters, нейтральная orchestration, capabilities, удаление второй authority, canonical docs | Архитектурная декомпозиция по seams уменьшила риск широкого переписывания; фактическая экономия INFERRED | Final architectural verification; ранние review traces частично локальны |
| PR #1, merged 8 октября | Canonical Pulse, backend table summaries, desktop table, paginated detail, cached comparison; девять commits | 24/24 заявлены как выполненные; live shell не был полным native click-through; Edge workaround только verification | 247 tests; реальный большой source-run описан в PR, здесь private данные не перечитывались. Последующая live приёмка выявила P1/P2 |
| PR #2, 10 октября | Windows CI, locked install, Ruff, required Node/Edge и skip rejection | Hosted красный: untracked CSV зависимость; focus/deadline и synthetic fixture исправлены | Финальный CI success; отдельный Standards advisory об unbounded waits разрешён |
| PR #3/#4 | Tooltips hover/focus; выбранные периоды/missing metrics в inspector | Presentation/accessibility fixes, узкая область; не причина P1/P2 по доказательствам | Genuine focused RED/GREEN; limited renderer evidence, затем live acceptance |
| Первая Product acceptance, 10 октября | Реальный Flask/Edge, 16 сценариев | 13 PASS /3 FAIL, две причины: rejected snapshot recovery и cached radio mismatch; зелёный main CI не предотвратил их | NOT READY; отдельные P1/P2 tickets, без переписывания исторических статусов |
| PR #5/#6 | P1 invalidation/recovery; P2 existing renderer sync | P1 Spec нашёл comparison context race; P2 восемь production строк плюс regression | P1 focused RED/GREEN и live fresh rows; P2 native reproduction, full275. Последующая Freshness не отменяет эти repairs |

## NPI-01…12 и незапланированная Freshness

| NPI / PR | Исходная цель → фактический результат | Исправления / изменение объёма | Подтверждённые проверки и участники |
|---|---|---|---|
| 01 / #7 | Pulse/ATI readiness → docs actual responsibilities +17 ATI UNKNOWN | Canonical slice wording clarified, точная membership ещё NEXT | 104 focused tests, CI275; Standards/Spec отчётно independent; Ponytail заключение. Docs-only, без fictional RED |
| 02 / #8 | Explicit origin union + frozen identity | Scalar injected options compatibility; generation during deepcopy; normalized frozen request | 68 focused API, full343; Spec и Ponytail нашли отдельные defects. Runtime UI ещё scalar |
| 06 / #9 | Проверить weighted route и independent coverage | Никаких новых формул; уточнение owner R3-05, без manufactured RED | 16 deterministic новых cases, full359; reviewers independently94 focused. Это verification task, не implementation failure |
| 03 / #10 | Complete regional All API | Foreign injected options и padded-region lookup; All compare resolve once | 70 All cases, 108 origins сверх100 suggestions; full429; Spec154/Ponytail70 focused самостоятельно. UI отложен |
| 04 / #11 | Explicit multi-origin frontend | Reset/region removal/late search; hosted UTF-8 declaration issue | Live60 rows/3origins/12destinations, full438; независимые axes, final CI после красного |
| 05 / #12 | Explicit All UI + frozen full set | Options needed complete region index; stale workflow diagram corrected | Live456rows/36origins, saved36→fresh37, 20 checkpoints; full443; scopes UI/API разведены |
| 07 / #13 | Per-origin frozen summary/detail | Extraction потеряла final row-generation variable (caught existing test); cached A→B→A/focus и row-only summary selector | Full464; 15 live checkpoints; Spec cached finding, Standards naming advisory; fixture errors помечены отдельно |
| Freshness / #14 | Проверить source revision перед frontend cache reuse | Новый public revision/presence seam; source change after successful revision всё ещё мог конфликтовать внутри calculation | Genuine baseline RED; Spec race → extra RED/GREEN, full485, 12 live checkpoints. Незапланированный lifecycle repair |
| 08 / #15 | Strict drill-up сохраняет frozen context | Question-mark labels, cancelled-finally focus, table scroll | Genuine RED; full492; native headed up/reentry/cancel; Spec blockers устранены |
| 09 / #16 | Сделать existing medoid узнаваемым | Обязательное reaffirmation user: временный geographical ориентир; FIAS/name/long wrap | 9 math/API,30 focused display checks,full528,25 live checkpoints. Семантическое подтверждение — осознанное решение, не bug |
| 10 / #17 | Exact saved XLSX API | Добавлена pinned XlsxWriter; completeness/provenance/legal names; Spec/Ponytail duplicate apostrophe finding | 39 export tests, full531; реальный HTTP workbook186rows independently reopened; rebase/merge-main после #16 потребовал final integrated CI |
| 11 / #18 | Download displayed frozen result | Binary transport, duplicate/late cancellation; два DOM fixtures исправлены без weakened assertions | Full593;10 реальных downloads reopened, errors/source/restart branches; human Excel UV |
| 12 / #19 | Integrated acceptance всей итерации | Drivers adapted к новой hierarchy; stale CURRENT readiness corrected; startup commands и redaction corrected | 78 criteria →76PASS/2UV после exact-HEAD CI;24 scenarios/extensions,12 downloads+90k workbook. Отдельные Standards/Spec; no production changes |

NPI номер ≠ execution order: 06 выполнен после02 до03/04. Это утверждённая зависимость, не хаос. 09 и10 действительно могли идти параллельно: один baseline `53c0037`, runtime seams почти независимы; #17 затем интегрировал #16. Дополнительные graph edges навязывать не требуется [E01, E02].

## Сколько повторов доказано

45 hosted runs: 27 PR и18 push-main,43 success/2failure [E09]. Это не число локальных тест-прогонов. Повторные review/fix циклы явно есть в P1,02,03,07,Freshness,08,10,11,12. Точное число сообщений и полных локальных прогонов за всю историю UNKNOWN; список сохранившихся логов не равен полному ledger.

Git prefix census:20 `fix` commits из117 non-merge после empty initial; в NPI span после9f665ed —10из45. Это нижнеинформативный proxy именования, не20distinct defects: другие repairs записаны как test/docs, один fix может покрывать несколько сценариев [E09].

Для #19 три PR CI на последовательных docs revisions плюс main после merge; для #9 три PR CI плюс main. Эти проверки корректно проверяют final SHA, но ранние publication/report-only commits создают потенциально устранимую работу. Сам факт повторного CI не доказывает, что запуск был ненужен.

## Почему поздно

P1/P2 были на базовом feature до presentation repairs. Их обнаружили сквозные действия «ошибка → повтор» и «cached mode → form edit». Freshness добавил независимую ветку «источник поменялся, но ещё не было rejected detail». NPI-07/08 требуют реального cached selection/focus, NPI-10 — reopened output и provenance. Эти seams должны проверяться в первом владельце контракта. Однако UI/export ветки, которых тогда не существовало, обоснованно проверяются позже; не следует ретроактивно объявлять backend PR неполным за будущий UI.

На NPI-12 доказан старый сервер5055 при новом candidate5082. Это delivery/onboarding failure, не дефект новой origin UI и не подтверждённая проблема browser cache. Изолированная разработка должна заканчиваться явной передачей проверенной ревизии/URL пользователю.
