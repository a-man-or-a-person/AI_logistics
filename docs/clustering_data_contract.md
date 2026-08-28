# Контракт данных территориальной кластеризации

Версия: `clustering-data-v1`. Это текущий аналитический milestone проекта.

## Семантика Pulse

- `units` — количество перевозок / объём направления и источник `shipment_count`;
- `bid_count` и `confidence` — производные диагностические поля Pulse;
- `forecast` — прогноз Pulse и полностью исключается;
- в датасет допускаются только `current` и `retro`;
- цена, `rub_per_km`, actual/market/fact и Pulse-derived diagnostics не являются
  признаками или весами кластеризации.

`PulseRawRecord` буквально сохраняет 25 исходных колонок. `LogisticsRecord` нормализует
подтверждённые поля, не называя `units` ценой. `ClusteringRoute` агрегирует строки до grain:

```text
origin_fias × destination_fias × destination_region × period_id
```

с `shipment_count = Σ Pulse.units`.

## Точки

`LocationPoint` содержит одну точку на destination FIAS, координаты, число исходных записей,
суммарный `shipment_count`, число активных периодов и origins. Fallback name+region явно
маркируется; центр региона не подставляется.

Основная географическая coverage дополняется бизнес-покрытием:

```text
Σ shipment_count geocoded destinations / Σ shipment_count all destinations
```

## Матрица и веса

Матрица KMeans всегда равна `X = [projected_x, projected_y]`.

- `weight_mode=none` — чистая география;
- `weight_mode=shipment_count` — география с бизнес-весом;
- `weight_mode=both` — рекомендуемый sweep обоих режимов.

`bid_count`, `confidence`, `forecast`, price, actual и market не могут попасть ни в `X`,
ни в `sample_weight`.

## Метрики и решение

Cluster metrics: silhouette, mean/p95/max radius, shipment-weighted mean/p95 radius,
размеры кластеров, shipment shares/CV, point/shipment coverage и ARI stability по seeds.
Geo-only и shipment-weighted assignments сравниваются через ARI.

Кандидаты выбираются Pareto-shortlist, а не максимумом silhouette и не WAPE. Decision gate:
`decision_gate_clustering.json`.

Territorialization metrics (polygon coverage, overlap, fragmentation) хранятся отдельно и
не входят в primary cluster score.

## Границы

Полигон не нужен KMeans и не блокирует исследование. Он применяется после assignments.
Production boundary требует локальный WGS84 GeoJSON НСПД/ЕГРН и manifest с SHA-256,
authority, effective date и статусом `official`. Development/unknown источники не должны
маркироваться официальными.

## Замороженные треки

- predictive price ML — deferred;
- H1 — blocked без trusted distance;
- actual-validation H2/E2/E3 — blocked без destination FIAS/route mix;
- `decision_gate_2.json` — исторический price-proxy artifact.
