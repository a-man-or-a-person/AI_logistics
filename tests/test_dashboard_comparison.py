"""Comparison uses aligned frozen metrics, neutral states and modal ownership."""

import json

import pytest
from test_clustering_frontend_contract import _run_browser_script
from test_dashboard_layout import _layout_script


def _comparison_script(actions):
    return _layout_script("""
      await choose('a');const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('compare-modes').focus();document.getElementById('compare-modes').click();await pause();
      const state=workspace.getState();
      for(const [mode,result] of Object.entries(state.comparison.results)){
        result.analysis.parameters={k_mode:'auto',n_clusters:2,geography_weight:.7,
          economics_weight:.3,volume_weight:.3,bear_threshold:.35,volume_threshold:.35};
        result.metrics={p95_distance_to_medoid_m:1000,within_cluster_weighted_rubkm_mad:12.5,
          between_cluster_rate_spread:20,within_cluster_trip_count_mad:3,
          between_cluster_mean_trip_spread:4,candidate_count:2,bear_zone_count:0,
          singleton_count:0,covered_trip_count:0};
        result.data_quality={resolved_points:4,economic_valid_points:2,trip_count_total:110,
          point_coverage_pct:50,trip_weight_coverage_pct:18.1818181818};
        result.status=mode.startsWith('bear')?'no_bears':'success';
      }
      workspace.show();
    """ + actions)


def test_comparison_has_five_aligned_columns_in_wide_local_scroll():
    actual = _run_browser_script(_comparison_script("""
      const table=document.querySelector('#comparison-cards table');
      const head=table?[...table.querySelectorAll('thead th')]:[];
      document.body.dataset.result=JSON.stringify({columns:head.length,
        modeNames:head.slice(1).map(e=>e.textContent),
        wide:table?.getBoundingClientRect().width>=1280,
        local:getComputedStyle(document.getElementById('comparison-cards')).overflowX,
        fullWidth:document.getElementById('comparison-view').getBoundingClientRect().width>innerWidth-50});
    """), reduced_motion=True)
    assert actual['columns'] == 6 and actual['wide'] and actual['local'] == 'auto' and actual['fullWidth'], actual
    assert len(set(actual['modeNames'])) == 5, actual


def test_compare_entry_is_reachable_without_a_selected_inspector():
    actual = _run_browser_script(_layout_script("""
      document.body.dataset.result=JSON.stringify({visible:document.getElementById('compare-modes').checkVisibility()});
    """), reduced_motion=True)
    assert actual == {'visible': True}, actual


@pytest.mark.parametrize('kind', ['missing', 'zero'])
def test_comparison_distinguishes_unavailable_zero_and_not_applicable(kind):
    actual = _run_browser_script(_comparison_script("""
      const result=state.comparison.results.geo_cost;
      result.metrics.p95_distance_to_medoid_m=""" + ('null' if kind == 'missing' else '0') + """;
      result.data_quality.economic_valid_points=""" + ('null' if kind == 'missing' else '0') + """;
      workspace.show();
      const values=key=>[...document.querySelectorAll('[data-comparison-metric="'+key+'"] td')].map(e=>e.textContent);
      document.body.dataset.result=JSON.stringify({p95:values('p95_distance_to_medoid_m'),
        economics:values('economicCoverage'),bear:document.getElementById('comparison-cards').textContent.includes('Зоны не найдены')});
    """), reduced_motion=True)
    assert actual['p95'][1] == ('—' if kind == 'missing' else '0 км'), actual
    assert actual['economics'][1] == ('—' if kind == 'missing' else '0%'), actual
    assert actual['p95'][3] == 'Не применимо' and actual['bear'], actual


def test_comparison_shows_distinct_point_and_machine_populations():
    actual = _run_browser_script(_comparison_script("""
      const row=key=>[...document.querySelectorAll('[data-comparison-metric="'+key+'"] td')].map(e=>e.textContent);
      document.body.dataset.result=JSON.stringify({economics:row('economicCoverage'),
        points:row('point_coverage_pct'),machines:row('trip_weight_coverage_pct')});
    """), reduced_motion=True)
    assert actual['economics'][1] == '50%' and actual['points'][1] == '50%' and actual['machines'][1] == '18,2%', actual


