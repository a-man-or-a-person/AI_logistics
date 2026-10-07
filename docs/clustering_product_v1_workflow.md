# Clustering Product v1 workflow

> **Статус: SUPPORTING / CURRENT.** Документ детализирует реализованный Product workflow. Каноническая архитектура находится в [current-state.md](architecture/current-state.md), а продуктовый смысл — в [CONTEXT.md](../CONTEXT.md).

## Контур

```text
Pulse + coordinate cache
  → single origin + single destination region
  → period / price / vehicle / tonnage filters
  → Geography | Geography + Cost | Geography + Volume | Bear Cost | Bear Volume
  → points + representatives + outliers + cluster table
  → synchronized map + table + inspector
  → lazy paginated Pulse rows for one destination
  → cached comparison on one data snapshot
```

## API

- `GET /api/clustering/options` — режимы, фильтры, K bounds, defaults и Bear thresholds;
- `GET /api/clustering/origins?q=&limit=` — searchable origin catalog по FIAS;
- `POST /api/clustering/run` — canonical point result with `data_snapshot` and a compact
  `cluster_table` for Geography, Geo+Cost and Geo+Volume;
- `POST /api/clustering/compare` — пять фиксированных режимов на одном data slice,
  `winner = null`;
- `POST /api/clustering/point-rows` — snapshot-safe Pulse rows for one destination,
  newest first, in pages of at most 50;
- `POST /api/clustering/preview` — совместимый диагностический preview.

Frontend-метод `runClusteringComparison()` выполняет один запрос к `/compare`.
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
