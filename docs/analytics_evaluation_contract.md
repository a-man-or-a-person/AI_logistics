# Контракт аналитической оценки стоимости

> **СТАТУС: DEFERRED / BLOCKED — NOT PART OF CLUSTERING PRODUCT V1.**
> H1 заблокирован отсутствием trusted distance; actual-validation H2/E2/E3 — отсутствием
> destination-level ground truth. Этот документ сохранён как контракт будущего ценового трека.

Версия методологии: `analytics-evaluation-v1`.

## Назначение

Этот слой отвечает на вопрос, улучшает ли конкретная гипотеза ошибку стоимости
перевозки относительно Pulse и встроенного ATI/market benchmark на тех же перевозках.
Clustering, территориализация и UI остаются отдельными компонентами.

## Конфиденциальность

Actual CSV, реальные facility mapping, canonical evaluation rows, predictions и
actual-derived отчёты хранятся только в ignored-путях:

- `data/private/`;
- `ml/configs/private/`;
- `reports/private/`.

Названия facilities не попадают в downstream evaluation rows: используется стабильный
`actual_origin_id`. В тестах разрешены только синтетические названия. Внешние HTTP/API
запросы с actual routes запрещены.

## Источники и grain

| Источник | Grain | Роль |
|---|---|---|
| actual snapshots | snapshot × shipment month × origin facility × destination region | target и ATI/market as-of benchmark |
| Pulse | origin FIAS × destination FIAS × period × tariff/vehicle/tonnage segment | price и региональная ставка ₽/км |
| origin mapping | actual facility → Pulse origin FIAS | контролируемый join |
| trusted distance | origin FIAS × destination region/FIAS × optional month | E1/E3 |
| cluster/route assignment | EvaluationKey × destination FIAS × cluster | E2/E3 |

Канонический `EvaluationKey`:

```text
shipment_month × actual_origin_id × normalized_destination_region
```

## Snapshot и ground truth

`current_month` — дата снимка, `shipment_date_month` — месяц перевозки, а
`horizon_months = shipment_month - snapshot_month`. `month_label` обязан совпадать с
`M{horizon}`. Random split snapshot-строк запрещён.

Для каждого `EvaluationKey` target выбирается из самой поздней snapshot-версии с
доступным `fact_rub_per_item`. Статусы:

- `final_post_shipment` — финальная версия после месяца перевозки;
- `m0_only` — последняя доступная версия M0;
- `pre_shipment_only` — доступен только предварительный факт;
- `missing` — target отсутствует.

Primary score не должен молча включать `pre_shipment_only` или `missing` без явной
настройки эксперимента.

## Leakage policy

Централизованно запрещены как prediction features:

- `fact_rub_total`;
- `fact_rub_per_item`;
- `market_spread`.

`auction_percent` и `qty_auction` имеют статус `diagnostic_only`, пока не доказано,
что они известны на `prediction_as_of`. `fact_*` — target, а не вход модели.

## Origin и destination matching

Auto-match origin разрешён только для связи `один actual facility в town ↔ один Pulse
FIAS в town` после точной conservative normalization. Связи `1→N` и `N→1` получают
`ambiguous`; запрещены first-candidate, fuzzy-nearest и matching по порядку.

Destination сопоставляется только по точной нормализованной области и известным alias.
Неизвестный регион получает `unmatched_region`; fuzzy matching не применяется.

Главные readiness-метрики mapping — coverage по quantity и business cells, а не только
доля origin IDs.

## Temporal semantics Pulse

Каждый Pulse evaluation record сохраняет `period_id`, `period_type` и
`source_snapshot_time`. Режимы:

- `current` — contemporaneous benchmark;
- `retro` — retrospective diagnostic;
- `forecast` — допустим только против уже реализованного actual target;
- смесь period types маркируется отдельно.

`price_types` (`spot`, `tender`) задаются явно и не смешиваются молча.

## Варианты

| Вариант | Формула/смысл | Реальный статус без дополнительных данных |
|---|---|---|
| E0 | `Σ units × bid_count / Σ bid_count` на origin FIAS × destination region × filters | после подтверждённого origin mapping |
| E0_unweighted | arithmetic mean Pulse units | diagnostic only |
| ATI_REF | market price из actual snapshot → финальный fact, отдельно по M0/M1/M2/... | доступен |
| E1 | Pulse regional ₽/км × trusted distance | blocked без distance |
| E2 | cluster-specific route price | blocked без destination FIAS/route mix |
| E3 | cluster-specific ₽/км × trusted distance | blocked без обоих источников |

Blocked variant возвращает `status`, `blocker`, `required_fields` и coverage, не падает
и не создаёт фиктивный score.

## Метрики

Primary metric — quantity-weighted WAPE:

```text
Σ qty × |prediction - actual| / Σ qty × actual
```

Secondary metrics: weighted MAE RUB/item, MdAPE, quantity-weighted bias, доля quantity
в ±10% и ±20%, число cells и evaluated quantity. RMSE не используется как primary.

Каждый отчёт также содержит coverage ground truth, origin mapping, Pulse match,
distance, cluster и final evaluation на уровне cells и/или quantity.

## Paired comparison и uncertainty

Decision gate сравнивает варианты только на common intersection доступных predictions.
All-available score остаётся диагностическим. Для E1 против E0 runner считает paired
bootstrap по collapsed `EvaluationKey` и сохраняет 95% confidence interval для
`ΔWAPE(E1 - E0)`.

## Decision gates

- data readiness: fact quantity coverage ≥ 90% и origin mapping quantity coverage ≥ 90%;
- H1 readiness: trusted distance quantity coverage ≥ 80%;
- H2 readiness: destination-level actual/route mix coverage ≥ 80%;
- success: relative WAPE improvement ≥ configurable 5% на common intersection, без
  материального ухудшения bias/coverage и без результата, обусловленного одним месяцем.

## Runner и outputs

Основная команда: `python -m ml.experiments.compare_variants`. Она сохраняет:

```text
reports/private/evaluation/
  run_metadata.json
  data_quality.json
  coverage.json
  leaderboard.csv
  decision_gate_actual.json
  paired_bootstrap.json
  e0/ e0_trip_weighted/ e1/ e2/ e3/
  ati_reference/by_horizon.csv
```

Metadata включает Git SHA, SHA-256 всех входных файлов, `created_at`, `as_of`, target
months, price types и версию методологии. Исторический `decision_gate_2.json` не
изменяется; `business_evaluation.py` остаётся Pulse-proxy experiment, а не финальным
actual-price decision gate.
