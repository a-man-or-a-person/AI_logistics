/**
 * api.js — запросы к Flask бэкенду
 */

const API_BASE = window.location.origin;
const REQUEST_TIMEOUT_MS = 30_000;

async function requestJson(url, options = {}) {
  const { signal: externalSignal, ...fetchOptions } = options;
  const controller = new AbortController();
  const abortFromCaller = () => controller.abort();
  externalSignal?.addEventListener('abort', abortFromCaller, { once: true });
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const resp = await fetch(url, { ...fetchOptions, signal: controller.signal });
    const data = await resp.json().catch(() => null);
    if (!resp.ok) {
      throw new Error(data?.error || `HTTP ${resp.status}`);
    }
    if (!data?.ok) throw new Error(data?.error || 'Некорректный ответ сервера');
    return data;
  } catch (error) {
    if (error.name === 'AbortError' && !externalSignal?.aborted) {
      throw new Error('Превышено время ожидания ответа сервера');
    }
    throw error;
  } finally {
    clearTimeout(timer);
    externalSignal?.removeEventListener('abort', abortFromCaller);
  }
}

/**
 * Загружает списки регионов.
 * @returns {Promise<{ship_regions: string[], del_regions: string[]}>}
 */
export async function fetchRegions() {
  const data = await requestJson(`${API_BASE}/api/regions`);
  return { ship_regions: data.ship_regions, del_regions: data.del_regions };
}

/**
 * Загружает общую статистику.
 * @returns {Promise<Object>}
 */
export async function fetchStats() {
  return requestJson(`${API_BASE}/api/stats`);
}

/**
 * Загружает точки для карты с фильтрами.
 * @param {Object} params
 * @param {string[]} params.fromRegions
 * @param {string[]} params.toRegions
 * @param {string[]} params.periodTypes  — retro, current, forecast
 * @param {string[]} params.priceTypes   — spot, tender
 * @returns {Promise<Object>}
 */
export async function fetchPoints(
  { fromRegions = [], toRegions = [], periodTypes = [], priceTypes = [] },
  { signal } = {},
) {
  const params = new URLSearchParams();
  if (fromRegions.length)  params.set('from_regions',  fromRegions.join(','));
  if (toRegions.length)    params.set('to_regions',    toRegions.join(','));
  if (periodTypes.length)  params.set('period_types',  periodTypes.join(','));
  if (priceTypes.length)   params.set('price_types',   priceTypes.join(','));

  const url = `${API_BASE}/api/points?${params.toString()}`;
  return requestJson(url, { signal });
}

/**
 * Загружает сырые записи для города.
 */
export async function fetchRecords(town, region, type, filters = {}) {
  const params = new URLSearchParams();
  if (filters.fromRegions?.length)  params.set('from_regions',  filters.fromRegions.join(','));
  if (filters.toRegions?.length)    params.set('to_regions',    filters.toRegions.join(','));
  if (filters.periodTypes?.length)  params.set('period_types',  filters.periodTypes.join(','));
  if (filters.priceTypes?.length)   params.set('price_types',   filters.priceTypes.join(','));
  
  params.append('town', town);
  params.append('region', region);
  params.append('type', type);
  
  const url = `${API_BASE}/api/records?${params.toString()}`;
  return requestJson(url);
}

/**
 * Запрашивает статус фонового геокодирования.
 */
export async function fetchGeocodeStatus() {
  return requestJson(`${API_BASE}/api/geocode-status`);
}

/**
 * Принудительно пересчитывает координаты для города.
 */
export async function regeocodeTown(town, region) {
  return requestJson(`${API_BASE}/api/regeocode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ town, region })
  });
}

/**
 * ML-кластеризация для региона
 */
export async function fetchMlClusters({ region, type, k, filters = {} }) {
  const params = new URLSearchParams();
  params.append('region', region);
  params.append('town_type', type);
  params.append('k', k);
  
  if (filters.periodTypes?.length) params.set('period_types', filters.periodTypes.join(','));
  if (filters.priceTypes?.length)  params.set('price_types', filters.priceTypes.join(','));

  const url = `${API_BASE}/api/ml-cluster?${params.toString()}`;
  return requestJson(url);
}
