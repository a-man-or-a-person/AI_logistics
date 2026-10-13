import {
  fetchClusteringOptions, fetchClusteringOrigins, fetchClusteringPointRows, fetchClusteringPointOrigins, runClustering,
  runClusteringComparison, fetchClusteringRevision, exportClustering,
} from '../api.js';
import {
  buildRequest, createClusteringState, datasetSnapshot, isComparisonStale,
  isResultStale, modeParameter, rejectDataSnapshot, rejectUnavailableResult, requestSignature, setResult, updateClusteringOptions,
} from './state.js';
import { readChecks, renderFormState, renderOptionControls } from './controls.js';
import { renderErrorState, renderInspector } from './inspector.js';
import { renderComparison } from './comparison.js';
import { clusterLabel, MODE_LABELS, PERIOD_LABELS, PRICE_LABELS } from './formatters.js';
import { renderClusterTable } from './table.js';
import {
  clearClusteringResult, focusClusteringPoint, highlightCluster, hoverCluster,
  renderClusteringPoints, setClusteringLayers, setMlResultStale,
} from '../map.js';

const $ = id => document.getElementById(id);
let state;
let originOptions = [];
let originTimer;
let originSearchVersion = 0;
let optionsVersion = 0;
let runController;
let pointRowsController;
let pointOriginsController;
let comparisonFocusReturn;
let activePanel;
let panelFocusReturn;
let panelBackground = [];
let panelFocusOwner;
let exportController;
let exportResult;
let exportStatus = { kind: 'idle', message: '' };

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
  return { show, hide, getState: () => state };
}

export function show() {
  if (state.result.data) renderClusteringPoints(state.result.data);
  renderAll();
}

function hide() {
  closePanel(false);
  if (state.comparison.open) closeComparison(false);
  cancelCalculation();
  cancelExport();
}

function wireEvents() {
  wirePanelPresentation();
  $('btn-export-clustering').addEventListener('click', downloadExport);
  $('btn-cancel-export').addEventListener('click', () => { cancelExport(); $('btn-export-clustering').focus(); });
  window.addEventListener('pagehide', cancelExport);
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
  $('all-origins').addEventListener('change', async () => {
    state.form.allOrigins = $('all-origins').checked;
    ++originSearchVersion;
    clearTimeout(originTimer);
    hideOriginOptions();
    renderAll();
    await loadContextOptions({originsChanged: true});
  });
  $('selected-origins').addEventListener('click', event => {
    const button = event.target.closest('[data-remove-origin]');
    if (button) removeOrigin(button.dataset.removeOrigin);
  });
  $('selected-origins').addEventListener('keydown', event => {
    if (['Delete', 'Backspace'].includes(event.key) && event.target.dataset.removeOrigin) {
      event.preventDefault();
      removeOrigin(event.target.dataset.removeOrigin);
    }
  });
  $('cluster-origin-options').addEventListener('keydown', event => {
    const options = [...document.querySelectorAll('.combo-option')];
    const index = options.indexOf(event.target);
    if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      options[(index + (event.key === 'ArrowDown' ? 1 : options.length - 1)) % options.length]?.focus();
    } else if (event.key === 'Escape') {
      event.stopPropagation();
      $('cluster-origin').focus();
      hideOriginOptions();
    }
  });
  $('cluster-region').addEventListener('change', async () => {
    state.form.destinationRegion = $('cluster-region').value;
    if (state.form.allOrigins || state.form.origins.length) await loadContextOptions();
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
  $('cluster-details-close').addEventListener('click', () => {
    const cluster = state.ui.selectedCluster;
    selectCluster(null);
    [...document.querySelectorAll('#cluster-list [data-cluster-id]')]
      .find(button => Number(button.dataset.clusterId) === cluster)?.focus({preventScroll: true});
  });
  $('compare-modes').addEventListener('click', openComparison);
  $('close-comparison').addEventListener('click', () => {
    closeComparison();
  });
  $('rerun-comparison').addEventListener('click', runComparison);
  window.addEventListener('clustering-point-select', event => {
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
      if (document.querySelector('.metric-help-popover:popover-open')) return;
      if (state.comparison.open) closeComparison();
      hideOriginOptions();
      closePanel();
    }
    if (event.key === 'Tab' && state.comparison.open) trapComparisonFocus(event);
    else if (event.key === 'Tab' && activePanel) trapPanelFocus(event);
  });
}

