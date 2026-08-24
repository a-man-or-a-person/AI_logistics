/**
 * app.js — состояние двух рабочих режимов и синхронизация UI с картой.
 */

import {
  fetchGeocodeStatus,
  fetchMlClusters,
  fetchPoints,
  fetchRecords,
  fetchRegions,
  fetchStats,
  regeocodeTown,
} from './api.js';
import { getFilters, initFilters, resetFilters } from './filters.js';
import {
  clearMarkers,
  clearMlClusters,
  focusMlZone,
  initMap,
  renderMlClusters,
  renderPoints,
  selectMlZone,
  setMlLayerVisibility,
  setMlResultStale,
  setThemeLayer,
} from './map.js';

const $ = id => document.getElementById(id);
const fmt = value => Number(value || 0).toLocaleString('ru-RU');
const ZONE_COLORS = ['#d84f4f', '#3478c5', '#198a68', '#d28a18', '#7a5ac8', '#c54a88', '#1d9690', '#d5662a', '#5a61c5', '#75a62c'];
const PERIOD_LABELS = { retro: 'Архив', current: 'Текущий', forecast: 'Прогноз' };
const PRICE_LABELS = { spot: 'Спот', tender: 'Тендер' };
const TYPE_LABELS = { shipment: 'Отгрузка', delivery: 'Доставка' };

const state = {
  mode: 'cluster',
  validRegions: new Set(),
  lastData: null,
  mlResult: null,
  resultParams: null,
  resultSignature: null,
  selectedZoneId: null,
};

let toastTimer = null;
let pointsController = null;
let geocodeInterval = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[char]);
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
  button?.classList.toggle('loading', active);
  if (button) button.disabled = active;
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

function checkedValue(name) {
  return document.querySelector(`input[name="${name}"]:checked`)?.value;
}

function getClusterParams() {
  const kMode = checkedValue('ml-k-mode') || 'auto';
  return {
    region: $('ml-region-input').value.trim(),
    type: checkedValue('ml-type') || 'delivery',
    period: checkedValue('ml-period') || 'current',
    price: checkedValue('ml-price') || 'spot',
    kMode,
    k: kMode === 'auto' ? 'auto' : Number($('ml-k-value').value || $('ml-k-value').textContent || 5),
    weightMode: checkedValue('ml-weight') || 'trip_count',
  };
}

function paramsSignature(params) {
  return JSON.stringify({
    region: params.region,
    type: params.type,
    period: params.period,
    price: params.price,
    k: params.k,
    weightMode: params.weightMode,
  });
}

function updateClusterPreview() {
  const params = getClusterParams();
  $('preview-region').textContent = params.region || 'Регион не выбран';
  $('preview-type').textContent = TYPE_LABELS[params.type];
  $('preview-period').textContent = PERIOD_LABELS[params.period];
  $('preview-price').textContent = PRICE_LABELS[params.price];
  $('run-caption').textContent = `K-Means · ${params.kMode === 'auto' ? 'Auto K' : `K = ${params.k}`}`;

  const stale = Boolean(state.mlResult && paramsSignature(params) !== state.resultSignature);
  $('analysis-stale').classList.toggle('hidden', !stale);
  if (stale) {
    const old = state.resultParams;
    $('stale-description').textContent = `На карте: ${PERIOD_LABELS[old.period]} · ${PRICE_LABELS[old.price]}. Пересчитайте зоны.`;
  }
  setMlResultStale(stale);
}

