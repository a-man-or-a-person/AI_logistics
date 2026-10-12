# Оценка ролей и проверок

Сравниваются результаты и ограничения подтверждённых ролей. Полного набора исходных prompts, действий, времени, стоимости и одинаковых задач на каждого worker нет. Поэтому **индивидуальные числовые оценки 0–10 и общий weighted score — N/A**. Confidence относится к конкретному выводу, а не к «таланту» агента. Количество tests или commits не заменяет результат.

## Сравнение полезности

| Роль | Что удалось | Что было недостаточно / неизвестно | Причина и изменение | Оценка / confidence |
|---|---|---|---|---|
| Orchestrator / implementation | Последовательная migration, exact frozen identity, отчёты и integrated release evidence | Поздние state-flow repairs и stale local checkout; вклад отдельных workers, эффективность/коммуникация N/A | **INFERRED** контракт не всегда превращался в полный transition test; закрепить startup SHA/source generation и negative-flow owner | Все шесть числовых измерений N/A; qualitative mixed; high confidence в результатах, low в attribution |
| Standards | Документированная authority/locality, устранение unbounded waits в guardrail history; NPI-12 executable evidence/doc review | Standards pass не доказывает business/runtime acceptance; какие defects конкретный worker пропустил N/A | Axis проверяет свою задачу; связанный runtime review не заменять style review | N/A; medium/high для конкретных retained findings |
| Spec | NPI-10 independently воспроизвёл worksheet-apostrophe и omitted-intent export provenance; NPI-08 labels/focus blockers | Обнаружение поздних findings есть, но первоначальная false-positive rate неизвестна | Продолжить exact criterion + concrete negative case; привязывать re-review к corrected SHA | N/A; high для retained finding/fix chain |
| Ponytail | NPI-07 выявил cached A→B→A wrong display, потерю focus и narrowing summary через row-only selector | Полный false-negative history и marginal cost относительно Spec unknown | Connected callers/state/render flow оказался полезен; давать runtime focus, не повторять весь Spec report | N/A; high для конкретных трёх findings |
| Architecture exploration/design | Реальные separate alternatives; итоговый catalog с пятью adapters и mode-neutral service | Нет сравнимого качества/стоимости каждого designer; attribution решения неизвестна | Использовать только когда interface/authority решение спорно | N/A; medium для process contribution |
| Discovery/domain synthesis | Отдельные product/ops/research и grain/export discovery threads; explicit Product/RESEARCH/LEGACY vocabulary | Нет per-thread scoring; business interpretation Bear/ATI осталась ограниченной, что не означает failure researcher-а | Сохранять unknowns и человеческие semantics checkpoints; не расширять implementation по гипотезе | N/A; medium |
| Graphify research | Version/safety audit; permanent integration REJECT при недоказанном ≥20% benefit | Setup/cache/ACL/main-guard costs; отсутствие общего timing/token telemetry | Измерять benefit до adoption; не оплачивать infrastructure без material outcome | N/A; high для bounded no-adoption decision |
| Ground truth | Rubric/source reading независимо от A/B по protocol; раскрыта разница storage vs visible retention | Static rubric не эквивалентен live acceptance; собственная полнота ограничена | Независимая source adjudication и transparent rubric amendments | N/A; medium/high |
| A/B task agents | Оба variants7/7 correct; source подтверждал graph edges и dynamic paths | T4/T6/T7 omissions, minor classification; heterogeneous counters; interruptions | Не принимать graph topology как execution truth; source stays primary | Есть только rubric task scores ниже; individual performance metrics N/A |

Источники конкретных findings: [NPI-10 Spec](../../npi10-evidence/spec-review.md), [NPI-08 Spec](../../npi08-evidence/spec-review.md), [NPI-07 Ponytail](../../npi07-evidence/ponytail-review.md), [NPI-12 supplement](../../npi12-evidence/review-supplement.md). Guardrail/refactor и Graphify source locations доступны через [evidence index](evidence-index.md); это локальные surviving evidence, часть не опубликована в Git.

## Шесть требуемых измерений

Для каждой индивидуальной исторической сущности качество результата, spec compliance, autonomy, verification reliability, efficiency, communication/handoff получают **N/A**. Reasons различны: нет полной actor-attribution; artifacts объединяют parent/child work; runtime elapsed/tokens не нормализованы; communication logs намеренно не публикуются; разные роли решали разные задачи. Оценка роли выше качественная и не является средним score исторических agents.

