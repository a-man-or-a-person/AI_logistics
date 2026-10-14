"""Selected-level inspector reads the same frozen canonical row, never a fallback."""

import json

import pytest
from test_clustering_frontend_contract import _run_browser_script
from test_dashboard_layout import _layout_script


def _inspector_script(actions, mode='geo_cost'):
    return _layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.querySelector('.mode-card.mode-'+{json.dumps(mode)}+' input').click();
      document.getElementById('btn-run-clustering').click();await pause();
      const result=workspace.getState().result.data;
      result.points=[{{id:'a',fias_id:'a',name:'A',cluster_id:0,trip_count:100,weighted_price:100,weighted_rub_per_km:10}},
        {{id:'b',fias_id:'b',name:'B',cluster_id:0,trip_count:10,weighted_price:300,weighted_rub_per_km:30}}];
      result.clusters=[{{cluster_id:0,point_ids:['a','b'],point_count:2,trip_count:110,
        weighted_price:118.18181818181819,weighted_rub_per_km:11.818181818181818,
        representative:{{point_id:'a',name:'A'}},connected:true}}];
      const coverage={{valid_points:2,total_points:2,valid_trip_count:20,total_trip_count:110}};
      const canonical={{cluster_id:0,point_count:2,trip_count:110,weighted_route_length:10,
        price:{{weighted:200}},rub_per_km:{{weighted:20}},coverage:{{route_length:coverage,price:coverage,rub_per_km:coverage}}}};
      result.cluster_table={{supported:true,rows:[{{...canonical,cluster_id:9,price:{{weighted:999}}}},canonical]}};
      workspace.getState().ui.selectedCluster=0;workspace.show();
    """ + actions)


@pytest.mark.parametrize('mode', ['geography', 'geo_cost', 'geo_volume'])
def test_ordinary_primary_means_join_the_saved_canonical_row_and_keep_compatibility(mode):
    actual = _run_browser_script(_inspector_script("""
      const primary=document.querySelector('.cluster-primary');
      const values=primary?[...primary.querySelectorAll('.metric-row strong')].map(e=>e.textContent):[];
      const hints=primary?[...primary.querySelectorAll('.help')].map(e=>e.getAttribute('aria-label')):[];
      const diagnostics=document.querySelector('.cluster-diagnostics');if(diagnostics)diagnostics.open=true;
      const frozen=primary?.textContent;
      document.querySelector('input[name="analysis-mode"][value="bear_zones"]').click();
      document.body.dataset.result=JSON.stringify({values,hints,
        compatible:diagnostics?.textContent||'',frozen:document.querySelector('.cluster-primary')?.textContent===frozen,
        selected:workspace.getState().ui.selectedCluster});
    """, mode), reduced_motion=True)
    assert actual['values'] == ['10 км', '200 ₽', '20 ₽/км'], actual
    assert all('20/110' in hint and '2/2' in hint for hint in actual['hints']), actual
    assert 'Совместимый' in actual['compatible'] and '11,8 ₽/км' in actual['compatible']
    assert 'Совместимая цена' in actual['compatible'] and '118 ₽' in actual['compatible'], actual
    assert actual['frozen'] and actual['selected'] == 0


@pytest.mark.parametrize('kind', ['missing_row', 'missing_values', 'zero'])
def test_primary_missing_or_zero_never_falls_back_to_a_legacy_or_other_row(kind):
    actions = {
        'missing_row': 'result.cluster_table.rows=[{...canonical,cluster_id:9}];',
        'missing_values': 'canonical.weighted_route_length=null;canonical.price.weighted=null;canonical.rub_per_km.weighted=null;',
        'zero': 'canonical.weighted_route_length=0;canonical.price.weighted=0;canonical.rub_per_km.weighted=0;',
    }[kind]
    actual = _run_browser_script(_inspector_script(actions + """
      workspace.show();const primary=document.querySelector('.cluster-primary');
      document.body.dataset.result=JSON.stringify({values:primary?[...primary.querySelectorAll('.metric-row strong')].map(e=>e.textContent):[],
        text:primary?.textContent||''});
    """), reduced_motion=True)
    assert actual['values'] == (['0 км', '0 ₽', '0 ₽/км'] if kind == 'zero' else ['—', '—', '—']), actual
    if kind == 'missing_row':
        assert 'недоступ' in actual['text'], actual


def test_point_selection_shows_the_point_level_and_keeps_its_real_parent():
    actual = _run_browser_script(_inspector_script("""
      document.querySelector('[data-point-id="a"]').click();await pause();
      document.body.dataset.result=JSON.stringify({point:document.getElementById('point-details').checkVisibility(),
        cluster:document.getElementById('cluster-details').checkVisibility(),
        list:document.getElementById('cluster-list').checkVisibility(),
        parent:workspace.getState().ui.selectedCluster,selected:workspace.getState().ui.selectedPoint});
    """), reduced_motion=True)
    assert actual == {'point': True, 'cluster': False, 'list': False, 'parent': 0, 'selected': 'a'}, actual


def test_selected_level_precedes_export_and_overview_content():
    actual = _run_browser_script(_inspector_script("""
      const root=document.getElementById('inspector-result');
      document.body.dataset.result=JSON.stringify({first:[...root.children].find(e=>e.checkVisibility())?.id});
    """), reduced_motion=True)
    assert actual == {'first': 'cluster-details'}, actual


def test_unknown_selected_counts_stay_unavailable_and_do_not_invent_a_small_sample():
    actual = _run_browser_script(_inspector_script("""
      result.clusters[0].point_count=null;result.clusters[0].trip_count=null;workspace.show();
      const stats=document.getElementById('cluster-detail-stats').textContent;
      document.querySelector('[data-point-id="a"]').click();await pause();
      result.points[0].trip_count=null;workspace.show();
      const machine=[...document.querySelectorAll('#point-details .point-facts>div')].find(row=>row.querySelector('dt').textContent==='Машины');
      document.body.dataset.result=JSON.stringify({stats,point:machine.querySelector('dd').textContent,
        warning:document.getElementById('cluster-detail-metrics').textContent.includes('Небольшой объём наблюдений')});
    """), reduced_motion=True)
    assert actual['stats'].count('—') == 2 and actual['point'] == '—' and not actual['warning'], actual


def test_unknown_origin_weights_and_source_counts_never_become_zero():
    actual = _run_browser_script(_inspector_script("""
      document.querySelector('[data-point-id="a"]').click();await pause();
      const summary=[...workspace.getState().ui.pointOrigins.values()][0];
      summary.origins[0].source_row_count=null;summary.origins[0].valid_route_length_trip_count=null;
      summary.origins[0].valid_price_trip_count=0;workspace.show();
      document.body.dataset.result=JSON.stringify({text:document.querySelector('.origin-summary').textContent});
    """), reduced_motion=True)
    assert '— строк' in actual['text'] and '— / 40 (—)' in actual['text'], actual
    assert '0 / 40 (0%)' in actual['text'], actual


@pytest.mark.parametrize('level', ['cluster', 'point', 'origin'])
def test_selected_level_reflows_inside_inspector_at_double_text_size(level):
    actual = _run_browser_script(_inspector_script("""
      document.documentElement.style.fontSize='32px';
      const level=""" + json.dumps(level) + """;
      if(level!=='cluster'){document.querySelector('[data-point-id="a"]').click();await pause();}
      if(level==='origin'){document.querySelector('[data-origin-fias="b"]').click();await pause();}
      document.querySelector('.cluster-diagnostics')?.setAttribute('open','');
      const panel=document.getElementById('clustering-inspector');
      document.body.dataset.result=JSON.stringify({width:panel.clientWidth,content:panel.scrollWidth});
    """), reduced_motion=True)
    assert actual['content'] <= actual['width'] + 1, actual


def test_selected_cluster_keeps_connectedness_and_small_sample_warning_visible():
    actual = _run_browser_script(_inspector_script("""
      result.clusters[0].trip_count=19;workspace.show();
      const warning=document.querySelector('#cluster-detail-metrics .inline-warning');
      const connected=[...document.querySelectorAll('#cluster-detail-metrics .metric-row')]
        .find(e=>e.textContent.includes('Пространственная связность'));
      document.body.dataset.result=JSON.stringify({warning:warning?.checkVisibility(),connected:connected?.checkVisibility()});
    """), reduced_motion=True)
    assert actual == {'warning': True, 'connected': True}, actual


def test_point_means_show_their_own_saved_valid_weights_and_missing_coverage():
    actual = _run_browser_script(_inspector_script("""
      Object.assign(result.points[0],{weighted_route_length:12,valid_route_length_trip_count:17,
        valid_price_trip_count:23,valid_rub_per_km_trip_count:29});
      document.querySelector('[data-point-id="a"]').click();await pause();
      const facts=document.querySelector('.point-facts').textContent;
      result.points[0].valid_price_trip_count=null;result.points[0].valid_rub_per_km_trip_count=0;workspace.show();
      document.body.dataset.result=JSON.stringify({facts,missing:document.querySelector('.point-facts').textContent});
    """), reduced_motion=True)
    assert all(value in actual['facts'] for value in ['17 / 100 (17%)', '23 / 100 (23%)', '29 / 100 (29%)']), actual
    assert '— / 100 (—)' in actual['missing'] and '0 / 100 (0%)' in actual['missing'], actual


@pytest.mark.parametrize('mode', ['bear_zones', 'bear_volume_zones'])
def test_bear_point_retains_saved_quality_flags(mode):
    actual = _run_browser_script(_inspector_script("""
      result.cluster_table.supported=false;result.points[0].data_quality_flags=['quality-sentinel'];
      document.querySelector('[data-point-id="a"]').click();await pause();
      document.body.dataset.result=JSON.stringify({quality:document.querySelector('.point-facts').textContent.includes('quality-sentinel')});
    """, mode), reduced_motion=True)
    assert actual == {'quality': True}, actual
