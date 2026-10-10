import { clusterLabel, decimal, escapeHtml, fmt, km, MODE_LABELS, PERIOD_LABELS, percent, rubKm } from './formatters.js';

const $ = id => document.getElementById(id);

function metric(label, value, hint = '') {
  return `<div class="metric-row"><span>${label}${hint ? `<button class="help" title="${escapeHtml(hint)}" aria-label="${escapeHtml(hint)}">?</button>` : ''}</span><strong>${value}</strong></div>`;
}

export function renderInspector(state, handlers = {}) {
  const result = state.result.data;
  $('inspector-empty').classList.toggle('hidden', Boolean(result));
  $('inspector-result').classList.toggle('hidden', !result);
  if (!result) return;
  const mode = result.analysis.mode;
  const selected = result.clusters.find(item => Number(item.cluster_id) === Number(state.ui.selectedCluster));
  const selectedPoint = result.points.find(item => item.id === state.ui.selectedPoint);
  const bearModes = ['bear_zones', 'bear_volume_zones'];
  $('result-status').className = `result-state ${result.status}`;
  $('result-status').innerHTML = result.status === 'no_bears'
    ? mode === 'bear_volume_zones'
      ? '<strong>На выбранных данных объёмные медвежьи зоны не обнаружены.</strong><span>Это нормальный результат: ни одна связная зона не превысила заданный порог объёма.</span>'
      : '<strong>На выбранных данных медвежьи зоны не обнаружены.</strong><span>Это нормальный результат: ни одна связная зона не превысила заданный порог.</span>'
    : result.status === 'invalid_connectedness'
      ? '<strong>Результат не прошёл проверку связности</strong><span>Разбиение не может использоваться как итоговое.</span>'
      : '';
  $('result-status').classList.toggle('hidden', result.status === 'success');
  $('result-title').textContent = MODE_LABELS[mode] || mode;
  const chosenK = result.analysis.parameters.n_clusters;
  const zoneType = mode === 'bear_volume_zones' ? 'bear_volume_zone' : 'bear_zone';
  const singletonType = mode === 'bear_volume_zones' ? 'high_volume_singleton' : 'expensive_singleton';
  $('result-subtitle').textContent = bearModes.includes(mode)
    ? `${result.clusters.filter(c => c.cluster_type === zoneType).length} зон · ${result.clusters.filter(c => c.cluster_type === singletonType).length} одиночных точек`
    : `${result.analysis.parameters.k_mode === 'auto' ? `Auto → ${chosenK}` : `K = ${chosenK}`} · ${fmt(result.points.filter(p => p.lat != null).length)} точек`;
  $('result-total-trips').textContent = `${fmt(result.data_quality.trip_count_total)} перевозок`;
  $('result-outliers').textContent = result.outliers?.length ? `Выбросов: ${fmt(result.outliers.length)}` : '';
  $('result-warnings').innerHTML = (result.warnings || []).map(warning => `<p data-warning-code="${escapeHtml(warning.code)}">${escapeHtml(warning.message)}</p>`).join('');
  $('result-warnings').classList.toggle('hidden', !(result.warnings || []).length);
  $('result-context').innerHTML = contextFor(result.analysis);
  $('result-quality').innerHTML = qualityFor(result.data_quality || {});
  $('result-metrics').innerHTML = metricsFor(result);
  $('point-details').classList.toggle('hidden', !selectedPoint);
  if (selectedPoint) {
    const key = handlers.pointRowsKey?.();
    renderPointDetails(
      selectedPoint,
      mode,
      handlers,
      state.ui.pointRows?.get(key),
      result.cluster_table?.supported === true,
      result.analysis.filters?.period_types || [],
    );
  }
  $('cluster-list').innerHTML = result.clusters.map(cluster => `
    <button class="cluster-card ${Number(cluster.cluster_id) === Number(state.ui.selectedCluster) ? 'selected' : ''}" type="button" data-cluster-id="${cluster.cluster_id}">
      <span class="cluster-symbol" data-index="${cluster.cluster_id}">${clusterLabel(cluster, mode)}</span>
      <span>${fmt(cluster.point_count)} точек</span><strong>${fmt(cluster.trip_count)} перевозок</strong>
    </button>`).join('');
  $('cluster-list').classList.toggle('hidden', Boolean(selected));
  $('cluster-details').classList.toggle('hidden', !selected);
  if (selected) renderClusterDetails(result, selected, mode);
  document.querySelectorAll('[data-cluster-id]').forEach(button => {
    button.addEventListener('mouseenter', () => handlers.onClusterHover?.(Number(button.dataset.clusterId)));
    button.addEventListener('mouseleave', () => handlers.onClusterHover?.(null));
    button.addEventListener('click', () => handlers.onClusterSelect?.(Number(button.dataset.clusterId), true));
  });
  document.querySelectorAll('[data-point-id]').forEach(button => {
    button.addEventListener('mouseenter', () => handlers.onPointHover?.(button.dataset.pointId));
    button.addEventListener('focus', () => handlers.onPointHover?.(button.dataset.pointId));
    button.addEventListener('click', () => handlers.onPointSelect?.(button.dataset.pointId));
  });
}

