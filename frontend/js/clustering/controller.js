import {
  fetchClusteringOptions, fetchClusteringOrigins, fetchClusteringPointRows, runClustering,
  runClusteringComparison,
} from '../api.js';
import {
  buildRequest, createClusteringState, datasetSnapshot, isComparisonStale,
  isResultStale, modeParameter, rejectDataSnapshot, requestSignature, setResult, updateClusteringOptions,
} from './state.js';
import { readChecks, renderFormState, renderOptionControls } from './controls.js';
import { renderErrorState, renderInspector } from './inspector.js';
import { renderComparison } from './comparison.js';
import { MODE_LABELS, PERIOD_LABELS, PRICE_LABELS } from './formatters.js';
import { renderClusterTable } from './table.js';
import {
  clearClusteringResult, focusClusteringPoint, highlightCluster, hoverCluster,
  renderClusteringPoints, setClusteringLayers, setMlResultStale,
} from '../map.js';

const $ = id => document.getElementById(id);
let state;
let originOptions = [];
let originTimer;
let runController;
let pointRowsController;
let comparisonFocusReturn;

export async function initClustering() {
  $('options-status').textContent = 'Загружаем направления…';
  $('options-status').classList.remove('hidden');
  const options = await fetchClusteringOptions();
  state = createClusteringState(options);
  renderOptionControls(state);
  wireEvents();
  await searchOrigins('');
  $('options-status').classList.add('hidden');
  renderAll();
  return { show, getState: () => state };
}

export function show() {
  if (state.result.data) renderClusteringPoints(state.result.data);
  renderAll();
}

function wireEvents() {
  $('clustering-controls').addEventListener('submit', event => {
    event.preventDefault();
    executeRun();
  });
  $('clustering-controls').addEventListener('change', event => {
    syncForm(event);
    renderAll();
  });
  $('clustering-controls').addEventListener('input', event => {
    if (event.target.id === 'manual-k') {
      syncForm(event);
      renderAll();
    }
  });
  $('cluster-origin').addEventListener('input', onOriginInput);
  $('cluster-origin').addEventListener('focus', () => showOriginOptions());
  $('cluster-origin').addEventListener('keydown', onOriginKeydown);
  $('cluster-region').addEventListener('change', async () => {
    state.form.destinationRegion = $('cluster-region').value;
    if (state.form.origin && state.form.destinationRegion) await loadContextOptions();
    renderAll();
  });
  document.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => {
    const input = $(button.dataset.step);
    input.value = Number(input.value || 0) + Number(button.dataset.delta);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }));
  document.querySelectorAll('.option-search').forEach(input => input.addEventListener('input', () => {
    document.querySelectorAll(`#${input.dataset.filterOptions} .check-chip`).forEach(label => {
      label.classList.toggle('hidden', !label.textContent.toLocaleLowerCase('ru').includes(input.value.toLocaleLowerCase('ru')));
    });
  }));
  document.querySelectorAll('[data-clustering-layer]').forEach(input => input.addEventListener('change', () => {
    setClusteringLayers(input.dataset.clusteringLayer, input.checked);
  }));
  $('btn-reset-clustering').addEventListener('click', reset);
  $('cluster-details-close').addEventListener('click', () => selectCluster(null));
  $('compare-modes').addEventListener('click', openComparison);
  $('close-comparison').addEventListener('click', () => {
    closeComparison();
  });
  $('rerun-comparison').addEventListener('click', runComparison);
  window.addEventListener('clustering-point-select', event => {
    if (event.detail.clusterId != null) selectCluster(event.detail.clusterId);
    selectPoint(event.detail.pointId);
  });
  window.addEventListener('ml-zone-hover', event => {
    state.ui.hoveredCluster = event.detail.clusterId;
    renderClusterTableState();
  });
  document.querySelectorAll('details.multi-select').forEach(details => {
    details.querySelector('summary')?.setAttribute('aria-expanded', String(details.open));
    details.addEventListener('toggle', () => {
      details.querySelector('summary')?.setAttribute('aria-expanded', String(details.open));
    });
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      if (state.comparison.open) closeComparison();
      hideOriginOptions();
      document.querySelectorAll('.control-panel.open,.analysis-inspector.open').forEach(panel => panel.classList.remove('open'));
    }
    if (event.key === 'Tab' && state.comparison.open) trapComparisonFocus(event);
  });
}

