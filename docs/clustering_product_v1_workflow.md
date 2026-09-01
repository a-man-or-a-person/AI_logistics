# Clustering Product v1 workflow

## Контур

```text
Pulse + coordinate cache
  → single origin + single destination region
  → period / price / vehicle / tonnage filters
  → Geography | Geography + Cost | Geography + Volume | Bear Cost | Bear Volume
  → points + representatives + outliers
  → inspector
  → comparison on one dataset snapshot
```

## API

- `GET /api/clustering/options` — режимы, фильтры, K bounds, defaults и Bear thresholds;
- `GET /api/clustering/origins?q=&limit=` — searchable origin catalog по FIAS;
- `POST /api/clustering/run` — canonical point-only result;
- `POST /api/clustering/compare` — пять фиксированных режимов на одном data slice,
  `winner = null`;
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
- `inspector.js` — summary, metrics, cluster/Bear details;
- `comparison.js` — нейтральные карточки и одна переключаемая карта;
- `controller.js` — orchestration и map ↔ inspector selection.

Изменение формы не удаляет предыдущий результат, а переводит его в stale-state.
Повторный расчёт оставляет карту видимой. `no_bears` — успешный пустой результат,
а connectedness violation — отдельный invalid state.

Desktop использует три колонки. На tablet inspector становится drawer, на mobile
controls и inspector открываются bottom-sheet поверх карты. Все drawers и dropdowns закрываются
по Escape; cluster/Bear labels не зависят только от цвета.

Перед запуском форма показывает полный preview направления, источника Pulse, сегмента,
режима и параметров. Карточка результата фиксирует тот же data slice, а сравнение явно
показывает общую выборку над пятью нейтральными карточками. Клик по продуктовой точке
одновременно открывает popup на карте и подробности в inspector без повторного запроса.
