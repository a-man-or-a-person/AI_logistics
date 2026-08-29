/** Application shell and canonical territorial-zones workflow. */

import {
  fetchClusteringOptions,
  fetchClusteringOrigins,
  fetchGeocodeStatus,
  fetchPoints,
  fetchRecords,
  fetchRegions,
  fetchStats,
  previewClustering,
  regeocodeTown,
  runClustering,
} from './api.js';
import {
  PERIOD_LABELS,
  PRICE_LABELS,
  buildClusteringRequest,
  requestSignature,
  zoneLabel,
} from './clustering.js';
import { getFilters, initFilters, resetFilters } from './filters.js';
import {
  clearClusteringResult,
  clearMarkers,
  highlightCluster,
  initMap,
  renderClusteringPoints,
  renderPoints,
  setClusteringLayers,
  setMlLayerVisibility,
  setMlResultStale,
  setThemeLayer,
} from './map.js';

const $ = id => document.getElementById(id);
const fmt = value => Number(value || 0).toLocaleString('ru-RU');
const number = (value, digits = 1) => value == null
  ? '—'
  : Number(value).toLocaleString('ru-RU', { maximumFractionDigits: digits });
const distance = value => value == null ? '—' : number(Number(value) / 1000, 1) + ' км';
const ZONE_COLORS = ['#d84f4f', '#3478c5', '#198a68', '#d28a18', '#7a5ac8', '#c54a88', '#1d9690', '#d5662a', '#5a61c5', '#75a62c'];

const state = {
  mode: 'cluster',
  lastData: null,
  origin: null,
  originOptions: [],
  result: null,
  resultRequest: null,
};
let toastTimer = null;
let originTimer = null;
let previewTimer = null;
let pointsController = null;
let previewController = null;
let clusteringController = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[char]);
}

function showToast(message, type = 'success', duration = 3600) {
  const toast = $('toast');
  toast.textContent = message;
  toast.className = 'show toast-' + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = ''; }, duration);
}

function setSystemStatus(kind, text) {
  $('status-dot').className = 'status-dot' + (kind ? ' ' + kind : '');
  $('status-text').textContent = text;
}

function setMapLoading(active, title = 'Загружаем данные…', detail = '') {
  $('loading-overlay').classList.toggle('hidden', !active);
  $('loading-text').textContent = title;
  $('loading-sub').textContent = detail;
  const button = state.mode === 'cluster' ? $('btn-run-ml') : $('btn-apply');
  if (button) {
    button.classList.toggle('loading', active);
    button.disabled = active;
  }
}

function setMapEmpty(title, subtitle, showSteps = state.mode === 'cluster') {
  const empty = $('empty-state');
  empty.querySelector('.empty-title').textContent = title;
  empty.querySelector('.empty-sub').textContent = subtitle;
  empty.querySelector('ol').style.display = showSteps ? '' : 'none';
  empty.classList.remove('hidden');
}

function hideMapEmpty() {
  $('empty-state').classList.add('hidden');
}

function checkedValues(id) {
  return [...document.querySelectorAll('#' + id + ' input:checked')].map(input => input.value);
}

function checkedValue(name) {
  return document.querySelector('input[name="' + name + '"]:checked')?.value;
}

function optionChecks(containerId, items, selected, labels) {
  const container = $(containerId);
  container.innerHTML = '';
  for (const value of items || []) {
    const label = document.createElement('label');
    label.className = 'filter-check';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = value;
    input.checked = selected.includes(value);
    const text = document.createElement('span');
    text.textContent = labels[value] || value;
    label.append(input, text);
    container.appendChild(label);
  }
}

function originLabel(origin) {
  return origin.name + (origin.region ? ' — ' + origin.region : '');
}

async function loadOriginSuggestions(query = '') {
  state.originOptions = await fetchClusteringOrigins(query, 30);
  const datalist = $('cluster-origin-options');
  datalist.innerHTML = '';
  for (const origin of state.originOptions) {
    const option = document.createElement('option');
    option.value = originLabel(origin);
    option.label = origin.fias_id;
    datalist.appendChild(option);
  }
}

