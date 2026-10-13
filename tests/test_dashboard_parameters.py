"""Parameter disclosure keeps the existing request and selected filters intact."""

import json

import pytest
from test_clustering_frontend_contract import _run_browser_script
from test_dashboard_layout import _layout_script


def test_parameter_sections_reopen_without_changing_request_or_selection():
    actual = _run_browser_script(_layout_script("""
      const sections=[...document.querySelectorAll('#clustering-controls > details.form-section')];
      const initial=sections.map(element=>element.open);
      const segment=sections[1];
      if(segment){
        const before=JSON.stringify(workspace.getState().form),count=requests.length;
        segment.open=true;
        const control=document.querySelector('#cluster-periods input');
        const checked=control.checked;
        segment.open=false;segment.open=true;
        document.body.dataset.result=JSON.stringify({initial,kept:control.checked===checked,
          form:JSON.stringify(workspace.getState().form)===before,noRequests:requests.length===count,
          summary:segment.querySelector('summary').textContent,
          visible:control.getClientRects().length>0});
      }else document.body.dataset.result=JSON.stringify({initial});
    """), reduced_motion=True)
    assert actual['initial'] == [True,False,True], actual
    assert actual['kept'] and actual['form'] and actual['noRequests'] and actual['visible']
    assert 'Текущий' in actual['summary'] and 'Спот' in actual['summary']
    assert 'Все кузова' in actual['summary'] and 'Все тоннажи' in actual['summary']


def test_closed_segment_retains_selected_labels_and_visible_warnings():
    actual = _run_browser_script(_layout_script("""
      const s=workspace.getState();
      Object.assign(s.form,{periodTypes:['current','forecast'],priceTypes:['spot','tender'],
        vehicleTypes:['unknown vehicle'],tonnageIds:['7'],mode:'geo_cost'});
      workspace.show();
      const segment=document.getElementById('segment-section');segment.open=false;
      document.body.dataset.result=JSON.stringify({summary:segment.querySelector('summary').textContent,
        warnings:document.getElementById('form-warnings').textContent,
        visible:document.getElementById('form-warnings').getClientRects().length>0,
        unknown:s.form.vehicleTypes[0]});
    """), reduced_motion=True)
    assert all(label in actual['summary'] for label in ['Текущий','Прогноз','Спот','Тендер','unknown vehicle','7 т'])
    assert 'прогноз' in actual['warnings'] and 'смешением' in actual['warnings']
    assert actual['visible'] and actual['unknown'] == 'unknown vehicle'


def test_api_facet_with_unknown_label_retains_count_selection_and_request():
    actual = _run_browser_script(_layout_script("""
      options.vehicle_types=[{value:'Vendor <unknown>',count:12}];
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      const segment=document.getElementById('segment-section');segment.open=true;
      document.querySelector('details:has(#cluster-vehicles)').open=true;
      const input=document.querySelector('#cluster-vehicles input');input.click();
      const label=input.closest('label').textContent;
      const search=document.querySelector('[data-filter-options="cluster-vehicles"]');
      search.value='missing';search.dispatchEvent(new Event('input',{bubbles:true}));
      segment.open=false;
      document.getElementById('btn-run-clustering').click();await pause();
      const payload=requests.find(request=>request.path==='run')?.payload;
      document.body.dataset.result=JSON.stringify({label,selected:input.checked,
        summary:segment.querySelector('summary').textContent,vehicles:payload?.vehicle_types,
        count:document.getElementById('vehicle-count').textContent});
    """), reduced_motion=True)
    assert 'Vendor <unknown>' in actual['label'] and '12' in actual['label']
    assert actual['selected'] and 'Vendor <unknown>' in actual['summary']
    assert actual['vehicles'] == ['Vendor <unknown>'] and actual['count'] == '1 выбрано'