function switchMode(mode) {
  if (!['data', 'cluster'].includes(mode) || state.mode === mode) return;
  state.mode = mode;
  const clusterMode = mode === 'cluster';
  $('workspace').classList.toggle('mode-cluster', clusterMode);
  $('workspace').classList.toggle('mode-data', !clusterMode);
  $('cluster-controls').classList.toggle('hidden', !clusterMode);
  $('data-controls').classList.toggle('hidden', clusterMode);
  $('controls-eyebrow').textContent = clusterMode ? 'Настройка анализа' : 'Фильтры карты';
  $('controls-title').textContent = clusterMode ? 'Территориальные зоны' : 'Исходные данные';
  document.querySelectorAll('.mode-tab').forEach(button => {
    const active = button.dataset.mode === mode;
    button.classList.toggle('active', active);
    active ? button.setAttribute('aria-current', 'page') : button.removeAttribute('aria-current');
  });
  $('map-info').classList.toggle('hidden', clusterMode || !state.lastData);
  $('map-legend').classList.toggle('hidden', clusterMode || !state.lastData);
  $('experimental-badge').classList.toggle('hidden', !clusterMode || !state.mlResult);

  if (clusterMode) {
    if (state.mlResult) {
      renderMlClusters(state.mlResult.clusters);
      hideMapEmpty();
      if (state.selectedZoneId != null) selectMlZone(state.selectedZoneId, false);
    } else {
      clearMarkers();
      setMapEmpty('Создайте первое разбиение региона', 'Выберите территорию и параметры анализа, затем рассчитайте зоны.', true);
    }
  } else if (state.lastData) {
    renderPoints(state.lastData.shipment_points, state.lastData.delivery_points);
    const total = state.lastData.total_ship + state.lastData.total_del;
    total ? hideMapEmpty() : setMapEmpty('По выбранным параметрам данных нет', 'Измените период, тип цены или регионы.', false);
  } else {
    clearMarkers();
    setMapEmpty('Выберите направление или регион', 'Настройте фильтры слева и покажите исходные точки на карте.', false);
  }
  window.setTimeout(() => window.dispatchEvent(new Event('resize')), 60);
}

async function loadAndRenderPoints() {
  const filters = getFilters();
  pointsController?.abort();
  if (!filters.fromRegions.length && !filters.toRegions.length) {
    state.lastData = null;
    clearMarkers();
    $('map-info').classList.add('hidden');
    $('map-legend').classList.add('hidden');
    setMapEmpty('Выберите направление или регион', 'Настройте фильтры слева и покажите исходные точки на карте.', false);
    return;
  }

  pointsController = new AbortController();
  setMapLoading(true, 'Обновляем карту…', 'Старые параметры сохранятся до завершения запроса');
  try {
    const data = await fetchPoints({
      fromRegions: filters.fromRegions,
      toRegions: filters.toRegions,
      periodTypes: filters.periodTypes,
      priceTypes: filters.priceTypes,
    }, { signal: pointsController.signal });
    state.lastData = data;
    if (state.mode === 'data') renderPoints(data.shipment_points, data.delivery_points);
    $('info-ship').textContent = fmt(data.total_ship);
    $('info-del').textContent = fmt(data.total_del);
    $('info-geocoded').textContent = fmt(data.geocoded);
    $('map-info').classList.remove('hidden');
    $('map-legend').classList.remove('hidden');
    const total = data.total_ship + data.total_del;
    total ? hideMapEmpty() : setMapEmpty('По выбранным параметрам данных нет', 'Измените период, тип цены или регионы.', false);
  } catch (error) {
    if (error.name !== 'AbortError') {
      setMapEmpty('Не удалось загрузить данные региона', error.message, false);
      showToast(`Не удалось обновить карту: ${error.message}`, 'error', 6000);
    }
  } finally {
    setMapLoading(false);
  }
}