function matchingOrigin() {
  const value = $('cluster-origin').value.trim();
  return state.originOptions.find(origin => (
    originLabel(origin) === value || origin.fias_id === value
  )) || null;
}

async function selectOrigin(origin) {
  if (state.origin?.fias_id === origin?.fias_id) return;
  state.origin = origin;
  $('cluster-origin-meta').textContent = origin
    ? (origin.region || 'Регион не указан') + ' · FIAS ' + origin.fias_id
    : 'Выберите значение из найденного списка';
  const select = $('cluster-region');
  select.replaceChildren(new Option(
    origin ? 'Выберите регион…' : 'Сначала выберите точку отправления',
    '',
  ));
  select.disabled = !origin;
  if (origin) {
    const options = await fetchClusteringOptions(origin.fias_id);
    for (const region of options.destination_regions) {
      select.add(new Option(region, region));
    }
  }
  state.result = null;
  state.resultRequest = null;
  clearClusteringResult();
  renderEmptyInspector();
  updatePreviewText();
}

function onOriginInput() {
  clearTimeout(originTimer);
  const match = matchingOrigin();
  if (match) {
    selectOrigin(match).catch(showPersistentError);
    return;
  }
  if (state.origin) selectOrigin(null).catch(showPersistentError);
  originTimer = setTimeout(async () => {
    try {
      await loadOriginSuggestions($('cluster-origin').value.trim());
      const exact = matchingOrigin();
      if (exact) await selectOrigin(exact);
    } catch (error) {
      showPersistentError(error);
    }
  }, 250);
}

function currentRequest() {
  return buildClusteringRequest({
    originFias: state.origin?.fias_id || '',
    destinationRegion: $('cluster-region').value,
    periodTypes: checkedValues('cluster-periods'),
    priceTypes: checkedValues('cluster-prices'),
    nClusters: $('cluster-k-value').value,
    weightMode: checkedValue('cluster-weight-mode') || 'none',
  });
}

function validateRequest(request) {
  if (!request.origin_fias) return 'Выберите точку отправления из найденного списка.';
  if (!request.destination_region) return 'Выберите регион доставки.';
  if (!request.period_types.length) return 'Выберите хотя бы один период.';
  if (!request.price_types.length) return 'Выберите хотя бы один тип цены.';
  if (!Number.isInteger(request.parameters.n_clusters)
      || request.parameters.n_clusters < 2
      || request.parameters.n_clusters > 10) {
    return 'Количество зон должно быть от 2 до 10.';
  }
  return null;
}

function updatePreviewText() {
  const request = currentRequest();
  $('preview-origin').textContent = state.origin?.name || 'Точка не выбрана';
  $('preview-region').textContent = request.destination_region || 'Регион не выбран';
  $('preview-mode').textContent = 'K-Means · ' + request.parameters.n_clusters + ' зон';
  $('run-caption').textContent = 'K-Means · ' + request.parameters.n_clusters + ' зон';
  const labels = [
    'Pulse',
    ...request.period_types.map(value => PERIOD_LABELS[value] || value),
    ...request.price_types.map(value => PRICE_LABELS[value] || value),
  ];
  $('preview-filters').innerHTML = labels.map(label => (
    '<span>' + escapeHtml(label) + '</span>'
  )).join('');
  if (state.resultRequest) {
    const stale = requestSignature(request) !== requestSignature(state.resultRequest);
    $('analysis-stale').classList.toggle('hidden', !stale);
    setMlResultStale(stale);
  }
  scheduleRawPreview();
}

function scheduleRawPreview() {
  clearTimeout(previewTimer);
  if (state.result) return;
  const request = currentRequest();
  if (validateRequest(request)) return;
  previewTimer = setTimeout(() => loadRawPreview(request), 300);
}

