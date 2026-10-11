"""Safe synthetic live fixture; uses real Flask and all five Product algorithms."""
import csv
import json
import os
import sys
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root))
evidence = root / '.scratch/npi05-evidence'
evidence.mkdir(parents=True, exist_ok=True)
source = evidence / 'synthetic.csv'
coords = evidence / 'coords.json'
os.environ['LOGISTICS_CSV_FILE'] = str(source)

from ml.data.loader import PULSE_COLUMNS  # noqa: E402 -- synthetic source configured first

rows = []
coordinates = {}
for index in range(12):
    name = f'Synthetic Destination {index:02}'
    coordinates[f'{name}::Region A'] = [55.1 + index // 4 * .04, 37.1 + index % 4 * .04]
    entries = [(f'synthetic-o{j:02}', f'Synthetic Origin {j:02}', 'current',
                'tender' if j == 35 else 'spot', 10 if j == 0 else 30 if j == 1 else 1,
                100 if j == 0 else 300 if j == 1 else 200) for j in range(36)]
    entries += [('synthetic-o00', 'Synthetic Origin 00', 'retro', 'spot', 4, 100)]
    for origin, origin_name, period, price_type, trips, distance in entries:
        row = dict.fromkeys(PULSE_COLUMNS, '')
        row.update(shipment_point_locality_fias_id=origin,
                   shipment_point_name_town=origin_name, shipment_point_region='Synthetic Origin Region',
                   delivery_point_locality_fias_id=f'synthetic-{index:02}',
                   delivery_point_town=name, delivery_point_region_unified='Region A',
                   period_id='202608' if period == 'current' else '202607', period_type=period,
                   price_type=price_type, vehicle_body_type='tent', tonnage_id='20',
                   bid_count=str(trips), units=str(distance * (10 + index)), route_length=str(distance))
        rows.append(row)
foreign = []
for index in range(12):
    item = dict(rows[index * 37])
    item.update(shipment_point_locality_fias_id='synthetic-foreign',
                shipment_point_name_town='Foreign Origin', delivery_point_region_unified='Region B')
    foreign.append(item)
rows.extend(foreign)
for index in range(12):
    coordinates[f'Synthetic Destination {index:02}::Region B'] = [56.1 + index // 4 * .04, 38.1 + index % 4 * .04]
assert len(rows) == 456 and len(coordinates) == 24
with source.open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
coords.write_text(json.dumps(coordinates), encoding='utf8')

from backend.app import app  # noqa: E402 -- create synthetic files before app import
from backend.clustering_api import set_clustering_service  # noqa: E402
from backend.services.clustering_service import ClusteringService  # noqa: E402

service = ClusteringService(source, coordinate_cache_path=coords)
set_clustering_service(service)

@app.post('/fixture/evict')
def evict():
    service._result_cache.clear()
    return {'ok': True}

@app.post('/fixture/add-origin')
def add_origin():
    added = []
    for index in range(12):
        row = dict(rows[index * 37])
        row.update(shipment_point_locality_fias_id='synthetic-new',
                   shipment_point_name_town='New Synthetic Origin', period_type='current',
                   price_type='spot', bid_count='1', units='2000', route_length='200')
        added.append(row)
    with source.open('a', encoding='utf-8', newline='') as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerows(added)
    return {'ok': True, 'added': len(added)}

app.run(host='127.0.0.1', port=5065, use_reloader=False)
