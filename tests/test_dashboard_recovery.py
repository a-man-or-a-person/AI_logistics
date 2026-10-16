"""Recovery guards and accessible lifetime at existing Product/LEGACY seams."""

import json
import re

import pytest
from test_clustering_frontend_contract import _read, _run_browser_script
from test_dashboard_inspector import _inspector_script
from test_dashboard_layout import _layout_script


@pytest.mark.parametrize('operation', ['run', 'compare'])
@pytest.mark.parametrize('failure', ['network', 'malformed'])
def test_unknown_revision_blocks_new_detail_and_recovers_without_changing_saved_identity(operation, failure):
    actual = _run_browser_script(_inspector_script("""
      const saved=workspace.getState().result.data, transport=globalThis.fetch;
      let malformed=false;
      globalThis.fetch=async(url,init)=>malformed&&String(url).endsWith('/revision')
        ? {ok:true,json:async()=>({ok:true,data_snapshot:saved.data_snapshot,available:[]})}:transport(url,init);
      const action=document.getElementById(""" + json.dumps('btn-run-clustering' if operation == 'run' else 'compare-modes') + """);
      """ + ('failRevision=true;' if failure == 'network' else 'malformed=true;') + """
      action.click();await pause();
      if(workspace.getState().comparison.open)document.getElementById('close-comparison').click();
      const before=requests.filter(r=>['point-origins','point-rows'].includes(r.path)).length;
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'a',clusterId:0}}));await pause();
      document.querySelector('.pulse-details summary').click();await pause();
      const guarded=requests.filter(r=>['point-origins','point-rows'].includes(r.path)).length===before;
      const notice=document.getElementById('result-status').textContent;
      const same=saved===workspace.getState().result.data;
      failRevision=false;malformed=false;action.click();await pause();
      if(workspace.getState().comparison.open)document.getElementById('close-comparison').click();
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'a',clusterId:0}}));await pause();
      document.querySelector('.pulse-details summary').click();await pause();
      document.body.dataset.result=JSON.stringify({guarded,notice,same,
        recovered:requests.filter(r=>['point-origins','point-rows'].includes(r.path)).length>before,
        uncertain:workspace.getState().revisionUncertain});
    """), reduced_motion=True)
    assert actual['guarded'] and 'актуальность' in actual['notice'], actual
    assert actual['same'] and actual['recovered'] and not actual['uncertain'], actual


@pytest.mark.parametrize('operation', ['run', 'compare'])
def test_pending_revision_blocks_detail_export_and_successfully_recovers(operation):
    actual = _run_browser_script(_inspector_script("""
      const transport=globalThis.fetch;let release;
      globalThis.fetch=async(url,init)=>{
        if(String(url).endsWith('/revision'))await new Promise(resolve=>release=resolve);
        return transport(url,init);
      };
      document.getElementById(""" + json.dumps('btn-run-clustering' if operation == 'run' else 'compare-modes') + """).click();await pause();
      if(workspace.getState().comparison.open)document.getElementById('close-comparison').click();
      const before=requests.length;
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'a',clusterId:0}}));await pause();
      document.querySelector('.pulse-details summary').click();await pause();
      const button=document.getElementById('btn-export-clustering');
      const disabled=button.getAttribute('aria-disabled');button.click();await pause();
      const guarded=requests.slice(before).every(r=>!['point-origins','point-rows','export'].includes(r.path));
      const notice=document.getElementById('result-status').textContent;
      release();await pause();
      if(workspace.getState().comparison.open)document.getElementById('close-comparison').click();
      document.body.dataset.result=JSON.stringify({guarded,disabled,notice,
        recovered:!workspace.getState().revisionPending&&!workspace.getState().revisionUncertain});
    """), reduced_motion=True)
    assert actual['guarded'] and actual['disabled'] == 'true' and 'Проверяем' in actual['notice'], actual
    assert actual['recovered'], actual


