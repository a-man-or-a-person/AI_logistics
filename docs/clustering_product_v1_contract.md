# Canonical clustering product contract

Дата: 2026-08-29.

## Назначение

Продукт решает один сценарий:

```text
origin FIAS → destination region → canonical destination locations → K-Means → zones
```

Production-слой оркестрирует исследовательские компоненты и не реализует отдельный
алгоритм кластеризации. Единственный production-алгоритм текущего MVP — geography-only
`ml.clustering.kmeans.KMeansClusterer`.

Цена и ₽/км могут фильтровать или оценивать исходную выборку, но не попадают в
`ClusterPoint` и не являются признаками K-Means. `trip_count` может использоваться
только как вес точки.

## Координаты

Используется существующий `backend/cache/coords_cache.json`. Неизвестная координата
остаётся `unresolved`, учитывается в `data_quality` и исключается из ML.

Запрещены:

- подстановка центра региона;
- jitter;
- fuzzy FIAS;
- пользовательское геокодирование во время расчёта зон.

## Границы

`BoundaryProvider` читает только локальный GeoJSON, явно заданный через
`LOGISTICS_REGION_BOUNDARIES_FILE`. При отсутствии утверждённой геометрии кластеры и
точки возвращаются, а API сообщает:

```json
{"available": false, "status": "boundary_unavailable", "geojson": null}
```

Bbox, искусственный прямоугольник и legacy Voronoi не используются как замена границы.

## Product scope

- источник: Pulse;
- algorithm: `kmeans`;
- ручной `n_clusters`: 2–10;
- `weight_mode`: `none | trip_count`;
- без Auto K;
- без ATI, CatBoost и фиктивных вариантов алгоритма;
- Data Map остаётся отдельным рабочим режимом.
