# Canonical clustering Product v1 contract

Дата актуализации: 2026-10-10.

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

Один Product запрос содержит непустой набор origin FIAS и один
`destination_region`. Селектор — ровно один из `origin_fias` (старый scalar)
или `origin_fiases` (список строк), или `all_origins: true`; список очищается от пробелов, сортируется
и дедуплицируется. Пустой/null/конфликтующий селектор возвращает
`INVALID_REQUEST` (400), неизвестный FIAS — `UNKNOWN_ORIGIN` (422).
Отсутствующий origin никогда не означает All. All разрешается в полный набор origins,
имеющих строки в выбранном destination region, до segment filters и независимо от q/limit.
False/null/строка/число вместо JSON true, а также смешанные селекторы отклоняются.
Периоды, типы цены, типы кузова и тоннаж — общие для всех origins списки:

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

`GET /options` поддерживает повторяемый `origin_fiases`; facets объединяют строки
выбранных origins без повторного подсчёта. Строки выбранного среза объединяются
по destination FIAS до coordinates и полного SpatialGraph. Каждый metric mean
использует собственный валидный вес машин. Исходные одинаковые строки с разными
source-row IDs сохраняются. Preview не строит graph/кластеры; пустой срез на
preview/run/compare возвращает `NO_DATA` (422).

`GET /origins?q=&limit=&destination_region=` ограничивает suggestions регионом;
q/limit сохраняют прежнюю семантику. `GET /options?all_origins=true&destination_region=…`
возвращает полный региональный каталог и union facets. Без destination region All
возвращает `INVALID_REQUEST` (400); отсутствующий регион/пустой каталог —
`UNKNOWN_DESTINATION_REGION` (422). Каталог и calculation rows проверяются в одном
generation; гонка возвращает `STALE_DATA_SNAPSHOT` (409), ошибка чтения — typed
`INTERNAL_ERROR` (500), без частичного успешного результата.

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
`STALE_DATA_SNAPSHOT` (HTTP 409), а отсутствие строк точки в frozen data slice —
`UNKNOWN_DESTINATION_POINT` (HTTP 422). Старый scalar payload без mode/parameters
сохраняет проверку cached data slice и прежнюю форму rows.
Новый payload с `origin_fiases` либо mode/parameters требует обоих полей
mode/parameters и точного saved result. Удобный готовый контекст —
`analysis.frozen_request`: resolved origins, region, четыре filters, mode и
нормализованные request parameters (отдельно от диагностических `analysis.parameters`).
Добавьте `data_snapshot` и `destination_fias`; необязательный `detail_origin_fias`
может только сузить выбранный набор, иначе `UNKNOWN_ORIGIN` (422).
Rows аддитивно содержат origin/name/фактический row region,
destination/name/region и saved `cluster_id`/`status`. Unassigned point имеет
null cluster, а не выдуманную membership. После eviction/restart точного результата
возвращается `RESULT_UNAVAILABLE` (409), без пересчёта или подстановки другого режима.

`analysis.origin_fiases`, `selection_intent`, `origins` и `origin_coverage`
фиксируют canonical выбор, display metadata и origins без строк после фильтров.
Scalar `analysis.origin`/`origin_fias` сохранены для singleton; у union они null.
Для All `analysis.selection_intent = {"all_origins": true}`, а `origin_fiases`
содержит фактический sorted/deduplicated набор, включая origins без строк после
фильтров. `analysis.frozen_request` всегда содержит explicit resolved origin_fiases,
без all_origins: detail принимает именно этот контекст и никогда не разрешает All.
Переданный All в point-rows возвращает `INVALID_REQUEST` (400). Cache reuse для
одинакового набора explicit/All сохраняет intent текущего запроса; calculation и
saved membership общие. После нового generation старый detail получает 409;
только новый preview/run/compare может разрешить расширенный каталог.
Location cache связан с generation/origins/region/filters, result cache дополнительно
с mode и нормализованными parameters; сохранённый ответ хранит фактическую membership
и exclusions. Source/coordinate generation проверяется также перед завершением
preview/run/compare/detail и публикацией cache entries: гонка даёт
`STALE_DATA_SNAPSHOT` (409). Snapshot сам по себе не идентифицирует результат.
XLSX и origin-summary endpoints пока отсутствуют.

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
All разрешается один раз перед пятью вариантами compare; каждый вариант использует
тот же resolved set, generation и полный geographic graph. Preview не запускает clustering.

Координаты берутся из существующего `backend/cache/coords_cache.json`.
Неразрешённые координаты учитываются в data quality и исключаются из ML.

## Совместимость

Data Map и `/api/ml-cluster` сохранены для legacy-клиентов. Product v1 вызывает
только `/api/clustering/*`.