function panelFocusables(panel) {
  return [...panel.querySelectorAll('button,input,select,textarea,a[href],summary,[tabindex]')]
    .filter(element => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length);
}

function closePanel(restoreFocus = true) {
  if (!activePanel) return;
  activePanel.classList.remove('open', 'panel-overlay');
  activePanel.removeAttribute('role');
  activePanel.removeAttribute('aria-modal');
  activePanel = null;
  for (const [element, wasInert] of panelBackground) element.inert = wasInert;
  panelBackground = [];
  $('panel-backdrop').classList.add('hidden');
  if (restoreFocus) panelFocusReturn?.focus();
}

function openPanel(panel, opener) {
  closePanel(false);
  const docked = panel.id === 'sidebar' ? innerWidth >= 1040
    : innerWidth >= 1320 && $('workspace').classList.contains('has-inspector-selection');
  if (!docked) {
    activePanel = panel;
    panelFocusReturn = opener;
    panel.classList.add('open', 'panel-overlay');
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panelBackground = [...document.querySelectorAll('.topbar,#sidebar,#clustering-center,#clustering-inspector,#comparison-view,#records-modal')]
      .filter(element => element !== panel).map(element => [element, element.inert]);
    for (const [element] of panelBackground) element.inert = true;
    $('panel-backdrop').classList.remove('hidden');
  }
  panel.setAttribute('tabindex', '-1');
  (panelFocusables(panel)[0] || panel).focus();
}

function trapPanelFocus(event) {
  const elements = panelFocusables(activePanel);
  const first = elements[0] || activePanel;
  const last = elements.at(-1) || activePanel;
  if (event.shiftKey && (document.activeElement === first || document.activeElement === activePanel)) {
    event.preventDefault(); last.focus();
  } else if (!event.shiftKey && (document.activeElement === last || !activePanel.contains(document.activeElement))) {
    event.preventDefault(); first.focus();
  }
}

function syncPanelLayout() {
  const selected = state.ui.selectedCluster != null || state.ui.selectedPoint != null;
  $('workspace').classList.toggle('has-inspector-selection', selected);
  const point = state.result.data?.points.find(item => item.id === state.ui.selectedPoint);
  const cluster = state.result.data?.clusters.find(item => item.cluster_id === state.ui.selectedCluster);
  $('selection-context').textContent = point?.name || (cluster ? clusterLabel(cluster, state.result.data.analysis.mode) : '');
  $('mobile-inspector-btn').textContent = selected ? 'Детали' : 'Результат';
  if (activePanel && ((activePanel.id === 'sidebar' && innerWidth >= 1040)
      || (activePanel.id === 'clustering-inspector' && innerWidth >= 1320 && selected))) closePanel();
  if (!activePanel) {
    for (const [id, opener] of [['sidebar', 'mobile-controls-btn'], ['clustering-inspector', 'mobile-inspector-btn']]) {
      if (getComputedStyle($(id)).display === 'none' && ($(id).contains(document.activeElement)
          || (document.activeElement === document.body && panelFocusOwner === $(id)))) $(opener).focus();
    }
  }
}

