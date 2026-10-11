"""Literal, sequential XLSX serialization of saved Product values."""
from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from tempfile import TemporaryDirectory, TemporaryFile

import xlsxwriter

from backend.product_modes import ProductClusteringError

TABLE_COLUMNS = (
    ('cluster_id', 'Кластер', None), ('point_count', 'Точки', '0'),
    ('trip_count', 'Машины', '0'), ('trip_share', 'Доля машин', '0.0%'),
    ('weighted_route_length', 'Маршрут', '0.0" км"'),
    ('price.min', 'Мин. цена', '0" ₽"'), ('price.median', 'Медианная цена', '0" ₽"'),
    ('price.weighted', 'Ср.-взв. цена', '0" ₽"'), ('price.max', 'Макс. цена', '0" ₽"'),
    ('rub_per_km.min', 'Мин. ₽/км', '0.0" ₽/км"'),
    ('rub_per_km.median', 'Медианный ₽/км', '0.0" ₽/км"'),
    ('rub_per_km.weighted', 'Ср.-взв. ₽/км', '0.0" ₽/км"'),
    ('rub_per_km.max', 'Макс. ₽/км', '0.0" ₽/км"'),
    ('economic_coverage', 'Покрытие экономики', None),
)
DETAIL_COLUMNS = ('source_row_id', 'period_id', 'source_timestamp', 'period_type',
    'price_type', 'vehicle_type', 'tonnage_id', 'price', 'route_length', 'rub_per_km',
    'trip_count', 'warnings', 'origin_fias', 'origin_name', 'origin_region',
    'destination_fias', 'destination_name', 'cluster_id')
UNKNOWN_REGION = 'Регион погрузки не определён'


def visible_cluster(cluster_id):
    return f'Кластер {cluster_id + 1}'


def raw_value(row, key):
    if '.' in key:
        metric, field = key.split('.')
        return row[metric][field]
    if key == 'economic_coverage':
        coverage = row[key]
        return coverage['valid_trip_count'] / coverage['total_trip_count'] if coverage['total_trip_count'] else None
    return row[key]


def validate_sort(value):
    if (not isinstance(value, dict) or set(value) != {'key', 'direction'}
            or not isinstance(value['key'], str) or not isinstance(value['direction'], str)
            or value['key'] not in {c[0] for c in TABLE_COLUMNS}
            or value['direction'] not in ('asc', 'desc')):
        raise ProductClusteringError('INVALID_REQUEST', 'Invalid table_sort.', 400)


