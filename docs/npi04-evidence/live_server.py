"""Safe synthetic live fixture; uses real Flask and all five Product algorithms."""
import csv
import json
import os
import sys
from pathlib import Path

root = Path.cwd()
sys.path.insert(0, str(root))
evidence = root / '.scratch/npi04-evidence'
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
    for origin, origin_name, period, price_type, trips, distance in (
        ('synthetic-a', 'Synthetic Alpha', 'current', 'spot', 10, 100),
        ('synthetic-b', 'Synthetic Beta', 'current', 'spot', 30, 300),
        ('synthetic-a', 'Synthetic Alpha', 'retro', 'spot', 4, 100),
        ('synthetic-b', 'Synthetic Beta', 'retro', 'spot', 6, 300),
        ('synthetic-c', 'Synthetic Gamma', 'current', 'tender', 5, 200),
    ):
        row = dict.fromkeys(PULSE_COLUMNS, '')
        row.update(shipment_point_locality_fias_id=origin,
                   shipment_point_name_town=origin_name, shipment_point_region='Synthetic Origin Region',
                   delivery_point_locality_fias_id=f'synthetic-{index:02}',
                   delivery_point_town=name, delivery_point_region_unified='Region A',
                   period_id='202608' if period == 'current' else '202607', period_type=period,
                   price_type=price_type, vehicle_body_type='tent', tonnage_id='20',
                   bid_count=str(trips), units=str(distance * (10 + index)), route_length=str(distance))
        rows.append(row)
assert len(rows) == 60 and len(coordinates) == 12
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

app.run(host='127.0.0.1', port=5064, use_reloader=False)
