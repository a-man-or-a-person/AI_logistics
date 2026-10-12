# Причины сбоев и практики

Здесь CONFIRMED относится к наблюдаемому событию; причины без прямого trace помечены INFERRED. Источники [E01–E10](evidence-index.md). Фикс-коммит сам по себе не доказывает плохую работу агента или избыточный feature.

## TOP-10 ошибок / пробелов процесса

| № | Evidence и последствие | Причина | Где исправить процесс |
|---|---|---|---|
|1|CONFIRMED: первая acceptance13PASS/3FAIL при зелёном main; P1 не восстанавливал rejected snapshot [E03]|INFERRED: «reject safely» и «recover successfully» проверялись раздельно; missing recovery transition|Первый владелец cache/detail обязан выполнить conflict→same request→fresh rows через real HTTP|
|2|CONFIRMED: P2 cached Geography затем Archive возвращал checked Bear Volume [E03]|CONFIRMED root code: renderer обновлял cards, `syncForm` читал stale radio/presets|Rendered controls и editable state проверять вместе; frozen display отдельно|
|3|CONFIRMED: Freshness source replacement без detail conflict позволял frontend cache bypass; отдельная race после revision [E04]|CONFIRMED: signature cache не доказывает generation/presence; INFERRED: source lifecycle contract был неполон|Единый invariant на cache acceptance, повторная generation check при result publication|
|4|CONFIRMED:5055 served old bytes; новый candidate работает на5082 [E08]|CONFIRMED: старый checkout/server, не новые UI algorithms; INFERRED: handoff не проверял фактический URL/revision|Запуск/передача: SHA+port+asset checks+native smoke|
|5|CONFIRMED: CI first hosted red из-за private/untracked CSV [E09]|CONFIRMED: endpoint test зависел от локального файла; локальная зелень скрывала зависимость|Clean fixture-only gate и явный источник данных; не включать private CSV в CI|
|6|CONFIRMED: sandbox startup/timeouts и Temp ownership ошибки в #2/#3/P2, old reviewer env без XlsxWriter на12 [E03,E08,E09]|INFERRED: окружение и application failures не всегда разделены до review run|Preflight interpreter/lock/temp/browser; environment failure не RED и не defect|
|7|CONFIRMED: cached A→B→A показывал не того origin; aborted-finally терял focus в08 [E05]|CONFIRMED code paths: cached handler/finally rerender; INFERRED: happy-path fresh fetch сильнее покрыт, чем reentry/cancel|Transitions cached/fresh/error/cancel с native focus oracle|
|8|CONFIRMED: NPI-10 ambiguous intent мог выдать provenance первого save; имя sheet после truncation незаконно [E06]|CONFIRMED: equal cached data не означает equal selection intent; validation before truncation недостаточна|Identity/provenance и post-transform validation на output boundary|
|9|CONFIRMED: CURRENT readiness оставался outdated до11/12; NPI-06 changed criterion owner [E02,E07,E08]|INFERRED: update obligations распределены по docs без единого final scope check|Один change-reach checklist на current docs/consumers и owner каждого criterion|
|10|CONFIRMED: repeated review/general full gates,315 evidence files/67.7MiB [E01,E09]|INFERRED: completeness интерпретировалась как повторение доказательств; publication docs commits запускали новые full CI|Risk-based reviews, unique evidence manifest, batch report до final publish|

Последний пункт — подтверждённый объём, **не доказанная бесполезность всех файлов/проверок**. Повторная full acceptance после объединения features необходима. Нет данных, чтобы честно составить десять персональных «ошибок агента»: эта таблица содержит системные gaps, а не выдуманные виновные.

## TOP-10 практик, которые сохранить

1. **Разделение Product/RESEARCH/LEGACY:** CONTEXT и ProductModeCatalog refactor сохраняют пять режимов и совместимость [E01,E11].
2. **Characterization до refactor:** `8dafa2a`, далее mode-neutral orchestration/adapters [E11].
3. **Узкий shared repair:** P2 восемь production строк в существующем renderer, без нового state framework [E03].
4. **Public-seam TDD:** Freshness RED против нетронутого baseline, реальные source changes и typed recovery [E04].
5. **Формулы с независимыми знаменателями:** NPI-06 explicit250km/40valid machines и separate price/rate [E02,E05].
6. **Сохранённая identity:**02/07/10 используют exact membership/frozen row access; export не пересчитывает clustering [E02,E06].
7. **Output проверяют после handoff:** XLSX reopened, full IDs/row counts/metrics и literal strings [E06–E08].
8. **CI fail-closed frontend:** missing browser/skips/empty JUnit не проходят; infra отрицательные probes [E09].
9. **Честные limitations:** docs01 не изобретают ATI;06 не изобретают RED;12 отделяет76PASS от production/human [E02,E08].
10. **Независимые actionable findings и minimal fixes:** Spec source race, Ponytail deepcopy generation, shared final re-review [E02,E04,E06].

## Оркестрация: двенадцать аспектов

| Аспект | Оценка по доказательствам |
|---|---|
|Декомпозиция|01 docs,02 union,03 All API,04/05 UI,06 numeric oracle,07/08 detail/navigation,10/11 API/download,12 acceptance — понятные seams. Порядок06 после02 верен [E01]|
|Размер tickets|P2 минимален;02 и10 захватывают identity/consumers, что оправдано. No timing/effort ledger: «оптимальный размер» UNKNOWN|
|Скрытые зависимости|Freshness понадобился после07; exact identity/presence affects detail/export. INFERRED: lifecycle dependency стоило выделить до consumer tickets|
|Роли|Отдельные Standards/Spec/Ponytail threads подтверждены metadata и review artifacts. Testing/browser — часто parent-owned tools, не отдельные agents [E10]|
|Параллельность|09/10 same baseline, затем17 integrated main. 03/04 могли параллельно после02/06/P2. Фактическая duration savings UNKNOWN|
|Handoff|Approved spec/coverage/order/execution requirements дают контракт. Local-only tracker и старые status labels могут расходиться с Git;12 reconciled ancestry вместо rewrite [E01,E08]|
|Контекст|Файлы служат authority, fresh chats уменьшают смешение. Repeated whole-doc/report loads могут стоить ресурсов; их совокупные tokens UNKNOWN|
|Requirements changes|NPI-09 business reaffirmation explicitly recorded. Future export branches deferred к11/12 без circular prerequisite. Это правильный scope control [E01,E05]|
|Git/worktrees|Existing untracked preserved, isolated branches. 19 registrations — измерение, не proof конфликтов. Единственная explicit integration17 после16; потери файлов/межагентные конфликты не доказаны|
|Context window|Metadata подтверждает sessions, но utilization/compaction losses не измерены. Нельзя обвинить window pressure без trace|
|User intervention|Medoid reaffirmation и authorizations описаны в reports; полный count prompts/approvals UNKNOWN. Human acceptance ещё не выполнена|
|Автоматизация|Сильные CI/Edge/OOXML oracles; duplicated reviews/logs и env preflight создают overhead. Graphify evaluation показывает, что дополнительный tool сначала исследовали, а не внедрили по рекламе [E12]|

Основному координатору следует владеть переходами и окончательной передачей работающей ревизии. Исполнитель должен сохранять validation/cancellation при extraction, reviewer — проверять контрпример, а не только success summary. Не поручать coordinator самостоятельно «подписывать» human acceptance или считать synthetic capacity производственным SLA.
