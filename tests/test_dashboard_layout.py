"""Rendered workspace layout and panel behavior at the existing controller seam."""

import json
import re

import pytest
from test_clustering_frontend_contract import (
    _product_workspace_script,
    _read,
    _run_browser_script,
    _run_node_script,
)


def _layout_script(actions):
    css = re.sub(r'^@import .+?\n', '', _read('frontend/css/style.css'))
    return _product_workspace_script(f"""
      const sheet=document.createElement('style');
      sheet.textContent={json.dumps(css)};document.head.append(sheet);
      document.body.getBoundingClientRect(); await document.fonts.ready;
      {{ {actions} }}
    """)


@pytest.mark.parametrize("viewport", [(1366, 768), (1440, 900), (1920, 1080), (1093, 614), (1152, 720), (1536, 864)])
def test_calculate_footer_and_saved_context_survive_form_scroll(viewport):
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const form=document.getElementById('clustering-controls');
      const button=document.getElementById('btn-run-clustering');
      const footer=button.closest('.panel-actions');
      const context=document.getElementById('result-context');
      form.scrollTop=form.scrollHeight; await pause();
      const box=button.getBoundingClientRect();
      document.body.dataset.result=JSON.stringify({outside:!form.contains(footer),
        association:button.form===form,oneCalculate:document.querySelectorAll('#btn-run-clustering').length===1,
        visible:box.top>=0&&box.bottom<=innerHeight&&box.height>=40,
        footerHeight:footer.getBoundingClientRect().height,
        contextInCenter:document.getElementById('clustering-center').contains(context),
        contextVisible:context.getBoundingClientRect().height>=64,
        formScrollable:getComputedStyle(form).overflowY==='auto'});
    """), reduced_motion=True, viewport=viewport)
    assert actual['outside'] is True, actual
    assert actual['association'] is True and actual['oneCalculate'] is True
    assert actual['visible'] is True and actual['footerHeight'] >= 72
    assert actual['contextInCenter'] is True and actual['contextVisible'] is True
    assert actual['formScrollable'] is True


def test_overview_has_no_docked_inspector_or_focusable_hidden_controls():
    actual = _run_browser_script(_layout_script("""
      const panel=document.getElementById('clustering-inspector');
      const style=getComputedStyle(panel);
      document.body.dataset.result=JSON.stringify({hidden:style.display==='none'||style.visibility==='hidden',
        usefulWidth:document.getElementById('clustering-center').getBoundingClientRect().width,
        controlsWidth:document.getElementById('sidebar').getBoundingClientRect().width});
    """), reduced_motion=True)
    assert actual['hidden'] is True, actual
    assert actual['usefulWidth'] >= 640
    assert actual['controlsWidth'] == 280


@pytest.mark.parametrize("panel_id,opener_id,viewport", [
    ("clustering-inspector", "mobile-inspector-btn", (1093, 614)),
    ("clustering-inspector", "mobile-inspector-btn", (1600, 1000)),
    ("sidebar", "mobile-controls-btn", (900, 720)),
])
def test_modal_panels_trap_focus_restore_opener_and_preserve_saved_state(panel_id, opener_id, viewport):
    actual = _run_browser_script(_layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const saved=workspace.getState().result.data;
      workspace.getState().ui.tableSort={{key:'point_count',direction:'asc'}};
      const ui=JSON.stringify(workspace.getState().ui), before=requests.length;
      const panel=document.getElementById({json.dumps(panel_id)});
      const opener=document.getElementById({json.dumps(opener_id)});
      opener.focus();opener.click();await pause();
      const entered=panel.contains(document.activeElement);
      const modal=panel.getAttribute('role')==='dialog'&&panel.getAttribute('aria-modal')==='true';
      const visible=panel.getBoundingClientRect().width>0;
      const elements=[...panel.querySelectorAll('button,input,select,textarea,a[href],summary,[tabindex]')]
        .filter(e=>!e.disabled&&e.tabIndex>=0&&e.getClientRects().length);
      elements.at(-1).focus();
      document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{{key:'Tab',bubbles:true,cancelable:true}}));
      const wrapForward=document.activeElement===elements[0];
      document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}}));
      const wrapBack=document.activeElement===elements.at(-1);
      const blocked=document.querySelector('.topbar').inert&&document.getElementById('clustering-center').inert;
      document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{{key:'Escape',bubbles:true}}));
      document.body.dataset.result=JSON.stringify({{entered,modal,visible,wrapForward,wrapBack,blocked,
        closed:!panel.classList.contains('open'),returned:document.activeElement===opener,
        restored:!document.querySelector('.topbar').inert&&!document.getElementById('clustering-center').inert,
        kept:saved===workspace.getState().result.data,ui:JSON.stringify(workspace.getState().ui)===ui,
        noRequests:requests.length===before}});
    """), reduced_motion=True, viewport=viewport)
    assert all(actual.values()), actual