def test_comparison_isolates_background_and_restores_focus_on_escape():
    actual = _run_browser_script(_comparison_script("""
      const background=[...document.querySelectorAll('.topbar,#workspace,#records-modal')].map(e=>e.inert);
      document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
      document.body.dataset.result=JSON.stringify({background,restored:[...document.querySelectorAll('.topbar,#workspace,#records-modal')].every(e=>!e.inert),
        closed:document.getElementById('comparison-view').classList.contains('hidden'),focus:document.activeElement.id});
    """), reduced_motion=True)
    assert all(actual['background']) and actual['restored'] and actual['closed'] and actual['focus'] == 'compare-modes', actual


def test_cached_mode_activation_keeps_its_focus_inside_comparison():
    actual = _run_browser_script(_comparison_script("""
      const tab=document.querySelector('[data-comparison-mode="geography"]');tab.focus();tab.click();await pause();
      document.body.dataset.result=JSON.stringify({mode:document.activeElement.dataset.comparisonMode,
        inside:document.getElementById('comparison-view').contains(document.activeElement)});
    """), reduced_motion=True)
    assert actual == {'mode': 'geography', 'inside': True}, actual


def test_comparison_retains_usable_matrix_at_narrow_double_text_size():
    actual = _run_browser_script(_comparison_script("""
      document.documentElement.style.fontSize='32px';await pause();
      const panel=document.getElementById('comparison-view'),matrix=document.getElementById('comparison-cards');
      document.body.dataset.result=JSON.stringify({height:matrix.clientHeight,
        accessible:panel.scrollHeight<=panel.clientHeight+1||getComputedStyle(panel).overflowY==='auto'});
    """), reduced_motion=True, viewport=(320, 900))
    assert actual['height'] >= 180 and actual['accessible'], actual


@pytest.mark.parametrize('operation', ['run', 'compare'])
@pytest.mark.parametrize('failure', ['network', 'malformed'])
def test_revision_uncertainty_blocks_export_until_a_successful_check(operation, failure):
    actual = _run_browser_script(_layout_script("""
      await choose('a');const region=document.getElementById('cluster-region');region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      const action=document.getElementById(""" + json.dumps('btn-run-clustering' if operation == 'run' else 'compare-modes') + """);
      action.click();await pause();
      const saved=workspace.getState().result.data;
      saved.cluster_table={supported:true,rows:[{cluster_id:0,trip_count:40}]};
      const transport=globalThis.fetch;let malformed=false;
      globalThis.fetch=async(url,init)=>String(url).endsWith('/revision')&&malformed
        ? {ok:true,json:async()=>({ok:true,data_snapshot:saved.data_snapshot,available:[]})}:transport(url,init);
      """ + ('failRevision=true;' if failure == 'network' else 'malformed=true;') + """
      action.click();await pause();
      if(workspace.getState().comparison.open)document.getElementById('close-comparison').click();
      const blocked=document.getElementById('btn-export-clustering').getAttribute('aria-disabled');
      const reason=document.getElementById('export-status').textContent;
      document.getElementById('btn-export-clustering').click();await pause();
      const unsafe=requests.filter(r=>r.path==='export').length;
      failRevision=false;malformed=false;action.click();await pause();
      if(workspace.getState().comparison.open)document.getElementById('close-comparison').click();
      document.getElementById('btn-export-clustering').click();await pause();
      document.body.dataset.result=JSON.stringify({blocked,reason,unsafe,
        same:saved===workspace.getState().result.data,exports:requests.filter(r=>r.path==='export').length});
    """), reduced_motion=True)
    assert actual['blocked'] == 'true' and actual['unsafe'] == 0, actual
    assert 'актуальность' in actual['reason'] and actual['same'] and actual['exports'] == 1, actual
