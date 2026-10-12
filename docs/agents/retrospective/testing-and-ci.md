# TDD, CI, browser и ресурсы

Первичные источники [E03–E09](evidence-index.md). Здесь historical evidence прочитано; production suite и браузеры заново не запускались для docs-only ретроспективы.

## Настоящий RED

| Случай | Доказательство дефекта до исправления | Что не следует считать RED |
|---|---|---|
| P1/P2 | Actual HTTP409 затем reuse; native checked radio/preview mismatch | PermissionError basetemp, fixture typo `to_dict` |
|02/03 | Union400, generation races200, injected foreign/scalar options, repeated All resolution | Отсутствие ещё не построенного UI в backend-only ticket |
|04/05 | Tokens/reset/region removal/late search и All intent/controller defects | Edge process startup failure; generated HTML charset failure — infra, не domain RED |
|07/08/09 | Missing summary404, cached wrong origin, native focus/scroll, medoid FIAS/map/overflow | Wrong test table ID; отсутствующий Archive у synthetic fixture; ожидание hidden control старым driver |
|Freshness | Baseline source replacement bypassed backend; revision succeeded, calculation409 recovery failed | Conformant All/P1/P2 regressions не обязаны становиться искусственно красными |
|10 | Endpoint404, partial-row success, illegal truncated name, wrong provenance | Сам статус200 без independently reopened workbook не GREEN |
|11 | Missing transport, raw connection-error handling | Controller sandbox timeout явно не behavioral RED |
|01/06/12 | Docs discovery / existing correct formulas / integrated verification | Искусственный failing test для уже правильного поведения не нужен |

Из сохранившихся RED logs и baseline checks подтверждается последовательность для перечисленных regressions; нельзя вывести процент соблюдения TDD за всю историю. Timestamp отчёта не доказывает, что каждый test был написан до production edit. Там, где есть baseline execution и actual failure, уверенность выше [E04–E07].

## Пирамида проверок

1. Быстрые Python public-contract tests: selection normalization, generation, weights, missing values, saved membership, typed errors. Независимые constants для финансов/метрик, а не та же production формула в expected.
2. Node state/controller tests: cancellation/late responses/cache reuse. Test doubles допустимы на API/map boundary, но DOM/render contracts требуют Edge.
3. Focused Edge DOM tests: checked controls, keyboard/focus, overflow/scroll, download lifecycle. Эти проверки обнаруживают browser semantics, которые Node не воспроизводит.
4. Небольшой live Flask + native Edge smoke после каждого изменённого transition: real source replacement/recovery, cached activation→form edit, parent change→late reply, download→reopen. Без повторения всей исторической walkthrough после каждого label edit.
5. Full merged-main acceptance и human acceptance на release. Production-scale testing после получения intended workload и target.

Не назначать произвольные проценты уровней: цена Edge уже отличается от Python и должна измеряться. Публичное действие/response/output — устойчивый oracle. NPI-11 DOM fixture repairs и NPI-12 hidden-control driver fixes показывают стоимость тесной связи fixture с renderer; они не доказывают, что все frontend tests избыточны. Сохранять assertions, обновлять минимальные doubles при новых native methods [E07, E08].

## CI: измеренные данные

GitHub API на момент исследования:45 runs,43success/2failure;27pull_request/18push-main. Все jobs прочитаны. Сумма `completed_at−started_at` jobs: **6113 секунд (101 мин53с)**, медиана88с. Это суммарное runner elapsed, включая install/setup/steps; не стоимость, не человеко-время и не critical-path duration. Сумма run `updated_at−created_at`:6284с, включая lifecycle задержки. Эти две величины не смешивать.

Два failure:

- [38050412351](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38050412351): Python suite зависел от untracked CSV. Existing synthetic fixture устранила зависимость, assertions сохранились.
- [38136824505](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38136824505): frontend contracts, generated HTML UTF-8. Исправлен shared harness, final candidate проходит.

Workflow — один Windows job, locked dependencies/pip check/Ruff/startup/Node+Edge/JUnit zero-skips/Python. Missing Edge, zero cases и skips не дают зелёный результат. NPI-12 baseline evidence говорит `protected:true`, но не полный effective required-check rule. Точная конфигурация enforcement здесь **UNKNOWN**; success jobs не доказывают невозможность merge без checks. Repo settings не менялись.