@pytest.mark.parametrize("viewport,docked", [((1366, 768), True), ((1093, 614), False)])
def test_selected_identity_zero_docks_or_opens_without_changing_saved_state(viewport, docked):
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const s=workspace.getState(),saved=s.result.data;
      saved.clusters=[{cluster_id:0,point_count:1,trip_count:40,point_ids:['x']}];
      saved.points[0].cluster_id=0;
      s.ui.selectedCluster=0;s.ui.tableSort={key:'point_count',direction:'asc'};
      workspace.show();await pause();
      const ui=JSON.stringify(s.ui),before=requests.length;
      const panel=document.getElementById('clustering-inspector');
      const initial=panel.getBoundingClientRect().width;
      const opener=document.getElementById('mobile-inspector-btn');
      opener.focus();opener.click();await pause();
      document.body.dataset.result=JSON.stringify({initial,width:panel.getBoundingClientRect().width,
        modal:panel.getAttribute('aria-modal')==='true',label:document.getElementById('selection-context').textContent,
        kept:s.result.data===saved,ui:JSON.stringify(s.ui)===ui,noRequests:requests.length===before,
        center:document.getElementById('clustering-center').getBoundingClientRect().width});
    """), reduced_motion=True, viewport=viewport)
    assert actual['initial'] == (320 if docked else 0), actual
    assert actual['width'] == 320
    assert actual['modal'] is (not docked)
    assert actual['label']
    assert actual['kept'] and actual['ui'] and actual['noRequests']
    assert actual['center'] >= 640


def test_origin_escape_dismisses_options_before_controls_drawer():
    actual = _run_browser_script(_layout_script("""
      const opener=document.getElementById('mobile-controls-btn');
      opener.focus();opener.click();
      const input=document.getElementById('cluster-origin');input.focus();await pause();
      input.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
      const first={options:input.getAttribute('aria-expanded'),panel:document.getElementById('sidebar').classList.contains('open')};
      input.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
      document.body.dataset.result=JSON.stringify({first,closed:!document.getElementById('sidebar').classList.contains('open'),returned:document.activeElement===opener});
    """), reduced_motion=True, viewport=(900,720))
    assert actual == {'first': {'options':'false','panel':True},'closed':True,'returned':True}


def test_leaving_product_closes_its_comparison_and_keeps_cached_results():
    actual = _run_browser_script(_layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('compare-modes').click();await pause();
      const s=workspace.getState(),saved=s.result.data,results=s.comparison.results,cache=s.comparison.cache;
      const before=requests.length;
      const navigation=document.querySelector('.mode-tab[data-view="data"]');navigation.focus();
      workspace.hide();
      document.body.dataset.result=JSON.stringify({closed:!s.comparison.open,
        hidden:document.getElementById('comparison-view').classList.contains('hidden'),
        focus:document.activeElement===navigation,kept:s.result.data===saved,
        results:s.comparison.results===results,cache:s.comparison.cache===cache,noRequests:requests.length===before});
    """), reduced_motion=True, viewport=(1093,614))
    assert all(actual.values()), actual