function contextFor(analysis) {
  const filters = analysis.filters || {};
  const periods = (filters.period_types || []).join(', ') || '—';
  const prices = (filters.price_types || []).join(', ') || '—';
  const vehicles = (filters.vehicle_types || []).join(', ') || 'Все';
  const tonnages = (filters.tonnage_ids || []).map(value => `${value} т`).join(', ') || 'Все';
  return `<strong>${escapeHtml(analysis.origin?.name || analysis.origin?.fias_id)} → ${escapeHtml(analysis.destination_region)}</strong>
    <span>Источник: Pulse</span>
    <small>${escapeHtml(periods)} · ${escapeHtml(prices)} · ${escapeHtml(vehicles)} · ${escapeHtml(tonnages)}</small>`;
}

function metricsFor(result) {
  const metrics = result.metrics || {};
  const mode = result.analysis.mode;
  const bearModes = ['bear_zones', 'bear_volume_zones'];
  const rows = [];
  if (!bearModes.includes(mode)) {
    rows.push(metric('Silhouette', decimal(metrics.silhouette ?? metrics.geographic_silhouette, 2)));
    rows.push(metric('Среднее расстояние', km((metrics.mean_distance_to_medoid_m ?? 0) / 1000)));
    rows.push(metric('P95', km((metrics.p95_distance_to_medoid_m ?? 0) / 1000)));
  }
  if (mode === 'geo_cost') {
    rows.unshift(metric('Geo / Cost', `${Math.round(result.analysis.parameters.geography_weight * 100)} / ${Math.round(result.analysis.parameters.economics_weight * 100)}`));
    rows.push(metric('Среднее отклонение ₽/км', rubKm(metrics.within_cluster_weighted_rubkm_mad), 'Стоимость перевозки, делённая на длину маршрута.'));
    rows.push(metric('Региональный уровень', rubKm(result.regional_weighted_rub_per_km)));
  }
  if (mode === 'geo_volume') {
    rows.unshift(metric('Geo / Volume', `${Math.round(result.analysis.parameters.geography_weight * 100)} / ${Math.round(result.analysis.parameters.volume_weight * 100)}`));
    rows.push(metric('Среднее отклонение объёма', `${decimal(metrics.within_cluster_trip_count_mad, 1)} перевозки`));
    rows.push(metric('Разброс средних объёмов', `${decimal(metrics.between_cluster_mean_trip_spread, 1)} перевозки`));
    rows.push(metric('Средний объём региона', `${decimal(result.regional_volume?.mean_trip_count_per_point, 1)} перевозки/точку`));
  }
  if (mode === 'bear_zones') {
    rows.push(metric('Порог зоны', `+${Math.round(result.analysis.parameters.bear_threshold * 100)}%`));
    rows.push(metric('Кандидаты', fmt(metrics.candidate_count)));
    rows.push(metric('Базовый уровень', rubKm(result.regional_weighted_rub_per_km)));
    rows.push(metric('Покрыто точек', fmt(metrics.covered_point_count)));
    rows.push(metric('Покрыто перевозок', fmt(metrics.covered_trip_count)));
  }
  if (mode === 'bear_volume_zones') {
    rows.push(metric('Порог объёмной зоны', `+${Math.round(result.analysis.parameters.volume_threshold * 100)}%`));
    rows.push(metric('Кандидаты', fmt(metrics.candidate_count)));
    rows.push(metric('Средний объём региона', `${decimal(result.regional_volume?.mean_trip_count_per_point, 1)} перевозки/точку`));
    rows.push(metric('Покрыто точек', fmt(metrics.covered_point_count)));
    rows.push(metric('Покрыто перевозок', fmt(metrics.covered_trip_count)));
  }
  const graph = result.graph_metrics || {};
  const advanced = [
    metric('Calinski–Harabasz', decimal(metrics.calinski_harabasz, 1)),
    metric('Davies–Bouldin', decimal(metrics.davies_bouldin, 2)),
    metric('Узлы графа', fmt(graph.node_count)),
    metric('Рёбра графа', fmt(graph.edge_count)),
    metric('Компоненты графа', fmt(graph.graph_component_count)),
    metric('Нарушения связности', fmt(graph.connectivity_violations)),
  ].join('');
  return `${rows.join('')}<details class="advanced-metrics"><summary>Расширенные метрики</summary>${advanced}</details>`;
}

