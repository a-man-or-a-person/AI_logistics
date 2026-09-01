/** DOM-independent Product v1 state and request snapshots. */

export const MODES = Object.freeze({
  geography: {
    label: 'По географии',
    description: 'Формирует территориально связанные зоны только по расположению точек.',
    badge: 'Только география',
  },
  geo_cost: {
    label: 'География + стоимость',
    description: 'Учитывает географическую близость и различия в ₽/км.',
    badge: 'География и ₽/км',
  },
  geo_volume: {
    label: 'География + объём',
    description: 'Учитывает географическую близость и различия в числе перевозок.',
    badge: 'География и объём',
  },
  bear_zones: {
    label: 'Медвежьи зоны',
    description: 'Ищет связанные участки с аномально высокой стоимостью.',
    badge: 'Без K',
  },
  bear_volume_zones: {
    label: 'Медвежьи зоны по объёму',
    description: 'Ищет связанные участки с аномально высоким объёмом перевозок.',
    badge: 'Без K',
  },
});

const sorted = values => [...(values || [])].sort((a, b) => String(a).localeCompare(String(b)));
const clone = value => value == null ? value : JSON.parse(JSON.stringify(value));

export function createClusteringState(options = {}) {
  return {
    options,
    form: {
      origin: null,
      destinationRegion: '',
      periodTypes: [...(options.defaults?.period_types || ['current'])],
      priceTypes: [...(options.defaults?.price_types || ['spot'])],
      vehicleTypes: [],
      tonnageIds: [],
      mode: options.defaults?.mode || 'geography',
      kMode: options.defaults?.k_mode || 'auto',
      k: options.k?.default || 5,
      costWeight: options.geo_cost_weights?.default?.economics ?? 0.30,
      volumeWeight: options.geo_volume_weights?.default?.volume ?? 0.30,
      bearThreshold: options.bear_thresholds?.zone_default ?? 0.35,
      bearVolumeThreshold: options.bear_volume_thresholds?.zone_default ?? 0.35,
      singletonThreshold: 0.70,
    },
    result: { status: 'empty', data: null, error: null, requestSnapshot: null, cache: new Map() },
    comparison: { open: false, status: 'empty', context: null, contextDisplay: null, results: {}, activeMode: null, error: null, cache: new Map() },
    ui: { selectedCluster: null, selectedPoint: null, inspectorMode: 'summary' },
  };
}

export function datasetSnapshot(form) {
  return {
    origin_fias: form.origin?.fias_id || '',
    destination_region: form.destinationRegion,
    period_types: sorted(form.periodTypes),
    price_types: sorted(form.priceTypes),
    vehicle_types: sorted(form.vehicleTypes),
    tonnage_ids: sorted(form.tonnageIds),
  };
}

export function buildRequest(form, mode = form.mode) {
  const request = { ...datasetSnapshot(form), mode, parameters: {} };
  if (mode === 'bear_zones') {
    request.parameters = {
      bear_threshold: Number(form.bearThreshold),
      singleton_threshold: Number(form.singletonThreshold),
    };
  } else if (mode === 'bear_volume_zones') {
    request.parameters = {
      volume_threshold: Number(form.bearVolumeThreshold),
      singleton_threshold: Number(form.singletonThreshold),
    };
  } else {
    request.parameters = {
      k_mode: form.kMode,
      n_clusters: form.kMode === 'auto' ? 'auto' : Number(form.k),
    };
    if (mode === 'geo_cost') {
      request.parameters.geography_weight = Number((1 - Number(form.costWeight)).toFixed(2));
      request.parameters.economics_weight = Number(form.costWeight);
    }
    if (mode === 'geo_volume') {
      request.parameters.geography_weight = Number((1 - Number(form.volumeWeight)).toFixed(2));
      request.parameters.volume_weight = Number(form.volumeWeight);
    }
  }
  return request;
}

export function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, stableValue(value[key])]));
  }
  return value;
}

export function semanticallyEqual(left, right) {
  return JSON.stringify(stableValue(left)) === JSON.stringify(stableValue(right));
}

export function requestSignature(request) {
  return JSON.stringify(stableValue(request));
}

export function isResultStale(state) {
  return Boolean(state.result.requestSnapshot)
    && !semanticallyEqual(buildRequest(state.form), state.result.requestSnapshot);
}

export function isComparisonStale(state) {
  return Boolean(state.comparison.context)
    && !semanticallyEqual(datasetSnapshot(state.form), state.comparison.context);
}

export function setResult(state, data, request) {
  const cache = state.result.cache || new Map();
  cache.set(requestSignature(request), data);
  state.result = { status: data.status || 'success', data, error: null, requestSnapshot: clone(request), cache };
  state.ui.selectedCluster = null;
  state.ui.selectedPoint = null;
}

export function warningKinds(form) {
  const warnings = [];
  if (form.periodTypes.includes('forecast')) warnings.push('forecast');
  if (form.periodTypes.includes('forecast') && form.periodTypes.includes('current')) warnings.push('current_forecast');
  if (
    ['geo_cost', 'bear_zones'].includes(form.mode)
    && (form.priceTypes.length > 1 || form.vehicleTypes.length > 1 || form.tonnageIds.length > 1)
  ) warnings.push('mixed_segment');
  return warnings;
}
