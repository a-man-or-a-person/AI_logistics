# Canonical clustering Product v1 contract

Дата актуализации: 2026-10-11.

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
`GET /options` без селектора возвращает полный список регионов доставки для выбора All;
с явными origins список регионов ограничен их перевозками.
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
`POST /api/clustering/point-origins` принимает frozen resolved request, snapshot и
destination_fias, обязательно mode/parameters (в том числе для scalar caller).
Возвращает data_snapshot, destination_fias, saved cluster_id/status и origins:
одна строка на contributing origin FIAS внутри этой точки, sorted по FIAS.
Поля: origin_fias/name, origin_regions (фактические distinct row regions, null
сохранён), source_row_count, trip_count, weighted_route_length/price/rub_per_km,
valid_route_length/price/rub_per_km_trip_count и warnings.
Покрытие каждого показателя — соответствующий valid count / trip_count.
Метрики используют существующий accumulator; null не заменяется нулём.
Zero-match origins остаются в analysis.origin_coverage, не создают summary rows.
Summary и detail используют общий frozen-row доступ, точную saved membership и
typed errors; нет All expansion или rerun. Inspector показывает summary отдельно,
origin buttons доступны клавиатурой и открывают lazy50 rows с source attribution.
XLSX доступен через backend API ниже; кнопка download относится к NPI-11.

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

## Проверка актуальности frontend cache

Перед reuse при новом Calculate/Compare frontend вызывает read-only
`POST /api/clustering/revision` с `{"results": [frozen_request + data_snapshot, ...]}`.
Допускается до 6 контекстов: пять вариантов сравнения и отображаемый результат.
All здесь запрещён: передаются только сохранённые resolved origins, mode/parameters
и четыре filters. Ответ: `{"ok": true, "data_snapshot": "opaque revision", "available": [true, ...]}`,
где available соответствует каждому входному контексту и означает наличие exact
saved result текущего generation в памяти. `GET /revision` возвращает тот же revision
и пустой available. Все ответы, включая ошибки, имеют `Cache-Control: no-store`;
frontend также использует fetch cache no-store.

Revision использует существующий SHA-256 от metadata token Pulse и coordinate cache
(resolved path, size, mtime_ns); пути и metadata endpoint не публикует. Это fingerprint
метаданных, **не hash содержимого**: изменение с тем же path/size/mtime не обнаруживается.
Проверка делает stat, без CSV parsing, content hashing, All expansion или clustering.
Generation проверяется повторно перед ответом; race даёт STALE_DATA_SNAPSHOT409,
ошибка чтения — INTERNAL_ERROR500. Проверка сбрасывает устаревшие in-memory caches,
но не изменяет исходные данные и не продлевает LRU lifetime saved result.

Несовпадение revision применяет существующую P1 invalidation ко всем frontend result,
comparison, origin-summary и point-row entries старого snapshot. Отсутствие exact result
при том же revision применяет RESULT_UNAVAILABLE recovery только к этому result.
Restart не обязан менять revision: наличие saved result проверяется отдельно.
Старый map/table остаётся frozen и stale до успешного нового run/compare; All заново
разрешается backend при расчёте. Ошибка revision check оставляет frozen display,
показывает ошибку и не публикует unverified cache как новый расчёт. Отменённые ответы
не публикуют результаты и не инвалидируют новый workspace.

Внутреннее переключение уже показанных вариантов Compare остаётся frozen navigation
без нового clustering/revision request. Проверка фиксирует актуальность на момент
ответа; последующее изменение источника/eviction может произойти после неё.
Detail сохраняет собственную generation/exact-result validation, без скрытого rerun.
Постоянный background polling, persistent result store и multi-worker cache coherence
не добавляются.

## Совместимость

