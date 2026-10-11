"""Safe synthetic live fixture; uses real Flask and all five Product algorithms."""
import csv
import json
import os
import sys
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root))
evidence = root / '.scratch/npi07-evidence'
evidence.mkdir(parents=True, exist_ok=True)
source = evidence / 'synthetic.csv'
coords = evidence / 'coords.json'
os.environ['LOGISTICS_CSV_FILE'] = str(source)

from ml.data.loader import PULSE_COLUMNS  # noqa: E402 -- synthetic source configured first

rows = []
coordinates = {}
def row(origin, index, trips, distance, price, region='Origin Region', price_type='spot', period='202608'):
    item = dict.fromkeys(PULSE_COLUMNS, '')
    item.update(shipment_point_locality_fias_id=origin, shipment_point_name_town=f'Synthetic {origin}',
        shipment_point_region=region, delivery_point_locality_fias_id=f'synthetic-{index:02}',
        delivery_point_town=f'Synthetic Destination {index:02}', delivery_point_region_unified='Region A',
        period_id=period, period_type='current', price_type=price_type, vehicle_body_type='tent',
        tonnage_id='20', bid_count=str(trips), units=str(price), route_length=str(distance))
    return item
for index in range(12):
    coordinates[f'Synthetic Destination {index:02}::Region A'] = [55.1 + index // 4 * .04, 37.1 + index % 4 * .04]
    rows.extend([row('a',index,10,100,1000), row('b',index,30,300,6000,'B Region')])
rows.extend([row('b',0,20,'','',''), row('b',0,20,'',4500,'B Region')])
rows.extend(row('a',0,1,100,1000, period='202609') for _ in range(60))
rows.extend(row(f'extra-{i:02}',0,1,200,2000) for i in range(31))
rows.append(row('c',0,999,100,1000, price_type='tender'))
archive = row('a', 1, 4, 100, 1000, period='202607')
archive['period_type'] = 'retro'
rows.append(archive)
assert len(rows) == 119
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
    added = [row('new', 0, 1, 200, 2000)]
    with source.open('a', encoding='utf-8', newline='') as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerows(added)
    return {'ok': True, 'added': len(added)}

app.run(host='127.0.0.1', port=5067, use_reloader=False)
