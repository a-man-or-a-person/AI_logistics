/** Application shell plus Product v1 clustering integration. */

import { compareClusteringModes, fetchClusteringOptions, fetchGeocodeStatus, fetchPoints, fetchRecords, fetchRegions, fetchStats, regeocodeTown, runClustering } from './api.js';
import { MODE_LABELS, PERIOD_LABELS, PRICE_LABELS, buildClusteringRequest, clusterTitle, createClusteringState, requestSignature } from './clustering.js';
import { getFilters, initFilters, resetFilters } from './filters.js';
import { clearClusteringResult, clearMarkers, highlightCluster, initMap, renderClusteringPoints, renderPoints, setClusteringLayers, setMlResultStale, setThemeLayer } from './map.js';

const $ = id => document.getElementById(id);
const fmt = value => Number(value || 0).toLocaleString('ru-RU');
const number = (value, digits = 1) => value == null ? '—' : Number(value).toLocaleString('ru-RU', { maximumFractionDigits: digits });
const ZONE_COLORS = ['#d84f4f', '#3478c5', '#198a68', '#d28a18', '#7a5ac8', '#c54a88', '#1d9690', '#d5662a', '#5a61c5', '#75a62c'];
const WARNING_TEXT = {
  contains_forecast: 'В анализ включены прогнозные данные Pulse.',
  mixed_tariff_segments: 'Анализ включает несколько тарифных сегментов. Различия ₽/км могут быть связаны не только с географией.',
  incomplete_coordinate_coverage: 'Часть точек не имеет координат и показана только в качестве данных.',
  economic_points_excluded: 'Точки без корректной экономики не участвовали в Geo+Cost и остались на карте отдельно.',
};

const state = { mode: 'cluster', lastData: null, clustering: createClusteringState() };
let toastTimer = null;
let pointsController = null;
let clusteringController = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
}