async function loadRawPreview(request) {
  if (state.result && state.resultRequest
      && requestSignature(request) === requestSignature(state.resultRequest)) return;
  previewController?.abort();
  previewController = new AbortController();
  try {
    const preview = await previewClustering(request, { signal: previewController.signal });
    renderClusteringPoints(preview);
    hideMapEmpty();
    const quality = preview.data_quality;
    $('preview-quality').textContent =
      fmt(quality.coordinates_resolved) + ' из ' + fmt(quality.locations_total)
      + ' точек с координатами · ' + number(quality.trip_coverage_pct) + '% перевозок';
  } catch (error) {
    if (error.name !== 'AbortError') {
      $('preview-quality').textContent = 'Не удалось загрузить исходные точки.';
    }
  }
}

async function executeClustering() {
  const request = currentRequest();
  const error = validateRequest(request);
  if (error) {
    showPersistentError(new Error(error));
    return;
  }
  clusteringController?.abort();
  clusteringController = new AbortController();
  setMapLoading(true, 'Рассчитываем ' + request.parameters.n_clusters + ' зон…');
  $('analysis-form-error').classList.add('hidden');
  try {
    const result = await runClustering(request, { signal: clusteringController.signal });
    state.result = result;
    state.resultRequest = request;
    renderClusteringPoints(result);
    renderInspector(result);
    hideMapEmpty();
    $('analysis-stale').classList.add('hidden');
    $('btn-reset-ml').classList.remove('hidden');
    setMlResultStale(false);
    showToast('Готово: ' + result.clusters.length + ' зон');
  } catch (requestError) {
    showPersistentError(requestError);
  } finally {
    setMapLoading(false);
  }
}

function showPersistentError(error) {
  $('analysis-form-error').textContent = error.message || String(error);
  $('analysis-form-error').classList.remove('hidden');
  showToast(error.message || String(error), 'error', 6000);
}

function renderInspector(result) {
  $('inspector-empty').classList.add('hidden');
  $('inspector-result').classList.remove('hidden');
  const quality = result.data_quality;
  const totalTrips = result.clusters.reduce((sum, cluster) => sum + cluster.trip_count, 0);
  $('result-k').textContent = result.clusters.length;
  $('result-cities').textContent = fmt(quality.coordinates_resolved);
  $('result-bids').textContent = fmt(totalTrips);
  $('result-region').textContent = result.analysis.origin.name + ' → ' + result.analysis.destination_region;
  $('result-data').textContent = [
    ...result.analysis.filters.period_types.map(value => PERIOD_LABELS[value] || value),
    ...result.analysis.filters.price_types.map(value => PRICE_LABELS[value] || value),
  ].join(' · ');
  $('result-weight').textContent = result.analysis.parameters.weight_mode === 'trip_count'
    ? 'По количеству перевозок'
    : 'Все точки одинаково';
  $('result-silhouette').textContent = number(result.metrics.silhouette, 3);
  $('result-mean-distance').textContent = distance(result.metrics.mean_distance_to_medoid_m);
  $('result-p95-distance').textContent = distance(result.metrics.p95_distance_to_medoid_m);
  $('result-max-distance').textContent = distance(result.metrics.max_distance_to_medoid_m);
  renderTerritorialMetrics(result);
  renderQuality(quality);
  renderWarnings(result);
  renderClusterList(result);
}

function renderTerritorialMetrics(result) {
  const section = $('territorial-metrics');
  section.classList.toggle('hidden', !result.territorial_metrics);
  if (!result.territorial_metrics) return;
  $('territorial-coverage').textContent = number(result.territorial_metrics.coverage_pct) + '%';
  $('territorial-overlap').textContent = number(result.territorial_metrics.overlap_pct) + '%';
  $('territorial-fragmented').textContent = fmt(result.territorial_metrics.fragmented_zone_count);
}

