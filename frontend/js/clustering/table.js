import { escapeHtml, MODE_LABELS, PERIOD_LABELS } from './formatters.js';

const $ = id => document.getElementById(id);
const nbsp = value => String(value).replace(/\u00a0/g, ' ');
const number = (value, digits = 0) => value == null ? '—' : nbsp(Number(value).toLocaleString('ru-RU', {
  minimumFractionDigits: digits,
  maximumFractionDigits: digits,
}));
const count = value => number(value);
const percent = value => value == null ? '—' : `${number(Number(value) * 100, 1)}%`;
const distance = value => value == null ? '—' : `${number(value, 1)} км`;
const price = value => value == null ? '—' : `${number(value)} ₽`;
const rate = value => value == null ? '—' : `${number(value, 1)} ₽/км`;
const coveragePercent = (valid, total) => valid != null && total ? `${number(valid / total * 100, 1)}%` : '—';

function rawValue(row, key) {
  if (key.startsWith('price.')) return row.price?.[key.slice(6)];
  if (key.startsWith('rub_per_km.')) return row.rub_per_km?.[key.slice(11)];
  if (key === 'economic_coverage') {
    const coverage = row.economic_coverage;
    return coverage?.valid_trip_count != null && coverage.total_trip_count ? coverage.valid_trip_count / coverage.total_trip_count : null;
  }
  return row[key];
}

function sortedRows(rows, sort) {
  return [...rows].sort((left, right) => {
    const a = rawValue(left, sort.key);
    const b = rawValue(right, sort.key);
    if (a == null || b == null) {
      if (a == null && b == null) return Number(left.cluster_id) - Number(right.cluster_id);
      return a == null ? 1 : -1;
    }
    const compared = Number(a) - Number(b);
    return compared ? compared * (sort.direction === 'asc' ? 1 : -1) : Number(left.cluster_id) - Number(right.cluster_id);
  });
}

function header(key, label, hint = '') {
  const help = hint ? `<span class="cluster-table-help" role="note" tabindex="0" aria-label="Формула: ${escapeHtml(label)}" aria-describedby="cluster-formula-${key}">ⓘ<span id="cluster-formula-${key}" class="cluster-table-tooltip" role="tooltip" popover="manual">${escapeHtml(hint)}</span></span>` : '';
  return `<th scope="col"><button type="button" data-sort-key="${key}" aria-label="Сортировать: ${escapeHtml(label)}">${escapeHtml(label)}</button>${help}</th>`;
}

function valueHelp(row, key, display, unit, coverage) {
  const raw = rawValue(row, key);
  const id = `cluster-value-${Number(row.cluster_id)}-${key}`;
  const hint = `Точное значение: ${raw == null ? 'недоступно' : `${raw} ${unit}`}.`
    + (coverage ? ` Покрытие метрики: ${coverage.valid_points ?? '—'}/${coverage.total_points ?? '—'} точек; ${coverage.valid_trip_count ?? '—'}/${coverage.total_trip_count ?? '—'} машин.` : '');
  return `<span class="cluster-table-help cluster-value-help" role="note" tabindex="0" aria-label="${escapeHtml(hint)}" aria-describedby="${id}">${display}<span id="${id}" class="cluster-table-tooltip" role="tooltip" popover="manual">${escapeHtml(hint)}</span></span>`;
}

function cell(row, key, format, unit, metric) {
  return `<td>${valueHelp(row, key, format(rawValue(row, key)), unit, row.coverage?.[metric])}</td>`;
}