def test_failed_revision_blocks_new_cached_origin_activation_without_destroying_cache():
    actual = _run_browser_script(_inspector_script("""
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'a',clusterId:0}}));await pause();
      const transport=globalThis.fetch;
      globalThis.fetch=async(url,init)=>String(url).endsWith('/point-rows')
        ?new Response(JSON.stringify({ok:true,rows:[{source_row_id:'safe-cache',origin_fias:'b',origin_name:'CACHE-SAFE',trip_count:1}],total:1,has_more:false}),{headers:{'Content-Type':'application/json'}})
        :transport(url,init);
      document.querySelector('[data-origin-fias="b"]').click();await pause();
      document.querySelector('[data-point-summary]').click();await pause();
      failRevision=true;document.getElementById('btn-run-clustering').click();await pause();
      document.querySelector('[data-origin-fias="b"]').click();await pause();
      const blocked=workspace.getState().ui.selectedOrigin===null;
      const retained=[...workspace.getState().ui.pointRows.values()].some(d=>d.rows.some(r=>r.source_row_id==='safe-cache'));
      failRevision=false;document.getElementById('btn-run-clustering').click();await pause();
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'a',clusterId:0}}));await pause();
      document.querySelector('[data-origin-fias="b"]').click();await pause();
      document.body.dataset.result=JSON.stringify({blocked,retained,recovered:workspace.getState().ui.selectedOrigin==='b'});
    """), reduced_motion=True)
    assert actual == {'blocked': True, 'retained': True, 'recovered': True}, actual


@pytest.mark.parametrize('exit_action', ['hide', 'pagehide'])
@pytest.mark.parametrize('late', ['success', 'error'])
def test_leaving_product_aborts_detail_and_ignores_late_response(exit_action, late):
    actual = _run_browser_script(_inspector_script("""
      const transport=globalThis.fetch;let release,signal;
      globalThis.fetch=async(url,init)=>{
        const response=await transport(url,init);
        if(String(url).endsWith('/point-origins')&&!release){
          signal=init.signal;await new Promise(resolve=>release=resolve);
          """ + ("return new Response(JSON.stringify({error:'Late old failure'}),{status:500});" if late == 'error' else '') + """
        }
        return response;
      };
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'a',clusterId:0}}));await pause();
      const before=workspace.getState().result.data;
      """ + ('workspace.hide();' if exit_action == 'hide' else "window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));") + """
      const aborted=signal.aborted;release();await pause();
      const detail=[...workspace.getState().ui.pointOrigins.values()][0];
      const suppressed=detail.status==='idle'&&!detail.origins.length&&!detail.error;
      workspace.show();const retry=document.querySelector('[data-origins-retry]');
      if(retry){retry.click();await pause();}
      document.body.dataset.result=JSON.stringify({aborted,suppressed,
        same:workspace.getState().result.data===before,recovered:Boolean(retry)&&detail.status==='success'});
    """), reduced_motion=True)
    assert actual == {'aborted': True, 'suppressed': True, 'same': True, 'recovered': True}, actual


def _records_script(actions):
    source = re.sub(r'^import[\s\S]*?;\n', '', _read('frontend/js/app.js'), flags=re.MULTILINE)
    source = source.split("\nif (document.readyState")[0]
    return _layout_script("""
      function clearMarkers() {}
      function renderPoints() {}
      let openedDataPoint;
      function showDataPoint(point,kind,options){openedDataPoint={point,kind,returned:options.returnFocus.id,inert:document.getElementById('clustering-center').inert};}
      globalThis.getFilters=()=>({fromRegions:['From'],toRegions:['To'],periodTypes:['current'],priceTypes:['spot']});
      globalThis.resetFilters=()=>{};
      const held=[], transport=globalThis.fetch;
      globalThis.fetch=async(url,init)=>{
        if(!String(url).includes('/api/records?'))return transport(url,init);
        return new Promise(resolve=>held.push({resolve,signal:init.signal,url:String(url)}));
      };
      eval(""" + json.dumps('{' + source + '\nstate.clustering=workspace;wireShell();}') + """);
      const open=town=>window.dispatchEvent(new CustomEvent('show-records-modal',{detail:{town,region:'Region',type:'delivery'}}));
      const answer=(index,records,status=200)=>held[index].resolve(new Response(JSON.stringify(
        status===200?{ok:true,records}:{error:'Old request failed'}),{status,headers:{'Content-Type':'application/json'}}));
    """ + actions)


