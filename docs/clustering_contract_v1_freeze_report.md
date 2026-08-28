# Clustering Contract v1 — research freeze report

Дата: 2026-08-28. Automatic product-mode or threshold winner не выбирался.

## Финальная Bear semantics

Pulse bid_count остаётся trip_count и используется как economic weight и отображаемый
объём данных. Он больше нигде не является eligibility threshold.

Default Bear rules:

- candidate: weighted ₽/км не ниже regional weighted ₽/км × 1.35;
- normal zone: connected candidate component с двумя или более точками и повторной
  zone-level проверкой +35%;
- expensive_singleton: одна candidate point с отклонением от +70%;
- при нулевом суммарном весе economics имеет status insufficient_weight; Geography
  всё равно может использовать координату.

Параметры min_trip_count, singleton_min_trip_count и тип
low_reliability_candidate удалены из кода и output contract.

## Пересчёт исходных трёх пилотов

| Pilot origin | До исправления | После исправления при +35% |
|---|---|---|
| 93b3df57… | 1 zone | 5 candidates, 1 zone, 2 points, 16 trips, 78.34 ₽/км, +50.0% |
| c2deb16a… | зон нет | 1 candidate и expensive singleton: 1 trip, 107.86 ₽/км, +99.2% |
| 555e7d61… | зон нет | 5 candidates, connected zones/singletons нет |

Второй пилот подтверждает новое бизнес-правило: singleton с одной перевозкой
показывается пользователю, а не скрывается.

## Bear threshold sensitivity

Первый пилот:

| Threshold | Candidates | Zones | Singletons | Covered points | Covered trips | Mean/max zone size |
|---:|---:|---:|---:|---:|---:|---:|
| +20% | 27 | 7 | 0 | 20 | 204 | 2.86 / 6 |
| +25% | 18 | 4 | 0 | 12 | 102 | 3.00 / 6 |
| +30% | 11 | 3 | 0 | 8 | 75 | 2.67 / 4 |
| +35% | 5 | 1 | 0 | 2 | 16 | 2.00 / 2 |
| +40% | 3 | 1 | 0 | 2 | 16 | 2.00 / 2 |
| +50% | 1 | 0 | 0 | 0 | 0 | 0 / 0 |

Количество структур ожидаемо чувствительно к threshold. Большее число зон при +20%
не трактуется как лучшее качество. Default остаётся +35%.

## Auto K 2…20

Старый selector позволял постоянно уменьшающемуся radius доминировать над complexity
и на одном из новых пилотов выбрал search ceiling K=20. Исправленный selector:

1. строит Pareto shortlist с quality, compactness, size sanity и explicit K cost;
2. не принимает варианты, создающие дополнительные tiny clusters;
3. среди близких quality candidates выбирает меньший K.

| Pilot profile | Selected Geography K | Search maximum |
|---|---:|---:|
| dense-central | 11 | 20 |
| elongated-northwest | 13 | 20 |
| large-south | 11 | 20 |
| large-ural | 10 | 20 |
| sparse-siberia | 3 | 20 |

Ни один pilot больше не упирается в maximum.

## Geo+Cost separation

Одинаковый max–min spread 33.66 на первом пилоте оказался корректным: во всех трёх
assignments сохранялись одни и те же extreme-rate clusters (44.69 и 78.34 ₽/км).
Сам max–min был недостаточен, поэтому добавлены cluster rate lists и variance metrics.

| Geo/cost | K | P95 radius | Within MAD | Within variance | Between variance | Between/within |
|---|---:|---:|---:|---:|---:|---:|
| 80/20 | 10 | 37.96 km | 2.219 | 10.782 | 6.875 | 0.638 |
| 70/30 | 9 | 42.93 km | 2.808 | 13.511 | 4.146 | 0.307 |
| 60/40 | 12 | 36.26 km | 2.021 | 9.198 | 8.458 | 0.920 |

Метрики действительно пересчитываются по каждому assignment. Default 70/30 сохранён;
автоматического выбора weight нет.

## Graph validation on five diverse real directions

| Profile | Resolved/total | Delaunay components / isolates / edges | mutual kNN components / isolates / edges |
|---|---:|---:|---:|
| dense-central | 110/145 | 15 / 9 / 193 | 15 / 8 / 170 |
| elongated-northwest | 106/109 | 27 / 16 / 170 | 26 / 12 / 146 |
| large-south | 105/105 | 12 / 8 / 195 | 16 / 10 / 184 |
| large-ural | 69/89 | 18 / 9 / 96 | 18 / 9 / 87 |
| sparse-siberia | 44/55 | 16 / 13 / 67 | 16 / 12 / 48 |

Delaunay+adaptive MAD pruning остаётся research default: components не больше mutual
kNN на четырёх из пяти pilots и graph сохраняет больше local edges. Mutual kNN остаётся
benchmark и иногда даёт меньше isolates. Во всех Geography и Geo+Cost runs
connectivity violations = 0.

Pruning multiplier sweep 1.5…4.0 дал монотонное изменение threshold/components без
обратных скачков; actual graph_threshold_m теперь сохраняется в experiment metadata.
Чувствительность существенна и должна оставаться видимой, а не скрываться одним default.

## Coordinate and FIAS quality

| Profile | Point coverage | Trip-weight coverage | Coordinate provenance |
|---|---:|---:|---|
| dense-central | 75.86% | 90.86% | unverified_cache |
| elongated-northwest | 97.25% | 97.82% | unverified_cache |
| large-south | 100.00% | 100.00% | unverified_cache |
| large-ural | 77.53% | 88.10% | unverified_cache |
| sparse-siberia | 80.00% | 83.92% | unverified_cache |

Region-center fallback, jitter и fuzzy FIAS guessing отсутствуют. Missing destination
FIAS исключается и считается в data_quality.excluded_missing_fias. Главный blocker
перед production API — не алгоритм кластеризации, а verified coordinate provenance и
coverage для выбранного business direction.

## Research freeze gate

- units = price, bid_count = trip_count: PASS;
- Geography connectivity violations = 0: PASS;
- Geo+Cost cannot create edges, violations = 0: PASS;
- Bear has no trip-count eligibility threshold: PASS;
- graph compared on five diverse real pilots: PASS;
- Auto K not stuck at search maximum: PASS;
- coordinate provenance ready for production: BLOCKED (all current cache coordinates
  are explicitly unverified).

Research contract зафиксирован. Production API/frontend не начинается до закрытия
coordinate provenance gate или явного решения принять unverified coordinates с warning.
