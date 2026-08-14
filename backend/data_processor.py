"""
Загрузка и агрегация данных из v_pulse_prices.csv.

Логика агрегации:
  - Агрегируем по уникальным городам (town_name)
  - Для каждого города: средняя цена, руб/км, км, кол-во заявок
  - Поддержка фильтрации по регионам отгрузки/доставки и period_type
"""

import csv
import os
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

CSV_FILE = os.path.join(os.path.dirname(__file__), "..", "v_pulse_prices.csv")
CSV_ENCODING = "utf-8-sig"
CSV_ENCODING_ERRORS = "replace"

# Индексы столбцов
COL_SHIP_FIAS     = 0
COL_SHIP_REGION   = 1
COL_SHIP_TOWN_SRC = 2
COL_SHIP_TOWN     = 3
COL_SHIP_PTYPE    = 4
COL_SHIP_ADDR     = 5
COL_DEL_FIAS      = 6
COL_DEL_REGION_SRC = 7
COL_DEL_REGION    = 8
COL_DEL_TOWN      = 9
COL_DEL_ADDR      = 10
COL_DEL_PTYPE     = 11
COL_PERIOD_ID     = 12
COL_PERIOD_TYPE   = 13   # retro / current / forecast
COL_BID_COUNT     = 14
COL_CONFIDENCE    = 15
COL_NANOS         = 16
COL_UNITS         = 17   # цена в рублях
COL_PRICE_TYPE    = 18   # spot / tender
COL_ROUTE_LENGTH  = 19   # км
COL_ROUTE_TYPE    = 20
COL_TONNAGE_ID    = 21
COL_VEHICLE_TYPE  = 22
COL_CURRENCY      = 23
COL_TECH_TS       = 24

def _strip_prefix(name: str) -> str:
    """Убирает типовые префиксы вида 'г ', 'гп ', 'г. ' из названий."""
    if not name:
        return ""
    for prefix in ("г ", "гп ", "г. ", "гп. ", "с ", "д ", "п ", "пгт ", "пос "):
        if name.startswith(prefix):
            return name[len(prefix):].strip()
    return name.strip()


MONTH_NAMES = {
    "01": "Янв", "02": "Фев", "03": "Мар", "04": "Апр",
    "05": "Май", "06": "Июн", "07": "Июл", "08": "Авг",
    "09": "Сен", "10": "Окт", "11": "Ноя", "12": "Дек",
}

# Глобальный кэш загруженных данных
_data: dict[str, Any] | None = None


def _format_period(period_id: str, period_type: str) -> str:
    if period_id and len(period_id) == 6:
        mm = period_id[4:6]
        yy = period_id[:4]
        return f"{MONTH_NAMES.get(mm, mm)} {yy}"
    return period_id or "—"


def _safe_float(val: str) -> float:
    try:
        return float(val.strip())
    except Exception:
        return 0.0


def _safe_int(val: str) -> int:
    try:
        return int(val.strip())
    except Exception:
        return 0


def load_data() -> dict[str, Any]:
    """
    Загружает CSV и строит структуры данных.
    Возвращает словарь с:
      - 'shipment_towns': {town_name: {region, records: [{...}]}}
      - 'delivery_towns': {town_name: {region, records: [{...}]}}
      - 'ship_regions': sorted list
      - 'del_regions': sorted list
      - 'total_rows': int
    """
    global _data
    if _data is not None:
        return _data

    logger.info(f"Загружаем данные из {CSV_FILE}...")

    csv_path = os.path.abspath(CSV_FILE)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV файл не найден: {csv_path}")

    # Структуры:
    # ship_towns[town_key] = {region, town_src, records: [record]}
    # del_towns[town_key] = {region, records: [record]}
    # record = {price, route_length, bid_count, period_type, period_id,
    #            price_type, ship_region, del_region, confidence}

    ship_towns: dict[str, dict] = {}
    del_towns: dict[str, dict] = {}
    ship_regions: set[str] = set()
    del_regions: set[str] = set()
    total_rows = 0

    with open(csv_path, "r", encoding=CSV_ENCODING, errors=CSV_ENCODING_ERRORS) as f:
        reader = csv.reader(f)
        next(reader)  # пропуск заголовка

        for row in reader:
            if len(row) < 20:
                continue

            total_rows += 1

            ship_region = row[COL_SHIP_REGION].strip()
            ship_town   = row[COL_SHIP_TOWN].strip()    # название (нормализованное)
            ship_town_src = row[COL_SHIP_TOWN_SRC].strip()  # исходное

            del_region  = row[COL_DEL_REGION].strip()
            del_town    = row[COL_DEL_TOWN].strip()

            period_type  = row[COL_PERIOD_TYPE].strip()
            period_id    = row[COL_PERIOD_ID].strip()
            price_type   = row[COL_PRICE_TYPE].strip()
            confidence   = row[COL_CONFIDENCE].strip()
            bid_count    = _safe_int(row[COL_BID_COUNT])
            units        = _safe_float(row[COL_UNITS])
            route_length = _safe_float(row[COL_ROUTE_LENGTH])

            if ship_region and ship_region.upper() != 'NULL':
                ship_regions.add(ship_region)
            if del_region and del_region.upper() != 'NULL':
                del_regions.add(del_region)

            record = {
                "price": units,
                "route_length": route_length,
                "bid_count": bid_count,
                "period_type": period_type,
                "period_id": period_id,
                "period_label": _format_period(period_id, period_type),
                "price_type": price_type,
                "confidence": confidence,
                "ship_region": ship_region,
                "del_region": del_region,
            }

            # Отгрузка — если name_town пусто, используем town_src (убираем префикс "г ", "гп ")
            effective_ship_town = ship_town or _strip_prefix(ship_town_src)
            if effective_ship_town and ship_region and ship_region.upper() != 'NULL':
                key = f"{effective_ship_town}::{ship_region}"
                if key not in ship_towns:
                    ship_towns[key] = {
                        "town": effective_ship_town,
                        "town_src": ship_town_src,
                        "region": ship_region,
                        "records": [],
                    }
                ship_towns[key]["records"].append(record)

            # Доставка
            if del_town and del_region and del_region.upper() != 'NULL':
                key = f"{del_town}::{del_region}"
                if key not in del_towns:
                    del_towns[key] = {
                        "town": del_town,
                        "region": del_region,
                        "records": [],
                    }
                del_towns[key]["records"].append(record)

    logger.info(
        f"Загружено строк: {total_rows}, "
        f"городов отгрузки: {len(ship_towns)}, "
        f"городов доставки: {len(del_towns)}"
    )

    _data = {
        "shipment_towns": ship_towns,
        "delivery_towns": del_towns,
        "ship_regions": sorted(ship_regions),
        "del_regions": sorted(del_regions),
        "total_rows": total_rows,
    }
    return _data


