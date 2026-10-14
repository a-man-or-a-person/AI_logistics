"""Saved summary is visible independently of inspector selection and draft edits."""

import json

import pytest
from test_clustering_frontend_contract import _run_browser_script
from test_dashboard_layout import _layout_script


def test_saved_quality_and_status_are_in_the_center_and_survive_draft_edits():
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const s=workspace.getState(),saved=s.result.data;
      saved.data_quality={resolved_points:2,destination_points_total:4,point_coverage_pct:50,
        trip_count_resolved:20,trip_count_total:110,trip_weight_coverage_pct:18.181818,
        economic_valid_points:1,excluded_missing_fias:0};
      saved.points=[{id:'x',lat:55,trip_count:10},{id:'b',lat:55.01,trip_count:10},
        {id:'c',lat:null,trip_count:40},{id:'d',lat:null,trip_count:50}];
      saved.clusters=[{cluster_id:0,point_count:1,trip_count:10},{cluster_id:1,point_count:1,trip_count:10}];
      saved.metrics={point_coverage_pct:100,mean_distance_to_medoid_m:0,p95_distance_to_medoid_m:0};
      workspace.show();
      const center=document.getElementById('clustering-center');
      const ids=['result-title','result-subtitle','result-total-trips','result-status','result-warnings','result-quality'];
      const snapshot=()=>ids.filter(id=>id!=='result-status').map(id=>document.getElementById(id).textContent).join('|');
      const summary=snapshot();
      document.querySelector('input[name="analysis-mode"][value="geo_volume"]').click();
      document.querySelector('#cluster-periods input[value="retro"]').click();
      document.body.dataset.result=JSON.stringify({center:ids.every(id=>center.contains(document.getElementById(id))),
        qualityVisible:document.getElementById('result-quality').checkVisibility(),
        kept:s.result.data===saved,unchanged:snapshot()===summary,
        quality:document.getElementById('result-quality').textContent,
        trips:document.getElementById('result-total-trips').textContent,
        subtitle:document.getElementById('result-subtitle').textContent});
    """), reduced_motion=True)
    assert actual['center'] and actual['qualityVisible'], actual
    assert actual['kept'] and actual['unchanged']
    assert '2 / 4' in actual['quality'] and '20 / 110' in actual['quality']
    assert '50%' in actual['quality'] and '18%' in actual['quality']
    assert '110' in actual['trips']
    assert 'Кластеры: 2' in actual['subtitle'] and 'Точки с координатами: 2' in actual['subtitle']


def test_summary_missing_counts_percentages_and_distances_do_not_become_zero():
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const result=workspace.getState().result.data;
      result.data_quality={resolved_points:0,destination_points_total:null,point_coverage_pct:null,
        trip_count_resolved:null,trip_count_total:0,trip_weight_coverage_pct:0,
        economic_valid_points:null,excluded_missing_fias:0};
      result.metrics={silhouette:0,mean_distance_to_medoid_m:null,p95_distance_to_medoid_m:0};
      result.graph_metrics={node_count:0,edge_count:null};workspace.show();
      const rows=id=>Object.fromEntries([...document.getElementById(id).querySelectorAll('.metric-row')]
        .map(row=>[row.firstElementChild.firstChild.textContent,row.lastElementChild.textContent]));
      document.body.dataset.result=JSON.stringify({quality:rows('result-quality'),metrics:rows('result-metrics')});
    """), reduced_motion=True)
    assert actual['quality']['Точки с координатами'] == '0 / —', actual
    assert actual['quality']['Покрытие точек'] == '—'
    assert actual['quality']['Машины с координатами'] == '— / 0'
    assert actual['quality']['Покрытие машин'] == '0%'
    assert actual['quality']['Точки с доступной экономикой'] == '— / 0'
    assert actual['quality']['Исключено строк без FIAS'] == '0'
    assert actual['metrics']['Среднее расстояние'] == '—'
    assert actual['metrics']['P95'] == '0 км'
    assert actual['metrics']['Silhouette'] == '0'
    assert actual['metrics']['Узлы графа'] == '0'
    assert actual['metrics']['Рёбра графа'] == '—'


