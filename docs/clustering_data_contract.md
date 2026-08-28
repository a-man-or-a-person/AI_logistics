# Clustering Contract v1

Версия: clustering-contract-v1. Предыдущий clustering-data-v1 и его трактовка
units → shipment_count отменены.

## Семантика Pulse

- price = units;
- trip_count = bid_count;
- rub_per_km = price / route_length, только если цена и расстояние положительны;
- при невалидной цене или дистанции rub_per_km = None, не 0;
- confidence сохраняется как качество источника, но не подменяет trip_count;
- retro, current, forecast — равноправные selectable period types.

Все экономические агрегаты используют одну формулу:

    weighted(metric) = Σ(metric_i × trip_count_i) / Σ trip_count_i

Она применяется к point, cluster, bear zone и region. Строки с нулевым или
отсутствующим trip_count не получают искусственный вес.

## Grain и фильтры

Один эксперимент обязан иметь:

    ONE origin_fias × ONE destination_region

Запрос без одного из этих значений отклоняется. Внутри grain применяются multi-select
фильтры period_types, price_types, vehicle_types, tonnage_ids. Выбранные строки
агрегируются до одной точки на destination_fias.

ClusterResult явно сообщает contains_forecast, выбранные фильтры и признаки
смешения price/vehicle/tonnage segments.

## LocationPoint

Точка содержит FIAS identity, WGS84 и локальные AEQD x/y, record_count,
trip_count, weighted price, weighted ₽/км, число активных периодов, источник
координат и data-quality flags. Missing destination FIAS не заменяется
name/region fallback; missing coordinates не заменяются центром региона.

## Пространственная связность

Все три product research modes используют один spatial graph:

- основной кандидат — Delaunay + adaptive MAD long-edge pruning;
- benchmark — mutual kNN;
- degree = 0 означает spatial_outlier;
- отдельный компонент из нескольких точек не считается outlier;
- ни цена, ни trip_count не меняют координаты или adjacency.

## Режимы

### Geography

Connectivity-constrained agglomerative clustering использует только x/y и graph.
Manual K и Auto K поддерживаются. Research Auto K сравнивает K=2…20 по silhouette,
Calinski–Harabasz, Davies–Bouldin, compactness, size sanity и explicit complexity
cost. Pareto/tie-breaking предпочитает меньший K среди близких вариантов и не
вознаграждает дополнительные tiny clusters. Каждый кластер проверяется на связность.

### Geo + Cost

Использует тот же graph как hard constraint. Feature space состоит из robust-scaled
x/y и weighted ₽/км. Default weights: 70/30; sensitivity: 80/20, 70/30, 60/40.
Экономическое сходство никогда не создаёт spatial edge и не объединяет разные
graph components.

### Bear Zones

Default candidate threshold: point rate не ниже regional rate × 1.35.
Обычная zone строится из connected component размером от двух candidate points и
повторно проходит zone-level 35% invariant. Singleton с отклонением от +70%
сразу получает cluster_type expensive_singleton.

trip_count используется только как экономический вес и показатель объёма данных.
Он не является eligibility threshold для zone или singleton. При суммарном весе 0
weighted economics недоступна (economic_status insufficient_weight), но Geography
по-прежнему может использовать точку.

## Результаты и границы

Общий ClusterResult содержит mode, internal algorithm, assignments, typed clusters,
regional economics, filters, forecast/mixed-segment metadata, warnings, typed outliers,
data quality и geographic/economic/graph metrics. Cluster summary включает point_ids,
trip_count, economics, centroid/medoid, mean/P95/max radius и connected=true для
проверенных product modes.

Polygons postponed. Существующий boundary/territorialization код сохранён как
отдельный post-processing и не является dependency нового clustering core.
Production API, frontend и map UX в этот milestone не подключаются.
