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

export function fetchClusteringOptions(originFias = '', destinationRegion = '', allOrigins = false) {
  const params = new URLSearchParams();
  if (allOrigins) params.set('all_origins', 'true');
  else if (Array.isArray(originFias)) {
    [...new Set(originFias)].sort().forEach(fias => params.append('origin_fiases', fias));
  } else if (originFias) params.set('origin_fias', originFias);
  if (destinationRegion) params.set('destination_region', destinationRegion);
  const suffix = params.toString() ? `?${params}` : '';
  return requestJson(`${API_BASE}/api/clustering/options${suffix}`);
}

export function fetchClusteringOrigins(query = '', limit = 20) {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return requestJson(`${API_BASE}/api/clustering/origins?${params}`);
}

function postClustering(path, payload, { signal, cache } = {}) {
  return requestJson(`${API_BASE}/api/clustering/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
    cache,
  });
}

export function previewClustering(payload, options) {
  return postClustering('preview', payload, options);
}

export function runClustering(payload, options) {
  return postClustering('run', payload, options);
}

export function fetchClusteringRevision(results, options = {}) {
  return postClustering('revision', {results}, {...options, cache: 'no-store'});
}

export function fetchClusteringPointRows(payload, options) {
  return postClustering('point-rows', payload, options);
}

export function fetchClusteringPointOrigins(payload, options) {
  return postClustering('point-origins', payload, options);
}

export async function exportClustering(payload, { signal } = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  if (signal?.aborted) abort();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; abort(); }, REQUEST_TIMEOUT_MS);
  let requestId;
  try {
    if (controller.signal.aborted) throw new DOMException('Загрузка отменена', 'AbortError');
    const response = await fetch(`${API_BASE}/api/clustering/export`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload), cache: 'no-store', signal: controller.signal,
    });
    requestId = response.headers.get('X-Request-ID')?.replace(/[\u0000-\u001f\u007f]/g, '').slice(0, 64);
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw Object.assign(new Error(data?.error || `HTTP ${response.status}`), { code: data?.code, requestId });
    }
    const disposition = response.headers.get('Content-Disposition') || '';
    if (response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase()
        !== 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        || !/^attachment\s*;/i.test(disposition)) {
      throw Object.assign(new Error('Сервер не вернул XLSX-вложение.'), { code: 'INVALID_EXPORT_RESPONSE' });
    }
    let filename = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1];
    if (filename) {
      try { filename = decodeURIComponent(filename); } catch { filename = null; }
    }
    filename ||= /filename="([^"]+)"|filename=([^;]+)/i.exec(disposition)?.slice(1).find(Boolean)?.trim();
    if (!filename || filename.length > 180 || /[<>:"/\\|?*\u0000-\u001f\u007f\u202a-\u202e\u2066-\u2069]/.test(filename)
        || /^(?:\.|CON\.|PRN\.|AUX\.|NUL\.|COM[1-9]\.|LPT[1-9]\.)/i.test(filename)
        || !/\.xlsx$/i.test(filename)) filename = 'clustering.xlsx';
    const blob = await response.blob();
    const bytes = new Uint8Array(await blob.arrayBuffer());
    // A complete ZIP end record prevents accepting an interrupted attachment as a workbook.
    let complete = false;
    for (let i = bytes.length - 22; i >= Math.max(4, bytes.length - 65557); i--) {
      if (bytes[i] === 80 && bytes[i + 1] === 75 && bytes[i + 2] === 5 && bytes[i + 3] === 6
          && i + 22 + bytes[i + 20] + 256 * bytes[i + 21] === bytes.length) { complete = true; break; }
    }
    if (bytes[0] !== 80 || bytes[1] !== 75 || bytes[2] !== 3 || bytes[3] !== 4 || !complete) {
      throw Object.assign(new Error('Получен неполный или некорректный XLSX.'), { code: 'INVALID_EXPORT_RESPONSE' });
    }
    if (controller.signal.aborted) throw new DOMException('Загрузка отменена', 'AbortError');
    return { blob, filename, requestId };
  } catch (error) {
    if (signal?.aborted) throw new DOMException('Загрузка отменена', 'AbortError');
    if (timedOut) throw Object.assign(new Error('Превышено время ожидания XLSX. Повторите загрузку.'), { code: 'EXPORT_TIMEOUT', requestId });
    if (error instanceof TypeError) throw Object.assign(new Error('Нет соединения с сервером. Повторите загрузку XLSX.'), { code: 'EXPORT_CONNECTION_ERROR', requestId });
    error.requestId ||= requestId;
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}

export function fetchMlClusters(params = {}) {
  return requestJson(`${API_BASE}/api/ml-cluster?${new URLSearchParams(params)}`);
}

/** Keep comparison transport in the API layer and one immutable dataset context. */
export function runClusteringComparison(dataset, options = {}) {
  return postClustering('compare', dataset, options);
}
