/** Application shell: legacy Data Map plus the independent Product v1 workspace. */

import {
  fetchGeocodeStatus, fetchPoints, fetchRecords, fetchRegions, regeocodeTown,
} from './api.js';
import { initClustering } from './clustering/controller.js';
import { getFilters, initFilters, resetFilters } from './filters.js';
import {
  clearMarkers, initMap, renderPoints, setThemeLayer, showDataPoint,
} from './map.js';

const $ = id => document.getElementById(id);
const state = { view: 'clustering', lastData: null, clustering: null };
let toastTimer;
let pointsController;
let recordsController;
let recordsFocusReturn;
let recordsBackground = [];

function fmt(value) { return Number(value || 0).toLocaleString('ru-RU'); }
function number(value) { return value == null ? '—' : Number(value).toLocaleString('ru-RU', { maximumFractionDigits: 1 }); }
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
}

function status(kind, text) {
  $('status-dot').className = `status-dot ${kind || ''}`;
  $('status-text').textContent = text;
}

function toast(message, type = 'success') {
  $('toast').setAttribute('role', type === 'error' ? 'alert' : 'status');
  $('toast').setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');
  $('toast').textContent = message;
  $('toast').className = `show toast-${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').className = ''; }, 3500);
}

function mapEmpty(title, subtitle, steps = false) {
  $('empty-state').querySelector('.empty-title').textContent = title;
  $('empty-state').querySelector('.empty-sub').textContent = subtitle;
  $('empty-state').querySelector('ol').classList.toggle('hidden', !steps);
  $('empty-state').classList.remove('hidden');
}

function setLoading(active, title = 'Загружаем данные…') {
  $('loading-overlay').classList.toggle('hidden', !active);
  $('loading-text').textContent = title;
}

function cancelDataMap() {
  pointsController?.abort();
  pointsController = null;
  setLoading(false);
}

async function loadDataMap() {
  const filters = getFilters();
  cancelDataMap();
  if (!filters.fromRegions.length && !filters.toRegions.length) {
    mapEmpty('Выберите направление или регион', 'Настройте фильтры слева.');
    return;
  }
  const controller = new AbortController();
  pointsController = controller;
  const current = () => !controller.signal.aborted && pointsController === controller && state.view === 'data';
  setLoading(true, 'Обновляем карту данных…');
  try {
    const data = await fetchPoints(filters, { signal: controller.signal });
    if (!current()) return;
    state.lastData = data;
    renderPoints(data.shipment_points, data.delivery_points);
    renderDataPointOptions();
    $('info-ship').textContent = fmt(data.total_ship);
    $('info-del').textContent = fmt(data.total_del);
    $('info-geocoded').textContent = fmt(data.geocoded);
    $('map-info').classList.remove('hidden');
    $('map-legend').classList.remove('hidden');
    $('empty-state').classList.toggle('hidden', Boolean(data.total_ship + data.total_del));
  } catch (error) {
    if (current() && error.name !== 'AbortError') toast(error.message, 'error');
  } finally {
    if (current()) { pointsController = null; setLoading(false); }
  }
}

function switchView(view) {
  if (!['data', 'clustering'].includes(view)) return;
  if (view !== state.view) closeModal(false);
  if (view === 'clustering' && state.view === 'data') cancelDataMap();
  state.view = view;
  const clustering = view === 'clustering';
  if (!clustering) state.clustering?.hide();
  $('workspace').classList.toggle('mode-cluster', clustering);
  $('workspace').classList.toggle('mode-data', !clustering);
  $('data-map-view').classList.toggle('hidden', clustering);
  $('clustering-controls').classList.toggle('hidden', !clustering);
  $('clustering-actions').classList.toggle('hidden', !clustering);
  $('controls-title').textContent = clustering ? 'Анализ кластеров' : 'Карта данных';
  document.querySelectorAll('.mode-tab').forEach(button => {
    const active = button.dataset.view === view;
    button.classList.toggle('active', active);
    button.toggleAttribute('aria-current', active);
  });
  $('map-info').classList.toggle('hidden', clustering || !state.lastData);
  $('map-legend').classList.toggle('hidden', clustering || !state.lastData);
  if (clustering) state.clustering?.show();
  else if (state.lastData) {
    renderPoints(state.lastData.shipment_points, state.lastData.delivery_points);
    $('empty-state').classList.add('hidden');
  } else {
    clearMarkers();
    mapEmpty('Выберите направление или регион', 'Настройте фильтры слева.');
  }
  setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
}

function initTheme() {
  let theme = localStorage.getItem('app-theme') || 'light';
  const apply = value => {
    theme = value;
    document.documentElement.toggleAttribute('data-theme', value === 'dark');
    localStorage.setItem('app-theme', value);
    setThemeLayer(value);
  };
  apply(theme);
  $('theme-toggle-header').addEventListener('click', () => apply(theme === 'dark' ? 'light' : 'dark'));
}

function renderDataPointOptions() {
  const data = state.lastData;
  $('data-point-navigation').classList.toggle('hidden', !data);
  const select = $('data-point-select');
  select.replaceChildren();
  for (const [kind, points] of [['ship', data?.shipment_points || []], ['del', data?.delivery_points || []]]) {
    points.forEach((point, index) => {
      if (point.lat == null || point.lon == null) return;
      const option = document.createElement('option');
      option.value = `${kind}:${index}`;
      option.textContent = `${kind === 'ship' ? 'Отгрузка' : 'Доставка'} · ${point.town} · ${point.region || 'Регион не указан'}`;
      select.append(option);
    });
  }
  const empty = !select.options.length;
  if (empty) select.add(new Option('Нет точек с координатами', ''));
  select.disabled = empty;
  $('open-data-point').disabled = empty;
}

function wireShell() {
  document.querySelectorAll('.mode-tab').forEach(button => button.addEventListener('click', () => switchView(button.dataset.view)));
  $('btn-apply').addEventListener('click', loadDataMap);
  $('btn-reset').addEventListener('click', () => { closeModal(false); cancelDataMap(); resetFilters(); state.lastData = null; clearMarkers(); renderDataPointOptions(); });
  $('open-data-point').addEventListener('click', event => {
    const [kind, index] = $('data-point-select').value.split(':');
    const points = kind === 'ship' ? state.lastData?.shipment_points : kind === 'del' ? state.lastData?.delivery_points : null;
    const point = points?.[Number(index)];
    if (point) {
      const returnFocus = $('sidebar').getAttribute('aria-modal') === 'true' ? $('mobile-controls-btn') : event.currentTarget;
      state.clustering?.closePanel(false);
      showDataPoint(point, kind, {returnFocus});
    }
  });
  $('modal-close').addEventListener('click', closeModal);
  $('modal-overlay').addEventListener('click', closeModal);
  document.addEventListener('keydown', event => {
    const modal = $('records-modal');
    if (modal.classList.contains('hidden')) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      closeModal();
    } else if (event.key === 'Tab') {
      event.stopPropagation();
      const first = $('modal-close');
      const last = modal.querySelector('.table-wrap');
      const outside = !modal.contains(document.activeElement) || document.activeElement === modal;
      if (event.shiftKey && (document.activeElement === first || outside)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || outside)) {
        event.preventDefault();
        first.focus();
      }
    }
  }, true);
  window.addEventListener('pagehide', () => closeModal(false));
  window.addEventListener('show-records-modal', showRecords);
  window.addEventListener('regeocode-point', async event => {
    try { await regeocodeTown(event.detail.town, event.detail.region); }
    catch (error) { toast(error.message, 'error'); }
  });
}

function closeModal(restoreFocus = true) {
  const modal = $('records-modal');
  if (modal.classList.contains('hidden')) return;
  recordsController?.abort();
  recordsController = null;
  modal.classList.add('hidden');
  modal.setAttribute('aria-busy', 'false');
  for (const [element, wasInert] of recordsBackground) element.inert = wasInert;
  recordsBackground = [];
  if (restoreFocus) {
    const target = recordsFocusReturn?.isConnected && recordsFocusReturn.checkVisibility()
      && !recordsFocusReturn.closest('[inert]') ? recordsFocusReturn : document.querySelector('.mode-tab[aria-current]');
    target?.focus();
  }
}

async function showRecords(event) {
  const { town, region, type } = event.detail;
  const modal = $('records-modal');
  recordsController?.abort();
  if (modal.classList.contains('hidden')) {
    recordsFocusReturn = document.activeElement;
    recordsBackground = [...document.querySelectorAll('.topbar,#workspace,#comparison-view')]
      .map(element => [element, element.inert]);
    for (const [element] of recordsBackground) element.inert = true;
  }
  const controller = new AbortController();
  recordsController = controller;
  const current = () => recordsController === controller && !controller.signal.aborted;
  modal.classList.remove('hidden');
  modal.setAttribute('aria-busy', 'true');
  $('modal-title').textContent = town;
  $('modal-error').textContent = '';
  $('modal-error').classList.add('hidden');
  $('records-tbody').innerHTML = '<tr><td colspan="9" role="status">Загружаем записи…</td></tr>';
  $('modal-close').focus();
  try {
    const result = await fetchRecords(town, region, type, getFilters(), {signal: controller.signal});
    if (!current()) return;
    if (!Array.isArray(result.records)) throw new Error('Некорректный ответ загрузки записей');
    $('records-tbody').innerHTML = result.records.map(record => `<tr>
      <td>${escapeHtml(record.price)}</td><td>${escapeHtml(record.route_length)}</td>
      <td>${number(record.rub_per_km)}</td><td>${escapeHtml(record.bid_count)}</td>
      <td>${escapeHtml(record.period_type)}</td><td>${escapeHtml(record.price_type)}</td>
      <td>${escapeHtml(record.confidence || '—')}</td><td>${escapeHtml(record.ship_region)}</td>
      <td>${escapeHtml(record.del_region)}</td></tr>`).join('')
      || '<tr><td colspan="9" role="status">Нет записей в выбранном срезе.</td></tr>';
  } catch (error) {
    if (!current()) return;
    $('records-tbody').innerHTML = '';
    $('modal-error').textContent = error.message;
    $('modal-error').classList.remove('hidden');
  } finally {
    if (current()) {
      recordsController = null;
      modal.setAttribute('aria-busy', 'false');
    }
  }
}

function startGeocodePolling() {
  setInterval(async () => {
    try {
      const result = await fetchGeocodeStatus();
      const active = result.running && result.total > 0;
      $('geocode-status').classList.toggle('hidden', !active);
      if (active) {
        $('geocode-status-text').textContent = `Координаты: ${result.done}/${result.total}`;
        $('geocode-progress-fill').style.width = `${Math.round(result.done / result.total * 100)}%`;
      }
    } catch (error) { console.warn(error); }
  }, 5000);
}

async function main() {
  status('loading', 'Инициализация');
  setLoading(true);
  try {
    initMap('map');
    initTheme();
    wireShell();
    const [regions, clustering] = await Promise.all([fetchRegions(), initClustering()]);
    initFilters(regions.ship_regions, regions.del_regions, () => {});
    state.clustering = clustering;
    switchView('clustering');
    status('', 'Данные готовы');
    startGeocodePolling();
  } catch (error) {
    console.error(error);
    status('error', 'Недоступно');
    mapEmpty('Не удалось запустить приложение', error.message);
  } finally { setLoading(false); }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main);
else main();
