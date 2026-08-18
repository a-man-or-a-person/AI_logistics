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