function renderQuality(quality) {
  $('quality-used').textContent = fmt(quality.coordinates_resolved)
    + ' / ' + fmt(quality.locations_total);
  $('quality-ratio').textContent = number(quality.location_coverage_pct) + '%';
  $('quality-fill').style.width = quality.location_coverage_pct + '%';
  $('quality-note').textContent = 'FIAS: ' + fmt(quality.fias_locations)
    + ' · fallback: ' + fmt(quality.fallback_locations)
    + ' · покрытие перевозок: ' + number(quality.trip_coverage_pct) + '%.';
  $('quality-unresolved-summary').textContent = quality.coordinates_unresolved
    ? fmt(quality.coordinates_unresolved) + ' точек исключены'
    : 'Нет исключённых точек';
  $('quality-unresolved-list').innerHTML = quality.unresolved.map(point => (
    '<div><strong>' + escapeHtml(point.name) + '</strong><span>'
      + fmt(point.trip_count) + ' перевозок</span></div>'
  )).join('');
}

function renderWarnings(result) {
  const warnings = [];
  if (!result.zones.available) {
    warnings.push(
      '<p><strong>Кластеры рассчитаны.</strong> Границы зон пока недоступны: '
      + 'для региона не подключена утверждённая геометрия.</p>',
    );
  }
  if (result.data_quality.coordinates_unresolved) {
    warnings.push('<p>' + fmt(result.data_quality.coordinates_unresolved)
      + ' точек без координат исключены из ML.</p>');
  }
  $('result-warnings').innerHTML = warnings.join('');
  $('result-warnings').classList.toggle('hidden', !warnings.length);
}

function renderClusterList(result) {
  $('zones-count').textContent = result.clusters.length;
  $('zone-list').innerHTML = '';
  result.clusters.forEach((cluster, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'zone-card';
    button.dataset.zoneId = cluster.cluster_id;
    button.style.setProperty('--zone-color', ZONE_COLORS[index % ZONE_COLORS.length]);
    button.innerHTML = '<span class="zone-card-swatch"></span>'
      + '<span class="zone-card-main"><strong>' + zoneLabel(cluster.cluster_id) + '</strong><span>'
      + fmt(cluster.point_count) + ' точек</span></span>'
      + '<span class="zone-card-bids"><strong>' + fmt(cluster.trip_count)
      + '</strong><span>перевозок</span></span>';
    button.addEventListener('mouseenter', () => highlightCluster(cluster.cluster_id));
    button.addEventListener('mouseleave', () => highlightCluster(null));
    button.addEventListener('click', () => chooseCluster(cluster.cluster_id, true, result));
    $('zone-list').appendChild(button);
  });
}

function chooseCluster(clusterId, focus = false, result = state.result) {
  const cluster = result?.clusters.find(item => Number(item.cluster_id) === Number(clusterId));
  if (!cluster) return;
  document.querySelectorAll('.zone-card').forEach(card => {
    card.classList.toggle('selected', Number(card.dataset.zoneId) === Number(clusterId));
  });
  highlightCluster(clusterId, focus);
  const color = ZONE_COLORS[result.clusters.indexOf(cluster) % ZONE_COLORS.length];
  $('zone-details').classList.remove('hidden');
  $('zone-details-swatch').style.background = color;
  $('zone-details-title').textContent = 'Зона ' + zoneLabel(cluster.cluster_id);
  $('zone-details-cities').textContent = fmt(cluster.point_count);
  $('zone-details-bids').textContent = fmt(cluster.trip_count);
  const medoid = result.points.find(point => point.id === cluster.medoid_point_id);
  $('zone-medoid').textContent = medoid?.name || cluster.medoid_point_id;
  $('zone-details-towns').innerHTML = result.points
    .filter(point => Number(point.cluster_id) === Number(clusterId))
    .sort((left, right) => left.name.localeCompare(right.name, 'ru'))
    .map(point => '<div><strong>' + escapeHtml(point.name) + '</strong><small>'
      + escapeHtml(point.fias_id) + '</small><span>' + fmt(point.trip_count)
      + ' перевозок</span></div>')
    .join('');
}

function clearClusterSelection() {
  highlightCluster(null);
  document.querySelectorAll('.zone-card').forEach(card => card.classList.remove('selected'));
  $('zone-details').classList.add('hidden');
}

function renderEmptyInspector() {
  $('inspector-result').classList.add('hidden');
  $('inspector-empty').classList.remove('hidden');
  $('btn-reset-ml').classList.add('hidden');
}

