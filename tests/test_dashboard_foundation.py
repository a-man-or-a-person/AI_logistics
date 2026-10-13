"""Rendered Product typography and theme checks at the approved DOM seam."""

import json

import pytest
from test_clustering_frontend_contract import _product_workspace_script, _read, _run_browser_script


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('reduced_motion', [False, True], ids=['system-motion', 'reduced-motion'])
def test_product_essential_values_and_actions_are_readable(theme, reduced_motion):
    actual = _run_browser_script(f"""
      (async () => {{
      const sheet=document.createElement('style');
      const loaded=new Promise(resolve=>{{sheet.onload=resolve;sheet.onerror=resolve;}});
      sheet.textContent={json.dumps(_read('frontend/css/style.css'))};document.head.append(sheet);
      await loaded;
      if ({json.dumps(theme)} === 'dark') document.documentElement.dataset.theme = 'dark';
      document.body.innerHTML = `<main class="workspace mode-cluster">
        <aside class="control-panel"><form id="clustering-controls"><p class="field-hint">Hint</p>
          <button class="primary-button">Calculate</button></form></aside>
        <div class="clustering-center"><section class="cluster-table-panel">
          <table><tbody><tr><th>Cluster 1</th><td>200 ₽</td></tr></tbody></table></section></div>
        <aside class="analysis-inspector"><div class="pulse-table"><table><tbody><tr><td>10 км <small>FIAS</small></td></tr></tbody></table></div></aside>
      </main><div id="toast" class="show toast-error">Error</div>`;
      document.body.getBoundingClientRect();
      await document.fonts.ready;
      const style = selector => getComputedStyle(document.querySelector(selector));
      const luminance = color => {{
        const values = color.match(/[\\d.]+/g).slice(0, 3).map(v => Number(v) / 255)
          .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
        return values[0] * .2126 + values[1] * .7152 + values[2] * .0722;
      }};
      const contrast = (a, b) => {{const x=luminance(a), y=luminance(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}};
      const button=style('.primary-button'), hint=style('.field-hint'), toast=style('#toast');
      const before={{rootFont:getComputedStyle(document.documentElement).fontSize,
        main:style('main').fontSize, table:style('td').fontSize, pulse:style('.pulse-table td').fontSize,
        nested:style('.pulse-table small').fontSize,
        alignment:style('td').textAlign, numbers:style('td').fontVariantNumeric,
        textContrast:contrast(hint.color, style('.control-panel').backgroundColor),
        errorContrast:contrast(toast.color, toast.backgroundColor),
        actionContrast:contrast(button.color, button.backgroundColor)}};
      document.documentElement.style.fontSize='32px';
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const actual={{...before,
        resizedRoot:getComputedStyle(document.documentElement).fontSize,
        resizedTable:style('td').fontSize,
        resizedMain:style('main').fontSize, resizedPulse:style('.pulse-table td').fontSize,
        resizedNested:style('.pulse-table small').fontSize,
        resizedFontChain:['body','main','table','tbody','tr','td'].map(selector=>[selector,style(selector).fontSize]),
        browser:navigator.userAgent, compat:document.compatMode, fonts:document.fonts.status,
        readyState:document.readyState,
        reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,
        transitions:document.getAnimations().filter(a=>a.constructor.name==='CSSTransition').map(a=>a.transitionProperty)}};
      document.body.dataset.result=JSON.stringify(actual);
      }})();
    """, reduced_motion=reduced_motion)
    if reduced_motion:
        assert actual['reducedMotion'] is True
        assert actual['transitions'] == [], json.dumps(actual)
    assert actual['table'] == actual['pulse'] == '13px'
    assert actual['main'] == '14px'
    assert actual['nested'] == '13px'
    assert actual['alignment'] == 'right'
    assert actual['numbers'] == 'tabular-nums'
    assert actual['textContrast'] >= 4.5
    assert actual['actionContrast'] >= 4.5
    assert actual['errorContrast'] >= 4.5
    assert actual['rootFont'] == '16px'
    assert actual['resizedRoot'] == '32px'
    assert actual['resizedTable'] == '26px', json.dumps(actual)
    assert actual['resizedMain'] == '28px', json.dumps(actual)
    assert actual['resizedPulse'] == actual['resizedNested'] == '26px', json.dumps(actual)


def test_inspector_help_escape_keeps_its_parent_panel_and_saved_result():
    actual = _run_browser_script(_product_workspace_script("""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const saved=workspace.getState().result.data;
      const ui=JSON.stringify(workspace.getState().ui), before=requests.length;
      const panel=document.getElementById('clustering-inspector');
      panel.classList.add('open');
      panel.insertAdjacentHTML('beforeend', '<button class="help" id="escape-help-trigger" type="button" popovertarget="escape-help">?</button><span id="escape-help" class="metric-help-popover" popover>Formula</span>');
      const help=document.getElementById('escape-help-trigger');
      help.focus();document.getElementById('escape-help').showPopover();
      help.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
      document.body.dataset.result=JSON.stringify({panelOpen:panel.classList.contains('open'),
        focus:document.activeElement.id, kept:workspace.getState().result.data===saved,
        uiUnchanged:JSON.stringify(workspace.getState().ui)===ui,noRequests:requests.length===before});
    """))
    assert actual == {'panelOpen': True, 'focus': 'escape-help-trigger', 'kept': True,
                      'uiUnchanged': True, 'noRequests': True}