function renderInspector(result, params) {
  const clusters = result.clusters || [];
  const totalCities = clusters.reduce((sum, cluster) => sum + Number(cluster.points_count || 0), 0);
  const totalBids = Number(result.region_total_bids ?? clusters.reduce((sum, cluster) => sum + Number(cluster.total_bids || 0), 0));
  $('inspector-empty').classList.add('hidden');
  $('inspector-result').classList.remove('hidden');
  $('result-k').textContent = result.k;
  $('result-mode').textContent = params.kMode === 'auto' ? 'Auto K' : `K = ${params.k}`;
  $('result-cities').textContent = fmt(totalCities);
  $('result-bids').textContent = fmt(totalBids);
  $('result-region').textContent = params.region;
  $('result-type').textContent = TYPE_LABELS[params.type];
  $('result-data').textContent = `Pulse · ${PERIOD_LABELS[params.period]} · ${PRICE_LABELS[params.price]}`;
  $('result-k-detail').textContent = params.kMode === 'auto' ? `Auto → ${result.k}` : String(result.k);

  const silhouette = Number(result.metrics?.silhouette ?? result.silhouette);
  const hasSilhouette = Number.isFinite(silhouette) && silhouette >= -1;
  $('metrics-section').classList.toggle('hidden', !hasSilhouette);
  if (hasSilhouette) $('result-silhouette').textContent = silhouette.toFixed(2);

  const quality = result.data_quality || {};
  const used = Number(quality.used_points ?? totalCities);
  const total = Number(quality.total_points ?? used);
  const excluded = Math.max(0, Number(quality.excluded_no_coordinates ?? total - used));
  const ratio = total ? Math.round((used / total) * 100) : 0;
  $('quality-used').textContent = `${fmt(used)} / ${fmt(total)}`;
  $('quality-ratio').textContent = `${ratio}%`;
  $('quality-fill').style.width = `${ratio}%`;
  $('quality-note').textContent = excluded
    ? `${fmt(excluded)} ${excluded === 1 ? 'точка исключена' : 'точки исключены'}: координаты недоступны.`
    : 'Все найденные точки имеют координаты.';

  $('zones-count').textContent = `${clusters.length}`;
  const zoneList = $('zone-list');
  zoneList.innerHTML = '';
  clusters.forEach((cluster, index) => {
    const id = Number(cluster.id);
    const color = ZONE_COLORS[index % ZONE_COLORS.length];
    const share = totalBids ? Math.round((Number(cluster.total_bids || 0) / totalBids) * 100) : 0;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'zone-card';
    button.dataset.zoneId = String(id);
    button.style.setProperty('--zone-color', color);
    button.innerHTML = `<span class="zone-card-swatch"></span><span class="zone-card-main"><strong>Z${id + 1}</strong><span>${fmt(cluster.points_count)} городов</span></span><span class="zone-card-bids"><strong>${fmt(cluster.total_bids)}</strong><span>${share}% перевозок</span></span>`;
    button.addEventListener('mouseenter', () => selectMlZone(id, false));
    button.addEventListener('mouseleave', () => selectMlZone(state.selectedZoneId, false));
    button.addEventListener('click', () => chooseZone(id, true));
    zoneList.appendChild(button);
  });
}

function chooseZone(zoneId, focus = false) {
  if (!state.mlResult) return;
  const cluster = state.mlResult.clusters.find(item => Number(item.id) === Number(zoneId));
  if (!cluster) return;
  state.selectedZoneId = Number(zoneId);
  document.querySelectorAll('.zone-card').forEach(card => card.classList.toggle('selected', Number(card.dataset.zoneId) === state.selectedZoneId));
  selectMlZone(state.selectedZoneId, false);
  if (focus) focusMlZone(state.selectedZoneId);

  const clusterIndex = state.mlResult.clusters.indexOf(cluster);
  const color = ZONE_COLORS[clusterIndex % ZONE_COLORS.length];
  $('zone-details').classList.remove('hidden');
  $('zone-details-swatch').style.background = color;
  $('zone-details-title').textContent = `Зона Z${Number(cluster.id) + 1}`;
  $('zone-details-cities').textContent = fmt(cluster.points_count);
  $('zone-details-bids').textContent = fmt(cluster.total_bids);
  $('zone-details-towns').innerHTML = (cluster.points || [])
    .slice().sort((a, b) => String(a.town).localeCompare(String(b.town), 'ru'))
    .map(point => `<li>${escapeHtml(point.town || 'Без названия')}</li>`).join('');
}

function clearZoneSelection() {
  state.selectedZoneId = null;
  selectMlZone(null, false);
  document.querySelectorAll('.zone-card').forEach(card => card.classList.remove('selected'));
  $('zone-details').classList.add('hidden');
}

async function runClustering() {
  const params = getClusterParams();
  $('analysis-form-error').classList.add('hidden');
  if (!params.region || !state.validRegions.has(params.region)) {
    $('analysis-form-error').textContent = 'Выберите регион из списка доступных значений.';
    $('analysis-form-error').classList.remove('hidden');
    $('ml-region-input').focus();
    return;
  }

  setMapLoading(true, 'Рассчитываем зоны…', `K-Means · ${params.kMode === 'auto' ? 'автоподбор количества зон' : `K = ${params.k}`}`);
  try {
    const result = await fetchMlClusters({
      region: params.region,
      type: params.type,
      k: params.k,
      weightMode: params.weightMode,
      filters: { periodTypes: [params.period], priceTypes: [params.price] },
    });
    if (!result.clusters?.length) {
      throw new Error('Недостаточно географических точек для кластеризации. Попробуйте другой период или тип цены.');
    }
    state.mlResult = result;
    state.resultParams = params;
    state.resultSignature = paramsSignature(params);
    state.selectedZoneId = null;
    renderMlClusters(result.clusters);
    renderInspector(result, params);
    hideMapEmpty();
    $('experimental-badge').classList.remove('hidden');
    $('btn-reset-ml').classList.remove('hidden');
    $('analysis-stale').classList.add('hidden');
    setMlResultStale(false);
    showToast(`Рассчитано ${result.k} зон для ${params.region}`, 'success');
  } catch (error) {
    $('analysis-form-error').textContent = error.message;
    $('analysis-form-error').classList.remove('hidden');
    setMapEmpty('Не удалось выполнить кластеризацию', error.message, false);
    showToast(`Расчёт не выполнен: ${error.message}`, 'error', 6000);
  } finally {
    setMapLoading(false);
  }
}

