# Логистика AI

Локальное Flask-приложение для анализа ставок перевозок, отображения городов на
карте и кластеризации логистических точек.

## Проектные документы

Начните с [Project Brief](docs/project/project-brief.md). Термины и принятые продуктовые решения принадлежат [CONTEXT.md](CONTEXT.md), а реализованная архитектура описана в [Current-State Architecture](docs/architecture/current-state.md).

## Требования

- Python 3.11+
- файл `v_pulse_prices.csv` в корне проекта (он не хранится в Git из-за размера)

Путь к CSV можно переопределить переменной `LOGISTICS_CSV_FILE`.

## Установка на Windows

Если существующее `.venv` ссылается на удалённую версию Python, переименуйте его
в `.venv.backup`, затем создайте окружение заново:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

`requirements-lock.txt` воспроизводит проверенное окружение целиком. Файлы
`requirements.txt` и `requirements-dev.txt` разделяют рабочие и тестовые
зависимости и удобны для их планового обновления.

Запуск:

```powershell
.\.venv\Scripts\python.exe run.py
```

По умолчанию сервер доступен только локально: <http://127.0.0.1:5000>.

## Проверки

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
```

GitHub Actions запускает эти проверки для PR в `main` и push в `main`:
один job на `windows-2022`, Python 3.12.10, Node 22.23.3 и зависимости из
`requirements-lock.txt`. Node-тесты и браузерные тесты Edge входят в
`tests/test_clustering_frontend_contract.py` и выполняются отдельным шагом.
Перед ними проверяется запуск Node и Edge; любой пропущенный frontend-тест
делает job неуспешным. `REQUIRE_FRONTEND_BROWSER=1` запрещает пропуск при
отсутствии Edge. Для такой же локальной проверки:

```powershell
$env:REQUIRE_FRONTEND_BROWSER = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_clustering_frontend_contract.py -ra
```

Для запрета merge при красном CI владелец репозитория должен назначить
`Quality / verification` обязательной проверкой в правилах ветки `main`.

## Clustering Product v1

Главный продуктовый экран решает одну задачу: пользователь выбирает один пункт
отправления, один регион назначения и сегменты Pulse, затем исследует один из пяти
режимов на point-based карте или сравнивает их на одном снимке данных:

- **По географии** — только пространственная структура, Auto/Manual K;
- **География + стоимость** — связная география и weighted ₽/км с пресетами
  80/20, 70/30 и 60/40;
- **География + объём** — связная география и `log1p` числа перевозок с теми же
  пресетами 80/20, 70/30 и 60/40;
- **Медвежьи зоны** — связанные дорогие зоны от выбранного порога и одиночные
  аномальные точки от фиксированных +70%;
- **Медвежьи зоны по объёму** — связанные участки с повышенным числом перевозок
  относительно среднего по региону и одиночные объёмные аномалии от +70%.

Product v1 использует отдельный canonical API:

- `GET /api/clustering/options`;
- `GET /api/clustering/origins`;
- `POST /api/clustering/preview`;
- `POST /api/clustering/run`;
- `POST /api/clustering/compare`.

`/compare` возвращает Geography Auto, Geo+Cost 70/30 Auto, Geo+Volume 70/30 Auto,
Bear Cost +35 и Bear Volume +35 без winner/recommendation. География не использует цену или число перевозок при
построении кластеров. Цена не может создать spatial edge. Product v1 отображает
только точки, medoid-центры и изолированные состояния — без полигонов, geocoding,
region-center fallback и fuzzy FIAS. Подробности:
`docs/clustering_product_v1_contract.md`.

Forecast разрешён, но backend возвращает `contains_forecast`, а интерфейс показывает
явное предупреждение. Data quality отдельно сообщает покрытие точек координатами и
покрытие перевозок; эти проценты не взаимозаменяемы.

Legacy `/api/ml-cluster` сохранён только для обратной совместимости и не вызывается
Product workflow.

## Исследовательский ML-слой

Аналитический код изолирован в `ml/` и не меняет существующие API и карту. Текущий
milestone формирует воспроизводимые географические кластеры с корректным бизнес-весом:

```powershell
.\.venv\Scripts\python.exe -m ml.data.audit
```

`PulseRawRecord` буквально сохраняет 25 колонок. Clustering Contract v1 задаёт
`price = units`, `trip_count = bid_count` и `rub_per_km = price / route_length`.
`retro/current/forecast` выбираются явно. Контракт описан в
`docs/clustering_data_contract.md`.

```powershell
.\.venv\Scripts\python.exe -m ml.data.clustering_dataset `
  --origin-fias "FIAS пункта отправления" `
  --destination-region "Ленинградская область" `
  --output-dir reports\clustering_data
.\.venv\Scripts\python.exe -m ml.experiments.clustering_data_audit `
  --origin-fias "FIAS пункта отправления" `
  --destination-region "Ленинградская область"
```