def _aggregate_records(records: list[dict], period_types: set[str], price_types: set[str]) -> dict | None:
    """Агрегирует набор записей для одного города — расширенная версия."""
    filtered = [
        r for r in records
        if (not period_types or r["period_type"] in period_types)
        and (not price_types or r["price_type"] in price_types)
    ]
    if not filtered:
        return None

    prices = [r["price"] for r in filtered if r["price"] > 0]
    lengths = [r["route_length"] for r in filtered if r["route_length"] > 0]
    bids = [r["bid_count"] for r in filtered]

    avg_price = sum(prices) / len(prices) if prices else 0
    avg_length = sum(lengths) / len(lengths) if lengths else 0
    avg_bids = sum(bids) / len(bids) if bids else 0
    rub_per_km = avg_price / avg_length if avg_length > 0 else 0

    period_types_found = sorted({r["period_type"] for r in filtered})
    price_types_found = sorted({r["price_type"] for r in filtered})

    # Min/Max цены и расстояния
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0
    min_length = min(lengths) if lengths else 0
    max_length = max(lengths) if lengths else 0

    # Разбивка по period_type
    by_period: dict[str, dict] = {}
    for pt in ["retro", "current", "forecast"]:
        pt_recs = [r for r in filtered if r["period_type"] == pt]
        if pt_recs:
            pt_prices = [r["price"] for r in pt_recs if r["price"] > 0]
            pt_lengths = [r["route_length"] for r in pt_recs if r["route_length"] > 0]
            by_period[pt] = {
                "count": len(pt_recs),
                "avg_price": round(sum(pt_prices) / len(pt_prices), 0) if pt_prices else 0,
                "avg_length": round(sum(pt_lengths) / len(pt_lengths), 1) if pt_lengths else 0,
                "rub_per_km": round(
                    (sum(pt_prices) / len(pt_prices)) / (sum(pt_lengths) / len(pt_lengths)), 1
                ) if pt_prices and pt_lengths else 0,
            }

    # Разбивка по price_type (spot / tender)
    by_price_type: dict[str, dict] = {}
    for ptype in ["spot", "tender"]:
        ptype_recs = [r for r in filtered if r["price_type"] == ptype]
        if ptype_recs:
            ptype_prices = [r["price"] for r in ptype_recs if r["price"] > 0]
            ptype_lengths = [r["route_length"] for r in ptype_recs if r["route_length"] > 0]
            by_price_type[ptype] = {
                "count": len(ptype_recs),
                "avg_price": round(sum(ptype_prices) / len(ptype_prices), 0) if ptype_prices else 0,
                "avg_length": round(sum(ptype_lengths) / len(ptype_lengths), 1) if ptype_lengths else 0,
            }

    # Top регионов отгрузки (для точек доставки) / доставки (для точек отгрузки)
    ship_region_counts: dict[str, int] = defaultdict(int)
    del_region_counts: dict[str, int] = defaultdict(int)
    for r in filtered:
        if r["ship_region"]:
            ship_region_counts[r["ship_region"]] += 1
        if r["del_region"]:
            del_region_counts[r["del_region"]] += 1

    top_ship_regions = sorted(ship_region_counts.items(), key=lambda x: -x[1])[:5]
    top_del_regions = sorted(del_region_counts.items(), key=lambda x: -x[1])[:5]

    # Средняя достоверность
    confidence_values = [r["confidence"] for r in filtered if r["confidence"] and r["confidence"] != "—"]
    avg_confidence = confidence_values[0] if len(set(confidence_values)) == 1 else (
        max(set(confidence_values), key=confidence_values.count) if confidence_values else "—"
    )

    return {
        "count": len(filtered),
        "avg_price": round(avg_price, 0),
        "avg_length": round(avg_length, 1),
        "avg_bids": round(avg_bids, 1),
        "rub_per_km": round(rub_per_km, 1),
        "min_price": round(min_price, 0),
        "max_price": round(max_price, 0),
        "min_length": round(min_length, 0),
        "max_length": round(max_length, 0),
        "period_types": period_types_found,
        "price_types": price_types_found,
        "by_period": by_period,
        "by_price_type": by_price_type,
        "top_ship_regions": [{"region": r, "count": c} for r, c in top_ship_regions],
        "top_del_regions": [{"region": r, "count": c} for r, c in top_del_regions],
        "confidence": avg_confidence,
    }