function wirePanelPresentation() {
  // Browsers can move focus to body before resize fires when a dock becomes hidden.
  document.addEventListener('focusin', event => {
    if (event.target !== document.body) panelFocusOwner = event.target.closest('#sidebar,#clustering-inspector');
  });
  document.addEventListener('pointerdown', event => {
    if (!event.target.closest('#sidebar,#clustering-inspector')) panelFocusOwner = null;
  });
  $('panel-backdrop').addEventListener('click', () => closePanel());
  $('mobile-controls-btn').addEventListener('click', event => openPanel($('sidebar'), event.currentTarget));
  $('mobile-inspector-btn').addEventListener('click', event => openPanel($('clustering-inspector'), event.currentTarget));
  document.querySelectorAll('[data-close-panel]').forEach(button => button.addEventListener('click', () => closePanel()));
  window.addEventListener('resize', syncPanelLayout);
  for (const query of ['(min-width: 1040px)', '(min-width: 1320px)']) {
    matchMedia(query).addEventListener('change', syncPanelLayout);
  }
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
}

async function searchOrigins(query) {
  const version = ++originSearchVersion;
  try {
    const origins = await fetchClusteringOrigins(query, 30);
    if (version !== originSearchVersion) return;
    originOptions = origins;
    $('cluster-origin-meta').textContent = origins.length ? 'Выберите отправление из подсказок' : 'Отправления не найдены. Измените поиск.';
  } catch (error) {
    if (version !== originSearchVersion) return;
    originOptions = [];
    $('cluster-origin-meta').textContent = `Не удалось загрузить отправления: ${error.message}. Повторите поиск.`;
  }
  $('cluster-origin-options').innerHTML = originOptions.map((origin, index) => `
    <button class="combo-option" type="button" role="option" aria-selected="${state.form.origins.some(item => item.fias_id === origin.fias_id)}" data-origin-index="${index}">
      <strong>${escapeText(origin.name)}</strong><small>${escapeText(origin.region)} · ${escapeText(origin.fias_id)}</small>
    </button>`).join('');
  document.querySelectorAll('[data-origin-index]').forEach(button => button.addEventListener('click', () => chooseOrigin(originOptions[Number(button.dataset.originIndex)])));
  return true;
}

function onOriginInput() {
  ++originSearchVersion;
  clearTimeout(originTimer);
  originTimer = setTimeout(async () => {
    if (await searchOrigins($('cluster-origin').value.trim())) showOriginOptions();
  }, 220);
}

function onOriginKeydown(event) {
  const options = [...document.querySelectorAll('.combo-option')];
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    showOriginOptions();
    (options.find(item => item.classList.contains('active'))?.nextElementSibling || options[0])?.focus();
  } else if (event.key === 'Escape' && $('cluster-origin').getAttribute('aria-expanded') === 'true') {
    event.stopPropagation();
    hideOriginOptions();
  }
}

function showOriginOptions() {
  $('cluster-origin-options').classList.toggle('hidden', !originOptions.length);
  $('cluster-origin').setAttribute('aria-expanded', String(Boolean(originOptions.length)));
}

function hideOriginOptions() {
  ++originSearchVersion;
  clearTimeout(originTimer);
  $('cluster-origin-options').classList.add('hidden');
  $('cluster-origin').setAttribute('aria-expanded', 'false');
}

async function chooseOrigin(origin) {
  if (!state.form.origins.some(item => item.fias_id === origin.fias_id)) state.form.origins.push(origin);
  $('cluster-origin').value = '';
  ++originSearchVersion;
  clearTimeout(originTimer);
  renderOrigins();
  renderAll();
  $('cluster-origin').focus();
  hideOriginOptions();
  await loadContextOptions({originsChanged: true});
}

async function removeOrigin(fias) {
  state.form.origins = state.form.origins.filter(origin => origin.fias_id !== fias);
  renderOrigins();
  $('cluster-origin').focus();
  hideOriginOptions();
  renderAll();
  await loadContextOptions({originsChanged: true});
}

function renderOrigins() {
  $('selected-origins').innerHTML = state.form.origins.map(origin => `
    <button type="button" data-remove-origin="${escapeText(origin.fias_id)}"
      aria-label="Удалить отправление ${escapeText(origin.name || origin.fias_id)} (${escapeText(origin.fias_id)})">
      ${escapeText(origin.name || origin.fias_id)} <small>${escapeText(origin.fias_id)}</small> ×
    </button>`).join('');
}