function resetClustering() {
  state.result = null;
  state.resultRequest = null;
  clearClusteringResult();
  renderEmptyInspector();
  $('analysis-stale').classList.add('hidden');
  $('analysis-form-error').classList.add('hidden');
  setMapEmpty('Настройте территориальный анализ', 'Выберите точку отправления и регион доставки.');
  scheduleRawPreview();
}

function switchMode(mode) {
  if (!['data', 'cluster'].includes(mode) || state.mode === mode) return;
  state.mode = mode;
  const clusteringMode = mode === 'cluster';
  $('workspace').classList.toggle('mode-cluster', clusteringMode);
  $('workspace').classList.toggle('mode-data', !clusteringMode);
  $('cluster-controls').classList.toggle('hidden', !clusteringMode);
  $('data-controls').classList.toggle('hidden', clusteringMode);
  $('controls-title').textContent = clusteringMode ? 'Территориальные зоны' : 'Исходные данные';
  document.querySelectorAll('.mode-tab').forEach(button => {
    button.classList.toggle('active', button.dataset.mode === mode);
  });
  $('map-info').classList.toggle('hidden', clusteringMode || !state.lastData);
  $('map-legend').classList.toggle('hidden', clusteringMode || !state.lastData);
  if (clusteringMode) {
    if (state.result) {
      renderClusteringPoints(state.result);
      hideMapEmpty();
    } else {
      scheduleRawPreview();
    }
  } else if (state.lastData) {
    renderPoints(state.lastData.shipment_points, state.lastData.delivery_points);
    hideMapEmpty();
  } else {
    clearMarkers();
    setMapEmpty('Выберите направление или регион', 'Настройте фильтры слева.', false);
  }
  window.setTimeout(() => window.dispatchEvent(new Event('resize')), 60);
}

async function loadAndRenderPoints() {
  const filters = getFilters();
  pointsController?.abort();
  if (!filters.fromRegions.length && !filters.toRegions.length) {
    setMapEmpty('Выберите направление или регион', 'Настройте фильтры слева.', false);
    return;
  }
  pointsController = new AbortController();
  setMapLoading(true, 'Обновляем карту…');
  try {
    const data = await fetchPoints(filters, { signal: pointsController.signal });
    state.lastData = data;
    if (state.mode === 'data') renderPoints(data.shipment_points, data.delivery_points);
    $('info-ship').textContent = fmt(data.total_ship);
    $('info-del').textContent = fmt(data.total_del);
    $('info-geocoded').textContent = fmt(data.geocoded);
    $('map-info').classList.remove('hidden');
    $('map-legend').classList.remove('hidden');
    if (data.total_ship + data.total_del) hideMapEmpty();
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    setMapLoading(false);
  }
}

function initTheme() {
  let theme = localStorage.getItem('app-theme') || 'light';
  const apply = next => {
    theme = next;
    document.documentElement.toggleAttribute('data-theme', next === 'dark');
    localStorage.setItem('app-theme', next);
    setThemeLayer(next);
  };
  apply(theme);
  $('theme-toggle-header').addEventListener('click', () => {
    apply(theme === 'dark' ? 'light' : 'dark');
  });
}