function coverageCell(row) {
  const coverage = row.economic_coverage;
  if (!coverage) return '<td>—</td>';
  const points = `${coverage.valid_points ?? '—'}/${coverage.total_points ?? '—'}`;
  const trips = `${coverage.valid_trip_count ?? '—'}/${coverage.total_trip_count ?? '—'}`;
  const priceCoverage = row.coverage?.price;
  const rateCoverage = row.coverage?.rub_per_km;
  const differentMetrics = priceCoverage && rateCoverage
    && (priceCoverage.valid_points !== rateCoverage.valid_points
      || priceCoverage.valid_trip_count !== rateCoverage.valid_trip_count);
  const detail = differentMetrics
    ? `; цена: ${priceCoverage.valid_points ?? '—'}/${priceCoverage.total_points ?? '—'} точек, ${priceCoverage.valid_trip_count ?? '—'}/${priceCoverage.total_trip_count ?? '—'} машин; ₽/км: ${rateCoverage.valid_points ?? '—'}/${rateCoverage.total_points ?? '—'} точек, ${rateCoverage.valid_trip_count ?? '—'}/${rateCoverage.total_trip_count ?? '—'} машин`
    : '';
  const partial = coverage.valid_points < coverage.total_points || coverage.valid_trip_count < coverage.total_trip_count;
  const display = `${coveragePercent(coverage.valid_points, coverage.total_points)} точек · ${coveragePercent(coverage.valid_trip_count, coverage.total_trip_count)} машин`;
  return `<td class="${partial ? 'partial-coverage' : ''}" title="Покрытие: ${points} точек; ${trips} машин${detail}">${valueHelp(row, 'economic_coverage', display, 'доля машин', coverage)}</td>`;
}

function rowHtml(row, selected, hovered) {
  const id = Number(row.cluster_id);
  const classes = [
    selected != null && id === Number(selected) ? 'selected' : '',
    hovered != null && id === Number(hovered) ? 'hovered' : '',
  ].filter(Boolean).join(' ');
  return `<tr data-cluster-id="${id}" class="${classes}">
    <th scope="row"><button type="button" aria-current="${selected != null && id === Number(selected)}" aria-label="Открыть кластер ${id + 1}">Кластер ${id + 1}</button></th>
    ${cell(row, 'point_count', count, 'точек')}${cell(row, 'trip_count', count, 'машин')}${cell(row, 'trip_share', percent, 'доля машин')}
    ${cell(row, 'weighted_route_length', distance, 'км', 'route_length')}
    ${cell(row, 'price.min', price, '₽', 'price')}${cell(row, 'price.median', price, '₽', 'price')}${cell(row, 'price.weighted', price, '₽', 'price')}${cell(row, 'price.max', price, '₽', 'price')}
    ${cell(row, 'rub_per_km.min', rate, '₽/км', 'rub_per_km')}${cell(row, 'rub_per_km.median', rate, '₽/км', 'rub_per_km')}${cell(row, 'rub_per_km.weighted', rate, '₽/км', 'rub_per_km')}${cell(row, 'rub_per_km.max', rate, '₽/км', 'rub_per_km')}
    ${coverageCell(row)}
  </tr>`;
}

function methodologyHtml(result) {
  const facts = result.cluster_table.methodology || {};
  const distribution = facts.distributions === 'unweighted_destination_points'
    ? 'Min, медиана и max рассчитаны по точкам назначения без весов.'
    : 'Распределение рассчитано backend.';
  const weighted = facts.weighted_values === 'metric_valid_trip_count'
    ? 'Средневзвешенные значения учитывают машины только с доступной метрикой.'
    : 'Средневзвешенные значения рассчитаны backend.';
  const mode = result.analysis?.mode;
  const periods = (result.cluster_table.period_types || [])
    .map(value => value === 'forecast' ? 'Прогноз Pulse' : PERIOD_LABELS[value] || value)
    .join(', ') || '—';
  const influence = mode === 'geography'
    ? 'экономика показана описательно и не влияла на разбиение.'
    : mode === 'geo_cost'
      ? 'география и ₽/км влияли на разбиение.'
      : 'география и объём влияли на разбиение.';
  return `<details class="cluster-table-methodology"><summary>Методика расчёта</summary> <p>${distribution} ${weighted} Пропуски не превращаются в нули и отражены в покрытии. Периоды: ${escapeHtml(periods)}. Режим: ${escapeHtml(MODE_LABELS[mode] || mode)} — ${influence}</p></details>`;
}