function syncForm(event) {
  const form = state.form;
  form.periodTypes = readChecks('cluster-periods');
  form.priceTypes = readChecks('cluster-prices');
  form.vehicleTypes = readChecks('cluster-vehicles');
  form.tonnageIds = readChecks('cluster-tonnages');
  form.mode = document.querySelector('input[name="analysis-mode"]:checked')?.value || form.mode;
  form.kMode = document.querySelector('input[name="k-mode"]:checked')?.value || form.kMode;
  form.k = Number($('manual-k').value);
  form.costWeight = Number(document.querySelector('input[name="cost-weight"]:checked')?.value ?? form.costWeight);
  form.volumeWeight = Number(document.querySelector('input[name="volume-weight"]:checked')?.value ?? form.volumeWeight);
  form.bearThreshold = Number(document.querySelector('input[name="bear-threshold"]:checked')?.value ?? form.bearThreshold);
  form.bearVolumeThreshold = Number(document.querySelector('input[name="bear-volume-threshold"]:checked')?.value ?? form.bearVolumeThreshold);
  form.singletonThreshold = modeParameter(state.modeCapabilities, form.mode, 'singleton_threshold')?.default
    ?? form.singletonThreshold;
  if (event.target.name === 'analysis-mode') state.ui.selectedCluster = null;
}

async function searchOrigins(query) {
  originOptions = await fetchClusteringOrigins(query, 30);
  $('cluster-origin-options').innerHTML = originOptions.map((origin, index) => `
    <button class="combo-option" type="button" role="option" data-origin-index="${index}">
      <strong>${escapeText(origin.name)}</strong><small>${escapeText(origin.region)}</small>
    </button>`).join('');
  document.querySelectorAll('[data-origin-index]').forEach(button => button.addEventListener('click', () => chooseOrigin(originOptions[Number(button.dataset.originIndex)])));
}

function onOriginInput() {
  if (state.form.origin && $('cluster-origin').value !== state.form.origin.name) clearOrigin();
  clearTimeout(originTimer);
  originTimer = setTimeout(async () => {
    await searchOrigins($('cluster-origin').value.trim());
    showOriginOptions();
  }, 220);
}

function onOriginKeydown(event) {
  const options = [...document.querySelectorAll('.combo-option')];
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    showOriginOptions();
    (options.find(item => item.classList.contains('active'))?.nextElementSibling || options[0])?.focus();
  } else if (event.key === 'Escape') hideOriginOptions();
}

function showOriginOptions() {
  $('cluster-origin-options').classList.toggle('hidden', !originOptions.length);
  $('cluster-origin').setAttribute('aria-expanded', String(Boolean(originOptions.length)));
}

function hideOriginOptions() {
  $('cluster-origin-options').classList.add('hidden');
  $('cluster-origin').setAttribute('aria-expanded', 'false');
}

async function chooseOrigin(origin) {
  state.form.origin = origin;
  state.form.destinationRegion = '';
  $('cluster-origin').value = origin.name;
  $('cluster-origin-meta').textContent = origin.region || 'Регион не указан';
  hideOriginOptions();
  setOptionsLoading(true, 'Загружаем регионы назначения…');
  try {
    const options = await fetchClusteringOptions(origin.fias_id);
    updateClusteringOptions(state, options);
    $('cluster-region').disabled = false;
    $('cluster-region').replaceChildren(new Option('Выберите регион…', ''));
    options.destination_regions.forEach(region => $('cluster-region').add(new Option(region, region)));
    renderAll();
  } catch (error) {
    showFormError(error.message);
  } finally {
    setOptionsLoading(false);
  }
}