async function loadContextOptions({originsChanged = false} = {}) {
  const version = ++optionsVersion;
  const origins = state.form.origins.map(origin => origin.fias_id);
  const all = state.form.allOrigins;
  const region = state.form.destinationRegion;
  setOptionsLoading(true, 'Загружаем доступные параметры…');
  try {
    let options = await fetchClusteringOptions(
      all ? [] : origins,
      originsChanged || all ? '' : region,
    );
    if (version !== optionsVersion) return;
    const regions = options.destination_regions;
    if ((all || originsChanged && origins.length) && region && regions.includes(region)) {
      options = await fetchClusteringOptions(origins, region, all);
      if (version !== optionsVersion) return;
    }
    updateClusteringOptions(state, options);
    $('cluster-region').replaceChildren(new Option('Выберите регион…', ''));
    regions.forEach(value => $('cluster-region').add(new Option(value, value)));
    state.form.destinationRegion = (all || origins.length) && regions.includes(region) ? region : '';
    $('cluster-region').value = state.form.destinationRegion;
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
    $('analysis-form-error').classList.add('hidden');
    renderAll();
  } catch (error) {
    if (version !== optionsVersion) return;
    showFormError(error.message);
  } finally {
    if (version === optionsVersion) setOptionsLoading(false);
  }
}

function setOptionsLoading(loading, message = '') {
  ['cluster-region', 'btn-run-clustering'].forEach(id => { $(id).disabled = loading; });
  $('cluster-region').disabled = loading || !(state.form.allOrigins || state.form.origins.length);
  $('compare-modes').disabled = loading;
  $('clustering-controls').classList.toggle('options-loading', loading);
  $('options-status').textContent = loading ? message : '';
  $('options-status').classList.toggle('hidden', !loading);
}

function clearOrigin() {
  state.form.origin = null;
  state.form.origins = [];
  ++optionsVersion;
  ++originSearchVersion;
  clearTimeout(originTimer);
  $('cluster-origin').value = '';
  renderOrigins();
  hideOriginOptions();
  state.form.destinationRegion = '';
  $('cluster-region').disabled = true;
  $('cluster-region').replaceChildren(new Option('Сначала выберите точку отправления', ''));
  $('cluster-origin-meta').textContent = 'Выберите одно или несколько отправлений';
}

function validate(request) {
  if (!request.all_origins && !request.origin_fias && !request.origin_fiases?.length) return 'Выберите хотя бы одно отправление из списка.';
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
  cancelPointDetailRequests();
  const request = buildRequest(state.form);
  const error = validate(request);
  if (error) return showFormError(error);
  cancelExport();
  cancelCalculation();
  $('analysis-form-error').classList.add('hidden');
  const cached = state.result.cache.get(requestSignature(request));
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
    const valid = (!cached && !state.result.data) || await validateCachedResults(cached ? [cached] : [], controller);
    if (controller.signal.aborted) return;
    const result = cached && valid ? cached : await runClustering(request, { signal: controller.signal });
    if (controller.signal.aborted) return;
    setResult(state, result, request);
    showSingleRunTable(result);
    renderClusteringPoints(result);
    $('empty-state').classList.add('hidden');
    renderAll();
  } catch (runError) {
    if (controller.signal.aborted) return;
    if (runError.code === 'STALE_DATA_SNAPSHOT' && state.result.data) {
      rejectDataSnapshot(state, state.result.data.data_snapshot);
      renderAll();
    }
    state.result.status = 'error';
    state.result.error = { code: runError.code, message: runError.message };
    showFormError(`${runError.code || 'Ошибка'}: ${runError.message}`);
    if (state.result.data) renderInspectorState();
    else renderErrorState(state.result.error);
    if (runError.code === 'NO_DATA' && !state.result.data) {
      $('empty-state').querySelector('.empty-title').textContent = 'По выбранным фильтрам данных нет.';
      $('empty-state').querySelector('.empty-sub').textContent = 'Измените сегмент данных и повторите расчёт.';
      $('empty-state').classList.remove('hidden');
    }
    renderClusterTableState();
  } finally {
    if (runController === controller) cancelCalculation();
  }
}