Зелёный CI не покрывал полный живой P1/P2 workflow. Исходная acceptance13PASS/3FAIL при successful exact-main CI — прямой counterexample. Позднее public-seam regressions закрепили переходы; full CI нельзя считать человеческой приёмкой.

## Полнота browser evidence

Screenshot показывает rendered state, network — были ли run/compare и какая frozen identity отправлена; DOM — checked/focus/order. Вместе это сильнее имени файла: в первоначальной acceptance `stale-recovered` screenshot в действительности не доказывал recovery. Native clicks, остановленные на scroll/geometry, не считаются submit без actual request [E03].

Real Flask исключает часть ошибок API doubles; headed Edge дополняет focus/видимость, но остаётся автоматизацией. NPI-12:12 downloads reopened плюс90k file; functional acceptance подтверждена на synthetic fixture. Реальный логист и desktop Excel не принимали результат по доступному evidence. Human acceptance UNVERIFIED.

## Старый checkout и onboarding

[Startup evidence](../../npi12-evidence/startup.json) сравнивает port5055 со старым `f69e64c` и candidate5082 с `596d9fb`; точные bytes HTML/JS совпали со своими checkout. Старый HTML не содержал multi-origin/All. ETag304 сам по себе нормален; это не доказательство browser caching bug.

Перед передачей URL записывать абсолютный checkout, SHA, interpreter, entrypoint `run.py`, port и источник synthetic/approved. Получить `/` и один изменённый JS asset, сверить с файлами запущенной revision; затем native smoke. Если занят порт, идентифицировать владельца и предложить корректный URL, сохраняя чужой процесс. Human acceptance проводить раньше: при первой usable origin-selection/map/table и первой downloadable workbook, не ждать всей итерации.

## Evidence и окружения

В final main315 tracked `*-evidence/` файлов,71,036,036 bytes (~67.7MiB); NPI-12 —92файла/18,544,173bytes. Counts получены из `git ls-files` и размеров checkout, а не repository pack size. Исторически19 worktree registrations до данной ретроспективы (включая root, baseline и external Temp worktree),12 NPI worktrees. Сейчас создаётся ещё один отчётный worktree; это не historical defect. Обнаружены минимум5 env directories:3 в root и по1 у10/11; полный диск/другие checkout не обследованы. Наличие нескольких env не доказывает, что их можно безопасно объединить.

Local full elapsed по reports: P2 19.50с;07 67.88с;Freshness113.04с;10 178.74с;11 304.65с. Это разные версии/среды; рост согласуется с frontend suite, но строгий causal attribution UNKNOWN. Число всех повторных local checks, installations, токены и денежная стоимость UNKNOWN.

## Capacity

NPI-12 synthetic:20k rows/100destinations export4.09с;90k/300 export21.27с, browser handoff19.52с, sequential-process peak486.15MiB. Полнота90k independently reopened подтверждена. Это один измеренный environment, не percentile/SLA. Существующий30с timeout создаёт ограниченный запас; repeated regional scans объясняют risk. Улучшать grouped traversal/index только после workload target; не вводить silent row cap.

## Что можно сэкономить

Локально: focused regression после finding; один полный run после production fixes, повтор лишь при новом code/test/environment change. Не повторять local full из-за report wording, final SHA CI оставить. Docs publish батчить перед final candidate: #19 три PR runs (837 job seconds суммарно), два ранних дают550с потенциально предотвращаемой работы; #9 два ранних ещё149с. **699с — ретроспективный upper-bound сценарий, не доказанная экономия:** если fixes/report status требуют нового кандидата, повтор нужен.

Предложение retention: уникальные RED/GREEN, oracle constants, observed actions/network summary, representative screenshots, manifest и baseline/final SHA — durable; остальные reproducible bulk logs в bounded artifact store с expiry. Expired artifact не должен быть единственной ссылкой PASS. Очистка только после confirmed merge+manifest+clean worktree+stopped owned processes; dirty/user files сохранять и эскалировать владельцу. Никакого cleanup в этой работе.
