"""Bounded startup diagnosis using synthetic data and static resources only."""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

root = Path.cwd()
personal = root.parents[1]
output = root / 'docs/npi12-evidence'


def inspect(port, checkout):
    results = []
    for url, path in (('/', 'frontend/index.html'), ('/js/clustering/state.js', 'frontend/js/clustering/state.js'),
                      ('/js/clustering/controller.js', 'frontend/js/clustering/controller.js')):
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{url}', timeout=5) as response:
            data = response.read()
            headers = dict(response.headers)
        local = (checkout / path).read_bytes()
        item = {'url': url, 'http_status': 200, 'sha256': hashlib.sha256(data).hexdigest(),
                'matches_checkout_bytes': data == local, 'cache_control': headers.get('Cache-Control'),
                'etag': headers.get('ETag')}
        if url == '/':
            item.update(multi_origin=b'selected-origins' in data, regional_all=b'all-origins' in data)
        request = urllib.request.Request(f'http://127.0.0.1:{port}{url}', headers={'If-None-Match': headers.get('ETag', '')})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                item['conditional_status'] = response.status
        except urllib.error.HTTPError as error:
            item['conditional_status'] = error.code
        results.append(item)
    return results


report = {'personal_branch': subprocess.check_output(['git', '-C', str(personal), 'branch', '--show-current'], text=True).strip(),
          'personal_head': subprocess.check_output(['git', '-C', str(personal), 'rev-parse', 'HEAD'], text=True).strip(),
          'candidate_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          'default_port': 5055, 'direct_backend_default_port': 5000,
          'existing_server_5055': inspect(5055, personal)}
source = root / '.scratch/npi12-navigation-evidence/synthetic.csv'
assert source.exists()
env = {**os.environ, 'LOGISTICS_CSV_FILE': str(source), 'PYTHONUTF8': '1'}
started = time.perf_counter()
with output.joinpath('startup-server.txt').open('w', encoding='utf8') as log:
    process = subprocess.Popen([sys.executable, 'run.py', '--port', '5082', '--no-browser'], env=env, stdout=log, stderr=log)
    try:
        for _ in range(100):
            assert process.poll() is None
            try:
                with urllib.request.urlopen('http://127.0.0.1:5082/', timeout=1):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise TimeoutError('run.py startup')
        report['candidate_startup_seconds'] = time.perf_counter() - started
        report['candidate_server_5082'] = inspect(5082, root)
        assert all(r['matches_checkout_bytes'] for r in report['candidate_server_5082'])
        assert report['candidate_server_5082'][0]['regional_all']
        assert all(r['matches_checkout_bytes'] for r in report['existing_server_5055'])
        assert not report['existing_server_5055'][0]['regional_all']
    finally:
        process.terminate()
        process.wait(timeout=10)
report['finding'] = 'REPRODUCED: port 5055 serves exact static bytes of the older personal checkout; isolated candidate run.py serves current controls.'
output.joinpath('startup.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print(report['finding'])
