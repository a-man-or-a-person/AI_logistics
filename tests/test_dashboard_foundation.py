"""Rendered Product typography and theme checks at the approved DOM seam."""

import json

import pytest
from test_clustering_frontend_contract import _read, _run_browser_script


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_product_essential_values_and_actions_are_readable(theme):
    actual = _run_browser_script(f"""
      (async () => {{
      document.head.insertAdjacentHTML('beforeend', '<style>' + {json.dumps(_read('frontend/css/style.css'))} + '</style>');
      if ({json.dumps(theme)} === 'dark') document.documentElement.dataset.theme = 'dark';
      document.body.innerHTML = `<main class="workspace mode-cluster">
        <aside class="control-panel"><form id="clustering-controls"><p class="field-hint">Hint</p>
          <button class="primary-button">Calculate</button></form></aside>
        <div class="clustering-center"><section class="cluster-table-panel">
          <table><tbody><tr><th>Cluster 1</th><td>200 ₽</td></tr></tbody></table></section></div>
        <aside class="analysis-inspector"><div class="pulse-table"><table><tbody><tr><td>10 км <small>FIAS</small></td></tr></tbody></table></div></aside>
      </main><div id="toast" class="show toast-error">Error</div>`;
      const style = selector => getComputedStyle(document.querySelector(selector));
      const luminance = color => {{
        const values = color.match(/[\\d.]+/g).slice(0, 3).map(v => Number(v) / 255)
          .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
        return values[0] * .2126 + values[1] * .7152 + values[2] * .0722;
      }};
      const contrast = (a, b) => {{const x=luminance(a), y=luminance(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}};
      const button=style('.primary-button'), hint=style('.field-hint'), toast=style('#toast');
      const before={{rootFont:getComputedStyle(document.documentElement).fontSize,
        table:style('td').fontSize, pulse:style('.pulse-table td').fontSize,
        nested:style('.pulse-table small').fontSize,
        alignment:style('td').textAlign, numbers:style('td').fontVariantNumeric,
        textContrast:contrast(hint.color, style('.control-panel').backgroundColor),
        errorContrast:contrast(toast.color, toast.backgroundColor),
        actionContrast:contrast(button.color, button.backgroundColor)}};
      document.documentElement.style.fontSize='32px';
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      document.body.dataset.result=JSON.stringify({{...before,
        resizedRoot:getComputedStyle(document.documentElement).fontSize,
        resizedTable:style('td').fontSize}});
      }})();
    """)
    assert actual['table'] == actual['pulse'] == '13px'
    assert actual['nested'] == '13px'
    assert actual['alignment'] == 'right'
    assert actual['numbers'] == 'tabular-nums'
    assert actual['textContrast'] >= 4.5
    assert actual['actionContrast'] >= 4.5
    assert actual['errorContrast'] >= 4.5
    assert actual['rootFont'] == '16px'
    assert actual['resizedRoot'] == '32px'
    assert actual['resizedTable'] == '26px'