@pytest.mark.parametrize('reason,expected', [
    ('draft','Форма изменена'),('stale','Данные Pulse или координаты изменились'),
    ('unavailable','Сохранённый результат недоступен'),
])
def test_saved_strip_keeps_mode_parameters_and_distinguishes_stale_causes(reason, expected):
    actual = _run_browser_script(_layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.querySelector('input[name="analysis-mode"][value="geo_cost"]').click();
      document.getElementById('btn-run-clustering').click();await pause();
      const s=workspace.getState(),saved=s.result.data;
      Object.assign(saved.analysis.parameters,{{geography_weight:0.7,economics_weight:0.3}});
      if({json.dumps(reason)}==='draft')document.querySelector('input[name="analysis-mode"][value="geo_volume"]').click();
      if({json.dumps(reason)}==='stale')s.rejectedSnapshots.add(saved.data_snapshot);
      if({json.dumps(reason)}==='unavailable')s.unavailableResults.add(saved);
      workspace.show();
      document.body.dataset.result=JSON.stringify({{context:document.getElementById('result-context').textContent,
        status:document.getElementById('result-status').textContent,
        visible:document.getElementById('result-status').checkVisibility(),kept:s.result.data===saved}});
    """), reduced_motion=True)
    assert 'География + стоимость' in actual['context'] and '70%' in actual['context'] and '30%' in actual['context'], actual
    assert expected in actual['status'] and actual['visible'] and actual['kept'], actual


@pytest.mark.parametrize('mode', ['bear_zones','bear_volume_zones'])
@pytest.mark.parametrize('status', ['success','no_bears'])
def test_bear_summary_keeps_candidates_and_covered_populations_visible(mode,status):
    actual = _run_browser_script(_layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.querySelector('input[name="analysis-mode"][value="'+{json.dumps(mode)}+'"]').click();
      document.getElementById('btn-run-clustering').click();await pause();
      const result=workspace.getState().result.data;
      result.status={json.dumps(status)};
      result.metrics={{candidate_count:2,covered_point_count:{2 if status=='success' else 0},
        covered_trip_count:{6 if status=='success' else 0}}};
      result.clusters={('[{cluster_id:0,cluster_type:'+json.dumps('bear_zone' if mode=='bear_zones' else 'bear_volume_zone')+',point_count:2,trip_count:6}]') if status=='success' else '[]'};
      workspace.show();
      document.body.dataset.result=JSON.stringify({{subtitle:document.getElementById('result-subtitle').textContent,
        status:document.getElementById('result-status').textContent,
        visible:document.getElementById('result-subtitle').checkVisibility()}});
    """), reduced_motion=True)
    assert 'Кандидаты: 2' in actual['subtitle'] and actual['visible'], actual
    assert f"Покрыто: {2 if status=='success' else 0} точек / {6 if status=='success' else 0} машин" in actual['subtitle']
    if status == 'no_bears':
        assert 'нормальный результат' in actual['status']