async function loadContextOptions() {
  setOptionsLoading(true, 'Загружаем доступные параметры…');
  try {
    const options = await fetchClusteringOptions(
      state.form.origin.fias_id,
      state.form.destinationRegion,
    );
    updateClusteringOptions(state, options);
    const facetValues = key => new Set((options[key] || []).map(item => typeof item === 'string' ? item : item.value));
    const contextualDefault = (key, preferred) => {
      const available = [...facetValues(key)];
      const configured = state.options.defaults?.[key] || [];
      const validConfigured = configured.filter(value => available.includes(value));
      if (validConfigured.length) return validConfigured.slice(0, 1);
      return available.includes(preferred) ? [preferred] : available.slice(0, 1);
    };
    state.form.periodTypes = state.form.periodTypes.filter(value => facetValues('period_types').has(value));
    state.form.priceTypes = state.form.priceTypes.filter(value => facetValues('price_types').has(value));
    state.form.vehicleTypes = state.form.vehicleTypes.filter(value => facetValues('vehicle_types').has(value));
    state.form.tonnageIds = state.form.tonnageIds.filter(value => facetValues('tonnage_ids').has(value));
    if (!state.form.periodTypes.length) state.form.periodTypes = contextualDefault('period_types', 'current');
    if (!state.form.priceTypes.length) state.form.priceTypes = contextualDefault('price_types', 'spot');
    renderOptionControls(state);
  } catch (error) {
    showFormError(error.message);
  } finally {
    setOptionsLoading(false);
  }
}

function setOptionsLoading(loading, message = '') {
  ['cluster-region', 'btn-run-clustering'].forEach(id => { $(id).disabled = loading; });
  $('clustering-controls').classList.toggle('options-loading', loading);
  $('options-status').textContent = loading ? message : '';
  $('options-status').classList.toggle('hidden', !loading);
}

function clearOrigin() {
  state.form.origin = null;
  state.form.destinationRegion = '';
  $('cluster-region').disabled = true;
  $('cluster-region').replaceChildren(new Option('Сначала выберите точку отправления', ''));
  $('cluster-origin-meta').textContent = 'Выберите одну точку отправления';
}

function validate(request) {
  if (!request.origin_fias) return 'Выберите точку отправления из списка.';
  if (!request.destination_region) return 'Выберите один регион доставки.';
  if (!request.period_types.length) return 'Выберите хотя бы один период.';
  if (!request.price_types.length) return 'Выберите хотя бы один тип цены.';
  const capability = modeParameter(state.modeCapabilities, request.mode, 'n_clusters');
  if (capability && request.parameters.k_mode === 'manual') {
    const min = capability?.min;
    const max = capability?.max;
    if (!Number.isInteger(request.parameters.n_clusters) || request.parameters.n_clusters < min || request.parameters.n_clusters > max) return `K должен быть от ${min} до ${max}.`;
  }
  return null;
}

function cancelCalculation() {
  runController?.abort();
  runController = null;
  $('loading-overlay').classList.add('hidden');
  $('update-badge').classList.add('hidden');
  $('loading-sub').textContent = '';
  $('btn-run-clustering').disabled = false;
  if (state.result.status === 'loading') state.result.status = state.result.data?.status || 'empty';
  if (state.comparison.status === 'loading') {
    state.comparison.status = Object.keys(state.comparison.results).length ? 'success' : 'empty';
  }
}