function resetClustering() {
  state.mlResult = null;
  state.resultParams = null;
  state.resultSignature = null;
  state.selectedZoneId = null;
  clearMlClusters();
  $('inspector-result').classList.add('hidden');
  $('inspector-empty').classList.remove('hidden');
  $('btn-reset-ml').classList.add('hidden');
  $('experimental-badge').classList.add('hidden');
  $('analysis-stale').classList.add('hidden');
  $('analysis-form-error').classList.add('hidden');
  setMapEmpty('Создайте первое разбиение региона', 'Выберите территорию и параметры анализа, затем рассчитайте зоны.', true);
}

function initTheme() {
  let theme = localStorage.getItem('app-theme') || 'light';
  const apply = next => {
    theme = next;
    document.documentElement.toggleAttribute('data-theme', next === 'dark');
    if (next === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    localStorage.setItem('app-theme', next);
    setThemeLayer(next);
    $('theme-toggle-header').title = next === 'dark' ? 'Переключить на светлую тему' : 'Переключить на тёмную тему';
  };
  apply(theme);
  $('theme-toggle-header').addEventListener('click', () => apply(theme === 'dark' ? 'light' : 'dark'));
}

function initInteractions() {
  document.querySelectorAll('.mode-tab').forEach(button => button.addEventListener('click', () => switchMode(button.dataset.mode)));
  $('btn-apply').addEventListener('click', loadAndRenderPoints);
  $('btn-reset').addEventListener('click', () => { resetFilters(); state.lastData = null; clearMarkers(); $('map-info').classList.add('hidden'); $('map-legend').classList.add('hidden'); setMapEmpty('Выберите направление или регион', 'Настройте фильтры слева и покажите исходные точки на карте.', false); });
  $('cluster-controls').addEventListener('submit', event => { event.preventDefault(); runClustering(); });
  $('cluster-controls').addEventListener('change', updateClusterPreview);
  $('ml-region-input').addEventListener('input', updateClusterPreview);
  document.querySelectorAll('input[name="ml-k-mode"]').forEach(input => input.addEventListener('change', () => { $('ml-k-stepper').classList.toggle('hidden', input.value !== 'manual' || !input.checked); updateClusterPreview(); }));
  const changeK = delta => { const output = $('ml-k-value'); output.value = Math.min(10, Math.max(2, Number(output.value || output.textContent) + delta)); output.textContent = output.value; updateClusterPreview(); };
  $('ml-k-minus').addEventListener('click', () => changeK(-1));
  $('ml-k-plus').addEventListener('click', () => changeK(1));
  $('btn-reset-ml').addEventListener('click', resetClustering);
  $('zone-details-close').addEventListener('click', clearZoneSelection);
  document.querySelectorAll('[data-ml-layer]').forEach(input => input.addEventListener('change', () => setMlLayerVisibility(input.dataset.mlLayer, input.checked)));

  window.addEventListener('ml-zone-select', event => chooseZone(event.detail.clusterId, false));
  window.addEventListener('ml-zone-hover', event => {
    const id = event.detail.clusterId;
    document.querySelectorAll('.zone-card').forEach(card => card.classList.toggle('map-hover', id != null && Number(card.dataset.zoneId) === Number(id)));
  });

  $('mobile-controls-btn').addEventListener('click', () => $('sidebar').classList.add('open'));
  $('mobile-inspector-btn').addEventListener('click', () => $('analysis-inspector').classList.add('open'));
  document.querySelectorAll('[data-close-panel]').forEach(button => button.addEventListener('click', () => button.closest('aside').classList.remove('open')));
  $('modal-close').addEventListener('click', closeModal);
  $('modal-overlay').addEventListener('click', closeModal);
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    closeModal();
    $('sidebar').classList.remove('open');
    $('analysis-inspector').classList.remove('open');
  });
}

