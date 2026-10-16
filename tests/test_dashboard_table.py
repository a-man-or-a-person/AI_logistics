"""Table precision, keyboard/scroll ownership and real OpenLayers membership."""

import re

from test_clustering_frontend_contract import _read, _run_browser_script, _run_node_script
from test_dashboard_layout import _layout_script


def _table_script(actions):
    return _layout_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const result=workspace.getState().result.data;
      const row={cluster_id:0,point_count:5,trip_count:110,trip_share:0.75,
        weighted_route_length:120.05555,price:{min:0,median:2166.525,weighted:3111.116,max:5000},
        rub_per_km:{min:10,median:10.0005,weighted:14.0001,max:30},
        coverage:{route_length:{valid_points:2,total_points:5,valid_trip_count:20,total_trip_count:110},
          price:{valid_points:3,total_points:5,valid_trip_count:30,total_trip_count:110},
          rub_per_km:{valid_points:2,total_points:5,valid_trip_count:20,total_trip_count:110}},
        economic_coverage:{valid_points:2,total_points:5,valid_trip_count:20,total_trip_count:110}};
      result.cluster_table={supported:true,rows:[row],period_types:['current'],
        methodology:{distributions:'unweighted_destination_points',weighted_values:'metric_valid_trip_count'}};
      workspace.getState().ui.tableVisible=true;workspace.getState().ui.tableOpen=true;workspace.show();
    """ + actions)


def test_sort_keeps_keyboard_focus_on_the_replacement_header():
    actual = _run_browser_script(_table_script("""
      const button=document.querySelector('[data-sort-key="price.weighted"]');button.focus();button.click();
      document.body.dataset.result=JSON.stringify({focus:document.activeElement.dataset.sortKey,
        sort:document.querySelector('[data-sort-key="price.weighted"]').closest('th').getAttribute('aria-sort')});
    """), reduced_motion=True)
    assert actual == {'focus': 'price.weighted', 'sort': 'ascending'}


def test_collapse_reopen_keeps_both_local_scroll_offsets():
    actual = _run_browser_script(_table_script("""
      const css=document.createElement('style');
      css.textContent='.cluster-table-scroll{width:220px;height:80px;overflow:auto}.cluster-table-scroll table{min-width:1800px}';
      document.head.append(css);
      result.cluster_table.rows=Array.from({length:20},(_,i)=>({...row,cluster_id:i}));workspace.show();
      const scroll=document.querySelector('.cluster-table-scroll');scroll.scrollLeft=160;scroll.scrollTop=90;
      const before=[scroll.scrollLeft,scroll.scrollTop];
      document.querySelector('[data-table-toggle]').click();document.querySelector('[data-table-toggle]').click();
      const after=document.querySelector('.cluster-table-scroll');
      document.body.dataset.result=JSON.stringify({before,after:[after.scrollLeft,after.scrollTop]});
    """), reduced_motion=True)
    assert actual['before'] == [160, 90]
    assert actual['after'] == actual['before'], actual


def test_identity_stays_visible_in_the_local_horizontal_scroll():
    actual = _run_browser_script(_table_script("""
      const css=document.createElement('style');css.textContent='.cluster-table-scroll{width:400px;overflow:auto}.cluster-table-scroll table{min-width:1800px}';document.head.append(css);
      const scroll=document.querySelector('.cluster-table-scroll');scroll.scrollLeft=300;
      const identity=scroll.querySelector('tbody th'),header=scroll.querySelector('thead th');
      const left=scroll.getBoundingClientRect().left;
      document.body.dataset.result=JSON.stringify({body:getComputedStyle(identity).position,
        header:getComputedStyle(header).position,visible:identity.getBoundingClientRect().left>=left});
    """), reduced_motion=True)
    assert actual == {'body': 'sticky', 'header': 'sticky', 'visible': True}, actual


def test_route_value_help_exposes_raw_precision_unit_and_its_own_coverage():
    actual = _run_browser_script(_table_script("""
      const cell=document.querySelector('tbody tr').children[4],help=cell.querySelector('.cluster-table-help');
      if(help)help.focus();
      const tip=cell.querySelector('.cluster-table-tooltip');
      document.body.dataset.result=JSON.stringify({visible:!!tip?.matches(':popover-open'),text:tip?.textContent||''});
    """), reduced_motion=True)
    assert actual['visible'], actual
    assert '120.05555' in actual['text'] and 'км' in actual['text']
    assert '2/5' in actual['text'] and '20/110' in actual['text'], actual


def test_unsupported_bear_table_explains_the_saved_mode_without_fabricating_rows():
    actual = _run_browser_script(_table_script("""
      result.analysis.mode='bear_zones';result.cluster_table={supported:false};
      workspace.getState().ui.tableVisible=false;workspace.show();
      const panel=document.getElementById('cluster-table-panel');
      document.body.dataset.result=JSON.stringify({visible:panel.checkVisibility(),text:panel.textContent,
        fabricated:!!panel.querySelector('tbody tr')});
    """), reduced_motion=True)
    assert actual['visible'] and not actual['fabricated'], actual
    assert 'Bear' in actual['text'] and 'таблиц' in actual['text'], actual


def test_cluster_zero_map_highlight_and_fit_exclude_unassigned_points():
    map_module = re.sub(r'^import .*?;\n', '', _read('frontend/js/map.js'), flags=re.MULTILINE).replace('export ', '')
    formatters = _read('frontend/js/clustering/formatters.js').replace('export ', '')
    actual = _run_browser_script(f"""
      {_read('frontend/js/ol.js')}
      {formatters}
      {map_module}
      document.body.innerHTML='<div id="map" style="width:800px;height:600px"></div><div id="popup"><div id="popup-content"></div><button id="popup-closer"></button></div>';
      const map=initMap('map');
      renderClusteringPoints({{analysis:{{mode:'geography'}},clusters:[{{cluster_id:0}}],points:[
        {{id:'member',cluster_id:0,lat:55,lon:37}},
        {{id:'outlier',cluster_id:null,lat:60,lon:40,status:'spatial_outlier'}}]}});
      const layer=map.getLayers().getArray().find(l=>l.getSource()?.getFeatures?.().some(f=>f.get('isProductPoint')));
      const features=layer.getSource().getFeatures(),member=features.find(f=>f.get('pointId')==='member'),outlier=features.find(f=>f.get('pointId')==='outlier');
      let fitted;map.getView().fit=extent=>{{fitted=[...extent]}};
      selectMlZone(0,true);
      const radius=feature=>layer.getStyle()(feature).getImage().getRadius();
      const selected=[radius(member),radius(outlier)];selectMlZone(null);hoverCluster(0);
      document.body.dataset.result=JSON.stringify({{selected,hovered:[radius(member),radius(outlier)],
        fitMember:JSON.stringify(fitted)===JSON.stringify(member.getGeometry().getExtent())}});
    """, reduced_motion=True)
    assert actual == {'selected': [7, 5], 'hovered': [7, 5], 'fitMember': True}, actual


def test_all_fourteen_raw_sort_keys_keep_null_last_and_ascending_identity_ties():
    table = re.sub(r'^import .*?;\n', '', _read('frontend/js/clustering/table.js'), flags=re.MULTILINE).replace('export ', '')
    actual = _run_node_script(table + """
      const rows=[0,1,2,3].map(id=>{
        const n=id===3?null:id===0?2.00004:2.00003;
        return {cluster_id:id,point_count:n,trip_count:n,trip_share:n,weighted_route_length:n,
          price:{min:n,median:n,weighted:n,max:n},rub_per_km:{min:n,median:n,weighted:n,max:n},
          economic_coverage:{valid_trip_count:n,total_trip_count:1}};
      });
      const keys=['cluster_id','point_count','trip_count','trip_share','weighted_route_length',
        'price.min','price.median','price.weighted','price.max','rub_per_km.min','rub_per_km.median',
        'rub_per_km.weighted','rub_per_km.max','economic_coverage'];
      console.log(JSON.stringify(Object.fromEntries(keys.map(key=>[key,
        ['asc','desc'].map(direction=>sortedRows(rows,{key,direction}).map(row=>row.cluster_id))]))));
    """)
    assert len(actual) == 14
    for key, orders in actual.items():
        assert orders == ([[0, 1, 2, 3], [3, 2, 1, 0]] if key == 'cluster_id'
                          else [[1, 2, 0, 3], [0, 1, 2, 3]]), (key, orders)


def test_each_metric_help_keeps_its_own_denominator_and_zero_is_not_missing():
    actual = _run_browser_script(_table_script("""
      row.price.min=0;row.price.max=null;workspace.show();
      const cells=[...document.querySelector('tbody tr').children];
      const hints=cells.slice(4).map(cell=>cell.querySelector('.cluster-value-help')?.getAttribute('aria-label'));
      document.body.dataset.result=JSON.stringify({route:hints[0],prices:hints.slice(1,5),
        rates:hints.slice(5,9),economics:hints[9],columns:cells.length});
    """), reduced_motion=True)
    assert actual['columns'] == 14
    assert '2/5' in actual['route'] and '20/110' in actual['route']
    assert all('3/5' in hint and '30/110' in hint for hint in actual['prices'])
    assert all('2/5' in hint and '20/110' in hint for hint in actual['rates'])
    assert '2/5' in actual['economics'] and '20/110' in actual['economics']
    assert '0 ₽' in actual['prices'][0] and 'недоступно' in actual['prices'][3], actual


def test_unknown_coverage_counts_never_manufacture_numeric_zero():
    actual = _run_browser_script(_table_script("""
      row.economic_coverage.valid_points=null;row.economic_coverage.valid_trip_count=null;workspace.show();
      const cell=document.querySelector('tbody tr td:last-child');
      document.body.dataset.result=JSON.stringify({text:cell.innerText,title:cell.title});
    """), reduced_motion=True)
    assert '0,0%' not in actual['text'] and actual['text'].count('—') == 2, actual
    assert '—/5' in actual['title'] and '—/110' in actual['title'], actual


def test_keyboard_toggle_retains_the_reopen_action_focus():
    actual = _run_browser_script(_table_script("""
      const toggle=document.querySelector('[data-table-toggle]');toggle.focus();toggle.click();
      const collapsed=!!document.activeElement.hasAttribute('data-table-toggle');
      document.activeElement.click();
      document.body.dataset.result=JSON.stringify({collapsed,
        open:workspace.getState().ui.tableOpen,focused:document.activeElement.hasAttribute('data-table-toggle')});
    """), reduced_motion=True)
    assert actual == {'collapsed': True, 'open': True, 'focused': True}, actual


def test_keyboard_cluster_activation_keeps_identity_focus_and_selected_zero():
    actual = _run_browser_script(_table_script("""
      result.clusters=[{cluster_id:0,point_ids:['x'],point_count:5,trip_count:110}];workspace.show();
      const identity=document.querySelector('tbody th button');identity.focus();identity.click();
      document.body.dataset.result=JSON.stringify({selected:workspace.getState().ui.selectedCluster,
        focused:document.activeElement.closest('tbody tr')?.dataset.clusterId,
        current:document.activeElement.getAttribute('aria-current'),
        details:document.getElementById('cluster-details').checkVisibility()});
    """), reduced_motion=True)
    assert actual == {'selected': 0, 'focused': '0', 'current': 'true', 'details': True}, actual


def test_value_help_scrolls_into_the_area_clear_of_sticky_identity_and_header():
    actual = _run_browser_script(_table_script("""
      const css=document.createElement('style');css.textContent='.cluster-table-scroll{width:400px;height:100px;flex:none}.cluster-table-scroll table{min-width:1800px}';document.head.append(css);
      const scroll=document.querySelector('.cluster-table-scroll');scroll.scrollLeft=500;
      const help=scroll.querySelector('tbody tr td .cluster-value-help');
      help.scrollIntoView({block:'center',behavior:'instant'});
      const r=help.getBoundingClientRect();
      document.body.dataset.result=JSON.stringify({hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('.cluster-value-help')===help});
    """), reduced_motion=True)
    assert actual['hit'], actual


def test_text_growth_keeps_the_full_table_without_methodology_disclosure():
    actual = _run_browser_script(_table_script("""
      document.documentElement.style.fontSize='200%';
      const panel=document.getElementById('cluster-table-panel'),scroll=panel.querySelector('.cluster-table-scroll');
      document.body.dataset.result=JSON.stringify({removed:!panel.querySelector('.cluster-table-methodology'),
        columns:panel.querySelectorAll('thead th').length,scrollable:getComputedStyle(scroll).overflowX==='auto',
        height:scroll.getBoundingClientRect().height});
    """), reduced_motion=True)
    assert actual['removed'] and actual['columns'] == 14 and actual['scrollable'] and actual['height'] > 0, actual