function qualityFor(quality) {
  const resolved = `${fmt(quality.resolved_points)} / ${fmt(quality.destination_points_total)}`;
  const resolvedTrips = `${fmt(quality.trip_count_resolved)} / ${fmt(quality.trip_count_total)}`;
  return `<h4>Качество данных</h4>
    ${metric('Точки с координатами', resolved)}
    ${metric('Покрытие точек', percent((quality.point_coverage_pct || 0) / 100))}
    ${metric('Перевозки с координатами', resolvedTrips)}
    ${metric('Покрытие перевозок', percent((quality.trip_weight_coverage_pct || 0) / 100))}
    ${metric('Экономика доступна', fmt(quality.economic_valid_points))}
    ${quality.excluded_missing_fias ? metric('Исключено без FIAS', fmt(quality.excluded_missing_fias)) : ''}`;
}

function renderClusterDetails(result, cluster, mode) {
  const points = result.points.filter(point => cluster.point_ids.includes(point.id));
  $('cluster-detail-title').textContent = clusterLabel(cluster, mode);
  $('cluster-detail-stats').innerHTML = `
    <div><strong>${fmt(cluster.point_count)}</strong><span>точек</span></div>
    <div><strong>${fmt(cluster.trip_count)}</strong><span>перевозок</span></div>
    ${(cluster.relative_volume_delta ?? cluster.relative_rate_delta) == null ? '' : `<div><strong>${percent(cluster.relative_volume_delta ?? cluster.relative_rate_delta)}</strong><span>к базовому уровню</span></div>`}`;
  $('cluster-detail-metrics').innerHTML = [
    metric('Представитель', escapeHtml(cluster.representative?.name || cluster.medoid_point_id)),
    mode === 'geography' ? metric('Описательный ₽/км', rubKm(cluster.weighted_rub_per_km), 'Показатель не использовался при построении зоны.') : metric('Среднее ₽/км', rubKm(cluster.weighted_rub_per_km)),
    mode === 'geo_cost' ? metric('Средневзвешенная цена', `${decimal(cluster.weighted_price, 0)} ₽`) : '',
    mode === 'geo_cost' ? metric('Региональный ₽/км', rubKm(cluster.regional_weighted_rub_per_km)) : '',
    ['geo_volume', 'bear_volume_zones'].includes(mode) ? metric('Средний объём точки', `${decimal(cluster.mean_trip_count, 1)} перевозки`) : '',
    ['geo_volume', 'bear_volume_zones'].includes(mode) ? metric('Средний объём региона', `${decimal(cluster.regional_mean_trip_count, 1)} перевозки/точку`) : '',
    ['geo_volume', 'bear_volume_zones'].includes(mode) ? metric('Отклонение объёма', percent(cluster.relative_volume_delta)) : '',
    cluster.mean_radius_km == null ? '' : metric('Средний радиус', km(cluster.mean_radius_km)),
    cluster.p95_radius_km == null ? '' : metric('P95 радиус', km(cluster.p95_radius_km)),
    cluster.max_radius_km == null ? '' : metric('Максимальный радиус', km(cluster.max_radius_km)),
    metric('Пространственная связность', cluster.connected === true ? 'Да' : cluster.connected === false ? 'Нет' : '—'),
    cluster.trip_count < 20 ? '<p class="inline-warning">Небольшой объём наблюдений · ' + fmt(cluster.trip_count) + ' перевозок</p>' : '',
  ].join('');
  $('cluster-points').innerHTML = points.map(point => `
    <button type="button" data-point-id="${escapeHtml(point.id)}"><span>${escapeHtml(point.name)}</span><strong>${fmt(point.trip_count)}</strong></button>`).join('');
}

