"""D-07 workspace placement and existing public interaction contracts."""

import pytest
from test_clustering_frontend_contract import _run_browser_script
from test_dashboard_table import _table_script


@pytest.mark.parametrize('viewport,baseline_area', [
    ((1366, 768), 252736), ((1440, 900), 376435), ((1920, 1080), 764849),
])
def test_desktop_map_starts_at_workspace_top_without_toolbar_or_context(viewport, baseline_area):
    actual = _run_browser_script(_table_script("""
      const center=document.getElementById('clustering-center'),map=document.getElementById('clustering-map');
      const r=map.getBoundingClientRect(),c=center.getBoundingClientRect();
      const sidebar=document.getElementById('clustering-inspector');
      document.body.dataset.result=JSON.stringify({top:r.top,centerTop:c.top,area:r.width*r.height,
        full:r.bottom<=innerHeight,context:sidebar.contains(document.getElementById('result-context')),
        compare:sidebar.contains(document.getElementById('compare-modes')),
        controlsHidden:!document.getElementById('mobile-controls-btn').checkVisibility(),
        resultHidden:!document.getElementById('mobile-inspector-btn').checkVisibility(),
        columns:document.querySelectorAll('#cluster-table-panel thead th').length});
    """), reduced_motion=True, viewport=viewport)
    assert actual['top'] == actual['centerTop'] == 68, actual
    assert actual['area'] >= baseline_area and actual['full'], actual
    assert all(actual[key] for key in ['context', 'compare', 'controlsHidden', 'resultHidden']), actual
    assert actual['columns'] == 14


def test_methodology_disclosure_is_removed_and_existing_metric_help_remains():
    actual = _run_browser_script(_table_script("""
      const table=document.getElementById('cluster-table-panel');
      const help=table.querySelector('[aria-describedby="cluster-formula-price.weighted"]');help.focus();
      document.body.dataset.result=JSON.stringify({removed:!table.querySelector('.cluster-table-methodology'),
        help:help.querySelector('[popover]').matches(':popover-open'),
        text:help.querySelector('[popover]').textContent,columns:table.querySelectorAll('thead th').length});
    """), reduced_motion=True)
    assert actual['removed'] and actual['help'] and actual['columns'] == 14, actual
    assert 'Пропуски' in actual['text'] and 'машин' in actual['text']


@pytest.mark.parametrize('viewport', [(1440, 900), (1093, 614), (900, 720)])
@pytest.mark.parametrize('close_with_escape', [False, True])
def test_relocated_compare_and_responsive_drawer_keep_focus_and_frozen_result(viewport, close_with_escape):
    actual = _run_browser_script(_table_script("""
      const panel=document.getElementById('clustering-inspector');
      if(innerWidth<1320)document.getElementById('mobile-inspector-btn').click();
      const compare=document.getElementById('compare-modes');compare.focus();compare.click();await pause();
      const dialog=document.getElementById('comparison-view');
      const opened=dialog.checkVisibility()&&dialog.contains(document.activeElement);
      const saved=workspace.getState().result.data;
      CLOSE_COMPARISON
      await pause();
      const returned=document.activeElement===compare&&compare.checkVisibility()&&!panel.inert;
      document.body.dataset.result=JSON.stringify({opened,returned,
        frozen:workspace.getState().result.data===saved,
        modalClosed:!panel.classList.contains('panel-overlay')});
    """.replace('CLOSE_COMPARISON',
        "document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));"
        if close_with_escape else "document.getElementById('close-comparison').click();")),
        reduced_motion=True, viewport=viewport)
    assert actual['opened'] and actual['returned'] and actual['frozen'], actual


def test_doubled_text_and_long_saved_origins_do_not_hide_selected_details():
    actual = _run_browser_script(_table_script("""
      document.documentElement.style.fontSize='200%';
      result.analysis.origins=Array.from({length:20},(_,i)=>({name:'Long saved origin '+i,fias_id:String(i)}));
      result.clusters=[{cluster_id:0,point_count:1,trip_count:40,point_ids:['x']}];
      result.points[0].cluster_id=0;workspace.show();
      document.querySelector('#cluster-list [data-cluster-id]').click();await pause();
      const visible=id=>{const r=document.getElementById(id).getBoundingClientRect(),
        p=document.getElementById('clustering-inspector').getBoundingClientRect(),
        tools=document.querySelector('.inspector-tools').getBoundingClientRect();
        return r.top>=Math.max(p.top,tools.bottom)&&r.bottom<=p.bottom};
      const cluster=visible('cluster-details-close');
      document.querySelector('#cluster-points [data-point-id]').click();await pause();
      document.body.dataset.result=JSON.stringify({cluster,point:visible('point-details-close')});
    """), reduced_motion=True, viewport=(1440,900))
    assert actual['cluster'] and actual['point'], actual


@pytest.mark.parametrize('reason', ['draft', 'critical', 'warnings'])
def test_narrow_result_control_announces_saved_result_attention(reason):
    actions = {
        'draft': "document.querySelector('input[name=\"analysis-mode\"][value=\"geo_cost\"]').click();",
        'critical': "result.status='invalid_connectedness';workspace.show();",
        'warnings': "result.warnings=[{code:'PARTIAL',message:'Partial source'}];workspace.show();",
    }
    actual = _run_browser_script(_table_script(actions[reason] + """
      const button=document.getElementById('mobile-inspector-btn');
      document.body.dataset.result=JSON.stringify({visible:button.checkVisibility(),
        marker:button.textContent.includes('•'),label:button.getAttribute('aria-label')});
    """), reduced_motion=True, viewport=(1093,614))
    assert actual['visible'] and actual['marker'] and 'предупреждения' in actual['label'], actual