def test_legacy_records_dialog_owns_focus_and_restores_background():
    actual = _run_browser_script(_records_script("""
      const opener=document.querySelector('.mode-tab[data-view="data"]');opener.focus();open('A');await pause();
      const modal=document.getElementById('records-modal'),close=document.getElementById('modal-close');
      const entered=modal.contains(document.activeElement);
      const isolated=document.querySelector('.topbar').inert&&document.getElementById('workspace').inert;
      close.focus();document.dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));
      const wrapped=modal.contains(document.activeElement);
      close.focus();document.dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));
      const table=document.activeElement.classList.contains('table-wrap');
      document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
      document.body.dataset.result=JSON.stringify({entered,isolated,wrapped,table,
        closed:modal.classList.contains('hidden'),focus:document.activeElement===opener,
        restored:!document.querySelector('.topbar').inert&&!document.getElementById('workspace').inert,
        aborted:held[0].signal.aborted});
    """), reduced_motion=True)
    assert actual == dict.fromkeys(('entered', 'isolated', 'wrapped', 'table', 'closed', 'focus', 'restored', 'aborted'), True), actual


@pytest.mark.parametrize('removal', ['close', 'replace'])
@pytest.mark.parametrize('late', ['success', 'error'])
def test_legacy_record_late_response_cannot_revive_or_overwrite_another_town(removal, late):
    actual = _run_browser_script(_records_script("""
      document.getElementById('records-tbody').innerHTML='<tr><td>prior row</td></tr>';
      open('A');await pause();const cleared=!document.getElementById('records-tbody').textContent.includes('prior row');
      """ + ("document.getElementById('modal-close').click();" if removal == 'close' else "open('B');await pause();answer(1,[{price:222,route_length:20,bid_count:2}]);await pause();") + """
      answer(0,[{price:111,route_length:10,bid_count:1}],""" + ('200' if late == 'success' else '500') + """);await pause();
      document.body.dataset.result=JSON.stringify({cleared,aborted:held[0].signal.aborted,
        hidden:document.getElementById('records-modal').classList.contains('hidden'),
        title:document.getElementById('modal-title').textContent,
        text:document.getElementById('records-tbody').textContent,
        error:document.getElementById('modal-error').textContent});
    """), reduced_motion=True)
    assert actual['cleared'] and actual['aborted'], actual
    assert '111' not in actual['text'] and 'Old request failed' not in actual['error'], actual
    assert actual['hidden'] is (removal == 'close'), actual
    if removal == 'replace':
        assert actual['title'] == 'B' and '222' in actual['text'], actual


@pytest.mark.parametrize('outcome', ['empty', 'error'])
def test_legacy_record_loading_and_completion_are_announced(outcome):
    actual = _run_browser_script(_records_script("""
      open('A');await pause();const modal=document.getElementById('records-modal');
      const busy=modal.getAttribute('aria-busy'),loading=document.getElementById('records-tbody').textContent;
      answer(0,[],""" + ('200' if outcome == 'empty' else '500') + """);await pause();
      document.body.dataset.result=JSON.stringify({busy,loading,done:modal.getAttribute('aria-busy'),
        text:document.getElementById('records-tbody').textContent,
        alert:document.getElementById('modal-error').getAttribute('role'),
        error:document.getElementById('modal-error').textContent});
    """), reduced_motion=True)
    assert actual['busy'] == 'true' and 'Загружаем' in actual['loading'] and actual['done'] == 'false', actual
    if outcome == 'empty':
        assert 'Нет записей' in actual['text'], actual
    else:
        assert actual['alert'] == 'alert' and 'Old request failed' in actual['error'], actual


@pytest.mark.parametrize('viewport', [(1440, 900), (1093, 614), (320, 900)])
@pytest.mark.parametrize('root_size', [16, 32])
def test_legacy_record_scroll_region_and_close_stay_in_dialog(viewport, root_size):
    actual = _run_browser_script(_records_script("""
      document.documentElement.style.fontSize=""" + json.dumps(str(root_size) + 'px') + """;
      open('Synthetic Destination 00');await pause();
      answer(0,Array.from({length:64},(_,i)=>({price:i,route_length:100,bid_count:2})));await pause();
      const modal=document.querySelector('.modal-content'),region=modal.querySelector('.table-wrap');
      const m=modal.getBoundingClientRect(),r=region.getBoundingClientRect(),c=document.getElementById('modal-close').getBoundingClientRect();
      document.body.dataset.result=JSON.stringify({inside:r.top>=m.top&&r.bottom<=m.bottom+1,
        local:region.scrollHeight>region.clientHeight&&getComputedStyle(region).overflowY==='auto',
        close:c.top>=0&&c.bottom<=innerHeight&&c.width>=40&&c.height>=40});
    """), reduced_motion=True, viewport=viewport)
    assert actual == {'inside': True, 'local': True, 'close': True}, actual


