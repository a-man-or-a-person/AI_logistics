import { clusterLabel, decimal, escapeHtml, fmt, km, MODE_LABELS, PERIOD_LABELS, PRICE_LABELS, percent, representativeLabel, rubKm } from './formatters.js';

const $ = id => document.getElementById(id);
let helpId = 0;

function count(value) { return value == null ? '—' : fmt(value); }
function distance(value) { return km(value == null ? null : value / 1000); }
function coverage(valid, total) { return `${count(valid)} / ${count(total)} (${valid != null && total > 0 ? `${decimal(valid / total * 100, 1)}%` : '—'})`; }

function metric(label, value, hint = '') {
  const id = `metric-help-${++helpId}`;
  return `<div class="metric-row"><span>${label}${hint ? `<button type="button" class="help" popovertarget="${id}" aria-label="${escapeHtml(hint)}">?</button><span id="${id}" class="metric-help-popover" popover>${escapeHtml(hint)}</span>` : ''}</span><strong>${value}</strong></div>`;
}

export function renderInspector(state, handlers = {}) {
  const result = state.result.data;
  handlers.onLayout?.();
  $('result-context').classList.toggle('hidden', !result);
  $('inspector-empty').classList.toggle('hidden', Boolean(result));
  $('inspector-result').classList.toggle('hidden', !result);
  if (!result) return;
  const mode = result.analysis.mode;
  const selected = state.ui.selectedCluster == null ? null : result.clusters.find(item => Number(item.cluster_id) === Number(state.ui.selectedCluster));
  const selectedPoint = result.points.find(item => item.id === state.ui.selectedPoint);
  const bearModes = ['bear_zones', 'bear_volume_zones'];
  $('result-status').className = `result-state ${result.status}`;
  const savedStatus = result.status === 'no_bears'
    ? mode === 'bear_volume_zones'
      ? '<strong>На выбранных данных объёмные медвежьи зоны не обнаружены.</strong><span>Это нормальный результат: ни одна связная зона не превысила заданный порог объёма.</span>'
      : '<strong>На выбранных данных медвежьи зоны не обнаружены.</strong><span>Это нормальный результат: ни одна связная зона не превысила заданный порог.</span>'
    : result.status === 'invalid_connectedness'
      ? '<strong>Результат не прошёл проверку связности</strong><span>Разбиение не может использоваться как итоговое.</span>'
      : '';
  const notices = [];
  if (state.unavailableResults?.has(result)) notices.push('Сохранённый результат недоступен. Рассчитайте заново; детализация и XLSX недоступны.');
  else if (state.rejectedSnapshots?.has(result.data_snapshot)) notices.push('Данные Pulse или координаты изменились. Рассчитайте заново; детализация и XLSX недоступны.');
  else if (state.revisionPending) notices.push('Проверяем актуальность данных. Показан сохранённый результат; детализация и XLSX недоступны до завершения проверки.');
  else if (state.revisionUncertain) notices.push('Не удалось проверить актуальность данных. Показан сохранённый результат; детализация и XLSX недоступны до успешной проверки. Повторите расчёт или сравнение.');
  else if (handlers.isStale?.()) notices.push('Форма изменена. Карта, таблица и файл относятся к сохранённому результату.');
  if (result.graph_metrics?.connectivity_violations > 0 && result.status !== 'invalid_connectedness') notices.push(`Нарушения связности: ${count(result.graph_metrics.connectivity_violations)}. Разбиение не может использоваться как итоговое.`);
  if (state.result.status === 'loading') notices.push('Рассчитываем. Показан предыдущий сохранённый результат.');
  if (state.result.status === 'error') notices.push(`Не удалось обновить результат. Показан сохранённый результат. ${state.result.error?.message || ''}`);
  const statusMarkup = savedStatus + notices.map(text => `<p>${escapeHtml(text)}</p>`).join('');
  if ($('result-status').dataset.markup !== statusMarkup) {
    $('result-status').innerHTML = statusMarkup;
    $('result-status').dataset.markup = statusMarkup;
  }
  $('result-status').classList.toggle('hidden', !statusMarkup);
  $('result-title').textContent = MODE_LABELS[mode] || mode;
  const chosenK = result.analysis.parameters.n_clusters;
  const zoneType = mode === 'bear_volume_zones' ? 'bear_volume_zone' : 'bear_zone';
  const singletonType = mode === 'bear_volume_zones' ? 'high_volume_singleton' : 'expensive_singleton';
  $('result-subtitle').textContent = bearModes.includes(mode)
    ? `Зоны: ${result.clusters.filter(c => c.cluster_type === zoneType).length} · Одиночные точки: ${result.clusters.filter(c => c.cluster_type === singletonType).length}`
      + ` · Кандидаты: ${count(result.metrics?.candidate_count)} · Покрыто: ${count(result.metrics?.covered_point_count)} точек / ${count(result.metrics?.covered_trip_count)} машин`
      + (mode === 'bear_zones' ? ` · База: ${rubKm(result.regional_weighted_rub_per_km)}` : ` · База: ${decimal(result.regional_volume?.mean_trip_count_per_point, 1)} машин/точку`)
    : `Кластеры: ${result.clusters.length} · ${result.analysis.parameters.k_mode === 'auto' ? `Auto → ${count(chosenK)}` : `K = ${count(chosenK)}`} · Точки с координатами: ${fmt(result.points.filter(p => p.lat != null).length)}`;
  $('result-total-trips').textContent = `${count(result.data_quality.trip_count_total)} машин`;
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
    <button class="cluster-card ${state.ui.selectedCluster != null && Number(cluster.cluster_id) === Number(state.ui.selectedCluster) ? 'selected' : ''}" type="button" data-cluster-id="${cluster.cluster_id}">
      <span class="cluster-symbol" data-index="${cluster.cluster_id}">${clusterLabel(cluster, mode)}</span>
      <span>${fmt(cluster.point_count)} точек</span><strong>${fmt(cluster.trip_count)} перевозок</strong>
    </button>`).join('');
  $('cluster-list').classList.toggle('hidden', Boolean(selected || selectedPoint));
  $('cluster-details').classList.toggle('hidden', !selected || Boolean(selectedPoint));
  if (selected && !selectedPoint) renderClusterDetails(result, selected, mode);
  document.querySelectorAll('[data-cluster-id]').forEach(button => {
    button.addEventListener('mouseenter', () => handlers.onClusterHover?.(Number(button.dataset.clusterId)));
    button.addEventListener('mouseleave', () => handlers.onClusterHover?.(null));
    button.addEventListener('click', () => handlers.onClusterSelect?.(Number(button.dataset.clusterId), true));
  });
  if (selected && !selectedPoint) document.querySelectorAll('[data-point-id]').forEach(button => {
    button.addEventListener('mouseenter', () => handlers.onPointHover?.(button.dataset.pointId));
    button.addEventListener('focus', () => handlers.onPointHover?.(button.dataset.pointId));
    button.addEventListener('click', () => handlers.onPointSelect?.(button.dataset.pointId));
  });
}

function contextFor(analysis) {
  const request = analysis.frozen_request;
  const filters = request || analysis.filters || {};
  const mode = request?.mode || analysis.mode;
  const parameters = request?.parameters || analysis.parameters || {};
  const periods = (filters.period_types || []).map(value => PERIOD_LABELS[value] || value).join(', ') || '—';
  const prices = (filters.price_types || []).map(value => PRICE_LABELS[value] || value).join(', ') || '—';
  const vehicles = (filters.vehicle_types || []).join(', ') || 'Все';
  const tonnages = (filters.tonnage_ids || []).map(value => `${value} т`).join(', ') || 'Все';
  const origins = analysis.origins || (analysis.origin ? [analysis.origin] : []);
  const zeroMatch = (analysis.origin_coverage || []).filter(origin => origin.zero_match);
  const all = analysis.selection_intent?.all_origins === true;
  const settings = mode === 'bear_zones' || mode === 'bear_volume_zones'
    ? `Порог ${percent(mode === 'bear_zones' ? parameters.bear_threshold : parameters.volume_threshold)} · Одиночные ${percent(parameters.singleton_threshold)}`
    : `${parameters.k_mode === 'auto' ? `Auto K → ${count(analysis.parameters?.n_clusters)}` : `K = ${count(parameters.n_clusters)}`}`
      + (mode === 'geo_cost' ? ` · География ${percent(parameters.geography_weight)} / Стоимость ${percent(parameters.economics_weight)}`
        : mode === 'geo_volume' ? ` · География ${percent(parameters.geography_weight)} / Объём ${percent(parameters.volume_weight)}` : '');
  return `<strong>${all ? 'Все отправления' : escapeHtml(origins.map(origin => origin.name || origin.fias_id).join(', '))} → ${escapeHtml(analysis.destination_region)}</strong>
    ${all ? `<details><summary>Сохранённые отправления: ${origins.length}</summary>${origins.map(origin => `<small>${escapeHtml(origin.name || origin.fias_id)} · ${escapeHtml(origin.fias_id)}</small>`).join('')}</details>` : ''}
    <span>Источник: Pulse</span>
    <small>${escapeHtml(MODE_LABELS[mode] || mode)} · ${escapeHtml(settings)}</small>
    ${zeroMatch.length ? `<small>Без строк по выбранным фильтрам: ${escapeHtml(zeroMatch.map(item => origins.find(origin => origin.fias_id === item.fias_id)?.name || item.fias_id).join(', '))}</small>` : ''}
    <small>${escapeHtml(periods)} · ${escapeHtml(prices)} · ${escapeHtml(vehicles)} · ${escapeHtml(tonnages)}</small>`;
}

function metricsFor(result) {
  const metrics = result.metrics || {};
  const mode = result.analysis.mode;
  const bearModes = ['bear_zones', 'bear_volume_zones'];
  const rows = [];
  if (!bearModes.includes(mode)) {
    rows.push(metric('Silhouette', decimal(metrics.silhouette ?? metrics.geographic_silhouette, 2), 'Среднее (b − a) / max(a, b) по назначенным точкам: a — среднее расстояние внутри кластера, b — до ближайшего другого кластера. Одиночная точка даёт 0. Сохранённые признаки оценки алгоритма, при географической оценке — координаты; без веса машин. — при недостаточном числе кластеров или точек.'));
    rows.push(metric('Среднее расстояние', distance(metrics.mean_distance_to_medoid_m), 'Невзвешенное среднее расстояний назначенных точек до medoid своего кластера в проекции; сохранённые метры показаны в километрах.'));
    rows.push(metric('P95', distance(metrics.p95_distance_to_medoid_m), '95-й перцентиль тех же невзвешенных расстояний до medoid; линейная интерполяция позиции (n − 1) × 0,95, метры переведены в километры.'));
  }
  if (mode === 'geo_cost') {
    rows.unshift(metric('Geo / Cost', `${percent(result.analysis.parameters.geography_weight)} / ${percent(result.analysis.parameters.economics_weight)}`, 'Сохранённые доли географического и экономического признаков из параметров расчёта.'));
    rows.push(metric('Среднее отклонение ₽/км', rubKm(metrics.within_cluster_weighted_rubkm_mad), 'Алгоритмическая диагностика: внутри кластера среднее |ставка точки − ставка кластера| с весами всех машин точек; затем среднее отклонений с весами машин кластеров. Это прежняя методика, не среднее канонической таблицы.'));
    rows.push(metric('Разброс средних ставок', rubKm(metrics.between_cluster_rate_spread), 'Максимум минус минимум сохранённых алгоритмических средних ставок кластеров, ₽/км. Не отношение средних цены и маршрута.'));
    rows.push(metric('Региональный уровень', rubKm(result.regional_weighted_rub_per_km), 'Прежний алгоритмический ориентир: среднее доступных ставок точек с весами всех машин точки в популяции режима. Не каноническое среднее с валидными весами метрики.'));
  }
  if (mode === 'geo_volume') {
    rows.unshift(metric('Geo / Volume', `${percent(result.analysis.parameters.geography_weight)} / ${percent(result.analysis.parameters.volume_weight)}`, 'Сохранённые доли географического и объёмного признаков из параметров расчёта.'));
    rows.push(metric('Среднее отклонение объёма', `${decimal(metrics.within_cluster_trip_count_mad, 1)} перевозки`, 'Невзвешенное среднее |машины точки − среднее число машин на точку её кластера| по назначенным точкам.'));
    rows.push(metric('Разброс средних объёмов', `${decimal(metrics.between_cluster_mean_trip_spread, 1)} перевозки`, 'Максимум минус минимум сохранённых средних машин на точку кластеров.'));
    rows.push(metric('Средний объём региона', `${decimal(result.regional_volume?.mean_trip_count_per_point, 1)} перевозки/точку`, 'Сумма машин популяции режима, делённая на число её точек; невзвешенное среднее объёма точки.'));
  }
  if (mode === 'bear_zones') {
    rows.push(metric('Порог зоны', result.analysis.parameters.bear_threshold == null ? '—' : `+${percent(result.analysis.parameters.bear_threshold)}`, 'Сохранённый порог превышения ставки точки над региональным ориентиром; правило одиночной точки задаётся отдельно каталогом.'));
    rows.push(metric('Кандидаты', count(metrics.candidate_count), 'Число точек, прошедших порог кандидата Bear Cost; кандидат не обязательно вошёл в зону или одиночный результат.'));
    rows.push(metric('Базовый уровень', rubKm(result.regional_weighted_rub_per_km), 'Сохранённое среднее доступных ставок точек с весами всех машин точек популяции Bear Cost. Исходная методика не изменена.'));
    rows.push(metric('Покрыто точек', count(metrics.covered_point_count), 'Число точек, вошедших в сохранённые зоны и одиночные результаты Bear Cost.'));
    rows.push(metric('Покрыто перевозок', count(metrics.covered_trip_count), 'Сумма машин точек сохранённых зон и одиночных результатов Bear Cost; не все машины среза и не число кандидатов.'));
  }
  if (mode === 'bear_volume_zones') {
    rows.push(metric('Порог объёмной зоны', result.analysis.parameters.volume_threshold == null ? '—' : `+${percent(result.analysis.parameters.volume_threshold)}`, 'Сохранённый порог превышения машин точки над средним объёмом точки региона; одиночные проверяются отдельным порогом.'));
    rows.push(metric('Кандидаты', count(metrics.candidate_count), 'Число точек, прошедших порог кандидата Bear Volume; кандидат не обязательно вошёл в зону или одиночный результат.'));
    rows.push(metric('Средний объём региона', `${decimal(result.regional_volume?.mean_trip_count_per_point, 1)} перевозки/точку`, 'Сумма машин положительных точек популяции Bear Volume, делённая на число этих точек.'));
    rows.push(metric('Покрыто точек', count(metrics.covered_point_count), 'Число точек сохранённых зон и одиночных результатов Bear Volume.'));
    rows.push(metric('Покрыто перевозок', count(metrics.covered_trip_count), 'Сумма машин точек сохранённых зон и одиночных результатов Bear Volume; популяция отличается от полного среза.'));
  }
  const graph = result.graph_metrics || {};
  const advanced = [
    metric('Calinski–Harabasz', decimal(metrics.calinski_harabasz, 1), 'По назначенным точкам в признаках режима: (межкластерная сумма квадратов / внутрикластерная) × (n − k) / (k − 1). n — точки, k — кластеры; без веса машин. Применяются соглашения sklearn для вырожденных данных. — если оценка недоступна.'),
    metric('Davies–Bouldin', decimal(metrics.davies_bouldin, 2), 'Среднее по k кластерам максимума (sᵢ + sⱼ) / dᵢⱼ: s — среднее расстояние точек до центроида, d — расстояние центроидов. Признаки режима, без веса машин; применяются соглашения sklearn для вырожденных данных. — если оценка недоступна.'),
    metric('Узлы графа', count(graph.node_count), 'Сохранённое число узлов пространственного графа, на котором оценён текущий режим.'),
    metric('Рёбра графа', count(graph.edge_count), 'Сохранённое число связей пространственного графа текущего режима.'),
    metric('Компоненты графа', count(graph.graph_component_count), 'Число связных компонент пространственного графа текущего режима.'),
    metric('Нарушения связности', count(graph.connectivity_violations), 'Число кластеров, не прошедших проверку связности на графе режима; ненулевое значение также предупреждает в сводке.'),
  ].join('');
  return `${rows.join('')}<h4 class="diagnostics-heading">Диагностика графа и разбиения</h4>${advanced}`;
}

function qualityFor(quality) {
  const resolved = `${count(quality.resolved_points)} / ${count(quality.destination_points_total)}`;
  const resolvedTrips = `${count(quality.trip_count_resolved)} / ${count(quality.trip_count_total)}`;
  return `<h4>Качество данных</h4>
    ${metric('Точки с координатами', resolved, 'Разрешённые координаты / все назначения сохранённого среза; это популяция data_quality, не покрытие назначенных кластеров.')}
    ${metric('Покрытие точек', percent(quality.point_coverage_pct == null ? null : quality.point_coverage_pct / 100), `100 × разрешённые точки / все назначения. Сохранённое значение: ${quality.point_coverage_pct ?? '—'}%.`)}
    ${metric('Машины с координатами', resolvedTrips, 'Машины назначений с разрешёнными координатами / все машины сохранённого среза.')}
    ${metric('Покрытие машин', percent(quality.trip_weight_coverage_pct == null ? null : quality.trip_weight_coverage_pct / 100), `100 × машины разрешённых назначений / все машины среза. Сохранённое значение: ${quality.trip_weight_coverage_pct ?? '—'}%.`)}
    ${metric('Точки с доступной экономикой', `${count(quality.economic_valid_points)} / ${count(quality.resolved_points)}`, 'Точки с доступной экономикой / точки с разрешёнными координатами, по сохранённым data_quality; не доля всех машин и не покрытие отдельной экономической метрики.')}
    ${metric('Исключено строк без FIAS', count(quality.excluded_missing_fias), 'Сохранённое число строк, исключённых из среза из-за отсутствующего FIAS назначения.')}`;
}

function canonicalClusterMetrics(result, cluster) {
  const rows = result.cluster_table?.supported === true ? result.cluster_table.rows : null;
  const row = Array.isArray(rows) ? rows.find(item => item.cluster_id === cluster.cluster_id) : null;
  const hint = (key, raw, unit) => {
    const coverage = row?.coverage?.[key];
    return `Сохранённая таблица: сумма (значение точки × валидные машины этой метрики) / сумма валидных машин этой метрики. При отсутствии валидного веса среднее недоступно. Точное значение: ${raw == null ? 'недоступно' : `${raw} ${unit}`}. Покрытие: ${coverage?.valid_points ?? '—'}/${coverage?.total_points ?? '—'} точек; ${coverage?.valid_trip_count ?? '—'}/${coverage?.total_trip_count ?? '—'} машин.`;
  };
  return `<div class="cluster-primary"><h5>Основные средние — сохранённая таблица</h5>
    ${result.analysis.mode === 'geo_cost' ? '' : '<p class="field-hint">Экономика показана описательно и не влияла на разбиение.</p>'}
    ${!row ? '<p class="inline-warning">Строка сохранённой таблицы недоступна. Основные средние недоступны.</p>' : ''}
    ${metric('Маршрут', km(row?.weighted_route_length), hint('route_length', row?.weighted_route_length, 'км'))}
    ${metric('Средневзвешенная цена', row?.price?.weighted == null ? '—' : `${decimal(row.price.weighted, 0)} ₽`, hint('price', row?.price?.weighted, '₽'))}
    ${metric('Средневзвешенный ₽/км', rubKm(row?.rub_per_km?.weighted), hint('rub_per_km', row?.rub_per_km?.weighted, '₽/км'))}
  </div>`;
}

function renderClusterDetails(result, cluster, mode) {
  const points = result.points.filter(point => cluster.point_ids.includes(point.id));
  $('cluster-detail-title').textContent = clusterLabel(cluster, mode);
  $('cluster-detail-stats').innerHTML = `
    <div><strong>${count(cluster.point_count)}</strong><span>точек</span></div>
    <div><strong>${count(cluster.trip_count)}</strong><span>перевозок</span></div>
    ${(cluster.relative_volume_delta ?? cluster.relative_rate_delta) == null ? '' : `<div><strong>${percent(cluster.relative_volume_delta ?? cluster.relative_rate_delta)}</strong><span>к базовому уровню</span></div>`}`;
  const ordinary = ['geography', 'geo_cost', 'geo_volume'].includes(mode);
  const representative = metric('Временный ориентир (medoid)', escapeHtml(representativeLabel(cluster)), 'Реальная точка кластера с минимальной суммой невзвешенных расстояний в проекции. Временный географический ориентир; выбор может измениться при изменении данных.');
  const diagnostics = [
    ordinary ? metric('Совместимый ₽/км: вес всего объёма доступных точек', rubKm(cluster.weighted_rub_per_km), `Сохранённый показатель: среднее ₽/км доступных точек, взвешенное по всему объёму машин этих точек; это не основной показатель с весами валидных машин таблицы. Точное значение: ${cluster.weighted_rub_per_km ?? '—'} ₽/км.`) : metric('Среднее ₽/км', rubKm(cluster.weighted_rub_per_km)),
    ordinary ? metric('Совместимая цена: вес всего объёма доступных точек', cluster.weighted_price == null ? '—' : `${decimal(cluster.weighted_price, 0)} ₽`, `Сохранённый показатель: цена доступных точек с весом всего их объёма машин, не валидных машин цены. Точное значение: ${cluster.weighted_price ?? '—'} ₽.`) : '',
    mode === 'geo_cost' ? metric('Региональный ₽/км', rubKm(cluster.regional_weighted_rub_per_km)) : '',
    ['geo_volume', 'bear_volume_zones'].includes(mode) ? metric('Средний объём точки', `${decimal(cluster.mean_trip_count, 1)} перевозки`) : '',
    ['geo_volume', 'bear_volume_zones'].includes(mode) ? metric('Средний объём региона', `${decimal(cluster.regional_mean_trip_count, 1)} перевозки/точку`) : '',
    ['geo_volume', 'bear_volume_zones'].includes(mode) ? metric('Отклонение объёма', percent(cluster.relative_volume_delta)) : '',
    cluster.mean_radius_km == null ? '' : metric('Средний радиус', km(cluster.mean_radius_km)),
    cluster.p95_radius_km == null ? '' : metric('P95 радиус', km(cluster.p95_radius_km)),
    cluster.max_radius_km == null ? '' : metric('Максимальный радиус', km(cluster.max_radius_km)),
  ].join('');
  $('cluster-detail-metrics').innerHTML = representative + (ordinary
    ? canonicalClusterMetrics(result, cluster) + `<details class="cluster-diagnostics"><summary>Расширенная аналитика и совместимые показатели</summary>${diagnostics}</details>`
    : diagnostics)
    + metric('Пространственная связность', cluster.connected === true ? 'Да' : cluster.connected === false ? 'Нет' : '—')
    + (cluster.trip_count != null && cluster.trip_count < 20 ? '<p class="inline-warning">Небольшой объём наблюдений · ' + fmt(cluster.trip_count) + ' перевозок</p>' : '');
  $('cluster-points').innerHTML = points.map(point => `
    <button type="button" data-point-id="${escapeHtml(point.id)}"><span>${escapeHtml(point.name)}</span><strong>${count(point.trip_count)}</strong></button>`).join('');
}

function renderPointDetails(point, mode, handlers, pulse = {}, tableMode = false, periodTypes = []) {
  const statuses = {
    assigned: 'В кластере', normal: 'В кластере', ordinary: 'Обычная точка', bear_candidate: 'Кандидат',
    bear_zone: 'Медвежья зона', expensive_singleton: 'Аномально дорогая точка',
    bear_volume_candidate: 'Кандидат по объёму', bear_volume_zone: 'Объёмная медвежья зона', high_volume_singleton: 'Аномально объёмная точка',
    spatial_outlier: 'Пространственно изолирована', economic_unavailable: 'Нет экономики',
  };
  const economics = !tableMode && mode !== 'bear_zones' ? '' : `
      ${!tableMode && point.weighted_price == null ? '' : `<div><dt>Средневзвешенная цена</dt><dd>${point.weighted_price == null ? '—' : `${decimal(point.weighted_price, 0)} ₽`}${tableMode ? `<small>Покрытие: ${coverage(point.valid_price_trip_count, point.trip_count)}</small>` : ''}</dd></div>`}
      ${!tableMode && point.weighted_rub_per_km == null ? '' : `<div><dt>Средневзвешенный ₽/км</dt><dd>${rubKm(point.weighted_rub_per_km)}${tableMode ? `<small>Покрытие: ${coverage(point.valid_rub_per_km_trip_count, point.trip_count)}</small>` : ''}</dd></div>`}
      ${!tableMode && point.regional_weighted_rub_per_km == null ? '' : `<div><dt>Региональный ₽/км</dt><dd>${rubKm(point.regional_weighted_rub_per_km)}</dd></div>`}
      ${!tableMode && point.relative_rate_delta == null ? '' : `<div><dt>Отклонение</dt><dd>${percent(point.relative_rate_delta)}</dd></div>`}`;
  const volume = !['geo_volume', 'bear_volume_zones'].includes(mode) ? '' : `
      ${point.regional_mean_trip_count == null ? '' : `<div><dt>Средний объём региона</dt><dd>${decimal(point.regional_mean_trip_count, 1)} перевозки/точку</dd></div>`}
      ${point.relative_volume_delta == null ? '' : `<div><dt>Отклонение объёма</dt><dd>${percent(point.relative_volume_delta)}</dd></div>`}`;
  const pulseRows = (pulse.rows || []).map(row => `<tr>
    <td>${escapeHtml(row.origin_name || row.origin_fias || '—')}<small>${escapeHtml(row.origin_fias || '')}</small></td>
    <td>${escapeHtml(row.origin_region || 'Регион погрузки не определён')}</td>
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
      : pulse.status === 'unavailable'
        ? '<p class="pulse-state error" role="alert">Сохранённый результат недоступен. Пересчитайте результат.</p>'
      : pulse.status === 'error'
        ? `<p class="pulse-state error" role="alert">${escapeHtml(pulse.error || 'Не удалось загрузить строки Pulse.')}</p><button type="button" data-pulse-retry>Повторить</button>`
        : pulse.status === 'success' && !pulseRows
          ? '<p class="pulse-state">Для точки нет строк Pulse в выбранном срезе.</p>'
          : '';
  const pulseDetails = tableMode || handlers.selectedOrigin ? `<details class="pulse-details" ${pulse.open ? 'open' : ''}>
    <summary aria-disabled="${Boolean(handlers.detailsBlocked && !pulse.open)}">Исходные строки Pulse${pulse.total == null ? '' : ` (${fmt(pulse.total)})`}</summary>
    ${!handlers.selectedOrigin ? '<button type="button" class="back-button" data-point-summary>← К сводке точки</button>' : ''}
    ${pulseState}
    ${handlers.selectedOrigin ? `<p>Отправление: ${escapeHtml(handlers.selectedOrigin)} → ${escapeHtml(point.fias_id || point.id)} · Источник: Pulse</p>` : ''}
    ${pulseRows ? `<div class="pulse-table"><table><thead><tr><th>Отправление / FIAS</th><th>Регион погрузки из строки</th><th>Период</th><th>Тип периода</th><th>Тип цены</th><th>Транспорт</th><th>Тоннаж</th><th>Цена</th><th>Маршрут</th><th>₽/км</th><th>Машины</th><th>Предупреждения</th></tr></thead><tbody>${pulseRows}</tbody></table></div>` : ''}
    ${pulse.hasMore && pulse.status !== 'loading' ? '<button type="button" data-pulse-more>Показать ещё</button>' : ''}
  </details>` : '';
  $('point-details').innerHTML = `
    <div class="section-row"><h4>Точка назначения</h4><button id="point-details-close" class="back-button" type="button">${point.cluster_id == null ? '← К обзору' : '← К кластеру'}</button></div>
    <h3>${escapeHtml(point.name)}</h3>
    <dl class="point-facts">
      <div><dt>FIAS</dt><dd>${escapeHtml(point.fias_id || point.id)}</dd></div>
      <div><dt>Статус</dt><dd>${escapeHtml(statuses[point.status] || point.status)}</dd></div>
      <div><dt>Кластер</dt><dd>${point.cluster_id == null ? 'Вне кластеров' : Number(point.cluster_id) + 1}</dd></div>
      <div><dt>${tableMode ? 'Машины' : 'Перевозки'}</dt><dd>${count(point.trip_count)}</dd></div>
      ${tableMode ? `<div><dt>Маршрут</dt><dd>${km(point.weighted_route_length)}<small>Покрытие: ${coverage(point.valid_route_length_trip_count, point.trip_count)}</small></dd></div>` : ''}
      ${tableMode ? `<div><dt>Периоды</dt><dd>${periodTypes.map(value => escapeHtml(value === 'forecast' ? 'Прогноз Pulse' : PERIOD_LABELS[value] || value)).join(', ') || '—'}</dd></div>` : ''}
      ${point.data_quality_flags?.length ? `<div><dt>Качество</dt><dd>${point.data_quality_flags.map(escapeHtml).join(', ')}</dd></div>` : ''}
      ${economics}
      ${volume}
    </dl>
    ${handlers.selectedOrigin ? '<button type="button" class="back-button" data-point-summary>← К сводке точки</button>' : ''}
    ${originSummary(handlers)}
    ${pulseDetails}`;
  document.getElementById('point-details-close').addEventListener('click', () => handlers.onPointClear?.());
  document.querySelector('[data-point-summary]')?.addEventListener('click', () => handlers.onPointSummary?.());
  document.querySelector('.pulse-details summary')?.addEventListener('click', event => {
    event.preventDefault();
    const details = event.currentTarget.parentElement;
    if (!details.open && handlers.detailsBlocked) return;
    details.open = !details.open;
    handlers.onPulseToggle?.(details.open);
  });
  document.querySelector('.pulse-details')?.addEventListener('toggle', event => { if (event.target.isConnected) handlers.onPulseToggle?.(event.target.open); });
  document.querySelector('[data-pulse-more]')?.addEventListener('click', () => handlers.onPulseMore?.());
  document.querySelector('[data-pulse-retry]')?.addEventListener('click', () => handlers.onPulseRetry?.());
  document.querySelectorAll('[data-origin-fias]').forEach(button => {
    button.addEventListener('click', () => handlers.onOriginSelect?.(button.dataset.originFias));
  });
  document.querySelector('[data-origins-retry]')?.addEventListener('click', () => handlers.onOriginsRetry?.());
}