Predictive price ML и E0–E3 сохранены как deferred-треки. H1 заблокирован без trusted
distance, actual-validation H2 — без destination-level ground truth.

### Исторические price-proxy эксперименты (deferred)

Воспроизведение текущего расчёта для пилотного региона запускается отдельно:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.current_baseline `
  --destination-region "Ленинградская область"
```

Этот отчёт сохранён только для воспроизводимости старого price-proxy исследования и не
используется при выборе кластеров.

Для проверки гипотезы километража нужен отдельный CSV внутренних перевозок по
контракту `ml/configs/internal_trips.example.csv`. После его получения:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.hypothesis_1_distance `
  --internal путь\к\internal_trips.csv `
  --destination-region "Ленинградская область" `
  --origin-fias "FIAS пункта отправления"
```

H2 research pipeline уже реализован и оценивается географическими и Pulse-proxy
метриками. Actual price ground truth доступен на grain
`origin facility × destination region × shipment month`; H1 по-прежнему ожидает
доверенный источник расстояний. Текущий actual не поддерживает прямую cluster-level
оценку H2 без destination FIAS или подтверждённого route mix.

### Deferred boundary/post-processing

> **DEFERRED — NOT PART OF CLUSTERING PRODUCT V1.** Следующие команды сохранены
> для воспроизводимости исследовательского boundary pipeline. Product v1 от них
> не зависит и не рендерит полигоны.

Spatial core устанавливается отдельно от runtime Flask:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m ml.data.locations `
  --destination-region "Ленинградская область" `
  --output-dir reports\locations\leningrad_region
```

`ml.data.locations` создаёт ровно одну аналитическую точку на destination FIAS,
отклоняет name/region fallback, явно маркирует unresolved coordinates и не подставляет центр региона.
Проекция `ml.spatial.projection` переводит WGS84 в локальные метры через AEQD.

Основной product smoke запускает на одном spatial graph пять режимов: Geography,
Geo+Cost, Geo+Volume, Bear Cost и Bear Volume. Delaunay с adaptive pruning используется
как primary graph, mutual kNN — как benchmark. Взвешенные режимы сохраняют sensitivity
80/20, 70/30 и 60/40.

Старый K-Means sweep сохранён только как legacy baseline:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.clustering_experiment `
  --locations reports\locations\leningrad_region\locations.json `
  --output-dir reports\clustering\leningrad_region `
  --k-min 2 --k-max 10 `
  --weight-mode both --stability-runs 5
```

Если получен утверждённый официальный GeoJSON границы региона, тот же runner строит
полностью покрывающие регион зоны и сохраняет `zones.geojson` для каждого `K`:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.clustering_experiment `
  --locations reports\locations\leningrad_region\locations.json `
  --output-dir reports\clustering\leningrad_region `
  --k-min 2 --k-max 10 `
  --boundary путь\к\official_boundary.geojson `
  --cell-size-m 2000
```

Для GeoJSON с несколькими субъектами дополнительно указывается точное значение свойства
региона через `--boundary-region-name`. Загрузчик принимает только валидные WGS84
`Polygon`/`MultiPolygon`; bbox и неофициальные запасные границы не подставляются.
Полигон является optional post-processing и не влияет на point assignments. Для production
используется локально выгруженная официальная граница НСПД/ЕГРН с
`boundary_manifest.json`; provenance и shipment-weighted containment проверяются командой:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.boundary_audit `
  --boundary путь\к\official_boundary.geojson `
  --manifest путь\к\boundary_manifest.json `
  --locations reports\locations\leningrad_region\locations.json `
  --require-official --output reports\clustering\leningrad_region\boundary_audit.json
```

Неоднозначные origin FIAS выносятся в приватную очередь ручной проверки, отсортированную
по `trip_count`:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.origin_fias_audit
```