@pytest.mark.parametrize('viewport', [(1440, 900), (320, 900)])
def test_data_map_keyboard_point_choice_opens_same_typed_point_and_reset_removes_stale_choices(viewport):
    actual = _run_browser_script(_records_script("""
      const entry=document.getElementById('data-point-navigation');
      if(!entry){document.body.dataset.result=JSON.stringify({entry:false});return;}
      const pointTransport=globalThis.fetch;
      globalThis.fetch=async(url,init)=>String(url).includes('/api/points?')
        ?new Response(JSON.stringify({ok:true,shipment_points:[{town:'Same town',region:'R',lat:55,lon:37}],
          delivery_points:[{town:'Same town',region:'R',lat:56,lon:38}],total_ship:1,total_del:1,geocoded:2}),{headers:{'Content-Type':'application/json'}})
        :pointTransport(url,init);
      document.querySelector('[data-view="data"]').click();
      if(innerWidth<1040)document.getElementById('mobile-controls-btn').click();
      document.getElementById('btn-apply').click();await pause();
      const select=document.getElementById('data-point-select');select.value='del:0';
      document.getElementById('open-data-point').click();
      const opened=openedDataPoint;
      const two=select.options.length===2&&select.options[0].textContent!==select.options[1].textContent;
      document.getElementById('btn-reset').click();
      document.body.dataset.result=JSON.stringify({entry:true,two,kind:opened.kind,town:opened.point.town,
        lat:opened.point.lat,returned:opened.returned,inert:opened.inert,reset:entry.classList.contains('hidden')});
    """), reduced_motion=True, viewport=viewport)
    assert actual == {'entry': True, 'two': True, 'kind': 'del', 'town': 'Same town', 'lat': 56,
                      'returned': 'open-data-point' if viewport[0] >= 1040 else 'mobile-controls-btn',
                      'inert': False, 'reset': True}, actual


@pytest.mark.parametrize('root_size', [16, 32])
@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_legacy_popup_essential_text_scales_and_period_labels_have_contrast(root_size, theme):
    source = re.sub(r'^import[\s\S]*?;\n', '', _read('frontend/js/map.js'), flags=re.MULTILINE).replace('export ', '')
    source = '{' + source + "\nglobalThis.fixturePopup=_makePopupContent({town:'Safe town',region:'R',avg_price:1079,rub_per_km:10.5,avg_length:103.2,avg_bids:2,count:64,by_period:{current:{avg_price:1079,rub_per_km:10.5,count:64}}},'del');}"
    actual = _run_browser_script(_layout_script("""
      eval(""" + json.dumps(source) + """);
      document.documentElement.style.fontSize=""" + json.dumps(str(root_size) + 'px') + """;
      document.documentElement.toggleAttribute('data-theme',""" + json.dumps(theme == 'dark') + """);
      const popup=document.getElementById('popup');popup.classList.remove('hidden');
      document.getElementById('popup-content').innerHTML=fixturePopup;await pause();
      const text=[...popup.querySelectorAll('*')].filter(e=>!e.children.length&&/[A-Za-zА-Яа-я0-9]/.test(e.textContent));
      const fonts=text.map(e=>parseFloat(getComputedStyle(e).fontSize));
      const luminance=color=>color.match(/[0-9.]+/g).slice(0,3).map(v=>Number(v)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
      const background=luminance(getComputedStyle(popup).backgroundColor);
      const contrast=[...popup.querySelectorAll('.pd-name span')].map(e=>{const l=luminance(getComputedStyle(e).color);return(Math.max(l,background)+.05)/(Math.min(l,background)+.05)});
      document.body.dataset.result=JSON.stringify({fonts,contrast,text:popup.textContent});
    """), reduced_motion=True)
    assert actual['fonts'] and min(actual['fonts']) >= 13 * root_size / 16, actual
    assert actual['contrast'] and min(actual['contrast']) >= 4.5, actual
    assert '64 зап.' in actual['text'] and '1\u00a0079' in actual['text'], actual


