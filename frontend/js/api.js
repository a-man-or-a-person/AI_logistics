/** HTTP client for the Data Map and canonical clustering API. */

const API_BASE = window.location.origin;
const REQUEST_TIMEOUT_MS = 30_000;

async function requestJson(url, options = {}) {
  const { signal: externalSignal, ...fetchOptions } = options;
  const controller = new AbortController();
  const abortFromCaller = () => controller.abort();
  externalSignal?.addEventListener('abort', abortFromCaller, { once: true });
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, { ...fetchOptions, signal: controller.signal });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const error = new Error(data?.error || `HTTP ${response.status}`);
      error.code = data?.code;
      throw error;
    }
    if (!Array.isArray(data) && !data?.ok) {
      throw new Error(data?.error || 'Некорректный ответ сервера');
    }
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

export async function fetchRegions() {
  const data = await requestJson(`${API_BASE}/api/regions`);
  return { ship_regions: data.ship_regions, del_regions: data.del_regions };
}

export function fetchStats() {
  return requestJson(`${API_BASE}/api/stats`);
}

export function fetchPoints(
  { fromRegions = [], toRegions = [], periodTypes = [], priceTypes = [] },
  { signal } = {},
) {
  const params = new URLSearchParams();
  if (fromRegions.length) params.set('from_regions', fromRegions.join(','));
  if (toRegions.length) params.set('to_regions', toRegions.join(','));
  if (periodTypes.length) params.set('period_types', periodTypes.join(','));
  if (priceTypes.length) params.set('price_types', priceTypes.join(','));
  return requestJson(`${API_BASE}/api/points?${params}`, { signal });
}

export function fetchRecords(town, region, type, filters = {}) {
  const params = new URLSearchParams({ town, region, type });
  if (filters.fromRegions?.length) params.set('from_regions', filters.fromRegions.join(','));
  if (filters.toRegions?.length) params.set('to_regions', filters.toRegions.join(','));
  if (filters.periodTypes?.length) params.set('period_types', filters.periodTypes.join(','));
  if (filters.priceTypes?.length) params.set('price_types', filters.priceTypes.join(','));
  return requestJson(`${API_BASE}/api/records?${params}`);
}

export function fetchGeocodeStatus() {
  return requestJson(`${API_BASE}/api/geocode-status`);
}

export function regeocodeTown(town, region) {
  return requestJson(`${API_BASE}/api/regeocode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ town, region }),
  });
}

export function fetchClusteringOptions(originFias = '', destinationRegion = '') {
  const params = new URLSearchParams();
  if (originFias) params.set('origin_fias', originFias);
  if (destinationRegion) params.set('destination_region', destinationRegion);
  const suffix = params.toString() ? `?${params}` : '';
  return requestJson(`${API_BASE}/api/clustering/options${suffix}`);
}

export function fetchClusteringOrigins(query = '', limit = 20) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return requestJson(`${API_BASE}/api/clustering/origins?${params}`);
}

function postClustering(path, payload, { signal } = {}) {
  return requestJson(`${API_BASE}/api/clustering/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });
}

export function previewClustering(payload, options) {
  return postClustering('preview', payload, options);
}

export function runClustering(payload, options) {
  return postClustering('run', payload, options);
}

export function fetchClusteringPointRows(payload, options) {
  return postClustering('point-rows', payload, options);
}

export function fetchMlClusters(params = {}) {
  return requestJson(`${API_BASE}/api/ml-cluster?${new URLSearchParams(params)}`);
}

/** Keep comparison transport in the API layer and one immutable dataset context. */
export function runClusteringComparison(dataset, options = {}) {
  return postClustering('compare', dataset, options);
}
