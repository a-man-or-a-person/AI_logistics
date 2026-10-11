"""Execute the empty-table frontend branch at the existing real-Edge controller seam."""
import json
import os
import runpy
import sys
from pathlib import Path

os.environ['REQUIRE_FRONTEND_BROWSER'] = '1'
sys.path.insert(0, str(Path.cwd()))
tests = runpy.run_path('tests/test_clustering_frontend_contract.py')
result = tests['_run_browser_script'](tests['_product_workspace_script']("""
  await choose('a');
  const region=document.getElementById('cluster-region');
  region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
  document.getElementById('btn-run-clustering').click();await pause();
  const saved=workspace.getState().result.data;
  const button=document.getElementById('btn-export-clustering');button.focus();button.click();await pause();
  document.body.dataset.result=JSON.stringify({status:document.getElementById('export-status').textContent,
    disabled:button.getAttribute('aria-disabled'),focus:document.activeElement.id,
    exportRequests:requests.filter(r=>r.path==='export').length,
    runRequests:requests.filter(r=>r.path==='run').length,sameResult:workspace.getState().result.data===saved});
"""))
assert 'error' not in result, result
assert result['exportRequests'] == 0 and result['runRequests'] == 1
assert result['sameResult'] and result['disabled'] == 'true'
assert result['focus'] == 'btn-export-clustering' and 'нет кластеров' in result['status']
Path('docs/npi12-evidence/empty-guard.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
print('PASS: real Edge/controller seam; empty saved table explains blocked export, no rerun.')