@pytest.mark.parametrize('operation', ['run', 'compare'])
@pytest.mark.parametrize('refresh', [False, True])
@pytest.mark.parametrize('late', ['success', 'error'])
def test_explicit_cancel_keeps_last_display_announces_and_ignores_late_operation(operation, refresh, late):
    actual = _run_browser_script(_layout_script("""
      await choose('a');const region=document.getElementById('cluster-region');region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      """ + ("document.getElementById('btn-run-clustering').click();await pause();workspace.getState().result.cache.clear();" if refresh else '') + """
      const saved=workspace.getState().result.data,transport=globalThis.fetch;let release,signal;
      globalThis.fetch=async(url,init)=>{
        const response=await transport(url,init);
        if(String(url).endsWith(""" + json.dumps('/' + operation) + """)){
          signal=init.signal;await new Promise(resolve=>release=resolve);
          """ + ("return new Response(JSON.stringify({error:'Late cancelled failure'}),{status:500});" if late == 'error' else '') + """
        }
        return response;
      };
      document.getElementById(""" + json.dumps('btn-run-clustering' if operation == 'run' else 'compare-modes') + """).click();await pause();
      const button=document.getElementById(""" + json.dumps('btn-cancel-calculation' if operation == 'run' else 'cancel-comparison') + """);
      if(!button){release();document.body.dataset.result=JSON.stringify({available:false});return;}
      const available=button.checkVisibility();button.click();await pause();release();await pause();
      document.body.dataset.result=JSON.stringify({available,aborted:signal.aborted,
        same:workspace.getState().result.data===saved,
        stopped:workspace.getState().result.status!=='loading'&&workspace.getState().comparison.status!=='loading',
        announced:document.getElementById('calculation-status').textContent.toLowerCase().includes('отмен'),
        focus:document.activeElement.id,error:document.getElementById('analysis-form-error').textContent});
    """), reduced_motion=True)
    assert actual.get('available') is True, actual
    assert actual['aborted'] and actual['same'] and actual['stopped'] and actual['announced'], actual
    assert actual['focus'] == ('btn-run-clustering' if operation == 'run' else 'compare-modes'), actual
    assert 'Late cancelled failure' not in actual['error'], actual


@pytest.mark.parametrize('outcome', ['success', 'error'])
def test_completed_comparison_removes_both_pending_cancel_actions(outcome):
    actual = _run_browser_script(_layout_script("""
      await choose('a');const region=document.getElementById('cluster-region');region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      """ + ('failRun=true;' if outcome == 'error' else '') + """
      document.getElementById('compare-modes').click();await pause();
      document.body.dataset.result=JSON.stringify({finished:workspace.getState().comparison.status,
        footer:document.getElementById('btn-cancel-calculation').classList.contains('hidden'),
        dialog:document.getElementById('cancel-comparison').classList.contains('hidden')});
    """), reduced_motion=True)
    assert actual == {'finished': outcome, 'footer': True, 'dialog': True}, actual


@pytest.mark.parametrize('operation', ['run', 'compare'])
def test_cancelled_pending_revision_stays_uncertain_until_a_successful_check(operation):
    actual = _run_browser_script(_inspector_script("""
      const transport=globalThis.fetch;let release;
      globalThis.fetch=async(url,init)=>{
        const response=await transport(url,init);
        if(String(url).endsWith('/revision'))await new Promise(resolve=>release=resolve);
        return response;
      };
      const action=document.getElementById(""" + json.dumps('btn-run-clustering' if operation == 'run' else 'compare-modes') + """);
      action.click();await pause();
      document.getElementById(""" + json.dumps('btn-cancel-calculation' if operation == 'run' else 'cancel-comparison') + """).click();
      release();await pause();
      const uncertain=workspace.getState().revisionUncertain;
      const blocked=document.getElementById('btn-export-clustering').getAttribute('aria-disabled');
      globalThis.fetch=transport;action.click();await pause();
      document.body.dataset.result=JSON.stringify({uncertain,blocked,recovered:!workspace.getState().revisionPending&&!workspace.getState().revisionUncertain});
    """), reduced_motion=True)
    assert actual == {'uncertain': True, 'blocked': 'true', 'recovered': True}, actual


