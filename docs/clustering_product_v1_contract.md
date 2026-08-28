# Clustering Product v1 contract

Дата: 2026-08-28.

## Назначение

Product v1 предоставляет три пользовательских режима для grain
`one origin FIAS × one destination region`:

- Geography;
- Geo + Cost;
- Bear Zones.

Research Contract v1 считается frozen dependency. Product-layer переиспользует
его data aggregation, local AEQD projection, spatial graph и алгоритмы без
изменения их исследовательских defaults.

## Coordinate policy

```text
coordinate_policy = accepted_existing_cache_v1
coordinate_source = cache
```

Существующие координаты `backend/cache/coords_cache.json` принимаются как
доверенный operational input для Product v1. Их историческое происхождение не
подтверждено, поэтому они не называются `verified`, а принятие cache фиксируется
отдельной policy.

Product-layer:

- использует только существующие валидные координаты из strict research resolver;
- оставляет неизвестные destination FIAS в статусе `unresolved`;
- не вызывает legacy `geocode_town()`;
- не подставляет центр региона;
- не добавляет jitter;
- не применяет fuzzy FIAS matching;
- не изменяет coordinate cache во время чтения или выполнения clustering.

Неполное покрытие координат возвращается в `data_quality` и warning
`incomplete_coordinate_coverage`, но отсутствие provenance больше не блокирует
Product API или UI.

## Product boundaries

Product v1 не строит polygons, не использует ATI/actual, не выбирает лучший режим
автоматически и не удаляет legacy `/api/ml-cluster`. Production API располагается
под `/api/clustering/*` и не зависит от legacy clustering backend.