def test_hidden_dock_returns_focus_even_when_browser_blurs_to_body_first():
    actual = _run_browser_script(_layout_script("""
      const panel=document.getElementById('sidebar');
      const input=document.getElementById('cluster-origin');input.focus();
      panel.style.display='none';
      document.body.getBoundingClientRect();
      window.dispatchEvent(new Event('resize'));
      document.body.dataset.result=JSON.stringify({returned:document.activeElement.id==='mobile-controls-btn'});
    """), reduced_motion=True)
    assert actual == {'returned':True}


def test_data_map_controls_drawer_stacks_heading_and_filters_without_clipping_actions():
    actual = _run_browser_script(_layout_script("""
      workspace.hide();
      const shell=document.getElementById('workspace');
      shell.classList.remove('mode-cluster');shell.classList.add('mode-data');
      document.getElementById('clustering-controls').classList.add('hidden');
      document.getElementById('clustering-actions').classList.add('hidden');
      document.getElementById('data-map-view').classList.remove('hidden');
      document.getElementById('mobile-controls-btn').click();await pause();
      const panel=document.getElementById('sidebar'),view=document.getElementById('data-map-view');
      const heading=panel.querySelector('.panel-heading').getBoundingClientRect();
      const filters=view.getBoundingClientRect();
      panel.scrollTop=panel.scrollHeight;await pause();
      const button=document.getElementById('btn-apply').getBoundingClientRect();
      document.body.dataset.result=JSON.stringify({column:getComputedStyle(panel).flexDirection==='column',
        stacked:filters.top>=heading.bottom,fullWidth:filters.width>=270,
        fullCenter:document.getElementById('clustering-center').getBoundingClientRect().width>=640,
        actionVisible:button.top>=56&&button.bottom<=innerHeight,
        controls:!!document.getElementById('btn-reset')&&!!document.getElementById('region-list-ship')&&!!document.getElementById('region-list-del')});
    """), reduced_motion=True, viewport=(900,720))
    assert all(actual.values()), actual


@pytest.mark.parametrize("root_font", [16,32])
@pytest.mark.parametrize("mode", ['geography','geo_cost','geo_volume','bear_zones','bear_volume_zones'])
def test_parameter_form_reflows_without_horizontal_scrolling(root_font, mode):
    actual = _run_browser_script(_layout_script(f"""
      document.querySelector('input[name="analysis-mode"][value="'+{json.dumps(mode)}+'"]').click();
      document.getElementById('segment-section').open=true;
      document.querySelectorAll('details.multi-select').forEach(element=>{{element.open=true}});
      document.documentElement.style.fontSize={json.dumps(str(root_font)+'px')};
      document.body.getBoundingClientRect();
      const form=document.getElementById('clustering-controls');
      document.body.dataset.result=JSON.stringify({{scroll:form.scrollWidth,client:form.clientWidth}});
    """), reduced_motion=True, viewport=(1440,900))
    assert actual['scroll'] <= actual['client'], actual