@pytest.mark.parametrize('coincident', [True, False])
def test_keyboard_data_point_reaches_unseparable_group_count_and_actions(coincident):
    source = re.sub(r'^import .*?;\n', '', _read('frontend/js/map.js'), flags=re.MULTILINE).replace('export ', '')
    actual = _run_browser_script(f"""
      (async()=>{{
      {_read('frontend/js/ol.js')}
      {_read('frontend/js/clustering/formatters.js').replace('export ', '')}
      {source}
      document.body.innerHTML='<div id="map" style="width:800px;height:600px"></div><button id="opener">Open</button><div id="popup"><div id="popup-content"></div><button id="popup-closer"></button></div>';
      const map=initMap('map');
      const points=[{{town:'First',region:'R',lat:55,lon:37,count:3}},
        {{town:'Second',region:'R',lat:55,lon:{37 if coincident else 37.000001},count:4}}];
      renderPoints([],points);map.getView().setZoom(map.getView().getMaxZoom());
      await new Promise(resolve=>setTimeout(resolve,350));map.renderSync();
      let emitted;window.addEventListener('regeocode-all-points',event=>emitted=event.detail.points);
      const opener=document.getElementById('opener');opener.focus();
      showDataPoint(points[0],'del',{{returnFocus:opener}});
      const count=document.querySelectorAll('.cluster-popup-item').length;
      const details=document.querySelectorAll('.popup-btn-details-small').length;
      const all=document.querySelector('.popup-btn-regeocode-all');if(all){{all.focus();all.click();}}
      const focus=document.activeElement.id;
      document.getElementById('popup').dispatchEvent(new KeyboardEvent('keydown',{{key:'Escape',bubbles:true}}));
      document.body.dataset.result=JSON.stringify({{count,details,emitted:emitted||null,focus,returned:document.activeElement===opener}});
      }})().catch(error=>document.body.dataset.result=JSON.stringify({{error:String(error)}}));
    """, reduced_motion=True)
    assert actual == {'count': 2, 'details': 2,
                      'emitted': [{'town': 'First', 'region': 'R'}, {'town': 'Second', 'region': 'R'}],
                      'focus': 'popup-closer', 'returned': True}, actual


@pytest.mark.parametrize('grouped', [True, False])
def test_disabled_popup_regeocode_action_keeps_escape_and_return_focus(grouped):
    source = re.sub(r'^import .*?;\n', '', _read('frontend/js/map.js'), flags=re.MULTILINE).replace('export ', '')
    actual = _run_browser_script(f"""
      (async()=>{{
      {_read('frontend/js/ol.js')}
      {_read('frontend/js/clustering/formatters.js').replace('export ', '')}
      {source}
      document.body.innerHTML='<div id="map" style="width:800px;height:600px"></div><button id="opener">Open</button><div id="popup"><div id="popup-content"></div><button id="popup-closer"></button></div>';
      const map=initMap('map'),point={{town:'First',region:'R',lat:55,lon:37,count:3}};
      renderPoints([],{json.dumps(grouped)}?[point,{{...point,town:'Second'}}]:[point]);
      map.getView().setZoom(map.getView().getMaxZoom());
      await new Promise(resolve=>setTimeout(resolve,350));map.renderSync();
      let emitted;window.addEventListener('regeocode-point',event=>emitted=event.detail);
      const opener=document.getElementById('opener');showDataPoint(point,'del',{{returnFocus:opener}});
      const button=document.querySelector({json.dumps('.popup-btn-regeocode-small[data-town="First"]' if grouped else '.popup-btn-regeocode')});
      button.focus();button.click();const focus=document.activeElement.id;
      document.getElementById('popup').dispatchEvent(new KeyboardEvent('keydown',{{key:'Escape',bubbles:true}}));
      document.body.dataset.result=JSON.stringify({{disabled:button.disabled,emitted,focus,returned:document.activeElement===opener}});
      }})().catch(error=>document.body.dataset.result=JSON.stringify({{error:String(error)}}));
    """, reduced_motion=True)
    assert actual == {'disabled': True, 'emitted': {'town': 'First', 'region': 'R'},
                      'focus': 'popup-closer', 'returned': True}, actual


