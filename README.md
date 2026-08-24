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

Без внутренних расстояний и референсной цены decision gate №1 намеренно не
считается пройденным: переход к усложнению через кластеризацию будет преждевременным.

## Настройки

| Переменная | Назначение | Значение по умолчанию |
|---|---|---|
| `LOGISTICS_CSV_FILE` | Путь к исходному CSV | `v_pulse_prices.csv` |
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