def write_workbook(saved, source_rows, table_sort):
    """Return a complete disk-backed file; no partial file escapes on any failure."""
    output = TemporaryFile('w+b')
    try:
        with TemporaryDirectory(prefix='product-xlsx-') as temporary:
            with xlsxwriter.Workbook(output, {'constant_memory': True, 'tmpdir': temporary,
                    'strings_to_formulas': False, 'strings_to_urls': False}) as workbook:
                formats = {pattern: workbook.add_format({'num_format': pattern})
                           for pattern in {c[2] for c in TABLE_COLUMNS if c[2]}}
                header = workbook.add_format({'bold': True})
                blank = workbook.add_format({})

                def write(sheet, index, values, patterns=()):
                    for column, value in enumerate(values):
                        style = formats.get(patterns[column]) if patterns else None
                        if isinstance(value, str):
                            result = sheet.write_string(index, column, value, style)
                        elif value is None:
                            result = sheet.write_blank(index, column, None, style or blank)
                        elif isinstance(value, int | float) and math.isfinite(value):
                            result = sheet.write_number(index, column, value, style)
                        else:
                            raise ValueError('Unserializable XLSX value')
                        if result != 0:
                            raise ValueError('XLSX cell limit or write failure')

                table = workbook.add_worksheet('Кластеры')
                table.freeze_panes(1, 0)
                table.write_row(0, 0, [c[1] for c in TABLE_COLUMNS], header)
                key = table_sort['key']
                sign = 1 if table_sort['direction'] == 'asc' else -1
                rows = sorted(saved['cluster_table']['rows'], key=lambda row: (
                    raw_value(row, key) is None, sign * (raw_value(row, key) or 0), row['cluster_id']))
                for index, row in enumerate(rows, 1):
                    values = [raw_value(row, c[0]) for c in TABLE_COLUMNS]
                    values[0] = visible_cluster(row['cluster_id'])
                    coverage = row['economic_coverage']
                    def percent(valid, total):
                        return f'{valid / total * 100:.1f}%' if total else '—'
                    values[-1] = (f"{percent(coverage['valid_points'], coverage['total_points'])} точек · "
                                  f"{percent(coverage['valid_trip_count'], coverage['total_trip_count'])} машин")
                    write(table, index, values, [c[2] for c in TABLE_COLUMNS])

                directions = {}
                regions = {}
                for record in source_rows:
                    region, cluster = record['origin_region'], record['cluster_id']
                    regions.setdefault(record['origin_fias'], set()).add(region)
                    identity = (region, cluster)
                    if identity not in directions:
                        label = f'{region if region is not None else UNKNOWN_REGION} → {visible_cluster(cluster)}'
                        # A unique numeric prefix also distinguishes null from a literal unknown-region label.
                        prefix = f'{len(directions) + 1} '
                        name = prefix + re.sub(r"[\[\]:*?/\\\x00-\x1f]", '_', label).strip("'")[:31-len(prefix)]
                        sheet = workbook.add_worksheet(name)
                        sheet.freeze_panes(1, 0)
                        sheet.write_row(0, 0, DETAIL_COLUMNS, header)
                        directions[identity] = [sheet, 0, label]
                    direction = directions[identity]
                    direction[1] += 1
                    values = [record[field] for field in DETAIL_COLUMNS]
                    values[11] = '; '.join(record['warnings'])
                    values[14] = region if region is not None else UNKNOWN_REGION
                    values[-1] = visible_cluster(cluster)
                    patterns = [None] * len(values)
                    patterns[7:11] = ['0" ₽"', '0.0" км"', '0.0" ₽/км"', '0']
                    write(direction[0], direction[1], values, patterns)

                context = workbook.add_worksheet('Контекст')
                context.write_row(0, 0, ['Контекст / методика', 'Значение'], header)
                facts = {
                    'frozen_request': saved['analysis']['frozen_request'],
                    'selection_intent': saved['analysis']['selection_intent'],
                    'origins': saved['analysis']['origins'],
                    'origin_coverage': saved['analysis']['origin_coverage'],
                    'source': 'Pulse', 'data_snapshot': saved['data_snapshot'],
                    'table_sort': table_sort, 'methodology': saved['cluster_table']['methodology'],
                    'units': {'price': '₽', 'route_length': 'км', 'rub_per_km': '₽/км', 'trip_count': 'машины'},
                    'valid_weights': 'Mean = sum(metric × valid positive trip_count) / sum(metric-valid trip_count); price, route_length, rub_per_km each use their own denominator. ₽/км = row price / row route_length, then machine weighting. Min/median/max describe destination points without weights.',
                    'missing_values': 'Blank numeric cells mean unavailable; zero remains numeric. Nonpositive metrics do not contribute to metric means. IDs and source timestamps are literal text; timestamps retain source timezone, no conversion.',
                    'normalized_fields': list(DETAIL_COLUMNS),
                    'data_quality': saved['data_quality'],
                    'exclusions': [ {'destination_fias': p['id'], 'status': p['status'], 'trip_count': p['trip_count'], 'source_row_count': p['source_row_count']}
                                    for p in saved['points'] if p['cluster_id'] is None or p['cluster_id'] < 0],
                    'export_created_at_utc': datetime.now(UTC).isoformat(),
                }
                for row in rows:
                    facts[f"cluster_mapping:{row['cluster_id']}"] = visible_cluster(row['cluster_id'])
                    facts[f"coverage:{row['cluster_id']}"] = row['coverage']
                for (region, cluster), (sheet, count, label) in directions.items():
                    facts[f'sheet:{sheet.name}'] = {'full_label': label, 'origin_region': region,
                        'canonical_cluster_id': cluster, 'source_row_count': count}
                for origin, labels in regions.items():
                    if len(labels) > 1:
                        facts[f'conflicting_origin_regions:{origin}'] = sorted(labels, key=lambda v: (v is None, v or ''))
                for index, (key, value) in enumerate(facts.items(), 1):
                    write(context, index, [key, value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, allow_nan=False)])
        output.seek(0)
        return output
    except Exception:
        output.close()
        raise