async function executeRun() {
  cancelPointRows();
  const request = buildRequest(state.form);
  const error = validate(request);
  if (error) return showFormError(error);
  cancelCalculation();
  $('analysis-form-error').classList.add('hidden');
  const cached = state.result.cache.get(requestSignature(request));
  if (cached) {
    setResult(state, cached, request);
    showSingleRunTable(cached);
    renderClusteringPoints(cached);
    $('empty-state').classList.add('hidden');
    renderAll();
    return;
  }
  const controller = new AbortController();
  runController = controller;
  const repeated = Boolean(state.result.data);
  state.result.status = 'loading';
  renderClusterTableState();
  $('loading-overlay').classList.toggle('hidden', repeated);
  $('update-badge').classList.toggle('hidden', !repeated);
  $('loading-text').textContent = 'Рассчитываем зоны…';
  $('loading-sub').textContent = MODE_LABELS[state.form.mode] || state.form.mode;
  $('btn-run-clustering').disabled = true;
  try {
    const result = await runClustering(request, { signal: controller.signal });
    if (controller.signal.aborted) return;
    setResult(state, result, request);
    showSingleRunTable(result);
    renderClusteringPoints(result);
    $('empty-state').classList.add('hidden');
    renderAll();
  } catch (runError) {
    if (controller.signal.aborted) return;
    state.result.status = 'error';
    state.result.error = { code: runError.code, message: runError.message };
    renderErrorState(state.result.error);
    if (runError.code === 'NO_DATA') {
      $('empty-state').querySelector('.empty-title').textContent = 'По выбранным фильтрам данных нет.';
      $('empty-state').querySelector('.empty-sub').textContent = 'Измените сегмент данных и повторите расчёт.';
      $('empty-state').classList.remove('hidden');
    }
    renderClusterTableState();
  } finally {
    if (runController === controller) cancelCalculation();
  }
}

function reset() {
  cancelCalculation();
  cancelPointRows();
  state = createClusteringState(state.options);
  renderOptionControls(state);
  clearOrigin();
  clearClusteringResult();
  $('empty-state').classList.remove('hidden');
  renderAll();
}

function selectCluster(clusterId, focus = false) {
  state.ui.selectedCluster = clusterId;
  highlightCluster(clusterId, focus);
  renderInspectorState();
  renderClusterTableState();
}

function showSingleRunTable(result) {
  state.ui.tableVisible = result.cluster_table?.supported === true;
  state.ui.tableOpen = state.ui.tableVisible;
  state.ui.tableSort = { key: 'trip_count', direction: 'desc' };
  state.ui.hoveredCluster = null;
}

function openComparison() {
  comparisonFocusReturn = document.activeElement;
  state.comparison.open = true;
  state.comparison.context = datasetSnapshot(state.form);
  state.comparison.contextDisplay = comparisonContext(state.form);
  renderComparisonState();
  $('comparison-view').focus();
  runComparison();
}

function closeComparison() {
  state.comparison.open = false;
  renderComparisonState();
  comparisonFocusReturn?.focus?.();
}

