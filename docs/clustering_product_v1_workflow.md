# Clustering Product v1 — workflow and stop report

Дата stop point: 2026-08-29.

## Product flow

```text
Pulse CSV
  -> lazy ClusteringRepository
  -> one origin FIAS x one destination region
  -> strict existing-cache coordinate resolution
  -> local AEQD projection + shared Delaunay graph
  -> selected product mode
  -> /api/clustering/*
  -> point-based map and inspector
```

Research Contract v1 используется как frozen dependency. Product-layer не меняет
Geography, Geo+Cost, Bear Zones, Auto K или adaptive graph defaults. Polygons,
ATI/actual, predictive ML и automatic winner не входят в Product v1.

## API

### `GET /api/clustering/options`

Без query parameters возвращает mode metadata, defaults и origins. При
`origin_fias` добавляет доступные destination regions. При `origin_fias` вместе с
`destination_region` добавляет period/price/vehicle/tonnage facets с counts.

### `POST /api/clustering/run`

Запускает ровно один режим: `geography`, `geo_cost` или `bear_zones`. Grain всегда
равен одному origin FIAS и одному destination region. Синтаксические ошибки имеют
HTTP 400, data-dependent невозможность — HTTP 422 со стабильным `code`.

### `POST /api/clustering/compare`

Переиспользует один spatial context и возвращает Geography Auto K, Geo+Cost 70/30
и Bear +35%. Response содержит facts-only comparison и `winner = null`.

Legacy `/api/ml-cluster` сохранён для обратной совместимости, но новый frontend его
не вызывает.

## Product defaults

- coordinate policy: `accepted_existing_cache_v1`;
- неизвестные координаты: `unresolved`, без region-center fallback, jitter или fuzzy FIAS;
- graph: Delaunay + adaptive MAD pruning, multiplier 3.0;
- Geography: Auto K 2…20;
- Geo+Cost: Auto K 2…20, 70% geography / 30% economics;
- Bear Zones: candidate +35%, expensive singleton +70%, без `trip_count` gate;
- polygons: disabled.

Geo+Cost использует induced subgraph только economic-valid points. Удаление точки
не создаёт новый spatial edge; точка возвращается со статусом
`economic_unavailable`.

## Caching and invalidation

Repository индексирует только clustering-поля и загружает Pulse при первом product
request. Fingerprint: resolved path, file size и mtime. Изменение Pulse полностью
перестраивает индекс.

Server result LRU содержит до 64 результатов. Его key включает dataset и coordinate
fingerprints, direction, filters, mode и parameters. Spatial graph LRU содержит до
32 графов по point IDs и координатам. Frontend дополнительно хранит результаты и
comparison в `Map` по стабильной request signature.

## Real-data smoke and performance

Direction: origin `93b3df57-4c89-44df-ac42-96f05e9cd3b9` → Московская область,
все period types и все тарифные сегменты; 145 destination points.

| Operation | Time | Result |
|---|---:|---|
| Cold repository load + Geography | 17.5983 s | 11 clusters |
| Geo+Cost after shared context | 0.0795 s | 9 clusters, graph cache hit |
| Bear Zones after shared context | 0.0082 s | 1 zone, graph cache hit |
| Repeated identical Geography | 0.0031 s | result cache hit |

Repository load count remained 1. Repeated requests therefore do not rescan the
543k-row source CSV.

## Verification

- full pytest suite: 98 passed;
- Ruff: clean;
- `git diff --check`: clean;
- real Flask HTTP smoke: `/`, JS module, contextual OPTIONS and all three `/run`
  modes returned successfully;
- legacy endpoint remains registered and returned its expected validation response;
- static frontend contract verifies removal of old K-Means/town-type/weight/seed
  controls, Product API usage, point-only renderer and full cache signature.

Interactive desktop/mobile browser verification could not be executed in the Codex
environment because no browser-control runtime was exposed. It remains a manual QA
item: mode switching, map highlight, inspector, stale banner, reset and mobile
sheets must be visually checked in a browser before release deployment.

## Known limitations

- coordinate cache is accepted operational input, not historically verified data;
- unresolved points cannot be drawn but remain in response and coverage metrics;
- first repository load is CPU/I/O bound;
- no polygons or administrative territorialization in Product v1;
- no ATI/actual business evaluation and no recommended mode.