export function renderClusterTable(state, handlers = {}) {
  const panel = $('cluster-table-panel');
  const scroll = panel.querySelector('.cluster-table-scroll');
  const focusedSort = panel.contains(document.activeElement) ? document.activeElement.dataset.sortKey : null;
  const focusedToggle = panel.contains(document.activeElement) && document.activeElement.hasAttribute('data-table-toggle');
  const focusedCluster = panel.contains(document.activeElement) && document.activeElement.matches('tbody th button')
    ? document.activeElement.closest('tr').dataset.clusterId : null;
  const scrollLeft = scroll?.checkVisibility() ? scroll.scrollLeft : Number(panel.dataset.scrollLeft || 0);
  const scrollTop = scroll?.checkVisibility() ? scroll.scrollTop : Number(panel.dataset.scrollTop || 0);
  panel.dataset.scrollLeft = scrollLeft;
  panel.dataset.scrollTop = scrollTop;
  const result = state.result.data;
  const table = result?.cluster_table;
  const supported = table?.supported === true && state.ui.tableVisible !== false;
  const unsupportedBear = table?.supported === false && ['bear_zones', 'bear_volume_zones'].includes(result?.analysis?.mode);
  panel.classList.toggle('hidden', !supported && !unsupportedBear);
  panel.classList.toggle('unsupported', unsupportedBear);
  panel.setAttribute('aria-busy', String(state.result.status === 'loading'));
  if (!supported) {
    panel.innerHTML = unsupportedBear ? `<p class="cluster-table-state">${escapeHtml(MODE_LABELS[result.analysis.mode])}: обычная таблица из 14 столбцов не поддерживается для Bear-режимов. Зоны, одиночные точки и кандидаты доступны на карте и в детализации.</p>` : '';
    delete panel.dataset.scrollLeft;
    delete panel.dataset.scrollTop;
    panel.classList.remove('collapsed', 'stale');
    return;
  }

  const open = state.ui.tableOpen !== false;
  const stale = handlers.isStale?.() || false;
  panel.classList.toggle('collapsed', !open);
  panel.classList.toggle('stale', stale);
  const sort = state.ui.tableSort || { key: 'trip_count', direction: 'desc' };
  const periods = (table.period_types || []).map(value => `<span class="cluster-table-period">${escapeHtml(value === 'forecast' ? 'Прогноз Pulse' : PERIOD_LABELS[value] || value)}</span>`).join('');
  const rows = Array.isArray(table.rows) ? sortedRows(table.rows, sort) : null;
  panel.innerHTML = `<header class="cluster-table-header"><div><span class="eyebrow">Кластеры результата</span><div class="cluster-table-periods">${periods}</div></div><button type="button" data-table-toggle aria-expanded="${open}">${open ? 'Свернуть таблицу' : 'Открыть таблицу'}</button></header>
    <div class="cluster-table-content ${open ? '' : 'hidden'}">
      ${stale ? '<p class="cluster-table-state">Таблица рассчитана для предыдущих параметров.</p>' : ''}
      ${rows == null ? '<p class="cluster-table-state error">Некорректные данные таблицы.</p>' : rows.length === 0 ? '<p class="cluster-table-state">В результате нет кластеров для таблицы.</p>' : `<div class="cluster-table-scroll"><table><thead><tr>
        ${header('cluster_id', 'Кластер')}${header('point_count', 'Точки')}${header('trip_count', 'Машины', 'Сумма машин в точках кластера.')}${header('trip_share', 'Доля машин', 'Доля машин кластера от всех машин кластеризованного результата.')}
        ${header('weighted_route_length', 'Маршрут', 'Сумма (длина маршрута точки × машины с доступной длиной) / сумма машин с доступной длиной. Пропуски исключены; при отсутствии данных — «—».')}
        ${header('price.min', 'Мин. цена', 'Минимум доступных средневзвешенных цен точек назначения.')}${header('price.median', 'Медианная цена', 'Медиана доступных средневзвешенных цен точек без весов; при чётном числе точек — среднее двух центральных значений.')}${header('price.weighted', 'Ср.-взв. цена', 'Сумма (цена точки × машины с доступной ценой) / сумма машин с доступной ценой. Пропуски исключены; при отсутствии данных — «—».')}${header('price.max', 'Макс. цена', 'Максимум доступных средневзвешенных цен точек назначения.')}
        ${header('rub_per_km.min', 'Мин. ₽/км', 'Минимум доступных средневзвешенных ₽/км точек назначения.')}${header('rub_per_km.median', 'Медианный ₽/км', 'Медиана доступных средневзвешенных ₽/км точек без весов; при чётном числе точек — среднее двух центральных значений.')}${header('rub_per_km.weighted', 'Ср.-взв. ₽/км', 'Сумма (₽/км точки × машины с доступным ₽/км) / сумма машин с доступным ₽/км. В Pulse ₽/км = цена / длина маршрута каждой строки, затем взвешивание по машинам; это не отношение средних цены и длины. Пропуски исключены; при отсутствии данных — «—».')}${header('rub_per_km.max', 'Макс. ₽/км', 'Максимум доступных средневзвешенных ₽/км точек назначения.')}
        ${header('economic_coverage', 'Покрытие экономики', 'Доля точек с доступными ценой и ₽/км от всех точек кластера; доля машин строк с положительными ценой и длиной маршрута от всех машин кластера. Доли показаны в процентах.')}
      </tr></thead><tbody>${rows.map(row => rowHtml(row, state.ui.selectedCluster, state.ui.hoveredCluster)).join('')}</tbody></table></div>`}
      ${methodologyHtml(result)}
    </div>`;

  const hideHelp = () => panel.querySelectorAll('.cluster-table-tooltip:popover-open').forEach(tip => tip.hidePopover());
  panel.querySelectorAll('.cluster-table-help').forEach(help => {
    const tip = help.querySelector('.cluster-table-tooltip');
    const show = () => {
      hideHelp();
      tip.showPopover();
      const anchor = help.getBoundingClientRect();
      const bounds = tip.getBoundingClientRect();
      tip.style.left = `${Math.max(8, Math.min(anchor.left, innerWidth - bounds.width - 8))}px`;
      tip.style.top = `${Math.max(8, anchor.top >= bounds.height + 8 ? anchor.top - bounds.height : Math.min(anchor.bottom, innerHeight - bounds.height - 8))}px`;
    };
    help.addEventListener('mouseenter', show);
    help.addEventListener('click', event => { event.stopPropagation(); show(); });
    help.addEventListener('focus', show);
    help.addEventListener('mouseleave', () => { if (!help.matches(':focus')) tip.hidePopover(); });
    help.addEventListener('blur', () => { if (!help.matches(':hover')) tip.hidePopover(); });
    help.addEventListener('keydown', event => {
      if (event.key === 'Escape') tip.hidePopover();
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); show(); }
    });
  });
  panel.querySelectorAll('.cluster-table-content, .cluster-table-scroll').forEach(container => {
    container.addEventListener('scroll', hideHelp);
  });

  const nextScroll = panel.querySelector('.cluster-table-scroll');
  if (nextScroll) { nextScroll.scrollLeft = scrollLeft; nextScroll.scrollTop = scrollTop; }

  panel.querySelectorAll('[data-sort-key]').forEach(button => {
    const active = button.dataset.sortKey === sort.key;
    button.closest('th').setAttribute('aria-sort', active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none');
    button.addEventListener('click', () => handlers.onSort?.(
      button.dataset.sortKey,
      active && sort.direction === 'asc' ? 'desc' : 'asc',
    ));
  });
  if (focusedSort) [...panel.querySelectorAll('[data-sort-key]')]
    .find(button => button.dataset.sortKey === focusedSort)?.focus({preventScroll: true});
  if (focusedToggle) panel.querySelector('[data-table-toggle]').focus({preventScroll: true});
  panel.querySelector('[data-table-toggle]').addEventListener('click', () => handlers.onToggle?.(!open));
  panel.querySelectorAll('tbody tr').forEach(row => {
    const id = Number(row.dataset.clusterId);
    row.addEventListener('mouseenter', () => handlers.onClusterHover?.(id));
    row.addEventListener('mouseleave', () => handlers.onClusterHover?.(null));
    row.addEventListener('focusin', () => handlers.onClusterHover?.(id));
    row.addEventListener('focusout', () => handlers.onClusterHover?.(null));
    row.addEventListener('click', () => handlers.onClusterSelect?.(id));
  });
  if (focusedCluster != null) [...panel.querySelectorAll('tbody tr')]
    .find(row => row.dataset.clusterId === focusedCluster)?.querySelector('button').focus({preventScroll: true});
}
