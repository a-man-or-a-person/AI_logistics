/**
 * app.js — точка входа, связывает map ↔ filters ↔ api
 */

import { fetchRegions, fetchStats, fetchPoints, fetchRecords, fetchGeocodeStatus, regeocodeTown } from './api.js';
import { initFilters, getFilters, resetFilters } from './filters.js';
import { initMap, renderPoints, clearMarkers, setThemeLayer } from './map.js';

// ── DOM refs ──────────────────────────────────────────────────

const $ = id => document.getElementById(id);

const loadingOverlay = $('loading-overlay');
const loadingText    = $('loading-text');
const loadingSub     = $('loading-sub');
const btnApply       = $('btn-apply');
const btnReset       = $('btn-reset');
const statusDot      = $('status-dot');
const statusText     = $('status-text');
const infoShip       = $('info-ship');
const infoDel        = $('info-del');
const infoGeocoded   = $('info-geocoded');
const emptyState     = $('empty-state');
const toast          = $('toast');
const statRows       = $('stat-total-rows');
const statShipTowns  = $('stat-ship-towns');
const statDelTowns   = $('stat-del-towns');
const geocodeStatus     = $('geocode-status');
const geocodeStatusText = $('geocode-status-text');
const geocodeProgressFill = $('geocode-progress-fill');

// DOM Refs (Modal)
const recordsModal   = $('records-modal');
const modalOverlay   = $('modal-overlay');
const modalClose     = $('modal-close');
const modalTitle     = $('modal-title');
const modalLoading   = $('modal-loading');
const modalError     = $('modal-error');
const recordsTbody   = $('records-tbody');

// ── Toast ─────────────────────────────────────────────────────

let _toastTimer = null;

