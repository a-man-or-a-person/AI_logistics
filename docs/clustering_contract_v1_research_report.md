# Clustering Contract v1 — research implementation report

> **FROZEN RESEARCH REFERENCE.** Это основание ML-инвариантов, а не отдельный
> Product v1 roadmap. Product workflow не зависит от boundary/actual/predictive треков.

Дата прогона: 2026-08-28.

## Git и regression baseline

- integration branch: feature/clustering-contract-v1;
- base: origin/feature/ml-clustering;
- analytics merged no-ff commit 04dab526;
- merge conflicts: none;
- pre-migration regression: 56 passed, Ruff clean;
- post-implementation regression: 68 passed, Ruff clean.

Pulse dataset SHA-256:
D7E9D7325FA298E2E7410070DE0D88E4D7F7C8C8209BCD52D03A2252E88E9C17.

## Data migration

Canonical source of truth:

    price = Pulse.units
    trip_count = Pulse.bid_count
    rub_per_km = price / route_length for positive price and distance

Destination price and ₽/км are weighted by trip_count. The experiment grain is one
origin FIAS × one destination region; retro/current/forecast and tariff segments are
selectable. Missing FIAS is excluded and missing coordinates are not replaced by a
region center.

## Graph study: three Moscow-region pilots

All pilots used all selectable period types and the current local coordinate cache.

| Origin FIAS | Points | Geocoded | Trip coverage | Delaunay components / isolates / edges | mutual kNN components / isolates / edges |
|---|---:|---:|---:|---:|---:|
| 93b3df57… | 145 | 110 | 90.8574% | 15 / 9 / 193 | 15 / 8 / 170 |
| c2deb16a… | 137 | 106 | 93.7035% | 18 / 11 / 182 | 22 / 10 / 157 |
| 555e7d61… | 137 | 104 | 82.3403% | 15 / 10 / 178 | 18 / 12 / 161 |

Delaunay + adaptive MAD pruning остаётся рекомендуемым research default: он не
требует выбора k, сохраняет planar local geometry и на двух из трёх пилотов дал
меньше components, чем mutual kNN. Mutual kNN сохраняется как обязательный benchmark.
Это рекомендация graph default, не выбор лучшего product mode.

## Geography

На первом пилоте Auto K выбрал 10 clusters: P95 radius 36.28 km, 9 spatial outliers,
trip coverage 93.10%, connectivity violations 0. На следующих двух пилотах Auto K
выбрал 10 и 9 clusters; connectivity violations также 0.

Manual K использует тот же component-wise constrained algorithm. Изменение цены или
trip_count не меняет geography assignments при фиксированных x/y и graph.

## Geo + Cost sensitivity

Первый пилот:

| Weights geo/cost | Auto K | P95 radius | Between-cluster ₽/km spread | Connectivity violations |
|---|---:|---:|---:|---:|
| 80/20 | 10 | 37.96 km | 33.66 | 0 |
| 70/30 | 9 | 42.93 km | 33.66 | 0 |
| 60/40 | 9 | 48.80 km | 33.66 | 0 |

На втором пилоте Auto K был 8/8/10, на третьем — 8/8/8. Во всех случаях violations
равны 0. Cost меняет merge priority только внутри spatial components и никогда не
создаёт edge.

## Bear Zones

Первоначальный research run использовал временное volume-ограничение и потому считается
superseded. Финальный contract: zone threshold +35%, singleton +70%, без допуска или
исключения по trip_count. Актуальные результаты после пересчёта приведены в freeze report.

## Period-slice stability, first pilot

| Pair | Common assigned FIAS | Geography ARI / NMI | Geo+Cost 70/30 ARI / NMI |
|---|---:|---:|---:|
| current vs forecast | 66 | 1.000 / 1.000 | 0.957 / 0.970 |
| current vs retro | 10 | 0.692 / 0.935 | 0.452 / 0.767 |
| forecast vs retro | 10 | 0.692 / 0.935 | 0.452 / 0.767 |

Bear mode не имел common assigned zone members на этих slices, поэтому membership
ARI/NMI не определены. Candidate recurrence: одна точка появилась в 2/3 slices,
остальные наблюдавшиеся candidates — в 1/3. Это facts-only diagnostic, не продуктовый
вывод.

## Blockers for clean Pulse spatial clustering

Чистый Geography mode блокируют или ограничивают только пространственные данные:

- unresolved coordinates: 24–31% pilot destination points;
- unverified coordinate-cache provenance/accuracy;
- missing destination FIAS (такие строки нельзя безопасно превратить в identity);
- необходимость проверить adaptive edge threshold на других регионах и согласованных
  3–5 business pilot routes.

Invalid distance, zero/missing trip_count и mixed tariff segments не блокируют чистую
Geography при валидных FIAS/x/y. Они блокируют или ослабляют только Geo+Cost/Bear
economics и обязательно отражаются в data_quality/filters metadata.

## Blockers only for future ATI/actual business evaluation

Они не делают Pulse spatial clustering невалидным:

- current actual-to-Pulse origin mapping coverage 0%;
- нет destination FIAS или подтверждённого route mix в actual grain;
- нет trusted route distance для distance-based ATI/actual variants;
- нужен point-in-time actual target и согласованный prediction/evaluation grain;
- нужны paired coverage и business weights для WAPE/MAE, отдельно от cluster quality.

Поэтому WAPE не используется для выбора Geography/Geo+Cost/Bear. Production API,
frontend, map UX и polygons не изменялись.