function renderPointDetails(point, mode, handlers, pulse = {}, tableMode = false, periodTypes = []) {
  const statuses = {
    assigned: 'В кластере', normal: 'В кластере', ordinary: 'Обычная точка', bear_candidate: 'Кандидат',
    bear_zone: 'Медвежья зона', expensive_singleton: 'Аномально дорогая точка',
    bear_volume_candidate: 'Кандидат по объёму', bear_volume_zone: 'Объёмная медвежья зона', high_volume_singleton: 'Аномально объёмная точка',
    spatial_outlier: 'Пространственно изолирована', economic_unavailable: 'Нет экономики',
  };
  const economics = !tableMode && mode !== 'bear_zones' ? '' : `
      ${!tableMode && point.weighted_price == null ? '' : `<div><dt>Средневзвешенная цена</dt><dd>${point.weighted_price == null ? '—' : `${decimal(point.weighted_price, 0)} ₽`}</dd></div>`}
      ${!tableMode && point.weighted_rub_per_km == null ? '' : `<div><dt>Средневзвешенный ₽/км</dt><dd>${rubKm(point.weighted_rub_per_km)}</dd></div>`}
      ${!tableMode && point.regional_weighted_rub_per_km == null ? '' : `<div><dt>Региональный ₽/км</dt><dd>${rubKm(point.regional_weighted_rub_per_km)}</dd></div>`}
      ${!tableMode && point.relative_rate_delta == null ? '' : `<div><dt>Отклонение</dt><dd>${percent(point.relative_rate_delta)}</dd></div>`}`;
  const volume = !['geo_volume', 'bear_volume_zones'].includes(mode) ? '' : `
      ${point.regional_mean_trip_count == null ? '' : `<div><dt>Средний объём региона</dt><dd>${decimal(point.regional_mean_trip_count, 1)} перевозки/точку</dd></div>`}
      ${point.relative_volume_delta == null ? '' : `<div><dt>Отклонение объёма</dt><dd>${percent(point.relative_volume_delta)}</dd></div>`}`;
  const pulseRows = (pulse.rows || []).map(row => `<tr>
    <td>${escapeHtml(row.period_id || '—')}</td><td>${escapeHtml(row.period_type || '—')}</td>
    <td>${escapeHtml(row.price_type || '—')}</td><td>${escapeHtml(row.vehicle_type || '—')}</td>
    <td>${escapeHtml(row.tonnage_id || '—')}</td><td>${decimal(row.price, 0)}</td>
    <td>${km(row.route_length)}</td><td>${rubKm(row.rub_per_km)}</td><td>${row.trip_count == null ? '—' : fmt(row.trip_count)}</td>
    <td>${(row.warnings || []).map(escapeHtml).join(', ') || '—'}</td>
  </tr>`).join('');
  const pulseState = pulse.status === 'loading'
    ? '<p class="pulse-state" role="status">Загружаем строки Pulse…</p>'
    : pulse.status === 'stale'
      ? '<p class="pulse-state error" role="alert">Данные Pulse изменились. Пересчитайте результат.</p>'
      : pulse.status === 'error'
        ? `<p class="pulse-state error" role="alert">${escapeHtml(pulse.error || 'Не удалось загрузить строки Pulse.')}</p><button type="button" data-pulse-retry>Повторить</button>`
        : pulse.status === 'success' && !pulseRows
          ? '<p class="pulse-state">Для точки нет строк Pulse в выбранном срезе.</p>'
          : '';
  const pulseDetails = tableMode ? `<details class="pulse-details" ${pulse.open ? 'open' : ''}>
    <summary>Исходные строки Pulse${pulse.total == null ? '' : ` (${fmt(pulse.total)})`}</summary>
    ${pulseState}
    ${pulseRows ? `<div class="pulse-table"><table><thead><tr><th>Период</th><th>Тип периода</th><th>Тип цены</th><th>Транспорт</th><th>Тоннаж</th><th>Цена</th><th>Маршрут</th><th>₽/км</th><th>Машины</th><th>Предупреждения</th></tr></thead><tbody>${pulseRows}</tbody></table></div>` : ''}
    ${pulse.hasMore && pulse.status !== 'loading' ? '<button type="button" data-pulse-more>Показать ещё</button>' : ''}
  </details>` : '';
  $('point-details').innerHTML = `
    <div class="section-row"><h4>Точка назначения</h4><button id="point-details-close" class="back-button" type="button">Закрыть</button></div>
    <h3>${escapeHtml(point.name)}</h3>
    <dl class="point-facts">
      <div><dt>FIAS</dt><dd>${escapeHtml(point.fias_id || point.id)}</dd></div>
      <div><dt>Статус</dt><dd>${escapeHtml(statuses[point.status] || point.status)}</dd></div>
      <div><dt>Кластер</dt><dd>${point.cluster_id == null ? '—' : Number(point.cluster_id) + 1}</dd></div>
      <div><dt>${tableMode ? 'Машины' : 'Перевозки'}</dt><dd>${fmt(point.trip_count)}</dd></div>
      ${tableMode ? `<div><dt>Маршрут</dt><dd>${km(point.weighted_route_length)}</dd></div>` : ''}
      ${tableMode ? `<div><dt>Периоды</dt><dd>${periodTypes.map(value => escapeHtml(value === 'forecast' ? 'Прогноз Pulse' : PERIOD_LABELS[value] || value)).join(', ') || '—'}</dd></div>` : ''}
      ${tableMode && point.data_quality_flags?.length ? `<div><dt>Качество</dt><dd>${point.data_quality_flags.map(escapeHtml).join(', ')}</dd></div>` : ''}
      ${economics}
      ${volume}
    </dl>
    ${pulseDetails}`;
  document.getElementById('point-details-close').addEventListener('click', () => handlers.onPointClear?.());
  document.querySelector('.pulse-details')?.addEventListener('toggle', event => handlers.onPulseToggle?.(event.target.open));
  document.querySelector('[data-pulse-more]')?.addEventListener('click', () => handlers.onPulseMore?.());
  document.querySelector('[data-pulse-retry]')?.addEventListener('click', () => handlers.onPulseRetry?.());
}

export function renderErrorState(error) {
  $('inspector-empty').classList.remove('hidden');
  $('inspector-result').classList.add('hidden');
  const titles = {
    INSUFFICIENT_POINTS: 'Недостаточно точек',
    INSUFFICIENT_ECONOMICS: 'Недостаточно экономических данных',
    NO_DATA: 'По выбранным фильтрам данных нет',
    UNKNOWN_ORIGIN: 'Точка отправления не найдена',
    UNKNOWN_DESTINATION_REGION: 'Регион назначения недоступен',
    INVALID_CLUSTER_COUNT: 'Недопустимое количество кластеров',
    INVALID_MODE_PARAMETERS: 'Недопустимые параметры режима',
  };
  $('inspector-empty').innerHTML = `<strong>${titles[error.code] || 'Не удалось выполнить анализ'}</strong><p>${escapeHtml(error.message)}</p>`;
}