async function validateCachedResults(candidates, controller) {
  const results = [...new Set([...candidates, state.result.data].filter(Boolean))];
  if (!results.length) return true;
  const contexts = results.map(result => ({
    ...frozenPointContext(result), data_snapshot: result.data_snapshot,
  }));
  let revision;
  try {
    revision = await fetchClusteringRevision(contexts, {signal: controller.signal});
  } catch (error) {
    if (!controller.signal.aborted && error.code === 'STALE_DATA_SNAPSHOT') {
      results.forEach(result => rejectDataSnapshot(state, result.data_snapshot));
      renderAll();
    }
    throw error;
  }
  if (controller.signal.aborted) return false;
  if (typeof revision.data_snapshot !== 'string' || !Array.isArray(revision.available)
      || revision.available.length !== results.length || revision.available.some(value => typeof value !== 'boolean')) {
    throw new Error('Некорректный ответ проверки актуальности данных');
  }
  results.forEach((result, index) => {
    if (result.data_snapshot !== revision.data_snapshot) rejectDataSnapshot(state, result.data_snapshot);
    else if (!revision.available[index]) rejectUnavailableResult(state, result);
  });
  renderAll();
  return candidates.every(result => !state.rejectedSnapshots.has(result.data_snapshot)
    && !state.unavailableResults.has(result));
}

function reset() {
  cancelExport();
  cancelCalculation();
  cancelPointDetailRequests();
  state = createClusteringState(state.options);
  renderOptionControls(state);
  clearOrigin();
  setOptionsLoading(false);
  clearClusteringResult();
  $('empty-state').classList.remove('hidden');
  renderAll();
}

function selectCluster(clusterId, focus = false) {
  if (clusterId == null || clusterId !== state.ui.selectedCluster) {
    cancelPointDetailRequests();
    state.ui.selectedPoint = null;
    state.ui.selectedOrigin = null;
  }
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
  comparisonFocusReturn = activePanel ? panelFocusReturn : document.activeElement;
  closePanel(false);
  state.comparison.open = true;
  renderComparisonState();
  $('comparison-view').focus();
  runComparison();
}

function closeComparison(restoreFocus = true) {
  state.comparison.open = false;
  renderComparisonState();
  if (restoreFocus) comparisonFocusReturn?.focus?.();
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
  cancelPointDetailRequests();
  const dataset = datasetSnapshot(state.form);
  const error = validate(buildRequest(state.form));
  if (error) return showFormError(error);
  cancelExport();
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
    results: {},
    activeMode: null,
    context: dataset,
    contextDisplay: comparisonContext(state.form),
    error: null,
  };
  renderComparisonState();
  try {
    const valid = (!cached && !state.result.data)
      || await validateCachedResults(Object.values(cached?.results || {}), controller);
    if (controller.signal.aborted) return;
    const response = cached && valid ? cached : await runClusteringComparison(dataset, {signal: controller.signal});
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
    if (error.code === 'STALE_DATA_SNAPSHOT' && state.result.data) {
      rejectDataSnapshot(state, state.result.data.data_snapshot);
      renderAll();
    }
    state.comparison.status = 'error';
    state.comparison.error = { code: error.code, message: error.message };
  }
  if (runController === controller) runController = null;
  renderComparisonState();
}

function activateComparisonMode(mode) {
  cancelPointDetailRequests();
  const result = state.comparison.results[mode];
  if (!result) return;
  cancelExport();
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
  const request = { ...state.comparison.context, mode, parameters: buildRequest(state.form, mode).parameters };
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
  renderExportState();
}