function initInteractions() {
  document.querySelectorAll('.mode-tab').forEach(button => {
    button.addEventListener('click', () => switchMode(button.dataset.mode));
  });
  $('btn-apply').addEventListener('click', loadAndRenderPoints);
  $('btn-reset').addEventListener('click', () => {
    resetFilters();
    state.lastData = null;
    clearMarkers();
  });
  $('cluster-controls').addEventListener('submit', event => {
    event.preventDefault();
    executeClustering();
  });
  $('cluster-controls').addEventListener('change', updatePreviewText);
  $('cluster-origin').addEventListener('focus', () => loadOriginSuggestions(
    $('cluster-origin').value.trim(),
  ).catch(showPersistentError));
  $('cluster-origin').addEventListener('input', onOriginInput);
  $('cluster-region').addEventListener('change', updatePreviewText);
  $('cluster-k-value').addEventListener('input', updatePreviewText);
  $('btn-reset-ml').addEventListener('click', resetClustering);
  $('zone-details-close').addEventListener('click', clearClusterSelection);
  document.querySelectorAll('[data-clustering-layer]').forEach(input => {
    input.addEventListener('change', () => {
      if (input.dataset.clusteringLayer === 'zones') {
        setMlLayerVisibility('zones', input.checked);
      } else {
        setClusteringLayers(input.dataset.clusteringLayer, input.checked);
      }
    });
  });
  for (const eventName of ['clustering-point-select', 'ml-zone-select']) {
    window.addEventListener(eventName, event => {
      if (event.detail.clusterId != null) chooseCluster(event.detail.clusterId);
    });
  }
  $('mobile-controls-btn').addEventListener('click', () => $('sidebar').classList.add('open'));
  $('mobile-inspector-btn').addEventListener('click', () => $('analysis-inspector').classList.add('open'));
  document.querySelectorAll('[data-close-panel]').forEach(button => {
    button.addEventListener('click', () => button.closest('aside').classList.remove('open'));
  });
  $('modal-close').addEventListener('click', () => $('records-modal').classList.add('hidden'));
  $('modal-overlay').addEventListener('click', () => $('records-modal').classList.add('hidden'));
}

function initMapEvents() {
  window.addEventListener('show-records-modal', async event => {
    const { town, region, type } = event.detail;
    $('records-modal').classList.remove('hidden');
    $('modal-title').textContent = town;
    try {
      const result = await fetchRecords(town, region, type, getFilters());
      $('records-tbody').innerHTML = result.records.map(record => (
        '<tr><td>' + escapeHtml(record.price) + '</td><td>' + escapeHtml(record.route_length)
        + '</td><td>' + number(record.rub_per_km) + '</td><td>' + escapeHtml(record.bid_count)
        + '</td><td>' + escapeHtml(record.period_type) + '</td><td>'
        + escapeHtml(record.price_type) + '</td><td>' + escapeHtml(record.confidence || '—')
        + '</td><td>' + escapeHtml(record.ship_region) + '</td><td>'
        + escapeHtml(record.del_region) + '</td></tr>'
      )).join('');
    } catch (error) {
      $('modal-error').textContent = error.message;
      $('modal-error').classList.remove('hidden');
    }
  });
  window.addEventListener('regeocode-point', async event => {
    try {
      await regeocodeTown(event.detail.town, event.detail.region);
    } catch (error) {
      showToast(error.message, 'error');
    }
  });
}

function startGeocodePolling() {
  window.setInterval(async () => {
    try {
      const status = await fetchGeocodeStatus();
      const active = status.running && status.total > 0;
      $('geocode-status').classList.toggle('hidden', !active);
      if (active) {
        $('geocode-status-text').textContent = 'Координаты: ' + status.done + '/' + status.total;
        $('geocode-progress-fill').style.width = Math.round(status.done / status.total * 100) + '%';
      }
    } catch (error) {
      console.warn(error);
    }
  }, 5000);
}

async function main() {
  setSystemStatus('loading', 'Инициализация');
  try {
    initMap('map');
    initTheme();
    initInteractions();
    initMapEvents();
    const [regions, options] = await Promise.all([
      fetchRegions(),
      fetchClusteringOptions(),
      fetchStats(),
      loadOriginSuggestions(),
    ]);
    initFilters(regions.ship_regions, regions.del_regions, () => {});
    optionChecks('cluster-periods', options.period_types, ['current'], PERIOD_LABELS);
    optionChecks('cluster-prices', options.price_types, ['spot'], PRICE_LABELS);
    updatePreviewText();
    setMapEmpty('Настройте территориальный анализ', 'Выберите точку отправления и регион доставки.');
    setSystemStatus('', 'Данные готовы');
    startGeocodePolling();
  } catch (error) {
    console.error(error);
    setSystemStatus('error', 'Недоступно');
    setMapEmpty('Не удалось запустить приложение', error.message, false);
  } finally {
    setMapLoading(false);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', main);
} else {
  main();
}
