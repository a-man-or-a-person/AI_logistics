# Clustering Product v1 workflow

> **Статус: SUPPORTING / CURRENT.** Документ детализирует реализованный Product workflow. Каноническая архитектура находится в [current-state.md](architecture/current-state.md), а продуктовый смысл — в [CONTEXT.md](../CONTEXT.md).

## Контур

```text
Pulse + coordinate cache
  → frontend explicit origin set or explicit All + single destination region
  → period / price / vehicle / tonnage filters
  → Geography | Geography + Cost | Geography + Volume | Bear Cost | Bear Volume
  → points + representatives + outliers + cluster table
  → synchronized map + table + inspector
  → frozen contributing-origin summary for one destination
  → origin selection
  → lazy paginated Pulse rows for one destination
  → cached comparison on one data snapshot
```

## API

- `GET /api/clustering/options` — режимы, фильтры, K bounds, defaults и Bear thresholds;
- `GET/POST /api/clustering/revision` — uncached metadata revision и наличие frozen saved results;
- `GET /api/clustering/origins?q=&limit=` — searchable origin catalog по FIAS;
- `POST /api/clustering/run` — canonical point result with `data_snapshot` and a compact
  `cluster_table` for Geography, Geo+Cost and Geo+Volume;
- `POST /api/clustering/compare` — пять фиксированных режимов на одном data slice,
  `winner = null`;
- `POST /api/clustering/point-rows` — snapshot-safe Pulse rows for one destination,
  newest first, in pages of at most 50;
- `POST /api/clustering/point-origins` — origin contributions for the exact saved point;
- `POST /api/clustering/preview` — совместимый диагностический preview.

Backend принимает scalar или canonical `origin_fiases`; options использует
повторяемый query parameter. Новые detail-клиенты передают
`analysis.frozen_request` + snapshot/destination для точного saved result,
получая row attribution и сохранённую membership. Старый scalar detail остаётся
совместимым. Backend All разрешает полный региональный каталог до segment filters;
intent хранится отдельно от frozen resolved set. Compare разрешает All один раз,
detail использует только saved explicit set и membership, без расширения или rerun.
UI включает explicit «Все отправления»: сначала выбрать All, затем регион доставки.
Ручные токены сохраняются при переключении; в All они скрыты, поиск отключён.
Снятие All возвращает ручной выбор и доступные ему регионы. Point origin summary
показывается отдельно в inspector; выбор origin открывает frozen origin→point rows.
Summary и rows имеют loading/error/retry и typed recalculation recovery. Form edits
не меняют их контекст. Нижняя таблица сохраняется. Export отсутствует.

Frontend-метод `runClusteringComparison()` выполняет один запрос к `/compare`.
Перед frontend cache reuse при новом Calculate/Compare revision check подтверждает
generation и exact saved-result lifetime; при смене источника/eviction cache отклоняется.
Failed validation показывает ошибку, старый map/table остаётся frozen. All заново
разрешается только новым расчётом. Внутреннее переключение сравнения сохраняет frozen
navigation без новых запросов. Revision не является cryptographic content identity;
подробности и ограничения — в Product contract.
Backend переиспользует location/spatial context и result LRU; UI переключает
сохранённые варианты на карте без повторных запросов.

Все ответы canonical API возвращают `X-Request-ID`. Сервисные логи связывают этот
идентификатор с фильтрами, размером выборки, покрытием координат, cache hit/miss и
временем расчёта; ошибки сохраняют тот же идентификатор для трассировки одного запроса.

## Frontend

Верхняя навигация разделяет «Карту данных» и «Кластеризацию». Product workspace
имеет три зоны: Controls → Map → Inspector.

Состояние и UI разделены по модулям в `frontend/js/clustering/`:

- `state.js` — form state, result snapshot, stale и comparison context;
- `controls.js` — динамические options и mode-specific controls;
- `inspector.js` — summary, metrics, cluster/Bear details и lazy Pulse rows;
- `table.js` — desktop cluster table, raw-value sorting и table actions;
- `comparison.js` — нейтральные карточки и одна переключаемая карта;
- `controller.js` — orchestration, cached mode activation и map ↔ table ↔ inspector selection.

Изменение формы не удаляет предыдущий результат, а переводит его в stale-state.
Отправления добавляются по FIAS из поиска и удаляются отдельными токенами.
Поиск не меняет выбранный набор; токены доступны кнопками и клавишами Delete/Backspace.
Options используют repeated `origin_fiases`; run/compare — sorted/deduplicated список.
Общие фильтры и один регион назначения применяются ко всему набору. Inspector
показывает frozen origins, включая origins без строк после фильтров.
Detail использует `analysis.frozen_request`, а cache key включает режим и параметры.
`RESULT_UNAVAILABLE` удаляет соответствующие run/detail/comparison entries и требует
явного fresh Calculate; source generation при этом не считается rejected.
Ошибка нового расчёта сохраняет предыдущую карту, таблицу и frozen inspector.
Повторный расчёт оставляет карту видимой. `no_bears` — успешный пустой результат,
а connectedness violation — отдельный invalid state.

Geography, Geo+Cost и Geo+Volume показывают одну backend-calculated cluster table;
Bear Cost и Bear Volume сохраняют прежнее представление. Раскрытие Pulse rows загружает
первую страницу только по запросу пользователя; смена точки, результата или comparison mode
не позволяет позднему ответу попасть в новый контекст.

Desktop использует три колонки. На tablet inspector становится drawer, на mobile
controls и inspector открываются bottom-sheet поверх карты. Все drawers и dropdowns закрываются
по Escape; cluster/Bear labels не зависят только от цвета.

Перед запуском форма показывает полный preview направления, источника Pulse, сегмента,
режима и параметров. Карточка результата фиксирует тот же data slice, а сравнение явно
показывает общую выборку над пятью нейтральными карточками. Клик по продуктовой точке
одновременно открывает popup на карте и подробности в inspector без повторного запроса.