function exportBlockedReason() {
  const result = state.result.data;
  if (!result) return 'Сначала рассчитайте результат.';
  if (state.rejectedSnapshots.has(result.data_snapshot)) return 'Данные Pulse изменились. Пересчитайте результат для загрузки XLSX.';
  if (state.unavailableResults.has(result)) return 'Сохранённый результат недоступен. Пересчитайте результат.';
  if (result.cluster_table?.supported !== true) return 'XLSX для Bear не поддерживается (EXPORT_UNSUPPORTED).';
  if (!result.cluster_table.rows?.length) return 'В результате нет кластеров для экспорта.';
  return '';
}

function renderExportState() {
  if (exportResult !== state.result.data) {
    exportController?.abort();
    exportController = null;
    exportResult = state.result.data;
    exportStatus = { kind: 'idle', message: '' };
  }
  const busy = Boolean(exportController);
  const blocked = exportBlockedReason();
  const button = $('btn-export-clustering');
  // Keep the native button focused while preventing duplicate activation.
  button.setAttribute('aria-disabled', String(busy || Boolean(blocked)));
  button.textContent = exportStatus.kind === 'error' && !blocked ? 'Повторить загрузку XLSX' : 'Скачать XLSX';
  $('export-controls').setAttribute('aria-busy', String(busy));
  $('btn-cancel-export').classList.toggle('hidden', !busy);
  const warning = !blocked && isResultStale(state) ? ' Форма изменена: XLSX использует исходные параметры сохранённого результата.' : '';
  $('export-status').textContent = (exportStatus.message || blocked || 'Полная таблица и строки Pulse сохранённого результата.')
    + (exportStatus.message && blocked ? ` ${blocked}` : '') + warning;
  $('export-status').classList.toggle('error', exportStatus.kind === 'error');
}

function cancelExport() {
  if (!exportController) return;
  exportController.abort();
  exportController = null;
  exportStatus = { kind: 'idle', message: 'Загрузка отменена.' };
  renderExportState();
}

async function downloadExport() {
  if (exportController || exportBlockedReason()) return;
  const result = state.result.data;
  const controller = new AbortController();
  exportController = controller;
  exportResult = result;
  exportStatus = { kind: 'loading', message: 'Подготавливаем XLSX…' };
  renderExportState();
  try {
    const file = await exportClustering({
      ...result.analysis.frozen_request, data_snapshot: result.data_snapshot,
      selection_intent: result.analysis.selection_intent, table_sort: { ...state.ui.tableSort },
    }, { signal: controller.signal });
    if (controller.signal.aborted || exportController !== controller || state.result.data !== result
        || exportBlockedReason()) return;
    const url = URL.createObjectURL(file.blob);
    const anchor = document.createElement('a');
    try {
      anchor.href = url; anchor.download = file.filename;
      anchor.hidden = true;
      document.body.append(anchor);
      anchor.click();
    } finally {
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    exportStatus = { kind: 'success', message: `Файл ${file.filename} передан браузеру для сохранения.` };
  } catch (error) {
    if (controller.signal.aborted || exportController !== controller || state.result.data !== result) return;
    if (error.code === 'STALE_DATA_SNAPSHOT') rejectDataSnapshot(state, result.data_snapshot);
    if (error.code === 'RESULT_UNAVAILABLE') rejectUnavailableResult(state, result);
    exportStatus = { kind: 'error', message: `${error.code || 'Ошибка загрузки'}: ${error.message}${error.requestId ? ` · Запрос: ${error.requestId}` : ''}` };
    renderAll();
  } finally {
    if (exportController === controller) { exportController = null; renderExportState(); }
  }
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
    route: `${form.allOrigins ? 'Все отправления' : form.origins?.map(origin => origin.name || origin.fias_id).join(', ') || form.origin?.name || 'Точка не выбрана'} → ${form.destinationRegion || 'Регион не выбран'}`,
    periods: form.periodTypes.map(value => PERIOD_LABELS[value] || value).join(', ') || '—',
    prices: form.priceTypes.map(value => PRICE_LABELS[value] || value).join(', ') || '—',
    vehicles: form.vehicleTypes.join(', ') || 'Все',
    tonnages: form.tonnageIds.map(value => `${value} т`).join(', ') || 'Все',
  };
}

