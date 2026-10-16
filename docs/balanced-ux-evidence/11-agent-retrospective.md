# Ретроспектива AI-разработки Balanced UX, тикеты 01–10

Дата: 16 октября 2026. Автор и accountable implementer отчёта: `/root`.
Риск этого этапа LOW: исследование, один отчёт и два локальных индекса наблюдений.
Рабочее место: `C:/folder/Python/AI_logistics_clean/.scratch/balanced-ux-worktree`.
Remote: `https://github.com/a-man-or-a-person/AI_logistics.git`.
Исследуемые base/main `4d21b54259c1a34a9d098a34aa518f447b411b65` → feature HEAD `ddbeeb466d5d79557e79a88fcd345a6782ad1408`.
[Draft PR22](https://github.com/a-man-or-a-person/AI_logistics/pull/22) при чтении API открыт, Draft, не merged; head/base совпадают.
Существующая feature branch сохранена по прямому указанию пользователя. Новая ветка, commit/push, изменение приложения, правил, тикетов и cleanup в эту работу не входят.

> Публикационная пометка: ограничения commit/push ниже описывают завершённый исследовательский этап. После него пользователь разрешил опубликовать этот отчёт и два индекса метаданных в существующей feature-ветке. Выводы и предложения по процессу сохранены. Пометка local-only обозначает сохранённый локальный источник: исходные сессии, архивы и неопубликованные planning/research-файлы в эту публикацию не входят. Два опубликованных индекса находятся рядом с отчётом; остальные кликабельные файловые ссылки ведут на опубликованные материалы.

## Вывод и границы уверенности

**Общая экспертная оценка — 6,6/10, уверенность средняя.** Агент хорошо защитил математические и жизненные контракты, самостоятельно довёл десять тикетов до технически проверенного кандидата и сохранил main. Однако отладка первого дефекта слишком долго опиралась на неподтверждённые гипотезы; повторные широкие проверки и дробные ревью оказались дорогими; полезность новой компоновки проверена слабее её формальной доступности. Зелёный CI не компенсирует эти недостатки.

Техническая поставка: 10/10 тикетов, 35/35 критериев, 294/294 обязательств; [Quality67 SUCCESS](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38778652240). Человеческая приёмка — **n=0 / UNVERIFIED**, production — UNVERIFIED. Это сохраняет смысл предыдущей технической приёмки, но не доказывает удобство или готовность к эксплуатации. [Итоговая сверка](10-integrated-acceptance.md), [закрывающий PR supplement](https://github.com/a-man-or-a-person/AI_logistics/pull/22#issuecomment-6203008601).

Новая пользовательская оценка «аналитика сверху уменьшила видимую карту» — факт обратной связи из задания этой ретроспективы. Снимки подтверждают геометрический эффект; степень влияния на работу логиста не измерена. Ни причинное влияние каждого skill, ни сэкономленные проценты времени из имеющихся данных установить нельзя.

## Метод / источники

Применён фактически доступный retro SKILL (`C:/Users/User/.codex/skills/retro/SKILL.md`, local-only), затем прочитан writing-for-agents (`C:/Users/User/.codex/skills/writing-for-agents/SKILL.md`, local-only). Отдельного инструмента Skill в этой среде нет: инструкции прочитаны через filesystem, их методология выполнена. Рассмотрены navigation, automated checks, coding standards, AGENTS, tool economy, no-ops и information access; рекомендации ниже ранжированы по эффекту и риску.

Источники, используемые далее:

- **R** — Research (`../design/dashboard-ux/ux-research-report.md`, local-only), AS-IS CJM (`../design/dashboard-ux/cjm-as-is.md`, local-only), TO-BE CJM (`../design/dashboard-ux/cjm-to-be.md`, local-only), decision gate (`../design/dashboard-ux/ux-decision-summary.md`, local-only), visual plan (`../design/dashboard-ux/visual-acceptance-plan.md`, local-only), source/skill audit (`../design/dashboard-ux/evidence/research-source-audit.md`, local-only).
- **P** — локальный approved D-01…D-05 (`../../.scratch/dashboard-redesign/product-decisions.md`, local-only), spec (`../../.scratch/dashboard-redesign/spec.md`, local-only), DAG (`../../.scratch/dashboard-redesign/risk-dependencies.md`, local-only), tokens (`../../.scratch/dashboard-redesign/design-tokens.md`, local-only), skill report (`../../.scratch/dashboard-redesign/skill-usage.md`, local-only), 10 отдельных тикетов (`../../.scratch/dashboard-redesign/issues`, local-only).
- **W** — [AGENTS](../../AGENTS.md), [Workflow v2](../agents/development-workflow.md), [Quality](../../.github/workflows/quality.yml), [Product workflow](../clustering_product_v1_workflow.md), [Product contract](../clustering_product_v1_contract.md).
- **E01…E10** — отчёты [01](01-foundation.md), [02](02-workspace.md), [03](03-parameters.md), [04](04-economic-compatibility.md), [05](05-frozen-summary.md), [06](06-map-and-table.md), [07](07-contextual-inspector.md), [08](08-comparison-and-export.md), [09](09-recovery-and-accessibility.md), [10](10-integrated-acceptance.md); [294-ID ledger](10-information-preservation.json).
- **L** — append-only progress (`../../.scratch/balanced-ux-progress.md`, local-only), архив 279 артефактов (`../../.scratch/balanced-foundation/10-runtime-manifest.json`, local-only), финальное закрытие (`../../.scratch/balanced-foundation/10-final-closure-20261016.json`, local-only).
- **S** — исходная implementation-сессия (`C:/Users/User/.codex/sessions/2026/10/13/rollout-2026-10-13T13-29-26-01a134cf-57be-79b3-9600-0a14853a8d4b.jsonl`, local-only). Ссылки на номера строк ниже относятся к этому JSONL, не к пересказу контекста. Метаданные и доступные tool calls/outputs исследованы; зашифрованные reasoning и тексты части межагентных сообщений не интерпретировались.
- **M** — созданные в этой ретроспективе локальные [CI index](11-retro-ci-index.json) и [session/JUnit index](11-retro-source-index.json). Они содержат компактные метаданные, без исходных бизнес-строк, credentials и скрытых рассуждений.

Факты проверялись по Git, текущему read-only GitHub API, журналам tool calls, JUnit и сохранённым отчётам/изображениям. Исторический reviewer PASS в E — свидетельство зафиксированной проверки, а не новый независимый runtime replay автора ретроспективы. Число skill-read calls само по себе не считается доказательством применения. Полные тесты и сценарии приложения заново не запускались: предмет — процесс завершённой итерации.

## 1. Фактическая хронология

| Время / фаза | Наблюдаемое событие и результат | Источник |
| --- | --- | --- |
| 12 октября, research | Разобраны 14 этапов CJM, 294 information ID, сценарии single/union/All, экономические знаменатели. Удобство Balanced помечено гипотезой; пользователей нет. Browser entry недоступен, использована историческая evidence; это явно раскрыто. | R, research-source-audit |
| 12 октября, decision gate | Balanced рекомендован с Conservative fallback; структура переносит overview над картой. До решения Product реализация остановлена. | R decision gate |
| 12 октября, approved spec/tickets | Пользователь утвердил D-01…D-05: Balanced, metric-valid Option A, совместимость API, Bear CURRENT, сохранение294. Созданы 10 тикетов/35 критериев и ацикличный DAG. Исторические NOT APPROVED не переписаны задним числом. | P |
| 13 октября, 14:00–19:36 MSK | 01: восемь коммитов, семь неудачных CI51–57; подтверждён reduced-motion root cause, исправлен также Escape/help. CI58 успешен. | E01, таблица CI ниже |
| 13 октября, 19:42 | 04: отдельный экономический regression guard, без изменения backend/ML; CI59 успешен. Подготовка шла независимо от CSS с отдельным владельцем файлов. | E04, b07706f |
| 13 октября, 21:37 → 14 октября, 17:16 | 02→03→05→06→07→08: шесть публикаций; CI60–65 успешны. Native geometry/focus и независимые числовые/XLSX проверки находили дефекты до публикации. | E02–E08, L |
| 14–15 октября, 09 | 49 recovery/accessibility регрессий, несколько superseded локальных Quality attempts, диагностика сетезависимого font fixture; итоговый локальный и hosted66 PASS. | E09 |
| 15 октября, 10 | Baseline-first техническое сравнение, 294-ID сверка, независимые API/value/workbook oracles. Найдены и исправлены две интеграционные ошибки; пять регрессий. Публикация ddbeeb4 в20:35 MSK. | E10 |
| 15 октября, 20:48 MSK / закрытие16 октября | Quality67 завершился успешно; после возобновления сессии проверены точный head, тестовый merge и родители, Draft, main, served assets. Финальное сообщение16 октября. | M CI, L, supplement |

В feature-range **17 коммитов**, без merge-коммитов: 8 на01 и по1 на остальные9 тикетов. Хронология коммитов не равна времени непрерывной работы. Исследовательские документы предшествуют range и не должны прибавляться как production-коммиты этой ветки. Проверка: `git log --reverse --format='%h %aI %s' 4d21b54..ddbeeb4`.

Порядок исполнения **01,04,02,03,05,06,07,08,09,10** соответствует DAG. Связи01→02 и02→03 обоснованы общими CSS/panel/footer;04 изолирует экономический контракт до его представления. Явно избыточные транзитивные рёбра не создавали дополнительных runtime gates. Возможность параллельных03/06 и07/08 не использована для production-правок: общие controller/inspector/CSS и требуемая последовательность делают это разумным. Не доказано, что больше параллелизма сократило бы сроки. Источник: P DAG, E scope, L.

## 2. CI, тесты и стоимость процесса

Текущий API возвращает ровно17 run этой feature branch: **10 SUCCESS, 7 FAILURE, все run_attempt=1**. Следовательно, «повторы»01 — новые коммиты/новые runs, а не rerun одного run. Все семь отказов — шаг Python suite; frontend contracts при этом прошли. Причины resize раскрыты в E01, current API отдельно подтверждает шаг/ревизию/исход.

| Quality | HEAD | Итог | Run | Длительность job, секунд |
| --- | --- | --- | --- | --- |
| 51 | 14b81db | FAILURE | [38387303328](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38387303328) | 259 |
| 52 | 6773700 | FAILURE | [38388863949](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38388863949) | 220 |
| 53 | e625bb1 | FAILURE | [38396169710](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38396169710) | 269 |
| 54 | a1c4656 | FAILURE | [38398675617](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38398675617) | 253 |
| 55 | 3ea8ab3 | FAILURE | [38400720015](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38400720015) | 439 |
| 56 | 0ab9dd5 | FAILURE | [38408410995](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38408410995) | 295 |
| 57 | 6cc25ee | FAILURE | [38411374557](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38411374557) | 282 |
| 58 | 1c180f3 | SUCCESS | [38431872983](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38431872983) | 295 |
| 59 | b07706f | SUCCESS | [38432668735](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38432668735) | 339 |
| 60 | 6abd5d9 | SUCCESS | [38448242297](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38448242297) | 339 |
| 61 | e5123ee | SUCCESS | [38472364954](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38472364954) | 368 |
| 62 | e56a35b | SUCCESS | [38529373807](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38529373807) | 397 |
| 63 | cd7821a | SUCCESS | [38548728866](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38548728866) | 458 |
| 64 | e7b8ec9 | SUCCESS | [38565644685](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38565644685) | 511 |
| 65 | 7361f2d | SUCCESS | [38579030269](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38579030269) | 585 |
| 66 | 99abadd | SUCCESS | [38733307165](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38733307165) | 638 |
| 67 | ddbeeb4 | SUCCESS | [38778652240](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38778652240) | 752 |

Сумма job execution intervals — **6699с =1ч51м39с**, из них failed2017с =33м37с. Это не billed minutes и не календарное ожидание агента. Полные required checks после каждого тикета прямо требовало исходное задание (`C:/Users/User/.codex/attachments/f437be88-780d-40b9-9b02-d54ecf8c0b46/Pasted%20text.txt`, local-only); ретроспектива не считает эти10 обязательных gates избыточными. Избежать стоило недоказанных кандидатов и лишнего локального перекрытия, а не контроля final HEAD.

Финально: hosted136 frontend/633 Python, 246,78/420,81с, zero skips; локально136/633, приблизительно409,99/550,8с. M сохраняет39 доступных завершённых JUnit XML с суммой23213,93с (~6ч27м); это сумма длительностей этих suite records, включая повторы и пересекающиеся наборы, **не** все запуски, уникальные tests, процессорное время или active wall time. Незавершённые попытки и часть reviewer runs в эту сумму не входят.

До09 локальный frontend набор включал dashboard tests, а Python `--ignore=test_clustering_frontend_contract.py` запускал их снова. Это видимое дублирование подтверждается E08 и E09; итоговая последовательность09/10 повторяет разделение существующего Quality:136 исходных frontend cases, затем остальной Python suite. Такую настройку стоило применять с01. Сам Quality уже содержит locked dependencies, pip check, Ruff, Node/Edge startup и reject-skips; нового общего lint/CI guardrail проекту не требуется. [Quality](../../.github/workflows/quality.yml), E09.

### Наблюдаемый расход моделей

Для implementation-family найдены39 JSONL-файлов, **не39 независимых агентов**: часть — продолжения. Учтены только собственные `token_usage_record` каждого файла (`thread_id == metadata.id`), с дедупликацией `response_id`. Из root исключено всё начиная с нового retro-запроса, строка12050. Накопительные event token_count и inherited context не суммировались второй раз. Метод и полный перечень файлов — M session index.

| Область доступных записей | Записей | Input tokens | В том числе cached input | Output tokens |
| --- | --- | --- | --- | --- |
| Основной агент | 1412 | 230584726 | 226631168 | 1036377 |
| Собственные записи дочерних сессий/продолжений | 2246 | 309236228 | 298128384 | 548782 |
| Всего | 3658 | 539820954 | 524759552 | 1585159 |

Это объём входа по множеству model calls с повторной передачей контекста, а не размер исходного задания. Reasoning output отдельно в metadata661665; он не прибавлялся к total второй раз. Общий записанный total541406113. Полнота провайдерского billing, фактическая цена, денежная стоимость и разбивка по тикетам — **UNKNOWN**. Исследовательские сессии12 октября и нынешняя ретроспектива в эти итоги не включены. Большой cached input не доказывает, что передача такого контекста бесплатна.

По S до retro:1112 exec calls,5 spawn,160 followup_task,45 send_message,47 sleep. Зафиксированы356 входящих agent messages: Spec161, Standards133, numerical38, diagnosis20, guard4. **Это сообщения, не356 ревью.** Число отдельных review passes нельзя надёжно восстановить из частично зашифрованных коммуникаций; минимум независимых осей и конкретные исполнения подтверждаются E01–E10. Не следует превращать160 dispatches в160 независимых проверок.

## 3. Тикет01: почему семь неудачных CI

| Кандидат | Проверяемая версия / фактический результат | Оценка процесса |
| --- | --- | --- |
| 14b81db /51 | После root16→32 table остаётся13 вместо26; исходные136 frontend проходят. | Настоящий сигнал, локальный environmental parity ещё не установлен. |
| 6773700 /52 | Два animation frames; root32 подтверждён, текст13. | Дешёвая гипотеза, быстро опровергнута. |
| e625bb1 /53 | Ожидание stylesheet/fonts; тот же отказ. | Полезная диагностика готовности, но не воспроизведение причины. |
| a1c4656 /54 | Прямой rem на cells вместо наследования; всё ещё13. | Production CSS изменён без локально красного оракула именно hosted-сбоя. |
| 3ea8ab3 /55 | Новые inline rem/iframe масштабируются, существующие nodes — нет. | Сильное сужение: conversion/root/parser не объясняют симптом. |
| 0ab9dd5 /56 | Font import перенесён в HTML link; тот же отказ; перенос впоследствии отменён. | Затратная неподтверждённая гипотеза с широкими повторными проверками. |
| 6cc25ee /57 | Relative-body experiment; fixed-body control работает; отказ сохраняется. | Ещё одно изменение до получения локального reproducer. |
| 1c180f3 /58 | Forced reduced motion даёт локальный root32/table13 и41 активный CSSTransition. transition:none/animation:none устраняют симптом; strict4cases GREEN. | Наконец причинная петля RED→fix→GREEN и успешный hosted. |

Источники: E01, соответствующие [коммиты](https://github.com/a-man-or-a-person/AI_logistics/compare/4d21b54259c1a34a9d098a34aa518f447b411b65...1c180f35486d3fe87e59fd0e12c343c49f3431a8), reduced-motion RED (`../../.scratch/balanced-foundation/reduced-motion-red.json`, local-only), [final test](../../tests/test_dashboard_foundation.py).

**Корневая причина доказана локальным контрпримером:** старый reduced-motion CSS уменьшал duration, но оставлял transitions; существующий font-size оказывался в активном transition. Поэтому новое rem-значение работало, а прежний элемент сохранял старый observed размер. Увеличение ожидания и перестановка шрифтов не исправляли механизм. Локальная Edge155 forced-reduce reproduction оказалась полезнее попытки получить CI Edge152: извлечённый152 зависал до CSS-evaluation и причины не установил. E01 сохраняет этот провал отдельно.

Что следовало сделать после первого устойчивого root32/table13: записать media flags, computed transition-property/duration и `document.getAnimations()`; сравнить normal/reduce в минимальном документе; получить одну локальную команду, воспроизводящую точный симптом; только потом редактировать production CSS. `diagnosing-bugs` был **прочитан рано** (S233), однако его требование red-capable tight loop сначала не выполнено. Проблема в исполнении методологии, а не просто в отсутствии skill.

Что агент сделал правильно: не снизил26px assertion, не выключил checks, не назвал engine bug доказанным, отменил опровергнутые font/body эксперименты; сохранил причины и failed logs. Дополнительный native Escape/help дефект исправлен собственной RED/GREEN, а не спрятан под resize. E01.

Повторная проблема09 — **другой механизм**: foundation fixture ожидал внешние Google CSS/fonts и мог не записать result до deadline. Held-request diagnostics показали блокировку readiness и на parent, и на candidate. Offline fixture стал следовать уже существующему layout-test pattern; production fonts/assertions/timeouts сохранены. Исторический естественный timeout не приписывается конкретной сетевой фазе без записи этой фазы. E09, diagnostic (`../../.scratch/balanced-foundation/std09-font-diagnostic.json`, local-only).

## 4. Оценка всех десяти тикетов

«Итерация» здесь означает наблюдаемую публикацию или явно записанный цикл исправлений/проверок. Git-коммиты посчитаны точно; полное число внутренних edit loops — UNKNOWN. Цифры ниже не маскируют setup failures под product RED. Skills перечислены только при наличии чтения плюс результата; сквозные правила TDD/Ponytail не объявляются отдельным invocation на каждом тикете.

| Тикет / публикации | Что сделано; трудности и найденные ошибки | Skills / reviewers; что сохранить и улучшить |
| --- | --- | --- |
| **01, 8 commits /8 CI;11 retained frontend XML** | Типографика/темы/help. Семь CI resize failures, contrast/малый nested text, Escape закрывал help вместе с inspector. | TDD, diagnosing-bugs, computer-use attempt, Ponytail, code-review; foundation_spec и targeted Standards. Сохранить строгие assertions; раньше media/transition RED, без speculative CSS. E01/S26,67,233. |
| **02, 1 commit;≥3 frontend suite records** | Shell/footer/drawers/reflow. Добавились реальные view-exit request guards, поэтому риск повышен до HIGH. Native200% form overflow и focus/scroll исправлены. | Spec/Standards+Ponytail, browser drivers; TDD discipline. Сохранить ранний live smoke и ownership; отдельно стабилизировать driver/media setup. E02. |
| **03, 1 commit;≥2 suite records** | Direction/Segment/Method,5 modes, invalid focus. Найдены hidden required group, Compare поверх controls, старый once listener после Reset, server alert в закрытом Segment. | TDD прочитан повторно S2974; Spec/Standards+Ponytail. Хорошая централизация current invalidField; заранее проверять всю error→repair→new error цепочку. E03. |
| **04, 1 commit;подготовка + независимые replays** | Числовой compatibility guard без production-изменений; canonical/legacy разные веса, missing/invalid/zero, Bear границы. Первая focused267+1deselected, independent268 включает пропущенного соседа. | economic_guard, economics_spec, economics_standards/Ponytail. Не выдумывать RED на conformant behavior; сохранить независимые constants и unchanged-source proof. E04. |
| **05, 1 commit;несколько defect loops, итоговая suite pair** | Frozen summary/quality/diagnostics. Null→0/NaN, два disclosure вместо одного, скрытые actions, status DOM replacement/quotes. Верхняя сводка увеличила вертикальную нагрузку. | Spec/Standards+Ponytail и отдельный numerical oracle; codebase-design seam прочитан S475. Сохранить собственные denominators; добавить ранний useful-map gate вместо только min240. E05. |
| **06, 1 commit;≥3 frontend/final records** | 14 columns,raw sorting,precision,coverage,map0≠null. Focus/scroll reset, unavailable→0%, sticky elements закрывали help; исправлены. Длинная failed suite6492,86с требует анализа harness/log, не трактуется как обычное время тестирования. | Spec/Standards+Ponytail; native strict hit tests. Сохранить raw identity и missing-last; reusable bounded hit/scroll helper вместо множества копий. E06/M. |
| **07, 1 commit;≥2 frontend records и дополнительные replays** | Contextual inspector/point/origin/Pulse. Primary metrics/counts/order/warnings/coverage и doubled-text reflow; исходная suite234 имела6 failures. Финальная239 PASS. | Spec/Standards+Ponytail, economics_spec own raw oracles. Сохранить cluster_id join и scope-specific weights; раньше проверять полный выбранный контекст/late-response lifecycle. E07/M. |
| **08, 1 commit;2 полные локальные suite pairs** | Aligned neutral compare и frozen complete XLSX. Narrow matrix/cached focus; old fixture пытался фокусировать inert navigation. Native unload signal transport потребовал корректировки driver. | spreadsheets read-only import/render, Spec/Standards+Ponytail, независимый workbook oracle. Сохранить реальный download+ZIP/XML/source reconciliation; разделить driver setup и продуктовый результат. E08/S6496–6632. |
| **09, 1 commit;attempt labels final1…9, не9 полных PASS** |49 recovery/a11y regressions: revision uncertainty/cancel/late responses, Data Map selector/groups, dialog/inert/focus/AX. Старые fake DOM, fonts readiness, superseded source и whitespace вызывали перезапуски. | diagnosing-bugs S7045/9540; Spec/Standards+Ponytail и numerical legacy oracle. Сохранить AX/native проверки; включать cross-surface focus раньше и отделять integration от расширения backlog в конце. E09. |
| **10, 1 commit;2 suite pairs, baseline/TOBE driver revisions** |294 ledger/35criteria,15contexts,22111 API assertions,5114 value-pipeline checks, actual books. Найдены Compare→map startup overlay и draft→saved layer leakage;5regressions. | Spec, Standards/Ponytail, numerical/output oracle. Сохранить независимость; раньше first-entry compare и saved-map/draft matrix, единый машинный ledger с разными evidence levels. E10. |

**Самые затратные:**01 по подтверждённым hosted failures/8commits;09 по breadth49регрессий и repeated/superseded attempts;10 по объёму сверки294 и повторной межагентной валидации. По деньгам или полной длительности ранжирование UNKNOWN. **Самые удачные:**04 как самостоятельный дешёвый контрактный guard без нового backend;03 как компактное исправление общей валидационной цепочки;08 как доказательство настоящего полного frozen XLSX. Это экспертная оценка результата относительно сложности, а не измеренная производительность. E03/04/08, M.

## 5. Skills: использование и маршрутизация

| Skill | Что подтверждено | Польза / ограничение |
| --- | --- | --- |
| research | В research-сессиях12 октября есть чтение и methodology/source deliverables; phase source-audit фиксирует background methodology agent. | Полезен для доказательств и ограничения hypotheses. Не заменил пользователей/faithful interaction validation. R. |
| ask-matt | Router чтение в research/decision; decision/source audit фиксирует выбранную последовательность. | Подтверждено чтение и routing, не отдельная «реализация skill» или доказанный эффект на скорость. R/P. |
| to-spec / to-tickets | Чтение в spec-сессии12 октября, реально созданы spec/10issues/DAG; P skill-report согласуется с tool calls. | Guard04 и preservation ownership явно зафиксированы; speculative API rewrite не выполнялся. Плотность пакета потребовала дорогой финальной сверки. |
| domain-modeling / codebase-design | Чтение и конкретные population/seam decisions в R/P; codebase-design также S475. | Сохранены Product vocabulary/ownership, не созданы лишние store/ADR/каталог. Не следует приписывать отдельный invocation каждому UIтикету. |
| tdd | S26 и2974, реальные baseline failures и regression files E01–10. | Высокая польза; conformant04 без искусственного RED. Дисциплина не полностью соблюдена для speculative hosted-resize кандидатов. |
| diagnosing-bugs | S233,7045,9540 и сохранённые causal probes. | Хорошая поздняя диагностика reduced-motion/fonts; ранняя прочитанная методология не удержала tight loop. |
| computer-use | Чтение S26; реальный CUA entry S50. В research доступ не состоялся; implementation native Edge выполнен разрешённым fallback по отдельному заданию. | «Прочитан skill», «CUA успешно управлял» и «native CDP evidence» — разные утверждения. Полезна явная маркировка. |
| code-review / ponytail-review | Code-review S67, независимые source/tests. Standards session читала ponytail-review; E помечает его targeted axis. | Найдены реальные ошибки. Не три независимых человека/агента, когда Standards и Ponytail делит один reviewer. |
| ponytail full | Чтение S17/21, обновлённой версии S1243; существующие modules/dependencies сохранены. | Реализация достаточно локальна; tool/evidence economy существенно слабее code economy. |
| spreadsheets | S6496–6632: несколько частей инструкции, read-only imports/renders, actual books. | Нашёл layout advisory; не доказал human Excel acceptance. Для чистой OOXML/source сверки уже достаточно stdlib; rendering оправдан только визуальным вопросом. |
| pr | S298/3462; реальный один DraftPR и exact-head supplements. | Полезная delivery discipline, main не затронут. |
| visualize / prototype / implement(-spec) | Встречаются в catalogs/обсуждении; полноценное исполнение в исследуемой реализации не установлено. | Не засчитываются как использованные по одному упоминанию. Отдельный prototype/ранний faithful layout мог помочь; это гипотеза, не доказательство, что skill предотвратил бы дефект. |

Не нужен больший список обязательных skills. Нужен completion test для уже выбранного: diagnosis заканчивается локальным точным RED, design — ранним rendered layout и решением по выявленному trade-off, review — собственным источником/проверкой. S и R/P дают доказательства разной силы; отчёт не повышает чтение skill до полного соблюдения всех его пунктов.

## 6. Независимые ревью и автономность

Пять логических delegated roles в implementation: **foundation_spec, economics_standards, economics_spec, economic_guard, resize_diagnosis**. Первые три дают разные оси: поведение/контракты, границы/риски/Ponytail, независимая арифметика и output. Guard — contributor, а не независимый reviewer собственного теста; diagnosis — исследование CI-различия. Исходные5spawn подтверждает S; дочерние продолжения не новые логические роли. E04/S, M.

Независимость содержательна там, где reviewer сам выполнял тест/арифметику или inspecting exact source: contrast/13px01, validation listener03, quoted-status05, missing coverage06, warnings/coverage07, narrow comparison08, inert popup/AX names/alerts09. В10 reviewer отдельно проверял294bindings, value pipeline и книги; интеграционные defects нашли в live переходах. Это разные источники ошибки, а не переписанные PASS. E01–10.

Но независимость доказательства не всегда требует повторять весь unchanged результат несколькими reviewers. В10 Spec/Standards оба проверяли publication mappings, архив и served assets; многократные followups на узкие изменения раздували coordination. Это кандидат на экономию, **не** основание отменять требуемые оси или единичный независимый numerical oracle. Нужен один shared finding ledger по root cause, один owner integrity-check, reviewers — только изменённые/спорные привязки плюс собственные high-risk probes. Проверяемую экономию пока не измеряли.

Автономность в утверждённом scope работала: последовательные gates, repair без изменения математики, один DraftPR, отсутствие main merge/cleanup. Многократные «продолжи» нельзя автоматически считать permission-seeking агента. В S до retro есть7 turn_aborted,6 usage_limit_exceeded,2 server_overloaded и1 HTTP403 runtime event; остановки имеют в том числе внешние причины. Полный causal split пауз на пользовательские/платформенные/организационные — UNKNOWN. Зафиксированные recovery ledger и exact served hashes помогли возобновлению без потери состояния. S event records, L.

Раньше требовалось не спрашивать разрешение на каждый тикет, а **предъявить конкретный продуктовый trade-off** при первом rendered результате02/05: «карта шире, но высота/одновременная работа map+table хуже». Это укладывается в уважение утверждённой спецификации; изменение выбранной компоновки требует Product решения. Отсутствие human acceptance не блокировало обычную разработку по явному заданию, но не освобождало от такого инженерного сигнала.

## 7. Почему потерю карты пропустили

[До1440×900](10-before-1440.png) и [после1440×900](10-after-1440.png) — реальные сохранённые Edge снимки, просмотренные в ретроспективе. До карта занимает примерно590px по высоте; после примерно240px при заметно большей ширине. Это приблизительное чтение границ на PNG, не новое DOM-измерение. После верхние context/KPI/quality блоки занимают большую часть центральной высоты; таблица доступна ниже, но её строки в исходном viewport почти не видны. Различия basemap loading не используются для оценки layout.

Причины разделяются:

1. **Утверждённая спецификация.** D-01 прямо переносит frozen context/KPI наверх. Tokens предусматривают auto-height/never clipped summary и map min240/table min180. Геометрический конфликт заложен в сочетании растущей L1 и фиксированного viewport; отдельного требования сохранить долю полезной видимой карты нет. В research имелся Conservative fallback. P/R.
2. **Отсутствие human acceptance.** Нет наблюдения логиста при одновременном чтении карты, списка и аналитики, нет принятого самим человеком layout. Поэтому technical PASS не смог закрыть воспринимаемую полезность. Эта граница честно оставлена UNVERIFIED. E10.
3. **Ответственность инженерной проверки.** Агент видел screenshots, overflow и minimum heights, но принял reachable+scrollable+min240 за достаточный visual verdict. Увеличение ширины и доступность14columns вытеснили вопрос «видно ли достаточно карты одновременно с задачей». E05 даже явно разрешает center scroll без summary cap. Следовало зафиксировать visual regression/trade-off и эскалировать его до завершения всех10тикетов; approved spec не оправдывает молчание.
4. **Метрика приёмки.**294IDs проверяют сохранность информации и access paths. Они не измеряют полезную площадь, частоту переключений внимания или необходимость scroll для сравнения. Функциональные T01–T10 и deterministic fixtures не эквивалентны judgement о рабочем пространстве. E10/R usability plan.

**Следствие:** это не доказательство неправильной математики или потери294полей; это доказанный пробел engineering/design acceptance. Возвращение постоянной правой аналитической панели, уменьшение верхней сводки и восстановление карты — отдельное пользовательское намерение, **здесь не реализовано и в новые тикеты не превращено**.

## 8. Качество архитектуры и остаточные риски

Git range содержит12 frontend files, десять test files (9новых dashboard modules и существующий frontend contract), CONTEXT и evidence. Frontend numstat:947added/318deleted; tests1844added/8deleted. Всего45files/20942insertions/326deletions, из них16575строк — preservation JSON. Число строк не равно сложности: часть production CSS остаётся длинными плотными строками. Проверка: `git diff --numstat 4d21b54..ddbeeb4 -- frontend tests`.

Положительное: controller/state остаются владельцами frozen/cache/request lifecycle; renderers и map — представления; optional signal API сохраняет прежние аргументы. Нет нового store/framework/dependency, backend/ML/Quality/lockfile range diff пуст. Изолированный04 зафиксировал уже существующие canonical rows; миграция API не потребовалась. E04/09, Git range.

Риски поддержки: дополнительные глобальные CSS overrides и взаимодействия app/controller/map/inert/focus; breadth новых recovery tests; внешние font/tile ресурсы; концентрация знания в крупной сессии и локальных архивах. Нельзя называть все1844test lines лишними: многие ловят реальные escaped bugs; явная избыточность — повторное исполнение одного набора и копии driver setup, а не число assertions само по себе. E01/06/09, M.

Evidence детализирована вплоть до147API/value IDs и2999disk checks, но большая часть ledger повторяет поля/длинные пояснения. Полезно генерировать компактную сводку и ссылки на единый frozen input/oracle; хранить bulk в архиве. Старые E01–09 оставляют PENDING, а planning tickets — ready-for-agent при уже завершённой реализации; L/E10 примиряют это, но discovery дорого. Новым reports нужен один очевидный execution-status pointer; исторические approvals и evidence переписывать не требуется. P/E/L.

## 9. Оценки

Оценки субъективны, шкала1–10; это оценка наблюдаемой работы агента, не benchmark моделей.

| Критерий | Балл | Доказательство / причина |
| --- | --- | --- |
| Планирование | 7 | Осмысленный DAG/04guard/owners; layout hypothesis слишком рано стал implementation shape без useful-map acceptance. P/R. |
| Архитектурные решения | 8 | Существующие ownership/API сохранены, backend/dependencies не расширены; shared lifecycle/focus всё же сложен. E04/09/Git. |
| Качество кода | 8 | Локальные root fixes, no weakened assertions, независимые находки закрыты; плотный CSS и межмодульные состояния требуют поддержки. E01–10. |
| Debugging | 4 |7hosted failures и production hypotheses до exact local RED; сильное причинное расследование позже. E01/E09. |
| Тестирование | 8 | Реальные numeric/disk/native/AX/late-response oracles, zero skips; дублирование suite и слабая visual usefulness metric. E/M. |
| Работа со skills | 6 | Реальные чтения+outputs; diagnosis tight-loop не соблюдён сразу, router breadth не гарантирует execution quality. S/R/P. |
| Делегирование | 7 | Разные независимые оси и реальные находки;160followups и повторная integrity сверка. E/M. |
| Скорость и эффективность | 4 |8publications01, повторное dashboard coverage, дорогие timeout attempts; денежная скорость UNKNOWN. M/E01/09. |
| Автономность | 8 | Полный approved scope, preserved main/Draft/данные; восстановление после внешних ограничений. S/L/API. |
| Product Contracts | 9 | Разделены canonical/legacy/Bear, frozen IDs, full export, медоид/forecast; unknown внешние callers не объявлены проверенными. E04/08/10. |
| UX-awareness | 4 | Доступность и data clarity улучшены, но полезная видимая карта уменьшилась без раннего решения; human0. Снимки/P/E05/10. |

Среднее11равновесных оценок73/11=**6,64**, округлённо6,6. Уверенность высокая для Git/CI и конкретных RED/GREEN, средняя для attribution skills/review economics, низкая для полной трудоёмкости и пользовательского эффекта.

## 10. Практические предложения, по приоритету

Все пункты — **предложения к согласованию**, сейчас правила, конфигурация, код и тикеты не меняются.

| Приоритет / категория | Предложение и место | Эффект / риск / как проверить |
| --- | --- | --- |
| **P0, automated checks + judgement** | В Workflow v2, Implementation: после первого рабочего layout делать paired same-state viewport capture с map/table/summary rectangles и native hit checks; reviewer явно сравнивает usable map+table. Product owner принимает бюджет видимой области до дальнейшего redesign. | Ловит нынешний escape до05–10. Числовой порог **не придумывать**; согласовать после faithful snapshot. Риск: механический minimum вновь станет proxy удобства. |
| **P0, debugging** | В Workflow verification добавить короткий escalation trigger: повтор того же CI assertion без точного local RED → снять browser/media/animations/network/readiness fingerprint и собрать minimal reproducer до следующего production candidate. | Прямо адресует01; existing diagnosing-bugs остаётся владельцем подробного loop. Не вводить безусловный запрет обоснованной CI-only диагностики при недоступной среде. |
| **P1, automated checks** | При следующем approved изменении test harness применять с начала текущий Quality split, offline deterministic CSS/font fixture, normal/reduce matrix; fail diagnostics выводят active transitions и phase ожидания. | Использует уже существующие тесты/guardrails. Production loaded-font/native gate остаётся отдельным. Оракулы не ослаблять. E01/09. |
| **P1, tool economy** | Один machine-readable run ledger: source/test hashes, scope, command, environment, result; full suites после freeze/обязательного code change, focused checks во время правок. Не запускать dashboard coverage дважды. | Сокращает повторяемую работу, не отменяя mandated local/hosted gates. Сравнить suite executions/unique failures на пяти задачах. |
| **P1, review routing** | В существующий reviewer protocol — один finding ID/root cause и change-boundary packet. Integrity/archive/publication проверяет один независимый owner; Spec/Standards отдельно проверяют свои invariants, numerical oracle — свои raw inputs. | Сохраняет независимость при меньшем дублировании. Risk: чрезмерно узкий packet скрывает cross-feature bug; disputed/high-risk переходы replay отдельно. |
| **P1, navigation** | Краткий execution-status pointer в README существующего local spec package: owner=L, финальный technical report=E10; historical tickets не источник текущего статуса. | Устраняет ready/PENDING ambiguity. Одной ссылки достаточно, не новая копия всех статусов. |
| **P2, skills routing** | В spec/review workflow вызывать diagnosis при первом устойчивом различии сред, faithful prototype до большого layout, spreadsheets только для workbook-вопроса. Проверять completion artifact, не факт чтения. | Не увеличивать compulsory skill catalog. Нужен пилот; экономия в процентах UNKNOWN. |
| **P2, information access / tooling** | Использовать фиксированный absolute Python, safe log capture и ограниченный file inventory без browser profiles; reusable task-owned native driver setup для focus/scroll/encoding. | Уменьшает Windows setup/encoding/navigation failures. Не менять глобальную среду и не публиковать session/profile internals. |
| **P2, evidence retention** | Компактные durable criterion rows + единый frozen input/oracle manifest; bulk logs/profiles/books локально/CI. У каждого PASS distinction source/function/Edge/native/human. | Снижает context load. Удаление старой evidence не предлагается; критическое доказательство не может зависеть только от expiring artifact. |

### Что оставить, убрать и где менять инструкции

**Оставить:** один accountable owner; isolated branch/Draft; exact-head CI и zero skips; настоящие RED/GREEN; независимые metric/source/XLSX oracles; lifecycle matrix и отдельные functional/human/production статусы; privacy/manifest/served-checkout verification. Это доказанные полезные практики E04/08/09/10, а не формальности для сокращения.

**Убрать из будущих исполнений:** speculative production resize fixes без соответствующего RED; повторный полный dashboard прогон в двух наборах; заново пересылаемые неизменённые большие summaries и integrity bundles всем reviewers; слепые reruns вместо captured phase; самостоятельные duplicate статусные таблицы. Обязательные gates текущего задания не отменять.

**AGENTS.md:** менять не требуется — он уже короткий navigation/preflight pointer. Дополнительные подробности туда повысят always-loaded context load. **CODING_STANDARDS:** новый общий запрет не нужен; механические media/font assertions принадлежат тестам. Judgement о пространстве карты — предмет visual acceptance и reviewer protocol. **Skills config:** глобальные изменения не обоснованы; улучшить выполнение существующих skills. Это следует методологии retro/writing-for-agents и фактам01/09, а не предположению «больше правил лучше».

Предлагаемая точная краткая вставка в Workflow v2 (не применена):

> At the first working layout, compare the same saved state and viewport against baseline: visible map, table and summary rectangles, native access and simultaneous task context. Record any material workspace trade-off for Product review before extending the layout. Technical reachability alone does not establish visual usefulness.

Вторая вставка рядом с defect loop (не применена):

> When the same hosted assertion fails again without a matching local RED, capture environment/media/animation and readiness-phase evidence and obtain a minimal reproducer before another production hypothesis. State an explicit exception when only hosted reproduction is possible.

Остальные изменения сначала проверить на пяти сопоставимых задачах: число full runs, CI job seconds, review dispatches/unique findings/duplicates, evidence bytes, escaped defects и human acceptance outcome. Ни эффект в процентах, ни стоимость такой процедуры сейчас не доказаны.

## 11. До следующей UX-итерации

1. Представить владельцу реальный faithful layout с постоянной правой аналитикой, компактной верхней сводкой и достаточной картой в1366×768/1440×900/1920×1080 и125%; согласовать наблюдаемые критерии рабочего пространства. Это следующий отдельный этап после согласования, не выполненный fix.
2. Зафиксировать same-state baseline для обычного результата, выбранного кластера/точки, раскрытой аналитики и полного списка; не ограничиваться пустым стартом.
3. Отделить три решения: доступность всех294обязательств, полезность simultaneous map/table/analytics, human business acceptance. Сохранить строгие контрактные tests.
4. Проводить короткую раннюю визуальную оценку до масштабного интеграционного evidence; full local/hosted gates сохранять в утверждённом объёме.
5. Согласовать предложенные дополнения процесса; затем отдельное разрешение на реализацию. Сейчас остановиться на этом отчёте.

Продуктовый код, AGENTS/Workflow/skills, исходные tickets/evidence не изменялись. Main/feature HEAD и DraftPR сохранены; никаких commit/push/merge/cleanup. Отчёт — self-retrospective с независимым lightweight content check, а не новая приёмка приложения. Остаточные human/production/Excel-layout риски из E10 сохраняются; clipping длинных XLSX headers — известный advisory.

## 12. Проверка самого отчёта

Проверяемые входы: Git history/diff, current read-only PR/CI metadata, source reports, raw own-thread token records,39JUnit XML, paired PNG. Все локальные Markdown targets разрешаются; арифметикаCI/usage/оценок согласована; whitespace check отчёта не выявил ошибок. Известный tracked cache statusM сохранён, его байты повторно сопоставлены с HEAD и равны; других tracked изменений нет. Новые файлы этого этапа — этот отчёт и два локальных индекса M.

Независимый LOW content reviewer `/root/retro_content_review`: **PASS**, base4d21b54/head ddbeeb4, uncommitted report. Самостоятельно прочитал AGENTS/Workflow, полный отчёт, оба индекса, E01/E09/E10, research/planning skill audits; проверил Git diff/numstat, CI6699/2017с,39JUnit/23213,929с,11оценок73/11 и оба PNG. По raw S независимо пересчитал все1412own-thread root usage records до строки12050 и проверил выборку cited skill-read calls. MINOR: две недоказанные counterfactual формулировки о предотвращённом API rewrite заменены наблюдаемыми фактами и повторно проверены. Нерешённых BLOCKER/MAJOR/MINOR нет.

Ограничения reviewer: не выполнял новый GitHub API fetch, не пересчитывал каждый child raw record, не перепроверял все исторические runtime/review claims и не запускал application suites. API и полный child aggregate проверены автором отчёта; независимость этих двух частей не заявляется. Content PASS не меняет human/production readiness. Mandatory application suites не перезапускались для report-only работы без публикации; commit/push/merge/cleanup не выполнялись.