def test_server_error_remains_visible_after_inline_validation_and_segment_close():
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.querySelectorAll('#cluster-periods input:checked').forEach(input=>input.click());
      document.getElementById('btn-run-clustering').click();await pause();
      document.querySelector('#cluster-periods input[value="current"]').click();
      document.getElementById('segment-section').open=false;failRun=true;
      document.getElementById('btn-run-clustering').click();await pause();
      const error=document.getElementById('analysis-form-error');
      document.body.dataset.result=JSON.stringify({message:error.textContent,
        visible:error.checkVisibility(),outside:!error.closest('details.form-section')});
    """), reduced_motion=True)
    assert 'NO_DATA' in actual['message'] and actual['visible'] and actual['outside'], actual


@pytest.mark.parametrize("mode,control,parameters", [
    ('geography',None,{'k_mode':'manual','n_clusters':3}),
    ('geo_cost','cost-weight',{'k_mode':'manual','n_clusters':3,'geography_weight':0.8,'economics_weight':0.2}),
    ('geo_volume','volume-weight',{'k_mode':'manual','n_clusters':3,'geography_weight':0.8,'volume_weight':0.2}),
    ('bear_zones','bear-threshold',{'bear_threshold':0.25,'singleton_threshold':0.7}),
    ('bear_volume_zones','bear-volume-threshold',{'volume_threshold':0.25,'singleton_threshold':0.7}),
])
def test_all_five_method_controls_submit_their_existing_parameters(mode,control,parameters):
    actual = _run_browser_script(_layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.querySelector('input[name="analysis-mode"][value='+{json.dumps(mode)}+']').click();
      if({json.dumps(control)})document.querySelector('input[name="'+{json.dumps(control)}+'"][value="'+
        ({json.dumps(mode)}.startsWith('bear')?'0.25':'0.2')+'"]').click();
      if(!{json.dumps(mode)}.startsWith('bear')){{
        document.querySelector('input[name="k-mode"][value="manual"]').click();
        const k=document.getElementById('manual-k');k.value='3';k.dispatchEvent(new Event('change',{{bubbles:true}}));
      }}
      document.getElementById('btn-run-clustering').click();await pause();
      const payload=requests.find(request=>request.path==='run')?.payload;
      document.body.dataset.result=JSON.stringify({{mode:payload?.mode,parameters:payload?.parameters,
        origins:payload?.origin_fiases,region:payload?.destination_region}});
    """), reduced_motion=True)
    assert actual == {'mode':mode,'parameters':parameters,'origins':['a'],'region':'R'}


@pytest.mark.parametrize('viewport', [(1440,900),(900,720)])
@pytest.mark.parametrize('filter_id', ['cluster-periods','cluster-prices'])
def test_invalid_closed_segment_opens_and_focuses_the_required_filter(filter_id, viewport):
    actual = _run_browser_script(_layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.querySelectorAll('#'+{json.dumps(filter_id)}+' input:checked').forEach(input=>input.click());
      const segment=document.getElementById('segment-section');segment.open=false;
      const before=requests.filter(request=>request.path==='run').length;
      document.getElementById('btn-run-clustering').click();await pause();
      document.body.dataset.result=JSON.stringify({{open:segment.open,
        focus:document.getElementById({json.dumps(filter_id)}).contains(document.activeElement),
        error:document.getElementById('analysis-form-error').textContent,
        noRun:requests.filter(request=>request.path==='run').length===before}});
    """), reduced_motion=True, viewport=viewport)
    assert actual['open'] and actual['focus'] and actual['error'] and actual['noRun'], actual


def test_invalid_comparison_returns_to_the_required_filter_drawer():
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const s=workspace.getState(),saved=s.result.data,cache=s.result.cache;
      document.querySelectorAll('#cluster-periods input:checked').forEach(input=>input.click());
      document.getElementById('segment-section').open=false;
      document.getElementById('mobile-inspector-btn').click();
      const before=requests.length;
      document.getElementById('compare-modes').click();await pause();
      document.body.dataset.result=JSON.stringify({closed:!s.comparison.open,
        focus:document.getElementById('cluster-periods').contains(document.activeElement),
        drawer:document.getElementById('sidebar').getAttribute('aria-modal')==='true',
        kept:s.result.data===saved&&s.result.cache===cache,noRequests:requests.length===before});
    """), reduced_motion=True, viewport=(900,720))
    assert all(actual.values()), actual


def test_reset_does_not_let_an_old_filter_clear_a_new_validation_error():
    actual = _run_browser_script(_layout_script("""
      async function selectContext(){
        await choose('a');const region=document.getElementById('cluster-region');
        region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      }
      await selectContext();
      document.querySelectorAll('#cluster-periods input:checked').forEach(input=>input.click());
      document.getElementById('btn-run-clustering').click();await pause();
      document.getElementById('btn-reset-clustering').click();await selectContext();
      document.querySelectorAll('#cluster-prices input:checked').forEach(input=>input.click());
      document.getElementById('btn-run-clustering').click();await pause();
      document.querySelector('#cluster-periods input[value="retro"]').click();await pause();
      const error=document.getElementById('analysis-form-error');
      const price=document.querySelector('#cluster-prices input');
      const kept=!error.classList.contains('hidden')&&price.getAttribute('aria-invalid')==='true';
      price.click();await pause();
      document.body.dataset.result=JSON.stringify({kept,cleared:error.classList.contains('hidden')
        &&!price.hasAttribute('aria-invalid'),periodClean:!document.querySelector('#cluster-periods input').hasAttribute('aria-invalid')});
    """), reduced_motion=True)
    assert all(actual.values()), actual
