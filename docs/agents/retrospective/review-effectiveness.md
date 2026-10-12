# Эффективность Standards, Spec и Ponytail

Сравниваются механизмы, а не модели. Источники [E03–E08, E10](evidence-index.md). GitHub review submissions/inline comments/conversation comments для #1–19 пусты; заключения лежат в reports и review Markdown. Отсутствие GitHub review объекта не означает отсутствия субагента. Полный precision/recall UNKNOWN: нет исчерпывающего независимого defect oracle.

| Механизм | Подтверждённая полезность | Пропуски / предел | Самостоятельная проверка | Решение |
|---|---|---|---|---|
| Standards | CI unbounded waits; NPI-10 field names вместо positional columns и CURRENT/NEXT; NPI-12 export scans advisory, evidence execution order | Standards0 при P1/P2 не ложный PASS своей оси: missing transitions относятся к Spec. Нулевой smell count не гарантирует runtime correctness | NPI-12 checked reader/assertions; обычно source/evidence inspection, не full live rerun | Оставить для architecture/ownership/infra, включать простые conventions в обычный review |
| Spec | P1 comparison race;02 scalar compatibility;03 injected options/region normalization;07 cached reentry;Freshness in-flight409;08 focus/labels;10 provenance/legal name;11/12 stale CURRENT docs | Первый feature24/24 не равен полноценной live приёмке; source-replacement cache branch дошёл до #14. Не доказано, какой конкретный reviewer должен был раньше обнаружить её | 03:154 focused tests;10 independent XlsxWriter reproduction. 12 API попытка collection failed из-за missing XlsxWriter в старом env; не PASS | Основной independent reviewer behavior/data; выбирать transitions, не перечитывать только checklist |
| Ponytail |02 generation during result copy;03 focused70 All;10 illegal worksheet suffix;12 latency/memory warning | В простых docs/presentation задачах часто Ship без новых blockers. Runtime proofs нередко parent-owned |03 independently70; P2 Node16, Edge startup timeout;10 no pytest/live Excel; Freshness no full rerun | Дополнительная экспертиза сложного риска, не обязательная третья подпись на всё |

## Дублирование и шум

CONFIRMED: NPI-10 Spec и Ponytail нашли один и тот же trailing-apostrophe defect. Считать **один дефект**, две независимые проверки; не удваивать productivity. NPI-12 Standards/Ponytail оба указывают repeated regional scan/timeout. Это полезное corroboration, но ещё не production blocker или доказанная SLA violation.

CONFIRMED: NPI-06 optional duplicated setup suggestion не приняли ради читаемости; NPI-05 две короткие existing label expressions оставили. Это добросовестные отклонённые advisories, не доказательство «плохих reviewers». INFERRED: обязательное повторение всех трёх широких проходов по каждой task тратит ресурсы там, где риск уже покрыт и нет независимого нового oracle.

Каждое finding должно содержать scenario, invariant, source line/SHA, severity, reproduction или reasoning, disposition и repeat-check. «Ship», «0 findings», число тестов и ссылка на чужой full log не заменяют эти поля. Reviewer может честно ограничиться source review; задача должна отдельно иметь executable evidence.

## PASS и независимость

PR #1 сообщает24/24, но оговаривает ограниченный live shell; первая полноценная walkthrough затем дала3FAIL. Это преждевременное расширение смысла acceptance, а не доказательство недобросовестности named reviewer. NPI-01/06 не фабрикуют RED для docs/conformant behavior — полезная зрелость. NPI-12 корректно разносит conditional final CI, functional/human/production readiness.

Независимый агент — отдельная session/thread с назначенной задачей. Разные заголовки одного parent ответа — три оси self-review. Независимый thread, читающий только parent report, не создаёт независимое runtime доказательство. Review scopes и фактически исполненные commands сохранять рядом с verdict. Historical raw prompts/tool traces проверены выборочно, exhaustive независимость всех заключений UNKNOWN.

## Схема v2 (предложение)

| Тип задачи | Обязательные проверки | Когда расширять |
|---|---|---|
| Простые docs/labels | Один reviewer на содержание/Spec+узкие conventions; links/diff; неизменённый обязательный CI final SHA | Domain meaning, confidential data или broad ownership требуют второго axis |
| Средняя функция | Independent Spec, public-seam regression, соседние contracts, live smoke затронутого пользовательского transition | Новый service/API seam или архитектурная ownership → Standards |
| Архитектура | Standards и Spec отдельными агентами, characterization/compatibility tests; Ponytail pass на scope и connected risky path | Третий агент только если независимая technical экспертиза реально добавляет oracle |
| Данные/метрики/export/security | Independent Spec с ручными constants/identity/completeness/literal checks; Standards ownership; Ponytail targeted load/lean/correctness pass | Здесь сохраняются все три **оси**, отдельный третий агент зависит от дополнительной ценности; full data/security проверки обязательны |
| Финальная приёмка | Ответственный owner выполняет runtime acceptance, merged-main CI, served revision, реальные действия/output; независимый reviewer проверяет итоговую матрицу и evidence | Независимый повтор выбранного risky сценария при недостаточном oracle/спорном PASS; постоянная новая executor-role не нужна. Human acceptance отдельным человеком |

Не нужны три универсальных reviewer на каждую задачу. Это проверяемая гипотеза оптимизации, не уже измеренная экономия. В pilot считать unique confirmed findings, duplicates, rejected advisories, review minutes/turns и escaped defects. Отключение review не отменяет безопасность, корректность данных, contracts или final full CI.
