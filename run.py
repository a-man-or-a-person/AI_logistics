"""
Точка запуска проекта Логистика AI.
Запускает Flask API сервер.

Использование:
    python run.py
    python run.py --port 8080
    python run.py --debug
"""

import sys
import os
import argparse
import logging
import threading
import webbrowser
import time

# Добавляем директорию проекта в путь
sys.path.insert(0, os.path.dirname(__file__))

def main():
    parser = argparse.ArgumentParser(description="Логистика AI — сервер карты перевозок")
    parser.add_argument("--port",  type=int, default=5000, help="Порт сервера (по умолчанию: 5000)")
    parser.add_argument("--host",  type=str, default="127.0.0.1", help="Адрес (по умолчанию: 127.0.0.1)")
    parser.add_argument("--debug", action="store_true", help="Режим отладки")
    parser.add_argument("--no-browser", action="store_true", help="Не открывать браузер автоматически")
    args = parser.parse_args()

    # Настройка логирования
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("run")

    # Предварительная загрузка данных
    logger.info("=" * 60)
    logger.info("  ЛОГИСТИКА AI — КАРТА ПЕРЕВОЗОК")
    logger.info("=" * 60)
    logger.info("Предварительная загрузка CSV данных...")

    try:
        from backend.data_processor import load_data
        data = load_data()
        logger.info(
            f"✓ Данные загружены: {data['total_rows']:,} строк, "
            f"{len(data['shipment_towns'])} городов отгрузки, "
            f"{len(data['delivery_towns'])} городов доставки"
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        sys.exit(1)

    url = f"http://{args.host}:{args.port}"
    logger.info(f"Запускаем сервер: {url}")

    # Открываем браузер автоматически (через 1 секунду)
    if not args.no_browser:
        def open_browser():
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    # Запуск Flask
    from backend.app import app
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,  # Отключаем ребут — данные уже загружены
    )


if __name__ == "__main__":
    main()