function showToast(msg, type = 'success', duration = 3500) {
  toast.textContent = msg;
  toast.className = `show toast-${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { toast.className = ''; }, duration);
}

// ── Loading state ─────────────────────────────────────────────

function setLoading(active, text = 'Загрузка данных...', sub = '') {
  if (active) {
    loadingOverlay.classList.remove('hidden');
    loadingText.textContent = text;
    loadingSub.textContent = sub;
    statusDot.className = 'status-dot loading';
    statusText.textContent = text;
    btnApply.classList.add('loading');
    btnApply.textContent = '⏳ Загрузка...';
  } else {
    loadingOverlay.classList.add('hidden');
    statusDot.className = 'status-dot';
    statusText.textContent = 'Готово';
    btnApply.classList.remove('loading');
    btnApply.textContent = '🔍 Показать на карте';
  }
}

function setError(msg) {
  loadingOverlay.classList.add('hidden');
  statusDot.className = 'status-dot error';
  statusText.textContent = 'Ошибка';
  btnApply.classList.remove('loading');
  btnApply.textContent = '🔍 Показать на карте';
  showToast(msg, 'error', 6000);
}

// ── Load & Render ─────────────────────────────────────────────

async function loadAndRenderPoints() {
  const filters = getFilters();

  // Если не выбран ни один регион (отгрузки или доставки), оставляем карту пустой
  if ((!filters.fromRegions || filters.fromRegions.length === 0) &&
      (!filters.toRegions || filters.toRegions.length === 0)) {
    clearMarkers();
    infoShip.textContent = '—';
    infoDel.textContent  = '—';
    if (emptyState) emptyState.classList.remove('hidden');
    setLoading(false);
    return;
  }

  setLoading(true, 'Запрос данных...', 'Загрузка точек по выбранным регионам...');

  try {
    const data = await fetchPoints({
      fromRegions:  filters.fromRegions,
      toRegions:    filters.toRegions,
      periodTypes:  filters.periodTypes,
      priceTypes:   filters.priceTypes,
    });

    renderPoints(data.shipment_points, data.delivery_points);

    // Обновить info panel
    infoShip.textContent      = data.total_ship.toLocaleString('ru-RU');
    infoDel.textContent       = data.total_del.toLocaleString('ru-RU');
    if (infoGeocoded) infoGeocoded.textContent = data.geocoded?.toLocaleString('ru-RU') || '—';

    // Показать/скрыть пустое состояние
    const total = data.total_ship + data.total_del;
    if (emptyState) emptyState.classList.toggle('hidden', total > 0);

    setLoading(false);
    showToast(
      `Загружено: ${data.total_ship} точек отгрузки, ${data.total_del} точек доставки`,
      'success'
    );
  } catch (err) {
    console.error(err);
    setError(`Ошибка загрузки: ${err.message}`);
  }
}

// ── Main ──────────────────────────────────────────────────────

async function main() {
  try {
    // 1. Инициализируем карту
    initMap('map');
  } catch (e) {
    console.error('Ошибка инициализации карты:', e);
    setError(` Ошибка карты: ${e.message}`);
    return;
  }

  // 2. Загружаем регионы и статистику
  setLoading(true, 'Инициализация...', 'Загружаем список регионов и статистику');

  try {
    const [regionsData, statsData] = await Promise.all([
      fetchRegions(),
      fetchStats(),
    ]);

    // Заполняем статистику в хедере
    if (statRows)      statRows.textContent      = statsData.total_rows?.toLocaleString('ru-RU') ?? '—';
    if (statShipTowns) statShipTowns.textContent = statsData.ship_towns_count?.toLocaleString('ru-RU') ?? '—';
    if (statDelTowns)  statDelTowns.textContent  = statsData.del_towns_count?.toLocaleString('ru-RU') ?? '—';

    // Инициализируем фильтры
    initFilters(regionsData.ship_regions, regionsData.del_regions, () => {});

    setLoading(false);

    // Сразу загружаем начальные данные
    await loadAndRenderPoints();

    // Запускаем polling статуса геокодирования
    startGeocodeStatusPolling();

  } catch (err) {
    console.error(err);
    setError(` Ошибка инициализации: ${err.message}`);
  }

  // Кнопка "Применить"
  btnApply.addEventListener('click', loadAndRenderPoints);

  // Кнопка "Сбросить"
  btnReset.addEventListener('click', async () => {
    resetFilters();
    clearMarkers();
    if (emptyState) emptyState.classList.remove('hidden');
    infoShip.textContent = '—';
    infoDel.textContent  = '—';
  });

  // Логика переключения темы (синхронизация кнопок + localStorage)
  const savedTheme = localStorage.getItem('app-theme') || 'dark';
  let currentTheme = savedTheme;

  function applyTheme(theme) {
    currentTheme = theme;
    const isLight = theme === 'light';

    if (isLight) {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    localStorage.setItem('app-theme', theme);
    setThemeLayer(theme);

    document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
      const icon = btn.querySelector('.theme-icon');
      const label = btn.querySelector('.theme-label');
      if (isLight) {
        if (icon) icon.textContent = '🌙';
        if (label) label.textContent = 'Тёмная тема';
        btn.setAttribute('title', 'Переключить на тёмную тему');
      } else {
        if (icon) icon.textContent = '☀️';
        if (label) label.textContent = 'Светлая тема';
        btn.setAttribute('title', 'Переключить на светлую тему');
      }
    });
  }

  // Применяем сохраненную или начальную тему
  applyTheme(currentTheme);

  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
      applyTheme(nextTheme);
    });
  });

  // Логика модального окна
  function closeModal() {
    recordsModal.classList.add('hidden');
  }

  modalClose.addEventListener('click', closeModal);
  modalOverlay.addEventListener('click', closeModal);

  window.addEventListener('regeocode-point', async (e) => {
    const { town, region } = e.detail;
    try {
      await regeocodeTown(town, region);
      await loadAndRenderPoints(); // Перезагружаем точки после пересчета
      
      // Показываем тост об успехе
      const toastEl = document.getElementById('toast');
      if (toastEl) {
        toastEl.textContent = `📍 Координаты для ${town} пересчитаны!`;
        toastEl.className = 'toast success show';
        setTimeout(() => toastEl.classList.remove('show'), 3000);
      }
    } catch (err) {
      console.error(err);
      alert(`Ошибка при пересчете: ${err.message}`);
    }
  });

  window.addEventListener('show-records-modal', async (e) => {
    const { town, region, type } = e.detail;
    recordsModal.classList.remove('hidden');
    modalTitle.textContent = `${type === 'shipment' ? 'Отгрузки из:' : 'Доставки в:'} ${town}`;
    recordsTbody.innerHTML = '';
    modalLoading.classList.remove('hidden');
    modalError.classList.add('hidden');

    try {
      const filters = getFilters();
      const res = await fetchRecords(town, region, type, {
        fromRegions: filters.fromRegions,
        toRegions: filters.toRegions,
        periodTypes: filters.periodTypes,
        priceTypes: filters.priceTypes
      });

      modalLoading.classList.add('hidden');

      if (!res.ok) throw new Error(res.error);

      if (res.records.length === 0) {
        recordsTbody.innerHTML = '<tr><td colspan="9" style="text-align:center">Нет данных</td></tr>';
        return;
      }

      // Отрисовка строк
      const rowsHtml = res.records.map(r => {
        const p = Number(r.price).toLocaleString('ru-RU');
        const km = Number(r.route_length).toLocaleString('ru-RU');
        const rkm = (r.price / (r.route_length || 1)).toLocaleString('ru-RU', {maximumFractionDigits: 1});
        const periodColor = r.period_type === 'retro' ? '#a78bfa' : r.period_type === 'current' ? '#38bdf8' : '#fbbf24';
        return `
          <tr>
            <td style="font-family: monospace; color: #3dd68c;">${p}</td>
            <td>${km}</td>
            <td>${rkm}</td>
            <td>${r.bid_count}</td>
            <td style="color:${periodColor}">${r.period_label || r.period_type}</td>
            <td>${r.price_type === 'spot' ? 'Спот' : 'Тендер'}</td>
            <td>${r.confidence || '—'}</td>
            <td>${r.ship_region}</td>
            <td>${r.del_region}</td>
          </tr>
        `;
      }).join('');
      recordsTbody.innerHTML = rowsHtml;
    } catch (err) {
      modalLoading.classList.add('hidden');
      modalError.classList.remove('hidden');
      modalError.textContent = 'Ошибка загрузки: ' + err.message;
    }
  });
}

// ── Geocode Status Polling ─────────────────────────────────────────

let _geocodeInterval = null;

function startGeocodeStatusPolling() {
  // Поллим каждые 5 секунд
  _geocodeInterval = setInterval(async () => {
    try {
      const status = await fetchGeocodeStatus();

      if (status.running && status.total > 0) {
        // Показываем статус-бар
        if (geocodeStatus) geocodeStatus.classList.remove('hidden');
        const pct = Math.round((status.done / status.total) * 100);
        if (geocodeStatusText) {
          geocodeStatusText.textContent = `Геокодирование: ${status.done}/${status.total} (найдено: ${status.found})`;
        }
        if (geocodeProgressFill) {
          geocodeProgressFill.style.width = `${pct}%`;
        }
      } else if (!status.running && status.total > 0) {
        // Геокодирование завершено — скрываем и перезагружаем карту
        if (geocodeStatus) geocodeStatus.classList.add('hidden');
        clearInterval(_geocodeInterval);
        _geocodeInterval = null;
        showToast(
          `✅ Геокодирование завершено: ${status.found} городов найдено. Обновляем карту...`,
          'success', 5000
        );
        // Перезагружаем точки с новыми координатами
        await loadAndRenderPoints();
      } else {
        // Нет активного геокодирования
        if (geocodeStatus) geocodeStatus.classList.add('hidden');
      }
    } catch (err) {
      // Молча игнорируем ошибки поллинга
      console.warn('Geocode status polling error:', err.message);
    }
  }, 5000);
}

// Запуск после загрузки DOM
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', main);
} else {
  main();
}