def test_group_popup_action_names_include_action_type_town_and_region():
    source = re.sub(r'^import .*?;\n', '', _read('frontend/js/map.js'), flags=re.MULTILINE).replace('export ', '')
    actual = _run_browser_script(f"""
      {source}
      document.body.innerHTML='<div id="group"></div>';
      const members=['ship','del'].map(kind=>({{get:key=>key==='kind'?kind:{{town:'Same <&"',region:'R <&"',avg_price:200,count:3}}}}));
      document.getElementById('group').innerHTML=_makeClusterPopupContent(members);
      document.body.dataset.result=JSON.stringify([...document.querySelectorAll('.cluster-popup-item')].map(row=>({{
        regeocode:row.querySelector('.popup-btn-regeocode-small').getAttribute('aria-label'),
        details:row.querySelector('.popup-btn-details-small').getAttribute('aria-label')}})));
    """, reduced_motion=True)
    assert actual == [{'regeocode': f'Пересчитать координаты: {kind} · Same <&" · R <&"',
                       'details': f'Детали: {kind} · Same <&" · R <&"'}
                      for kind in ['Отгрузка', 'Доставка']], actual


def test_legacy_filter_selection_states_and_removed_tag_focus_are_accessible():
    source = _read('frontend/js/filters.js').replace('export ', '')
    actual = _run_browser_script(f"""
      {source}
      document.body.innerHTML=['region-list-ship','region-list-del','tags-ship','tags-del','period-toggles','price-toggles'].map(id=>`<div id="${{id}}"></div>`).join('')+'<input id="search-ship"><input id="search-del">';
      initFilters(['Origin Region'],['Region A']);
      const pressed=()=>[document.querySelector('#region-list-ship button'),document.querySelector('[data-period="current"]'),document.querySelector('[data-ptype="spot"]')].map(b=>b.getAttribute('aria-pressed'));
      const initial=pressed();document.querySelector('#region-list-ship button').click();
      document.querySelector('[data-period="current"]').click();document.querySelector('[data-ptype="spot"]').click();
      const changed=pressed();const remove=document.querySelector('#tags-ship button');remove.focus();remove.click();
      const removedFocus=document.activeElement===document.querySelector('#region-list-ship button');
      resetFilters();document.body.dataset.result=JSON.stringify({{initial,changed,reset:pressed(),removedFocus,
        filters:getFilters()}});
    """, reduced_motion=True)
    assert actual == {'initial': ['false', 'true', 'true'], 'changed': ['true', 'false', 'false'],
                      'reset': ['false', 'true', 'true'], 'removedFocus': True,
                      'filters': {'fromRegions': [], 'toRegions': [],
                                  'periodTypes': ['retro', 'current', 'forecast'],
                                  'priceTypes': ['spot', 'tender']}}, actual


def test_legacy_error_toast_is_an_alert_and_normal_status_returns_to_polite():
    source = re.sub(r'^import[\s\S]*?;\n', '', _read('frontend/js/app.js'), flags=re.MULTILINE)
    source = source.split('\nif (document.readyState')[0]
    actual = _run_browser_script(f"""
      {source}
      document.body.innerHTML='<div id="toast" role="status" aria-live="polite"></div>';
      const notice=document.getElementById('toast');toast('Safe network error','error');
      const error={{role:notice.getAttribute('role'),live:notice.getAttribute('aria-live'),text:notice.textContent}};
      toast('Safe status');clearTimeout(toastTimer);
      document.body.dataset.result=JSON.stringify({{error,normal:{{role:notice.getAttribute('role'),live:notice.getAttribute('aria-live'),text:notice.textContent}}}});
    """, reduced_motion=True)
    assert actual == {'error': {'role': 'alert', 'live': 'assertive', 'text': 'Safe network error'},
                      'normal': {'role': 'status', 'live': 'polite', 'text': 'Safe status'}}, actual