function renderEmptyState() {
  if (state.result.data || state.result.status === 'error') return;
  const ready = Boolean((state.form.allOrigins || state.form.origins?.length || state.form.origin) && state.form.destinationRegion);
  $('empty-state').querySelector('.empty-title').textContent = ready
    ? 'Всё готово к расчёту.'
    : 'Выберите направление и параметры анализа.';
  $('empty-state').querySelector('.empty-sub').textContent = ready
    ? 'Запустите анализ, чтобы увидеть зоны на карте.'
    : 'Результат появится на карте.';
}

function renderInspectorState() {
  const focused = globalThis.document?.activeElement;
  const focusedOrigin = focused?.dataset.originFias;
  const focusedPulse = focused?.matches?.('.pulse-details summary');
  renderInspector(state, {
    onLayout: syncPanelLayout,
    pointRowsKey,
    pointOrigins: state.ui.pointOrigins?.get(pointOriginsKey()),
    selectedOrigin: state.ui.selectedOrigin,
    onOriginSelect: origin => {
      cancelPointDetailRequests();
      state.ui.selectedOrigin = origin;
      const detail = pointRowsForSelection();
      detail.open = true;
      if (detail.status === 'idle' || detail.status === 'error') loadPointRows();
      else renderInspectorState();
    },
    onOriginsRetry: () => loadPointOrigins(),
    onClusterHover: clusterId => highlightCluster(clusterId),
    onClusterSelect: selectCluster,
    onPointSelect: pointId => {
      selectPoint(pointId, true);
    },
    onPointClear: () => {
      const point = state.ui.selectedPoint;
      selectPoint(null);
      const parent = state.ui.selectedCluster == null
        ? document.querySelector('.cluster-card')
        : [...document.querySelectorAll('[data-point-id]')].find(button => button.dataset.pointId === point);
      parent?.focus({preventScroll: true});
    },
    onPointSummary: () => {
      const origin = state.ui.selectedOrigin;
      cancelPointDetailRequests();
      pointRowsForSelection().open = false;
      state.ui.selectedOrigin = null;
      pointRowsForSelection().open = false;
      renderInspectorState();
      const parent = origin
        ? [...document.querySelectorAll('[data-origin-fias]')].find(button => button.dataset.originFias === origin)
        : document.querySelector('.pulse-details summary');
      parent?.focus({preventScroll: true});
    },
    onPulseToggle: open => {
      const detail = pointRowsForSelection();
      detail.open = open;
      if (!open) cancelPointDetailRequests();
      else if (detail.status === 'idle') loadPointRows();
    },
    onPulseMore: () => loadPointRows(),
    onPulseRetry: () => loadPointRows(),
  });
  if (focusedPulse) document.querySelector('.pulse-details summary')?.focus({preventScroll: true});
  if (focusedOrigin) {
    [...document.querySelectorAll('[data-origin-fias]')]
      .find(button => button.dataset.originFias === focusedOrigin)?.focus({preventScroll: true});
  }
}

function pointOriginsKey() {
  const result = state.result.data;
  if (!result || !state.ui.selectedPoint) return null;
  return requestSignature({
    data_snapshot: result.data_snapshot,
    ...frozenPointContext(result),
    destination_fias: state.ui.selectedPoint,
  });
}

function pointRowsKey() {
  const key = pointOriginsKey();
  return key && state.ui.selectedOrigin
    ? requestSignature({...JSON.parse(key), detail_origin_fias: state.ui.selectedOrigin}) : key;
}

function frozenPointContext(result) {
  return result.analysis.frozen_request || {
    origin_fias: result.analysis.origin.fias_id,
    destination_region: result.analysis.destination_region,
    ...(result.analysis.filters || {}),
  };
}