function trapComparisonFocus(event) {
  const focusable = [...$('comparison-view').querySelectorAll('button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])')];
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

async function runComparison() {
  const dataset = datasetSnapshot(state.form);
  const error = validate(buildRequest(state.form));
  if (error) return showFormError(error);
  cancelCalculation();
  const controller = new AbortController();
  runController = controller;
  const cache = state.comparison.cache || new Map();
  const signature = requestSignature(dataset);
  const cached = cache.get(signature);
  state.comparison = {
    ...state.comparison,
    cache,
    open: true,
    status: 'loading',
    context: dataset,
    contextDisplay: comparisonContext(state.form),
    error: null,
  };
  renderComparisonState();
  try {
    const response = cached || await runClusteringComparison(dataset, {signal: controller.signal});
    if (controller.signal.aborted) return;
    if (Object.values(response.results || {}).some(result => state.rejectedSnapshots?.has(result.data_snapshot))) {
      throw Object.assign(new Error('Данные Pulse изменились. Пересчитайте результат.'), {code: 'STALE_DATA_SNAPSHOT'});
    }
    cache.set(signature, response);
    state.comparison.results = response.results || {};
    state.comparison.activeMode = state.comparison.results[state.form.mode]
      ? state.form.mode
      : state.comparisonModeIds.find(mode => state.comparison.results[mode]);
    state.comparison.status = 'success';
    if (state.comparison.activeMode) activateComparisonMode(state.comparison.activeMode);
  } catch (error) {
    if (controller.signal.aborted) return;
    state.comparison.status = 'error';
    state.comparison.error = { code: error.code, message: error.message };
  }
  if (runController === controller) runController = null;
  renderComparisonState();
}

function activateComparisonMode(mode) {
  cancelPointRows();
  const result = state.comparison.results[mode];
  if (!result) return;
  cancelCalculation();
  state.comparison.activeMode = mode;
  state.form.mode = mode;
  if (modeParameter(state.modeCapabilities, mode, 'n_clusters')) {
    state.form.kMode = result.analysis.parameters.k_mode ?? state.form.kMode;
    state.form.k = result.analysis.parameters.n_clusters || state.form.k;
  }
  if (mode === 'geo_cost') state.form.costWeight = result.analysis.parameters.economics_weight ?? state.form.costWeight;
  if (mode === 'geo_volume') state.form.volumeWeight = result.analysis.parameters.volume_weight ?? state.form.volumeWeight;
  if (mode === 'bear_zones') state.form.bearThreshold = result.analysis.parameters.bear_threshold ?? state.form.bearThreshold;
  if (mode === 'bear_volume_zones') state.form.bearVolumeThreshold = result.analysis.parameters.volume_threshold ?? state.form.bearVolumeThreshold;
  state.form.singletonThreshold = modeParameter(state.modeCapabilities, mode, 'singleton_threshold')?.default
    ?? state.form.singletonThreshold;
  const request = { ...buildRequest(state.form, mode), ...state.comparison.context };
  setResult(state, result, request);
  showSingleRunTable(result);
  renderClusteringPoints(result);
  renderAll();
}

function renderAll() {
  renderFormState(state);
  $('vehicle-count').textContent = state.form.vehicleTypes.length ? `${state.form.vehicleTypes.length} выбрано` : 'Все';
  $('tonnage-count').textContent = state.form.tonnageIds.length ? `${state.form.tonnageIds.length} выбрано` : 'Все';
  const stale = isResultStale(state);
  $('analysis-stale').classList.toggle('hidden', !stale);
  setMlResultStale(stale);
  renderEmptyState();
  renderInspectorState();
  renderClusterTableState();
  renderComparisonState();
}

function renderClusterTableState() {
  renderClusterTable(state, {
    isStale: () => isResultStale(state),
    onToggle: open => {
      state.ui.tableOpen = open;
      renderClusterTableState();
      window.dispatchEvent(new Event('resize'));
    },
    onSort: (key, direction) => {
      state.ui.tableSort = { key, direction };
      renderClusterTableState();
    },
    onClusterHover: clusterId => {
      state.ui.hoveredCluster = clusterId;
      hoverCluster(clusterId);
    },
    onClusterSelect: clusterId => selectCluster(clusterId, true),
  });
}

function comparisonContext(form) {
  return {
    route: `${form.origin?.name || 'Точка не выбрана'} → ${form.destinationRegion || 'Регион не выбран'}`,
    periods: form.periodTypes.map(value => PERIOD_LABELS[value] || value).join(', ') || '—',
    prices: form.priceTypes.map(value => PRICE_LABELS[value] || value).join(', ') || '—',
    vehicles: form.vehicleTypes.join(', ') || 'Все',
    tonnages: form.tonnageIds.map(value => `${value} т`).join(', ') || 'Все',
  };
}

function renderEmptyState() {
  if (state.result.data || state.result.status === 'error') return;
  const ready = Boolean(state.form.origin && state.form.destinationRegion);
  $('empty-state').querySelector('.empty-title').textContent = ready
    ? 'Всё готово к расчёту.'
    : 'Выберите направление и параметры анализа.';
  $('empty-state').querySelector('.empty-sub').textContent = ready
    ? 'Запустите анализ, чтобы увидеть зоны на карте.'
    : 'Результат появится на карте.';
}

function renderInspectorState() {
  renderInspector(state, {
    pointRowsKey,
    onClusterHover: clusterId => highlightCluster(clusterId),
    onClusterSelect: selectCluster,
    onPointSelect: pointId => {
      selectPoint(pointId, true);
    },
    onPointClear: () => {
      selectPoint(null);
    },
    onPulseToggle: open => {
      const detail = pointRowsForSelection();
      detail.open = open;
      if (!open) cancelPointRows();
      else if (detail.status === 'idle') loadPointRows();
    },
    onPulseMore: () => loadPointRows(),
    onPulseRetry: () => loadPointRows(),
  });
}

function pointRowsKey() {
  const result = state.result.data;
  if (!result || !state.ui.selectedPoint) return null;
  return requestSignature({
    data_snapshot: result.data_snapshot,
    origin_fias: result.analysis.origin.fias_id,
    destination_region: result.analysis.destination_region,
    destination_fias: state.ui.selectedPoint,
    ...(result.analysis.filters || {}),
  });
}

function pointRowsForSelection() {
  const key = pointRowsKey();
  if (!key) return {status: 'idle', rows: [], total: null, hasMore: false, open: false};
  if (!state.ui.pointRows.has(key)) {
    const status = state.rejectedSnapshots?.has(state.result.data.data_snapshot) ? 'stale' : 'idle';
    state.ui.pointRows.set(key, {status, rows: [], total: null, hasMore: false, open: false, error: null});
  }
  return state.ui.pointRows.get(key);
}

function cancelPointRows() {
  pointRowsController?.abort();
  pointRowsController = null;
  const detail = pointRowsForSelection();
  if (detail.status === 'loading') detail.status = detail.rows.length ? 'success' : 'idle';
}

function selectPoint(pointId, focus = false) {
  cancelPointRows();
  state.ui.selectedPoint = pointId;
  if (pointId && focus) focusClusteringPoint(pointId);
  renderInspectorState();
}

async function loadPointRows({restart = false} = {}) {
  const result = state.result.data;
  const point = result?.points.find(item => item.id === state.ui.selectedPoint);
  if (!point || result.cluster_table?.supported !== true) return;
  if (state.rejectedSnapshots?.has(result.data_snapshot)) return;
  const key = pointRowsKey();
  const detail = pointRowsForSelection();
  detail.open = true;
  if (detail.status === 'loading' || (!restart && detail.status === 'success' && !detail.hasMore)) return;
  if (restart) Object.assign(detail, {rows: [], total: null, hasMore: false});
  const controller = new AbortController();
  pointRowsController?.abort();
  pointRowsController = controller;
  detail.status = 'loading';
  detail.error = null;
  renderInspectorState();
  const filters = result.analysis.filters || {};
  try {
    const response = await fetchClusteringPointRows({
      data_snapshot: result.data_snapshot,
      origin_fias: result.analysis.origin.fias_id,
      destination_region: result.analysis.destination_region,
      destination_fias: point.fias_id || point.id,
      period_types: filters.period_types || [],
      price_types: filters.price_types || [],
      vehicle_types: filters.vehicle_types || [],
      tonnage_ids: filters.tonnage_ids || [],
      offset: detail.rows.length,
      limit: 50,
    }, {signal: controller.signal});
    if (controller.signal.aborted || key !== pointRowsKey()) return;
    const known = new Set(detail.rows.map(row => row.source_row_id));
    detail.rows.push(...response.rows.filter(row => !known.has(row.source_row_id)));
    detail.total = response.total;
    detail.hasMore = response.has_more;
    detail.status = 'success';
  } catch (error) {
    if (controller.signal.aborted || key !== pointRowsKey()) return;
    if (error.code === 'STALE_DATA_SNAPSHOT') {
      rejectDataSnapshot(state, result.data_snapshot);
      renderAll();
    }
    detail.status = error.code === 'STALE_DATA_SNAPSHOT' ? 'stale' : 'error';
    detail.error = error.message;
  } finally {
    if (pointRowsController === controller) pointRowsController = null;
    if (key === pointRowsKey()) renderInspectorState();
  }
}

function renderComparisonState() {
  renderComparison(state, {
    isStale: () => isComparisonStale(state),
    onActivate: mode => {
      activateComparisonMode(mode);
    },
    onShowMap: mode => {
      activateComparisonMode(mode);
      closeComparison();
    },
  });
}

function showFormError(message) {
  $('analysis-form-error').textContent = message;
  $('analysis-form-error').classList.remove('hidden');
}

function escapeText(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
}
