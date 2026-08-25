# Логистика AI

Локальное Flask-приложение для анализа ставок перевозок, отображения городов на
карте и кластеризации логистических точек.

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

## Исследовательский ML-слой

Аналитический код изолирован в `ml/` и не меняет существующие API и карту. Первый
этап формирует аудит исходного CSV и единый контракт данных:

```powershell
.\.venv\Scripts\python.exe -m ml.data.audit
```

Результаты сохраняются в `reports/data_audit.json` и `reports/data_audit.csv`.
Путь к другому источнику можно передать первым аргументом; для быстрой проверки
доступен параметр `--limit N`.

Воспроизведение текущего расчёта для пилотного региона запускается отдельно:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.current_baseline `
  --destination-region "Ленинградская область"
```

Отчёт одновременно показывает совместимый с backend расчёт и вариант, взвешенный
по `bid_count`; это делает различие методик явным до проверки внутренних километражей.

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

Spatial core устанавливается отдельно от runtime Flask:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m ml.data.locations `
  --destination-region "Ленинградская область" `
  --output-dir reports\locations\leningrad_region
```

`ml.data.locations` создаёт ровно одну аналитическую точку на destination FIAS,
явно маркирует fallback и unresolved coordinates и не подставляет центр региона.
Проекция `ml.spatial.projection` переводит WGS84 в локальные метры через AEQD.

Географический K-Means baseline запускается sweep-ом, а не ручным подбором:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.clustering_experiment `
  --locations reports\locations\leningrad_region\locations.json `
  --output-dir reports\clustering\leningrad_region `
  --k-min 2 --k-max 10
```

Baseline использует только метрические `x/y`; ставки и `₽/км` остаются исключительно
для последующей business evaluation. Polygon coverage, WAPE и stability в leaderboard
остаются пустыми до соответствующих этапов и не подменяются proxy-метриками.

Универсальный `ml.spatial.territorialize` принимает утверждённую границу региона,
результат любого `Clusterer` и строит grid-based зоны с проверками coverage, overlap
и connected components. Граница региона не подменяется bbox или центром региона.

Out-of-time economic evaluation запускается отдельно от clustering:

```powershell
.\.venv\Scripts\python.exe -m ml.experiments.business_evaluation `
  --clustering-dir reports\clustering\leningrad_region\origin_krivodanovka `
  --destination-region "Ленинградская область" `
  --origin-fias "96fe63dd-2802-415b-8b73-e06c2147ceef" `
  --train-periods 202608 --test-periods 202609,202610,202611
```

Ставки обучаются только на train. Прогнозные периоды Pulse явно считаются proxy,
а не заменой фактическим ATI/internal ценам.

### Actual-price evaluation

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

## Структура

- `backend/app.py` — HTTP API и раздача интерфейса;
- `backend/data_processor.py` — чтение CSV, фильтрация и агрегация;
- `backend/geocoder.py` — координаты и постоянный JSON-кэш;
- `backend/ml_clustering.py` — KMeans и полигоны Voronoi;
- `frontend/` — статический интерфейс OpenLayers;
- `tests/` — проверки расчётов, API-валидации и отсутствия мутаций ML.

CSV загружается один раз на процесс. Для текущего файла примерно на 543 тысячи
строк холодный запуск занимает несколько секунд; для существенно больших данных
следующим шагом стоит перенести нормализованные записи в SQLite или DuckDB.