def test_one_analytics_disclosure_exposes_each_technical_metric_and_its_help():
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      document.querySelector('.result-diagnostics').open=true;
      const rows=[...document.getElementById('result-metrics').querySelectorAll('.metric-row')];
      document.body.dataset.result=JSON.stringify({visible:rows.every(row=>row.checkVisibility()),
        help:rows.every(row=>row.querySelector('button.help')?.getAttribute('aria-label')),
        labels:rows.map(row=>row.firstElementChild.firstChild.textContent)});
    """), reduced_motion=True)
    assert actual['visible'] and actual['help'], actual
    assert all(label in actual['labels'] for label in ['Silhouette','P95','Calinski–Harabasz','Davies–Bouldin','Нарушения связности'])


@pytest.mark.parametrize('mode', ['geography','geo_cost','geo_volume','bear_zones','bear_volume_zones'])
def test_missing_saved_parameters_never_render_nan_or_undefined(mode):
    actual = _run_browser_script(_layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.querySelector('input[name="analysis-mode"][value="'+{json.dumps(mode)}+'"]').click();
      document.getElementById('btn-run-clustering').click();await pause();
      const result=workspace.getState().result.data;
      const parameters={{k_mode:'auto',n_clusters:null,geography_weight:null,economics_weight:null,
        volume_weight:null,bear_threshold:null,volume_threshold:null,singleton_threshold:null}};
      result.analysis.parameters=parameters;result.analysis.frozen_request.parameters={{...parameters}};
      workspace.show();document.querySelector('.result-diagnostics').open=true;
      const nodes=['result-context','result-subtitle','result-metrics'];
      document.body.dataset.result=JSON.stringify({{text:nodes.map(id=>document.getElementById(id).textContent).join('|')}});
    """), reduced_motion=True)
    assert 'NaN' not in actual['text'] and 'undefined' not in actual['text'] and 'null' not in actual['text'], actual
    assert '—' in actual['text']


def test_workspace_panel_actions_remain_visible_when_the_summary_requires_center_scroll():
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const center=document.getElementById('clustering-center');
      center.scrollTop=center.scrollHeight;
      const actions=document.querySelector('.workspace-actions').getBoundingClientRect();
      document.body.dataset.result=JSON.stringify({scroll:center.scrollTop,
        visible:actions.top>=56&&actions.bottom<=innerHeight,
        map:getComputedStyle(document.getElementById('clustering-map')).minHeight,
        table:getComputedStyle(document.getElementById('cluster-table-panel')).minHeight});
    """), reduced_motion=True, viewport=(1093,614))
    assert actual['scroll'] > 0 and actual['visible'], actual
    assert actual['map'] == '240px' and actual['table'] == '180px'


def test_unchanged_saved_status_does_not_replace_its_announcement_content():
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const s=workspace.getState();s.rejectedSnapshots.add(s.result.data.data_snapshot);workspace.show();
      const status=document.getElementById('result-status'),paragraph=status.querySelector('p');
      workspace.show();
      const kept=status.querySelector('p')===paragraph;
      s.rejectedSnapshots.clear();s.result.status='error';
      s.result.error={message:`Retry "saved" & user's <input>`};workspace.show();
      const errorParagraph=status.querySelector('p');workspace.show();
      document.body.dataset.result=JSON.stringify({kept,
        quoted:status.querySelector('p')===errorParagraph,escaped:!status.querySelector('input'),
        live:status.getAttribute('role')==='status'&&status.getAttribute('aria-live')==='polite'});
    """), reduced_motion=True)
    assert actual['kept'] and actual['quoted'] and actual['escaped'] and actual['live'], actual


@pytest.mark.parametrize('status', ['success','invalid_connectedness'])
def test_connectivity_and_critical_warnings_stay_visible_above_the_map(status):
    actual = _run_browser_script(_layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const result=workspace.getState().result.data;result.status={json.dumps(status)};
      result.graph_metrics={{connectivity_violations:2}};
      result.warnings=[{{code:'PARTIAL_ECONOMICS',message:'Missing economics <b>must remain text</b>'}}];
      workspace.show();
      const warning=document.getElementById('result-warnings');
      document.body.dataset.result=JSON.stringify({{status:document.getElementById('result-status').textContent,
        statusVisible:document.getElementById('result-status').checkVisibility(),
        warningVisible:warning.checkVisibility(),escaped:!warning.querySelector('b'),
        code:warning.querySelector('p').dataset.warningCode}});
    """), reduced_motion=True)
    assert 'связности' in actual['status'] and 'итоговое' in actual['status'], actual
    assert actual['statusVisible'] and actual['warningVisible'] and actual['escaped']
    assert actual['code'] == 'PARTIAL_ECONOMICS'
