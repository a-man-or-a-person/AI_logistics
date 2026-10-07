# Canonical clustering Product v1 contract

Дата актуализации: 2026-10-08.

## Назначение

Product v1 — рабочее место сравнения пяти способов анализа одного и того же
логистического сегмента:

- `geography` — связная кластеризация только по географии;
- `geo_cost` — связная кластеризация по географии и взвешенному `₽/км`;
- `geo_volume` — связная кластеризация по географии и числу перевозок;
- `bear_zones` — связные дорогие зоны и отдельные дорогие точки;
- `bear_volume_zones` — связные зоны и отдельные точки с аномально высоким объёмом.

Система показывает метрики рядом, но не выбирает победителя.

## Dataset

Один запрос всегда содержит одну origin point (`origin_fias`) и один
`destination_region`. Периоды, типы цены, типы кузова и тоннаж — списки:

```json
{
  "origin_fias": "…",
  "destination_region": "Ленинградская область",
  "period_types": ["current"],
  "price_types": ["tender"],
  "vehicle_types": ["tent truck"],
  "tonnage_ids": ["7"]
}
```

`price = Pulse.units`, `trip_count = Pulse.bid_count`, а экономический признак
вычисляется как `price / route_length` и агрегируется backend с весом
`trip_count`.

## Параметры режимов

Для `geography`, `geo_cost` и `geo_volume`:

```json
{"mode":"geography","parameters":{"k_mode":"auto","n_clusters":"auto"}}
```

или manual K в границах из `/api/clustering/options`.

Geo+Cost дополнительно принимает только три фиксированных пресета:

```json
{"geography_weight":0.7,"economics_weight":0.3}
```

Допустимые пары: `0.8/0.2`, `0.7/0.3`, `0.6/0.4`. Economic-invalid точки
возвращаются со статусом `economic_unavailable`, но не участвуют в расчёте.

Geo+Volume принимает те же три пары весов через `geography_weight` и
`volume_weight`. Признак объёма равен `log1p(trip_count)` и robust-scaled;
пространственный граф остаётся обязательным ограничением связности.

Для Bear Zones:

```json
{"mode":"bear_zones","parameters":{"bear_threshold":0.35,"singleton_threshold":0.70}}
```

Bear eligibility требует положительный `trip_count` и валидный
`weighted_rub_per_km`; отдельное наличие `weighted_price` не требуется.

Для Bear Zones по объёму:

```json
{"mode":"bear_volume_zones","parameters":{"volume_threshold":0.35,"singleton_threshold":0.70}}
```

Базовый уровень — среднее число перевозок на разрешённую точку региона. Допустимые
пороги зоны: `+20`, `+25`, `+30`, `+35`, `+40`, `+50%`; порог одиночной точки
фиксирован на `+70%`.

## Результат

Ответ содержит `status`, `analysis`, `data_quality`, `warnings`, `metrics`,
`graph_metrics`, `regional_economics`, `regional_volume`, `data_snapshot`, `cluster_table`,
`points`, `clusters` и `outliers`.
Кластеры содержат medoid representative и признак
`connected`. Product API не возвращает и frontend не строит полигоны.

Для `geography`, `geo_cost` и `geo_volume` поле `cluster_table` содержит компактные
backend-calculated строки фактических кластеров; для Bear-режимов оно равно
`{"supported": false}`. `data_snapshot` фиксирует поколения Pulse и coordinate cache.

`POST /api/clustering/point-rows` принимает тот же frozen data slice, `data_snapshot`,
`destination_fias`, `offset` и `limit`. Endpoint возвращает не более 50 исходных строк Pulse
в детерминированном newest-first порядке. Несовпадение snapshot возвращает
`STALE_DATA_SNAPSHOT` (HTTP 409), а точка вне frozen result —
`UNKNOWN_DESTINATION_POINT` (HTTP 422).

Нормальные result states: `success`, `no_bears`. Нарушение связности не выдаётся
как успешный результат, а возвращает typed error `CONNECTIVITY_VIOLATION`.
Ошибки данных используют HTTP 422 и стабильные codes: `UNKNOWN_ORIGIN`,
`UNKNOWN_DESTINATION_REGION`, `NO_DATA`, `INSUFFICIENT_POINTS`,
`INSUFFICIENT_ECONOMICS`.

Ошибки параметров используют отдельные стабильные коды: `INVALID_CLUSTER_COUNT`
для синтаксически или фактически недопустимого K и `INVALID_MODE_PARAMETERS` для
неподдерживаемого пресета Geo/Cost или Geo/Volume, Bear threshold либо постороннего параметра режима.
`INVALID_REQUEST` остаётся кодом ошибки общей формы JSON-запроса.

Каждый ответ `/api/clustering/*` содержит заголовок `X-Request-ID`. Клиент может
передать собственный идентификатор (до 64 символов), иначе backend создаёт его сам.
В журнал расчёта входят request ID, режим, направление, фильтры, число исходных строк,
покрытие координат, состояния repository/location/graph/result cache и время расчёта.

`POST /api/clustering/compare` фиксирует Geography Auto, Geo+Cost 70/30 Auto,
Geo+Volume 70/30 Auto, Bear Cost +35 и Bear Volume +35 на одном data slice.
Поле `winner` всегда равно `null`.

Координаты берутся из существующего `backend/cache/coords_cache.json`.
Неразрешённые координаты учитываются в data quality и исключаются из ML.

## Совместимость

Data Map и `/api/ml-cluster` сохранены для legacy-клиентов. Product v1 вызывает
только `/api/clustering/*`.