Frontend поддерживает explicit multi-select по FIAS, один регион назначения и общие
фильтры. Сохранённый результат и detail используют frozen origins/filters/mode/parameters;
редактирование формы меняет только editable state и stale indication. Ошибка нового run
сохраняет прежний результат. `STALE_DATA_SNAPSHOT` инвалидирует rejected generation,
а `RESULT_UNAVAILABLE` — только соответствующий saved result, включая comparison copies;
оба состояния требуют явного успешного пересчёта. UI имеет explicit «Все отправления»
для одного выбранного региона доставки. Request/cache intent остаётся All, saved context
раскрывает полный resolved набор с FIAS и zero-match origins; detail использует explicit frozen set.

Data Map и `/api/ml-cluster` сохранены для legacy-клиентов. Product v1 вызывает
только `/api/clustering/*`.

## CURRENT navigation guarantee (NPI-08)

Frontend drill-up and parent selection do not call run/compare or change frozen membership.
Point-to-origin details keep the saved resolved origins, region, filters, mode/parameters
and snapshot. Same-context loaded summaries/pages remain reusable. New calculations
still validate revision/result presence; STALE_DATA_SNAPSHOT and RESULT_UNAVAILABLE
never cause a silent result substitution during navigation.

## CURRENT saved XLSX export (NPI-10)

`POST /api/clustering/export` принимает полный `analysis.frozen_request`,
`data_snapshot` и `table_sort: {key, direction}`. Scalar origin совместим;
All нужно передавать как уже разрешённый frozen origin set. Mode, parameters
и все четыре filter lists обязательны. Никакого нового расчёта при export нет.
Необязательный `selection_intent` копируется из saved `analysis.selection_intent`:
backend принимает только provenance, уже наблюдавшийся для этого exact результата.
Это сохраняет оба намерения после shared cache reuse All/explicit. Без него
используется provenance первого сохранения; NPI-11 должен передавать intent явно.

Sort key — любой существующий столбец таблицы: `cluster_id`, `point_count`,
`trip_count`, `trip_share`, `weighted_route_length`, `price.min/median/weighted/max`,
`rub_per_km.min/median/weighted/max`, `economic_coverage`; direction — `asc`/`desc`.
Сортировка числовая, null last, tie по canonical cluster ID.

Первый лист «Кластеры» повторяет 14 headers и все saved table rows. Далее идут
непустые направления actual source row region → saved cluster; строки сохраняют
source-row IDs и normalized поля detail плюс origin/region/destination и visible
cluster label. В конце «Контекст» содержит frozen request/intent/origins/zero-match,
Pulse/snapshot, методику, единицы, coverage, exclusions, mappings и время export UTC.
Missing-region identity отличается от реального одноимённого source label.
Unassigned points, включая canonical `-1` spatial outliers, исключены с counts/reasons.
Point JSON аддитивно включает `source_row_count` для проверки полноты detail.

Числа сохраняются без UI rounding, formats задают отображение; пропуски — blank,
zero — numeric. Идентификаторы и source timestamps — literal text, timezone сохранён.
Формулы, hyperlinks, macros и external links не генерируются из source strings.
XlsxWriter 3.2.9 записывает последовательные строки с constant memory в временные
файлы; готовый HTTP attachment disk-backed. Ошибка cell/row/resource/write limits
отменяет весь workbook; arbitrary caps или silent truncation отсутствуют.

Generation source+coordinates проверяется до чтения, каждым frozen-point read
и после complete file. Metadata fingerprint сохраняет существующие ограничения;
это не content hash и не lease на время последующей передачи HTTP.
Typed JSON: invalid context/sort `INVALID_REQUEST`400; stale `STALE_DATA_SNAPSHOT`409;
evicted/restarted exact result `RESULT_UNAVAILABLE`409; Bear `EXPORT_UNSUPPORTED`422;
empty table `NO_DATA`422; missing/incomplete/duplicate rows or membership conflict
`EXPORT_INCONSISTENT_DATA`409; operational failure `EXPORT_FAILED`500.
Успех: XLSX MIME, `.xlsx` attachment, `X-Request-ID`, `Cache-Control: no-store`,
`X-Content-Type-Options: nosniff`. Ошибки не содержат private paths/source dumps.