function originSummary(handlers) {
  const summary = handlers.pointOrigins;
  if (!summary) return '';
  const states = {
    loading: 'Загружаем вклад отправлений…',
    stale: 'Данные Pulse изменились. Пересчитайте результат.',
    unavailable: 'Сохранённый результат недоступен. Пересчитайте результат.',
  };
  return `<section class="origin-summary" aria-label="Вклад отправлений"><h4>Вклад отправлений в точку</h4>
    <p>Источник: Pulse. Средние взвешены по машинам с валидным показателем. Покрытие: валидные машины / все машины отправления. Пропуски не равны нулю.</p>
    ${summary.status === 'success' ? (summary.origins || []).map(origin => `
      <button type="button" data-origin-fias="${escapeHtml(origin.origin_fias)}" aria-disabled="${Boolean(handlers.detailsBlocked)}" aria-pressed="${handlers.selectedOrigin === origin.origin_fias}">
        <strong>${escapeHtml(origin.origin_name || 'Название недоступно')}</strong> · ${escapeHtml(origin.origin_fias)}
        <span>${count(origin.trip_count)} машин · ${count(origin.source_row_count)} строк</span>
        <span>Маршрут: ${km(origin.weighted_route_length)} · покрытие ${coverage(origin.valid_route_length_trip_count, origin.trip_count)}</span>
        <span>Цена: ${origin.weighted_price == null ? '—' : `${decimal(origin.weighted_price, 0)} ₽`} · покрытие ${coverage(origin.valid_price_trip_count, origin.trip_count)}</span>
        <small>Регионы погрузки из строк: ${(origin.origin_regions || []).map(region => escapeHtml(region || 'Регион погрузки не определён')).join(', ')}</small>
        ${origin.warnings?.length ? `<small>${origin.warnings.map(escapeHtml).join(', ')}</small>` : ''}
      </button>`).join('') : `<p role="${summary.status === 'loading' ? 'status' : 'alert'}">${escapeHtml(states[summary.status] || summary.error || 'Не удалось загрузить вклад отправлений.')}</p>`}
    ${summary.status === 'error' || summary.status === 'idle' ? '<button type="button" data-origins-retry>Повторить</button>' : ''}
  </section>`;
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