def get_map_points(
    from_regions: list[str] | None = None,
    to_regions: list[str] | None = None,
    period_types: list[str] | None = None,
    price_types: list[str] | None = None,
) -> dict[str, Any]:
    """
    Возвращает данные для карты с учётом фильтров.

    Если from_regions/to_regions пусты — возвращаем все регионы.
    """
    data = load_data()

    from_set = set(from_regions) if from_regions else set()
    to_set = set(to_regions) if to_regions else set()
    period_set = set(period_types) if period_types else set()
    price_set = set(price_types) if price_types else set()

    ship_points = []
    del_points = []

    # Точки отгрузки
    for town_key, info in data["shipment_towns"].items():
        if from_set and info["region"] not in from_set:
            continue

        # Фильтрация записей: если указаны to_regions — берём только маршруты туда
        records = info["records"]
        if to_set:
            records = [r for r in records if r["del_region"] in to_set]

        agg = _aggregate_records(records, period_set, price_set)
        if agg is None:
            continue

        ship_points.append({
            "type": "shipment",
            "town": info["town"],
            "region": info["region"],
            **agg,
        })

    # Точки доставки
    for town_key, info in data["delivery_towns"].items():
        if to_set and info["region"] not in to_set:
            continue

        records = info["records"]
        if from_set:
            records = [r for r in records if r["ship_region"] in from_set]

        agg = _aggregate_records(records, period_set, price_set)
        if agg is None:
            continue

        del_points.append({
            "type": "delivery",
            "town": info["town"],
            "region": info["region"],
            **agg,
        })

    return {
        "shipment_points": ship_points,
        "delivery_points": del_points,
        "total_ship": len(ship_points),
        "total_del": len(del_points),
    }


def get_regions() -> dict[str, list[str]]:
    """Возвращает списки регионов отгрузки и доставки."""
    data = load_data()
    return {
        "ship_regions": data["ship_regions"],
        "del_regions": data["del_regions"],
    }


def get_stats() -> dict[str, Any]:
    """Общая статистика."""
    data = load_data()
    return {
        "total_rows": data["total_rows"],
        "ship_towns_count": len(data["shipment_towns"]),
        "del_towns_count": len(data["delivery_towns"]),
        "ship_regions_count": len(data["ship_regions"]),
        "del_regions_count": len(data["del_regions"]),
    }


def get_raw_records(
    town: str,
    region: str,
    town_type: str,
    from_regions: list[str] | None = None,
    to_regions: list[str] | None = None,
    period_types: list[str] | None = None,
    price_types: list[str] | None = None,
) -> list[dict]:
    """Возвращает сырые записи для указанного города, отфильтрованные."""
    data = load_data()
    if not data:
        return []

    from_set = set(r.upper() for r in (from_regions or []))
    to_set = set(r.upper() for r in (to_regions or []))
    period_set = set(p.upper() for p in (period_types or []))
    price_set = set(p.upper() for p in (price_types or []))

    key = f"{town}::{region}"

    if town_type == "shipment":
        town_data = data["shipment_towns"].get(key)
        if not town_data:
            return []
        
        filtered = []
        for r in town_data["records"]:
            if from_set and r["ship_region"].upper() not in from_set:
                continue
            if to_set and r["del_region"].upper() not in to_set:
                continue
            if period_set and r["period_type"].upper() not in period_set:
                continue
            if price_set and r["price_type"].upper() not in price_set:
                continue
            filtered.append(r)
        
        return filtered

    elif town_type == "delivery":
        town_data = data["delivery_towns"].get(key)
        if not town_data:
            return []
        
        filtered = []
        for r in town_data["records"]:
            if from_set and r["ship_region"].upper() not in from_set:
                continue
            if to_set and r["del_region"].upper() not in to_set:
                continue
            if period_set and r["period_type"].upper() not in period_set:
                continue
            if price_set and r["price_type"].upper() not in price_set:
                continue
            filtered.append(r)
            
        return filtered
        
    return []
