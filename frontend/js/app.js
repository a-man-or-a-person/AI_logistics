/** Application shell: legacy Data Map plus the independent Product v1 workspace. */

import {
  fetchGeocodeStatus, fetchPoints, fetchRecords, fetchRegions, regeocodeTown,
} from './api.js';
import { initClustering } from './clustering/controller.js';
import { getFilters, initFilters, resetFilters } from './filters.js';
import {
  clearMarkers, initMap, renderPoints, setThemeLayer,
} from './map.js';

const $ = id => document.getElementById(id);
const state = { view: 'clustering', lastData: null, clustering: null };
let toastTimer;
let pointsController;

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

async function loadDataMap() {
  const filters = getFilters();
  pointsController?.abort();
  if (!filters.fromRegions.length && !filters.toRegions.length) {
    mapEmpty('Выберите направление или регион', 'Настройте фильтры слева.');
    return;
  }
  pointsController = new AbortController();
  setLoading(true, 'Обновляем карту данных…');
  try {
    const data = await fetchPoints(filters, { signal: pointsController.signal });
    state.lastData = data;
    renderPoints(data.shipment_points, data.delivery_points);
    $('info-ship').textContent = fmt(data.total_ship);
    $('info-del').textContent = fmt(data.total_del);
    $('info-geocoded').textContent = fmt(data.geocoded);
    $('map-info').classList.remove('hidden');
    $('map-legend').classList.remove('hidden');
    $('empty-state').classList.toggle('hidden', Boolean(data.total_ship + data.total_del));
  } catch (error) {
    if (error.name !== 'AbortError') toast(error.message, 'error');
  } finally {
    setLoading(false);
  }
}

function switchView(view) {
  if (!['data', 'clustering'].includes(view)) return;
  state.view = view;
  const clustering = view === 'clustering';
  $('workspace').classList.toggle('mode-cluster', clustering);
  $('workspace').classList.toggle('mode-data', !clustering);
  $('data-map-view').classList.toggle('hidden', clustering);
  $('clustering-controls').classList.toggle('hidden', !clustering);
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

function wireShell() {
  document.querySelectorAll('.mode-tab').forEach(button => button.addEventListener('click', () => switchView(button.dataset.view)));
  $('btn-apply').addEventListener('click', loadDataMap);
  $('btn-reset').addEventListener('click', () => { resetFilters(); state.lastData = null; clearMarkers(); });
  $('mobile-controls-btn').addEventListener('click', () => $('sidebar').classList.add('open'));
  $('mobile-inspector-btn').addEventListener('click', () => $('clustering-inspector').classList.add('open'));
  document.querySelectorAll('[data-close-panel]').forEach(button => button.addEventListener('click', () => button.closest('aside').classList.remove('open')));
  $('modal-close').addEventListener('click', closeModal);
  $('modal-overlay').addEventListener('click', closeModal);
  window.addEventListener('show-records-modal', showRecords);
  window.addEventListener('regeocode-point', async event => {
    try { await regeocodeTown(event.detail.town, event.detail.region); }
    catch (error) { toast(error.message, 'error'); }
  });
}

function closeModal() { $('records-modal').classList.add('hidden'); }

async function showRecords(event) {
  const { town, region, type } = event.detail;
  $('records-modal').classList.remove('hidden');
  $('modal-title').textContent = town;
  $('modal-error').classList.add('hidden');
  try {
    const result = await fetchRecords(town, region, type, getFilters());
    $('records-tbody').innerHTML = result.records.map(record => `<tr>
      <td>${escapeHtml(record.price)}</td><td>${escapeHtml(record.route_length)}</td>
      <td>${number(record.rub_per_km)}</td><td>${escapeHtml(record.bid_count)}</td>
      <td>${escapeHtml(record.period_type)}</td><td>${escapeHtml(record.price_type)}</td>
      <td>${escapeHtml(record.confidence || '—')}</td><td>${escapeHtml(record.ship_region)}</td>
      <td>${escapeHtml(record.del_region)}</td></tr>`).join('');
  } catch (error) {
    $('modal-error').textContent = error.message;
    $('modal-error').classList.remove('hidden');
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