@pytest.mark.parametrize("operation", ['run','compare'])
def test_leaving_product_cancels_pending_work_without_publishing_over_another_view(operation):
    actual = _run_browser_script(_layout_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const s=workspace.getState(),saved=s.result.data;
      const originalFetch=globalThis.fetch;
      let release,signal;
      globalThis.fetch=async(url,init)=>{{
        const response=await originalFetch(url,init);
        if(String(url).endsWith('/'+{json.dumps(operation)})){{signal=init.signal;await new Promise(resolve=>release=resolve)}}
        return response;
      }};
      const maps=[];renderClusteringPoints=result=>maps.push(result);
      if({json.dumps(operation)}==='run')document.querySelector('input[name="analysis-mode"][value="geo_cost"]').click();
      document.getElementById({json.dumps('btn-run-clustering' if operation=='run' else 'compare-modes')}).click();await pause();
      const ui=JSON.stringify(s.ui),cacheSize=s.result.cache.size;
      const comparisonCache=s.comparison.cache,comparisonEntries=[...comparisonCache.entries()];
      workspace.hide();release();await pause();
      document.body.dataset.result=JSON.stringify({{aborted:signal.aborted,kept:s.result.data===saved,
        noMap:maps.length===0,ui:JSON.stringify(s.ui)===ui,cache:s.result.cache.size===cacheSize,
        comparisonClosed:!s.comparison.open,
        comparisonCache:s.comparison.cache===comparisonCache&&comparisonCache.size===comparisonEntries.length
          &&comparisonEntries.every(([key,value])=>comparisonCache.get(key)===value)}});
    """), reduced_motion=True, viewport=(1093,614))
    assert all(actual.values()), actual


@pytest.mark.parametrize("ending", ['success','error','replacement','reset','current','retry'])
def test_data_map_request_cannot_publish_after_view_exit_or_reset(ending):
    source = re.sub(r'^import[\s\S]*?;\n', '', _read('frontend/js/app.js'), flags=re.MULTILINE)
    source = source.split('if (document.readyState')[0]
    actual = _run_node_script(f"""
      const nodes=new Map();
      const node=id=>{{if(!nodes.has(id)){{const classes=new Set();nodes.set(id,{{
        textContent:'',className:'',addEventListener(type,fn){{this[type]=fn}},
        querySelector(){{return node(id+'-child')}},classList:{{
          add(...names){{names.forEach(n=>classes.add(n))}},remove(...names){{names.forEach(n=>classes.delete(n))}},
          contains(n){{return classes.has(n)}},toggle(n,on){{on?classes.add(n):classes.delete(n)}}}}
      }})}}return nodes.get(id)}};
      const document={{getElementById:node,querySelectorAll:()=>[]}};
      const window={{dispatchEvent(){{}},addEventListener(){{}}}};
      const getFilters=()=>({{fromRegions:['R'],toRegions:[]}}),resetFilters=()=>{{}};
      const pending=[],maps=[];
      const clearMarkers=()=>{{}},renderPoints=(a,b)=>maps.push([a,b]);
      const fetchPoints=(filters,options)=>new Promise((resolve,reject)=>pending.push({{resolve,reject,signal:options.signal}}));
      {source}
      state.clustering={{show(){{}},hide(){{}}}};
      switchView('data');const first=loadDataMap();
      if({json.dumps(ending)}==='reset'){{wireShell();node('btn-reset').click()}}
      else if(!['current','retry'].includes({json.dumps(ending)}))switchView('clustering');
      if({json.dumps(ending)}==='replacement'){{switchView('data');loadDataMap()}}
      else if(['success','error'].includes({json.dumps(ending)}))setLoading(true,'Product work');
      if(['error','retry'].includes({json.dumps(ending)}))pending[0].reject(new Error('Data Map failure'));
      else pending[0].resolve({{shipment_points:['old'],delivery_points:[],total_ship:1,total_del:0,geocoded:1}});
      await first;
      let retried=true;
      if({json.dumps(ending)}==='retry'){{
        retried=node('toast').className==='show toast-error'&&node('loading-overlay').classList.contains('hidden');
        clearTimeout(toastTimer);node('toast').className='';
        const second=loadDataMap();pending[1].resolve({{shipment_points:['fresh'],delivery_points:[],total_ship:1,total_del:0,geocoded:1}});
        await second;
      }}
      const published=['current','retry'].includes({json.dumps(ending)});
      console.log(JSON.stringify({{aborted:pending[0].signal.aborted,kept:state.lastData===null,
        noMap:maps.length===0,noError:!node('toast').className,
        loading:node('loading-overlay').classList.contains('hidden')===({json.dumps(ending)}==='reset'||published),
        published:!published||(state.lastData.shipment_points[0]===({json.dumps(ending)}==='retry'?'fresh':'old')&&maps.length===1),retried}}));
    """)
    if ending in ['current','retry']:
        assert actual['aborted'] is False and actual['kept'] is False and actual['noMap'] is False, actual
        assert all(actual[key] for key in ['noError','loading','published','retried']), actual
    else:
        assert all(actual.values()), actual
