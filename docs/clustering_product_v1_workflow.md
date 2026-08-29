# Canonical clustering workflow

## Контур

```text
Pulse
  → ml.data.locations.build_location_dataset
  → coordinate quality audit
  → LocalProjection
  → geography-only ClusterPoint
  → KMeansClusterer
  → ClusterResult
  → optional approved boundary + territorialize
  → /api/clustering/*
  → «Территориальные зоны»
```

## API

- `GET /api/clustering/options` — source, algorithm, weight/filter capabilities и
  destination regions для выбранного `origin_fias`;
- `GET /api/clustering/origins?q=&limit=` — ограниченный searchable origin catalog,
  дедуплицированный по FIAS;
- `POST /api/clustering/preview` — исходные destination locations и data quality до
  запуска K-Means;
- `POST /api/clustering/run` — canonical `ClusterResult`, UI-safe points/clusters,
  metrics и optional zones.

Пример запроса:

```json
{
  "origin_fias": "…",
  "destination_region": "Ленинградская область",
  "period_types": ["current"],
  "price_types": ["spot"],
  "algorithm": "kmeans",
  "parameters": {
    "n_clusters": 5,
    "weight_mode": "none"
  }
}
```

Ошибки структуры и K возвращают HTTP 400. Нехватка resolved-точек возвращает HTTP 422
с кодом `INSUFFICIENT_POINTS`. Отсутствие boundary не является ошибкой кластеризации.

## UI

Интерфейс разделён на «Карту данных» и «Территориальные зоны». В территориальном режиме
пользователь ищет origin, выбирает destination region, периоды, типы цены, K и вес.
До расчёта показываются исходные resolved-точки. После расчёта inspector показывает
географические метрики, data quality, unresolved-точки и список зон.

Выбор зоны синхронизирован между картой и inspector. Изменение параметров после расчёта
показывает stale-state. На планшете inspector становится drawer, на мобильном controls
и result открываются поверх карты.

## Проверки

Обязательные regression-тесты покрывают geography-only вход, все dataset-фильтры,
unresolved policy, детерминированность, invalid/insufficient K, boundary
available/unavailable, territorial metrics и сохранность Data Map API.