function closeModal() {
  $('records-modal').classList.add('hidden');
}

async function showRecords({ town, region, type }) {
  $('records-modal').classList.remove('hidden');
  $('modal-title').textContent = `${type === 'shipment' ? 'Отгрузки из' : 'Доставки в'}: ${town}`;
  $('records-tbody').innerHTML = '';
  $('modal-loading').classList.remove('hidden');
  $('modal-error').classList.add('hidden');
  try {
    const filters = getFilters();
    const result = await fetchRecords(town, region, type, filters);
    $('modal-loading').classList.add('hidden');
    $('records-tbody').innerHTML = result.records.length ? result.records.map(record => {
      const price = Number(record.price || 0);
      const distance = Number(record.route_length || 0);
      return `<tr><td>${escapeHtml(fmt(price))}</td><td>${escapeHtml(fmt(distance))}</td><td>${escapeHtml((price / (distance || 1)).toLocaleString('ru-RU', { maximumFractionDigits: 1 }))}</td><td>${escapeHtml(record.bid_count)}</td><td>${escapeHtml(record.period_label || record.period_type)}</td><td>${record.price_type === 'spot' ? 'Спот' : 'Тендер'}</td><td>${escapeHtml(record.confidence || '—')}</td><td>${escapeHtml(record.ship_region)}</td><td>${escapeHtml(record.del_region)}</td></tr>`;
    }).join('') : '<tr><td colspan="9">По выбранным параметрам записей нет.</td></tr>';
  } catch (error) {
    $('modal-loading').classList.add('hidden');
    $('modal-error').classList.remove('hidden');
    $('modal-error').textContent = `Не удалось загрузить исходные данные: ${error.message}`;
  }
}

function initMapEvents() {
  window.addEventListener('show-records-modal', event => showRecords(event.detail));
  window.addEventListener('regeocode-point', async event => {
    try {
      await regeocodeTown(event.detail.town, event.detail.region);
      if (state.mode === 'data') await loadAndRenderPoints();
      showToast(`Координаты для ${event.detail.town} обновлены`);
    } catch (error) { showToast(`Не удалось обновить координаты: ${error.message}`, 'error'); }
  });
  window.addEventListener('regeocode-all-points', async event => {
    for (const point of event.detail.points) {
      try { await regeocodeTown(point.town, point.region); } catch (error) { console.warn(error); }
    }
    if (state.mode === 'data') await loadAndRenderPoints();
  });
}

function startGeocodePolling() {
  geocodeInterval = window.setInterval(async () => {
    try {
      const status = await fetchGeocodeStatus();
      const active = status.running && status.total > 0;
      $('geocode-status').classList.toggle('hidden', !active);
      if (active) {
        const ratio = Math.round((status.done / status.total) * 100);
        $('geocode-status-text').textContent = `Координаты: ${status.done}/${status.total}`;
        $('geocode-progress-fill').style.width = `${ratio}%`;
      }
    } catch (error) { console.warn('Geocode status:', error.message); }
  }, 5000);
}

async function main() {
  setSystemStatus('loading', 'Инициализация');
  try {
    initMap('map');
    initTheme();
    initInteractions();
    initMapEvents();
    const [regions] = await Promise.all([fetchRegions(), fetchStats()]);
    initFilters(regions.ship_regions, regions.del_regions, () => {});
    const allRegions = [...new Set([...regions.ship_regions, ...regions.del_regions])].sort((a, b) => a.localeCompare(b, 'ru'));
    state.validRegions = new Set(allRegions);
    $('ml-region-options').replaceChildren(...allRegions.map(region => { const option = document.createElement('option'); option.value = region; return option; }));
    updateClusterPreview();
    setMapEmpty('Создайте первое разбиение региона', 'Выберите территорию и параметры анализа, затем рассчитайте зоны.', true);
    setSystemStatus('', 'Данные готовы');
    startGeocodePolling();
  } catch (error) {
    console.error(error);
    setSystemStatus('error', 'Недоступно');
    setMapEmpty('Не удалось запустить приложение', error.message, false);
    showToast(`Ошибка инициализации: ${error.message}`, 'error', 7000);
  } finally {
    setMapLoading(false);
  }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main);
else main();
