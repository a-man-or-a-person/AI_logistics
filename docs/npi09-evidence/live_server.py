"""NPI-09 only: synthetic Pulse, real Flask and unchanged Product algorithms."""
import csv
import json
import os
import sys
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root))
evidence = root / '.scratch/npi09-live'
evidence.mkdir(parents=True, exist_ok=True)
source, coords = evidence / 'pulse.csv', evidence / 'coords.json'
os.environ['LOGISTICS_CSV_FILE'] = str(source)

from ml.data.loader import PULSE_COLUMNS  # noqa: E402


def row(origin, index, trips, price):
    item = dict.fromkeys(PULSE_COLUMNS, '')
    item.update(shipment_point_locality_fias_id=origin, shipment_point_name_town=f'Synthetic {origin}',
                shipment_point_region='Origin Region', delivery_point_locality_fias_id=f'p{index}',
                delivery_point_town='' if index == 0 else f'село Synthetic {index}',
                delivery_point_region_unified='Region A', period_id='202608', period_type='current',
                price_type='spot', vehicle_body_type='tent', tonnage_id='20',
                bid_count=str(trips), units=str(price), route_length='100')
    return item


rows, coordinates = [], {}
for index in range(12):
    rows.extend([row('a', index, 500 if index == 0 else 10, 100000 if index == 1 else 1000),
                 row('b', index, 1, 1000)])
    name = '<missing>' if index == 0 else f'село Synthetic {index}'
    coordinates[f'{name}::Region A'] = [55 + index // 4 * .04, 37 + index % 4 * .04]
outside = row('a', 12, 9999, 1000)
outside['delivery_point_town'] = 'деревня без координат'
rows.append(outside)
archive = row('a', 1, 1, 1000)
archive['period_type'] = 'retro'
rows.append(archive)
assert len(rows) == 26
with source.open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
coords.write_text(json.dumps(coordinates), encoding='utf-8')

from backend.app import app  # noqa: E402
from backend.clustering_api import set_clustering_service  # noqa: E402
from backend.services.clustering_service import ClusteringService  # noqa: E402

set_clustering_service(ClusteringService(source, coordinate_cache_path=coords))


@app.post('/fixture/change-source')
def change_source():
    with source.open('a', encoding='utf-8', newline='') as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerow(row('new', 1, 1, 1000))
    return {'ok': True}


app.run(host='127.0.0.1', port=5069, use_reloader=False)