В режиме Geography matrix использует только метрические `x/y`; цена и `trip_count`
не меняют adjacency. Geo+Cost добавляет robust-scaled weighted ₽/км, сохраняя graph
как hard constraint. Geo+Volume аналогично добавляет robust-scaled `log1p(trip_count)`.
Сравнительный отчёт не выбирает автоматического winner.

Универсальный `ml.spatial.territorialize` принимает утверждённую границу региона,
результат любого `Clusterer` и строит grid-based зоны с проверками coverage, overlap
и connected components. Граница региона не подменяется bbox или центром региона.

`decision_gate_clustering.json` — текущий gate. `decision_gate_2.json` сохранён как
исторический price-proxy artifact.

Out-of-time economic evaluation (deferred) запускается отдельно от clustering:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.business_evaluation `
  --clustering-dir reports\clustering\leningrad_region\origin_krivodanovka `
  --destination-region "Ленинградская область" `
  --origin-fias "96fe63dd-2802-415b-8b73-e06c2147ceef" `
  --train-periods 202608 --test-periods 202609,202610,202611
```

Ставки обучаются только на train. Прогнозные периоды Pulse явно считаются proxy,
а не заменой фактическим ATI/internal ценам.

### Actual-price evaluation (deferred / blocked)

Конфиденциальный actual-файл, private mapping и производные отчёты не хранятся в Git.
Сначала создайте conservative mapping-кандидаты:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.actual_audit
.\.venv\Scripts\python.exe -m ml.experiments.build_origin_mapping_candidates
```

Неоднозначные origins требуют ручной проверки в ignored-файле
`ml/configs/private/origin_mapping.csv`. После проверки единый runner запускается так:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.compare_variants `
  --actual "$env:LOGISTICS_ACTUAL_FILE" `
  --pulse "$env:LOGISTICS_CSV_FILE" `
  --origin-map "$env:LOGISTICS_ORIGIN_MAP_FILE" `
  --price-types tender `
  --period-types current `
  --output-dir reports\private\evaluation
```

`E0`, `E0_trip_weighted`, `E1`, `E2`, `E3` и `ATI_REF` используют общий metrics
engine. Decision gate сравнивает варианты на common intersection. Нехватка trusted
distance или destination-level ground truth возвращает `blocked`, а не фиктивную метрику.
Полный контракт описан в `docs/analytics_evaluation_contract.md`.

## Настройки

| Переменная | Назначение | Значение по умолчанию |
|---|---|---|
| `LOGISTICS_CSV_FILE` | Путь к исходному CSV | `v_pulse_prices.csv` |
| `LOGISTICS_ACTUAL_FILE` | Путь к конфиденциальному actual snapshot CSV | `v_fact_sibur_actual.csv` |
| `LOGISTICS_ORIGIN_MAP_FILE` | Путь к проверенному private origin mapping | не задан |
| `LOGISTICS_DISTANCE_FILE` | Путь к доверенным расстояниям для E1/E3 | не задан |
| `LOGISTICS_HOST` | Адрес прямого запуска `backend/app.py` | `127.0.0.1` |
| `LOGISTICS_PORT` | Порт прямого запуска | `5000` |
| `LOGISTICS_DEBUG` | Включить Flask debug (`1`) | выключен |
| `LOGISTICS_CORS_ORIGINS` | Разрешённые CORS-origin через запятую | CORS выключен |
| `LOGISTICS_REGION_BOUNDARIES_FILE` | Локальный утверждённый GeoJSON границ регионов | не задан |

## Структура

- `backend/app.py` — HTTP API и раздача интерфейса;
- `backend/data_processor.py` — чтение CSV, фильтрация и агрегация;
- `backend/geocoder.py` — координаты и постоянный JSON-кэш;
- `backend/services/clustering_service.py` — product orchestration поверх `ml/`;
- `backend/services/boundary_provider.py` — доступ только к настроенному GeoJSON;
- `frontend/` — статический интерфейс OpenLayers;
- `tests/` — проверки расчётов, API-валидации и отсутствия мутаций ML.

CSV загружается один раз на процесс. Для текущего файла примерно на 543 тысячи
строк холодный запуск занимает несколько секунд; для существенно больших данных
следующим шагом стоит перенести нормализованные записи в SQLite или DuckDB.