Есть ограниченное исключение: сохранённая Graphify evaluation содержит **rubric качества конкретных task answers**. Это не шкала эффективности агента, не тесты Product и не вывод о models:

| Task | A /10 | B /10 | Установленное ограничение |
|---|---:|---:|---|
| T1 Request trace | 10.0 | 9.8 | B minor LEGACY/research classification |
| T2 NPI-04 reach | 10.0 | 10.0 | Source-verification остаётся обязательной |
| T3 Frozen identity | 10.0 | 10.0 | HTTP no-path не опровергает связь |
| T4 P1/P2 | 9.8 | 9.3 | Table visibility / failed fresh retry omissions |
| T5 Five mode semantics | 9.8 | 9.5 | Presets / Geo+Volume transform omissions |
| T6 Product boundaries | 9.2 | 8.8 | NEXT/forecast/tender distinctions omitted |
| T7 Origin impact | 9.2 | 8.8 | Failure/NO_DATA/keyboard checks omitted |

Сумма A68/70, B66.2/70. Разница1.8 points одного эксперимента не устанавливает systematic regression. Self-reported shell counts71→84, file counts153→135 и searches84→74 имеют разные scopes; их нельзя переводить в token/time savings. Full elapsed и tokens **N/A**. Измеренные24 graph processes20.368s — overhead процессов, а не whole-task duration. Это вывод сохранённого independent quantitative audit, с raw coverage/replay/interruption ограничениями.

## Индивидуальная критика, которую доказательства позволяют

**A1:** хорошо — сохранился масштабный compatibility/refactor и integrated outcome. Плохо — первоначальная process coverage не удержала все transitions до первых fixes. Root cause **INFERRED**: transition ownership/checkouts были слабее invariant coverage. Изменение: одним owner-ом замыкать form→saved→reject→refresh→export path; точный checkout до browser. Не оценивать личную autonomy без prompts.

**A2/A3/A4:** хорошо — complementary saved findings с targeted RED/GREEN. Плохо — reviewers не перепроигрывали все live/full tests; zero blockers в axis не означал human/production acceptance. Это **CONFIRMED boundary**, не автоматическое нарушение skill. Изменение: reviewers указывают exact reviewed SHA и собственные actions; parent owns final gates. Их выводы проверяются regressions и другими axes, scope повторных проходов — corrected findings и затронутые callers.

**A5/A6:** хорошо — независимые source/design threads существовали. Плохо — не сохранилась доказательная сравнительная оценка альтернатив/индивидуальной пользы. Причина неизвестна; не приписывать expensive architecture failure. Изменение: краткий decision record для необратимого выбора, reuse context pointers. Не выделять постоянные дополнительные implementation roles ради названий.

**A7/A8/A9:** хорошо — независимая reference/source проверка и отказ от tool adoption без gate. Плохо — setup/harness и неунифицированный accounting помешали количественному выводу. Root cause **CONFIRMED** в setup/audit: ACL/cache/Windows multiprocessing/overlapping child и incomplete telemetry. Изменение: заранее фиксировать measured scope и минимальный telemetry envelope; tooling experiments сохранять ограниченными. Не поручать graph-only worker-у runtime/business acceptance.

У A9 сохранены также конкретные harness failures в quantitative-audit: A-T7 пришлось заменить artifact-log; B-T4 три artifact-script failure; B-T7 replacement patch failure. Это повторная работа по оформлению evidence, отдельно от качества source answers и interrupted calls. Их цена UNKNOWN, поэтому rubric68/70 против66.2/70 не переводится в efficiency score. Предложение: один проверенный writer/schema для experiment artifacts вместо ad-hoc string replacement; не новый runtime framework.

Публикуемая оценка системы должна опираться на retained repairs, acceptance и operational limits, а не на выдуманный average agent score. Три наиболее доказательно полезные практики: конкретный Spec negative-case reproduction, connected Ponytail state/focus review, независимая integrated evidence проверка. Сравнить их ROI в рублях/токенах сейчас нельзя.

Пропущено: числовое ранжирование людей/agents без сопоставимых данных. Риск: task rubric и качественная полезность роли не доказывают автономность, скорость или экономию всей разработки.