function showToast(message, type = 'success', duration = 3600) {
  const toast = $('toast');
  toast.textContent = message;
  toast.className = `show toast-${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = ''; }, duration);
}

function setSystemStatus(kind, text) {
  $('status-dot').className = `status-dot${kind ? ` ${kind}` : ''}`;
  $('status-text').textContent = text;
}

function setMapLoading(active, title = 'Загружаем данные…', detail = '') {
  $('loading-overlay').classList.toggle('hidden', !active);
  $('loading-text').textContent = title;
  $('loading-sub').textContent = detail;
  const button = state.mode === 'cluster' ? $('btn-run-ml') : $('btn-apply');
  if (button) { button.classList.toggle('loading', active); button.disabled = active; }
}

function setMapEmpty(title, subtitle, showSteps = state.mode === 'cluster') {
  const empty = $('empty-state');
  empty.querySelector('.empty-title').textContent = title;
  empty.querySelector('.empty-sub').textContent = subtitle;
  empty.querySelector('ol').style.display = showSteps ? '' : 'none';
  empty.classList.remove('hidden');
}
function hideMapEmpty() { $('empty-state').classList.add('hidden'); }
function checkedValues(id) { return [...document.querySelectorAll(`#${id} input:checked`)].map(input => input.value); }
function checkedValue(name) { return document.querySelector(`input[name="${name}"]:checked`)?.value; }

function optionChecks(containerId, items, selected = null, labels = {}) {
  const container = $(containerId);
  container.innerHTML = '';
  for (const item of items || []) {
    const value = typeof item === 'string' ? item : item.value;
    const count = typeof item === 'string' ? null : item.count;
    const label = document.createElement('label');
    label.className = 'filter-check';
    const input = document.createElement('input');
    input.type = 'checkbox'; input.value = value; input.checked = selected ? selected.includes(value) : true;
    const text = document.createElement('span');
    text.textContent = `${labels[value] || value}${count == null ? '' : ` · ${fmt(count)}`}`;
    label.append(input, text); container.appendChild(label);
  }
}

const originLabel = origin => `${origin.name} · ${origin.region}`;
const selectedOrigin = () => state.clustering.options?.origins.find(item => item.fias_id === $('cluster-origin').value);

async function loadOriginOptions() {
  const options = await fetchClusteringOptions();
  state.clustering.options = options;
  $('cluster-origin').replaceChildren(new Option('Выберите origin…', ''));
  for (const origin of options.origins) $('cluster-origin').add(new Option(originLabel(origin), origin.fias_id));
  optionChecks('cluster-periods', options.period_types, ['current'], PERIOD_LABELS);
}

function clearFacetControls() {
  for (const id of ['cluster-prices', 'cluster-vehicles', 'cluster-tonnages']) $(id).innerHTML = '';
}

async function onOriginChange() {
  const originFias = $('cluster-origin').value;
  $('cluster-region').replaceChildren(new Option(originFias ? 'Выберите регион…' : 'Сначала выберите origin', ''));
  $('cluster-region').disabled = !originFias;
  state.clustering.contextOptions = null;
  if (originFias) {
    const options = await fetchClusteringOptions({ originFias });
    for (const region of options.destination_regions) $('cluster-region').add(new Option(region, region));
  }
  clearFacetControls(); updateClusteringPreview();
}

async function onRegionChange() {
  const originFias = $('cluster-origin').value;
  const destinationRegion = $('cluster-region').value;
  clearFacetControls();
  if (originFias && destinationRegion) {
    const options = await fetchClusteringOptions({ originFias, destinationRegion });
    state.clustering.contextOptions = options;
    optionChecks('cluster-periods', options.facets.period_types, ['current'], PERIOD_LABELS);
    optionChecks('cluster-prices', options.facets.price_types, null, PRICE_LABELS);
    optionChecks('cluster-vehicles', options.facets.vehicle_types);
    optionChecks('cluster-tonnages', options.facets.tonnage_ids);
  }
  updateClusteringPreview();
}

function formValues() {
  return {
    originFias: $('cluster-origin').value, destinationRegion: $('cluster-region').value,
    mode: $('cluster-mode').value, periodTypes: checkedValues('cluster-periods'),
    priceTypes: checkedValues('cluster-prices'), vehicleTypes: checkedValues('cluster-vehicles'),
    tonnageIds: checkedValues('cluster-tonnages'), kMode: checkedValue('cluster-k-mode') || 'auto',
    k: Number($('cluster-k-value').value || $('cluster-k-value').textContent || 5),
    bearThreshold: Number($('cluster-bear-threshold').value || 35),
  };
}
const currentRequest = () => buildClusteringRequest(formValues());

function updateModeSettings() {
  const bear = $('cluster-mode').value === 'bear_zones';
  $('cluster-k-settings').classList.toggle('hidden', bear);
  $('cluster-bear-settings').classList.toggle('hidden', !bear);
  document.querySelectorAll('.bear-layer').forEach(element => element.classList.toggle('hidden', !bear));
}

function onAnalysisModeChange() {
  updateClusteringPreview();
  const request = currentRequest();
  if (!validateRequest(request)) {
    const cached = state.clustering.resultCache.get(requestSignature(request));
    if (cached) showProductResult(cached, request);
  }
}

function updateClusteringPreview() {
  updateModeSettings();
  const values = formValues();
  $('preview-origin').textContent = selectedOrigin()?.name || 'Origin не выбран';
  $('preview-region').textContent = values.destinationRegion || 'Регион не выбран';
  $('preview-mode').textContent = MODE_LABELS[values.mode];
  const labels = [...values.periodTypes.map(value => PERIOD_LABELS[value] || value), ...values.priceTypes.map(value => PRICE_LABELS[value] || value), ...values.vehicleTypes, ...values.tonnageIds];
  $('preview-filters').innerHTML = ['Pulse', ...labels].map(label => `<span>${escapeHtml(label)}</span>`).join('');
  $('cluster-forecast-warning').classList.toggle('hidden', !values.periodTypes.includes('forecast'));
  $('run-caption').textContent = values.mode === 'bear_zones' ? `${MODE_LABELS[values.mode]} · +${values.bearThreshold}%` : `${MODE_LABELS[values.mode]} · ${values.kMode === 'auto' ? 'Auto K' : `K = ${values.k}`}`;
  if (state.clustering.resultRequest) {
    const stale = requestSignature(currentRequest()) !== requestSignature(state.clustering.resultRequest);
    $('analysis-stale').classList.toggle('hidden', !stale); setMlResultStale(stale);
  }
}

function validateRequest(request) {
  if (!request.origin_fias) return 'Выберите точку отправления.';
  if (!request.destination_region) return 'Выберите регион назначения.';
  if (!request.filters.period_types.length) return 'Выберите хотя бы один период.';
  return null;
}

async function executeClustering() {
  const request = currentRequest();
  const error = validateRequest(request);
  $('analysis-form-error').classList.toggle('hidden', !error);
  if (error) { $('analysis-form-error').textContent = error; return; }
  const signature = requestSignature(request);
  clusteringController?.abort(); setMapLoading(true, 'Рассчитываем зоны…', MODE_LABELS[request.mode]);
  try {
    let result = state.clustering.resultCache.get(signature);
    if (!result) {
      clusteringController = new AbortController();
      result = await runClustering(request, { signal: clusteringController.signal });
      state.clustering.resultCache.set(signature, result);
    }
    showProductResult(result, request);
    showToast(request.mode === 'bear_zones' && !result.clusters.length ? 'Медвежьи зоны на выбранных данных не обнаружены' : `Готово: ${fmt(result.summary.cluster_count)} зон`);
  } catch (requestError) {
    $('analysis-form-error').textContent = requestError.message; $('analysis-form-error').classList.remove('hidden');
    showToast(`Расчёт не выполнен: ${requestError.message}`, 'error', 6000);
  } finally { setMapLoading(false); }
}

function showProductResult(result, request) {
  state.clustering.result = result; state.clustering.resultRequest = request; state.clustering.selectedClusterId = null;
  renderClusteringPoints(result); renderInspector(result, request); hideMapEmpty();
  $('btn-reset-ml').classList.remove('hidden'); $('analysis-stale').classList.add('hidden'); setMlResultStale(false);
}

function resultDataLabel(request) {
  const values = [...request.filters.period_types.map(value => PERIOD_LABELS[value] || value), ...request.filters.price_types.map(value => PRICE_LABELS[value] || value)];
  return `Pulse · ${values.join(' + ') || 'все сегменты'}`;
}

function renderInspector(result, request) {
  $('inspector-empty').classList.add('hidden'); $('inspector-result').classList.remove('hidden');
  $('result-mode-badge').textContent = MODE_LABELS[result.mode]; $('result-k').textContent = fmt(result.summary.cluster_count);
  $('result-mode').textContent = result.mode === 'bear_zones' ? `Порог +${number(result.parameters.bear_threshold_pct, 0)}%` : result.parameters.k_mode === 'manual' ? `K = ${result.parameters.selected_k}` : `Auto → ${result.parameters.selected_k}`;
  $('result-cities').textContent = fmt(result.regional_stats.destination_count); $('result-bids').textContent = fmt(result.regional_stats.trip_count);
  $('result-region').textContent = `${selectedOrigin()?.name || request.origin_fias} → ${request.destination_region}`;
  $('result-type').textContent = MODE_LABELS[result.mode]; $('result-data').textContent = resultDataLabel(request);
  $('result-k-detail').textContent = result.mode === 'bear_zones' ? `+${number(result.parameters.bear_threshold_pct, 0)}% / singleton +70%` : result.parameters.k_mode === 'manual' ? String(result.parameters.selected_k) : `Auto → ${result.parameters.selected_k}`;
  $('result-silhouette').textContent = number(result.metrics?.silhouette, 2);
  const quality = result.data_quality;
  $('quality-used').textContent = `${fmt(quality.resolved_points)} / ${fmt(quality.destination_points_total)}`;
  $('quality-ratio').textContent = `${number(quality.point_coverage_pct)}%`; $('quality-fill').style.width = `${quality.point_coverage_pct}%`;
  $('quality-note').textContent = `Покрытие перевозок: ${number(quality.trip_weight_coverage_pct)}%.`;
  const warningBox = $('result-warnings');
  warningBox.innerHTML = result.warnings.map(code => `<p>${escapeHtml(WARNING_TEXT[code] || code)}</p>`).join('');
  warningBox.classList.toggle('hidden', !result.warnings.length); renderClusterList(result);
}

function renderClusterList(result) {
  $('zones-count').textContent = String(result.clusters.length); const list = $('zone-list'); list.innerHTML = '';
  if (!result.clusters.length) { list.innerHTML = '<p class="empty-list">На выбранных данных медвежьи зоны не обнаружены.</p>'; return; }
  result.clusters.forEach((cluster, index) => {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'zone-card'; button.dataset.zoneId = cluster.cluster_id;
    button.style.setProperty('--zone-color', ZONE_COLORS[index % ZONE_COLORS.length]);
    button.innerHTML = `<span class="zone-card-swatch"></span><span class="zone-card-main"><strong>${escapeHtml(clusterTitle(cluster))}</strong><span>${fmt(cluster.point_count)} точек</span></span><span class="zone-card-bids"><strong>${fmt(cluster.trip_count)}</strong><span>${number((cluster.relative_rate_delta || 0) * 100, 0)}% к региону</span></span>`;
    button.addEventListener('click', () => chooseCluster(cluster.cluster_id, true)); list.appendChild(button);
  });
}

function chooseCluster(clusterId, focus = false) {
  const result = state.clustering.result; const cluster = result?.clusters.find(item => Number(item.cluster_id) === Number(clusterId)); if (!cluster) return;
  state.clustering.selectedClusterId = Number(clusterId);
  document.querySelectorAll('.zone-card').forEach(card => card.classList.toggle('selected', Number(card.dataset.zoneId) === Number(clusterId)));
  highlightCluster(clusterId, focus); const color = ZONE_COLORS[result.clusters.indexOf(cluster) % ZONE_COLORS.length];
  $('zone-details').classList.remove('hidden'); $('zone-details-swatch').style.background = color; $('zone-details-title').textContent = clusterTitle(cluster);
  $('zone-details-cities').textContent = fmt(cluster.point_count); $('zone-details-bids').textContent = fmt(cluster.trip_count);
  $('zone-economics').innerHTML = `<div><dt>Средневзвешенная цена</dt><dd>${number(cluster.weighted_price, 0)} ₽</dd></div><div><dt>Средневзвешенный ₽/км</dt><dd>${number(cluster.weighted_rub_per_km)} ₽/км</dd></div><div><dt>Региональный ₽/км</dt><dd>${number(cluster.regional_weighted_rub_per_km)} ₽/км</dd></div><div><dt>Отклонение</dt><dd>${number((cluster.relative_rate_delta || 0) * 100, 0)}%</dd></div><div><dt>Mean / P95 radius</dt><dd>${number(cluster.mean_radius_km)} / ${number(cluster.p95_radius_km)} км</dd></div>`;
  const points = result.points.filter(point => Number(point.cluster_id) === Number(clusterId));
  $('zone-details-towns').innerHTML = points.sort((a, b) => a.name.localeCompare(b.name, 'ru')).map(point => `<div><strong>${escapeHtml(point.name)}</strong><small>${escapeHtml(point.fias_id)}</small><span>${fmt(point.trip_count)} · ${number(point.weighted_rub_per_km)} ₽/км · ${number((point.relative_rate_delta || 0) * 100, 0)}%</span></div>`).join('');
}

function clearClusterSelection() {
  state.clustering.selectedClusterId = null; highlightCluster(null);
  document.querySelectorAll('.zone-card').forEach(card => card.classList.remove('selected')); $('zone-details').classList.add('hidden');
}

async function compareModes() {
  const request = currentRequest(); const error = validateRequest(request);
  if (error) { $('analysis-form-error').textContent = error; $('analysis-form-error').classList.remove('hidden'); return; }
  const signature = requestSignature(request, false); setMapLoading(true, 'Сравниваем режимы…', 'Один spatial context, без automatic winner');
  try {
    let comparison = state.clustering.comparisonCache.get(signature);
    if (!comparison) {
      comparison = await compareClusteringModes(request); state.clustering.comparisonCache.set(signature, comparison);
      const modeParameters = {
        geography: { k_mode: 'auto' },
        geo_cost: { k_mode: 'auto', geography_weight: 0.7, economics_weight: 0.3 },
        bear_zones: { bear_threshold_pct: 35, singleton_threshold_pct: 70 },
      };
      for (const [mode, result] of Object.entries(comparison.results)) {
        state.clustering.resultCache.set(requestSignature({ ...request, mode, parameters: modeParameters[mode] }), result);
      }
    }
    renderComparison(comparison, request);
  } catch (requestError) { showToast(`Сравнение недоступно: ${requestError.message}`, 'error', 6000); }
  finally { setMapLoading(false); }
}

function renderComparison(comparison, baseRequest) {
  if (!state.clustering.result) {
    showProductResult(comparison.results.geography, { ...baseRequest, mode: 'geography', parameters: { k_mode: 'auto' } });
  }
  $('comparison-section').classList.remove('hidden');
  $('comparison-cards').innerHTML = comparison.comparison.map(row => `<button type="button" data-compare-mode="${row.mode}"><strong>${MODE_LABELS[row.mode]}</strong><span>${fmt(row.cluster_count)} зон</span><span>P95: ${number(row.p95_radius_km)} км</span><span>Выбросы: ${fmt(row.outlier_count)}</span></button>`).join('');
  document.querySelectorAll('[data-compare-mode]').forEach(button => button.addEventListener('click', () => {
    const mode = button.dataset.compareMode; $('cluster-mode').value = mode; updateClusteringPreview();
    const result = comparison.results[mode]; showProductResult(result, { ...baseRequest, mode, parameters: result.parameters });
  }));
}

function resetClustering() {
  state.clustering.result = null; state.clustering.resultRequest = null; state.clustering.selectedClusterId = null; clearClusteringResult();
  $('inspector-result').classList.add('hidden'); $('inspector-empty').classList.remove('hidden'); $('btn-reset-ml').classList.add('hidden');
  $('analysis-stale').classList.add('hidden'); $('analysis-form-error').classList.add('hidden'); $('comparison-section').classList.add('hidden');
  setMapEmpty('Создайте первое разбиение региона', 'Выберите направление и тип анализа.', true);
}

function switchMode(mode) {
  if (!['data', 'cluster'].includes(mode) || state.mode === mode) return; state.mode = mode; const clusteringMode = mode === 'cluster';
  $('workspace').classList.toggle('mode-cluster', clusteringMode); $('workspace').classList.toggle('mode-data', !clusteringMode);
  $('cluster-controls').classList.toggle('hidden', !clusteringMode); $('data-controls').classList.toggle('hidden', clusteringMode);
  $('controls-title').textContent = clusteringMode ? 'Территориальные зоны' : 'Исходные данные';
  document.querySelectorAll('.mode-tab').forEach(button => button.classList.toggle('active', button.dataset.mode === mode));
  $('map-info').classList.toggle('hidden', clusteringMode || !state.lastData); $('map-legend').classList.toggle('hidden', clusteringMode || !state.lastData);
  if (clusteringMode) {
    if (state.clustering.result) { renderClusteringPoints(state.clustering.result); hideMapEmpty(); }
    else { clearMarkers(); setMapEmpty('Создайте первое разбиение региона', 'Выберите направление и тип анализа.', true); }
  } else if (state.lastData) { renderPoints(state.lastData.shipment_points, state.lastData.delivery_points); hideMapEmpty(); }
  else { clearMarkers(); setMapEmpty('Выберите направление или регион', 'Настройте фильтры слева.', false); }
  window.setTimeout(() => window.dispatchEvent(new Event('resize')), 60);
}

async function loadAndRenderPoints() {
  const filters = getFilters(); pointsController?.abort();
  if (!filters.fromRegions.length && !filters.toRegions.length) { setMapEmpty('Выберите направление или регион', 'Настройте фильтры слева.', false); return; }
  pointsController = new AbortController(); setMapLoading(true, 'Обновляем карту…');
  try {
    const data = await fetchPoints(filters, { signal: pointsController.signal }); state.lastData = data;
    if (state.mode === 'data') renderPoints(data.shipment_points, data.delivery_points);
    $('info-ship').textContent = fmt(data.total_ship); $('info-del').textContent = fmt(data.total_del); $('info-geocoded').textContent = fmt(data.geocoded);
    $('map-info').classList.remove('hidden'); $('map-legend').classList.remove('hidden');
    data.total_ship + data.total_del ? hideMapEmpty() : setMapEmpty('По выбранным параметрам данных нет', 'Измените фильтры.', false);
  } catch (error) { if (error.name !== 'AbortError') showToast(error.message, 'error'); }
  finally { setMapLoading(false); }
}

function initTheme() {
  let theme = localStorage.getItem('app-theme') || 'light';
  const apply = next => { theme = next; document.documentElement.toggleAttribute('data-theme', next === 'dark'); localStorage.setItem('app-theme', next); setThemeLayer(next); };
  apply(theme); $('theme-toggle-header').addEventListener('click', () => apply(theme === 'dark' ? 'light' : 'dark'));
}

function initInteractions() {
  document.querySelectorAll('.mode-tab').forEach(button => button.addEventListener('click', () => switchMode(button.dataset.mode)));
  $('btn-apply').addEventListener('click', loadAndRenderPoints); $('btn-reset').addEventListener('click', () => { resetFilters(); state.lastData = null; clearMarkers(); });
  $('cluster-controls').addEventListener('submit', event => { event.preventDefault(); executeClustering(); }); $('cluster-controls').addEventListener('change', updateClusteringPreview);
  $('cluster-origin').addEventListener('change', onOriginChange); $('cluster-region').addEventListener('change', onRegionChange); $('cluster-mode').addEventListener('change', onAnalysisModeChange);
  document.querySelectorAll('input[name="cluster-k-mode"]').forEach(input => input.addEventListener('change', () => $('cluster-k-stepper').classList.toggle('hidden', checkedValue('cluster-k-mode') !== 'manual')));
  const changeK = delta => { const output = $('cluster-k-value'); output.value = Math.min(20, Math.max(2, Number(output.value || output.textContent) + delta)); output.textContent = output.value; updateClusteringPreview(); };
  $('cluster-k-minus').addEventListener('click', () => changeK(-1)); $('cluster-k-plus').addEventListener('click', () => changeK(1));
  $('btn-reset-ml').addEventListener('click', resetClustering); $('btn-compare-clustering').addEventListener('click', compareModes); $('zone-details-close').addEventListener('click', clearClusterSelection);
  document.querySelectorAll('[data-clustering-layer]').forEach(input => input.addEventListener('change', () => setClusteringLayers(input.dataset.clusteringLayer, input.checked)));
  window.addEventListener('clustering-point-select', event => { if (event.detail.clusterId != null) chooseCluster(event.detail.clusterId, false); });
  $('mobile-controls-btn').addEventListener('click', () => $('sidebar').classList.add('open')); $('mobile-inspector-btn').addEventListener('click', () => $('analysis-inspector').classList.add('open'));
  document.querySelectorAll('[data-close-panel]').forEach(button => button.addEventListener('click', () => button.closest('aside').classList.remove('open')));
  $('modal-close').addEventListener('click', () => $('records-modal').classList.add('hidden')); $('modal-overlay').addEventListener('click', () => $('records-modal').classList.add('hidden'));
}

function initMapEvents() {
  window.addEventListener('show-records-modal', async event => {
    const { town, region, type } = event.detail; $('records-modal').classList.remove('hidden'); $('modal-title').textContent = town;
    try {
      const result = await fetchRecords(town, region, type, getFilters());
      $('records-tbody').innerHTML = result.records.map(record => `<tr><td>${escapeHtml(record.price)}</td><td>${escapeHtml(record.route_length)}</td><td>${number(record.rub_per_km)}</td><td>${escapeHtml(record.bid_count)}</td><td>${escapeHtml(record.period_type)}</td><td>${escapeHtml(record.price_type)}</td><td>${escapeHtml(record.confidence || '—')}</td><td>${escapeHtml(record.ship_region)}</td><td>${escapeHtml(record.del_region)}</td></tr>`).join('');
    } catch (error) { $('modal-error').textContent = error.message; $('modal-error').classList.remove('hidden'); }
  });
  window.addEventListener('regeocode-point', async event => { try { await regeocodeTown(event.detail.town, event.detail.region); } catch (error) { showToast(error.message, 'error'); } });
}

function startGeocodePolling() {
  window.setInterval(async () => {
    try {
      const status = await fetchGeocodeStatus(); const active = status.running && status.total > 0; $('geocode-status').classList.toggle('hidden', !active);
      if (active) { $('geocode-status-text').textContent = `Координаты: ${status.done}/${status.total}`; $('geocode-progress-fill').style.width = `${Math.round(status.done / status.total * 100)}%`; }
    } catch (error) { console.warn(error); }
  }, 5000);
}

async function main() {
  setSystemStatus('loading', 'Инициализация');
  try {
    initMap('map'); initTheme(); initInteractions(); initMapEvents();
    const [regions] = await Promise.all([fetchRegions(), fetchStats(), loadOriginOptions()]);
    initFilters(regions.ship_regions, regions.del_regions, () => {}); updateClusteringPreview();
    setMapEmpty('Создайте первое разбиение региона', 'Выберите направление и тип анализа.', true); setSystemStatus('', 'Данные готовы'); startGeocodePolling();
  } catch (error) { console.error(error); setSystemStatus('error', 'Недоступно'); setMapEmpty('Не удалось запустить приложение', error.message, false); }
  finally { setMapLoading(false); }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main); else main();