function pointRowsForSelection() {
  const key = pointRowsKey();
  if (!key) return {status: 'idle', rows: [], total: null, hasMore: false, open: false};
  if (!state.ui.pointRows.has(key)) {
    const status = state.unavailableResults?.has(state.result.data) ? 'unavailable'
      : state.rejectedSnapshots?.has(state.result.data.data_snapshot) ? 'stale' : 'idle';
    state.ui.pointRows.set(key, {status, rows: [], total: null, hasMore: false, open: false, error: null});
  }
  return state.ui.pointRows.get(key);
}

function cancelPointDetailRequests() {
  pointOriginsController?.abort();
  pointOriginsController = null;
  const summary = state.ui.pointOrigins?.get(pointOriginsKey());
  if (summary?.status === 'loading') summary.status = 'idle';
  pointRowsController?.abort();
  pointRowsController = null;
  const detail = pointRowsForSelection();
  if (detail.status === 'loading') detail.status = detail.rows.length ? 'success' : 'idle';
}

function selectPoint(pointId, focus = false) {
  cancelPointDetailRequests();
  state.ui.selectedPoint = pointId;
  state.ui.selectedOrigin = null;
  if (pointId) {
    state.ui.selectedCluster = state.result.data.points.find(point => point.id === pointId)?.cluster_id ?? null;
    highlightCluster(state.ui.selectedCluster);
    renderClusterTableState();
  }
  if (pointId && focus) focusClusteringPoint(pointId);
  renderInspectorState();
  if (pointId && state.result.data.analysis.frozen_request) loadPointOrigins();
}

async function loadPointOrigins() {
  const result = state.result.data;
  const key = pointOriginsKey();
  if (!key || state.unavailableResults?.has(result) || state.rejectedSnapshots?.has(result.data_snapshot)) return;
  const cache = state.ui.pointOrigins ||= new Map();
  const summary = cache.get(key) || {status: 'idle', origins: []};
  cache.set(key, summary);
  if (summary.status === 'success' || summary.status === 'loading') return;
  const controller = new AbortController();
  pointOriginsController?.abort();
  pointOriginsController = controller;
  summary.status = 'loading';
  renderInspectorState();
  try {
    const response = await fetchClusteringPointOrigins(JSON.parse(key), {signal: controller.signal});
    if (controller.signal.aborted || key !== pointOriginsKey()) return;
    Object.assign(summary, response, {status: 'success'});
  } catch (error) {
    if (controller.signal.aborted || key !== pointOriginsKey()) return;
    if (error.code === 'STALE_DATA_SNAPSHOT') rejectDataSnapshot(state, result.data_snapshot);
    if (error.code === 'RESULT_UNAVAILABLE') rejectUnavailableResult(state, result);
    summary.status = error.code === 'STALE_DATA_SNAPSHOT' ? 'stale'
      : error.code === 'RESULT_UNAVAILABLE' ? 'unavailable' : 'error';
    summary.error = error.message;
    renderAll();
  } finally {
    if (pointOriginsController === controller) pointOriginsController = null;
    if (key === pointOriginsKey()) renderInspectorState();
  }
}

async function loadPointRows({restart = false} = {}) {
  const result = state.result.data;
  const point = result?.points.find(item => item.id === state.ui.selectedPoint);
  if (!point || (result.cluster_table?.supported !== true && !state.ui.selectedOrigin)) return;
  if (state.unavailableResults?.has(result) || state.rejectedSnapshots?.has(result.data_snapshot)) return;
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
  try {
    const response = await fetchClusteringPointRows({
      ...frozenPointContext(result),
      data_snapshot: result.data_snapshot,
      destination_fias: point.fias_id || point.id,
      ...(state.ui.selectedOrigin ? {detail_origin_fias: state.ui.selectedOrigin} : {}),
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
    } else if (error.code === 'RESULT_UNAVAILABLE') {
      rejectUnavailableResult(state, result);
      renderAll();
    }
    detail.status = error.code === 'RESULT_UNAVAILABLE' ? 'unavailable'
      : error.code === 'STALE_DATA_SNAPSHOT' ? 'stale' : 'error';
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
