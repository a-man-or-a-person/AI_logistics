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

const parameter = (name, kind, defaultValue, choices = [], minimum = null, maximum = null, fixed = false, manualDefault = null) => ({
  name, kind, default: defaultValue, choices, min: minimum, max: maximum, fixed, manual_default: manualDefault,
});

function compatibilityCapabilities(options) {
  const k = options.k || {};
  const kParameters = () => [
    parameter('k_mode', 'choice', options.defaults?.k_mode, k.modes || []),
    parameter('n_clusters', 'cluster_count', options.defaults?.k_mode, [], k.min, k.max, false, k.default),
  ];
  const definitions = {
    geography: () => ({ parameters: kParameters(), presets: [] }),
    geo_cost: () => ({
      parameters: [
        ...kParameters(),
        parameter('geography_weight', 'choice', options.geo_cost_weights?.default?.geography, (options.geo_cost_weights?.presets || []).map(item => item.geography)),
        parameter('economics_weight', 'choice', options.geo_cost_weights?.default?.economics, (options.geo_cost_weights?.presets || []).map(item => item.economics)),
      ],
      presets: options.geo_cost_weights?.presets || [],
    }),
    geo_volume: () => ({
      parameters: [
        ...kParameters(),
        parameter('geography_weight', 'choice', options.geo_volume_weights?.default?.geography, (options.geo_volume_weights?.presets || []).map(item => item.geography)),
        parameter('volume_weight', 'choice', options.geo_volume_weights?.default?.volume, (options.geo_volume_weights?.presets || []).map(item => item.volume)),
      ],
      presets: options.geo_volume_weights?.presets || [],
    }),
    bear_zones: () => ({
      parameters: [
        parameter('bear_threshold', 'choice', options.bear_thresholds?.zone_default, options.bear_thresholds?.zone_options || []),
        parameter('singleton_threshold', 'choice', options.bear_thresholds?.singleton_default, [options.bear_thresholds?.singleton_default], null, null, options.bear_thresholds?.singleton_fixed),
      ],
      presets: [],
    }),
    bear_volume_zones: () => ({
      parameters: [
        parameter('volume_threshold', 'choice', options.bear_volume_thresholds?.zone_default, options.bear_volume_thresholds?.zone_options || []),
        parameter('singleton_threshold', 'choice', options.bear_volume_thresholds?.singleton_default, [options.bear_volume_thresholds?.singleton_default], null, null, options.bear_volume_thresholds?.singleton_fixed),
      ],
      presets: [],
    }),
  };
  return (options.modes || []).filter(id => definitions[id]).map(id => ({
    id,
    ...definitions[id](),
    semantic_dimensions: [],
    result_kind: null,
    comparison: { supported: true, parameters: {} },
  }));
}

export function productModeCapabilities(options = {}) {
  const published = Array.isArray(options.mode_capabilities) ? options.mode_capabilities : [];
  return clone(published.length ? published : compatibilityCapabilities(options));
}

export function modeParameter(capabilities, modeId, name) {
  return capabilities.find(item => item.id === modeId)?.parameters?.find(item => item.name === name);
}

export function updateClusteringOptions(state, options) {
  state.options = { ...state.options, ...options };
  state.modeCapabilities = productModeCapabilities(state.options);
  state.comparisonModeIds = state.modeCapabilities
    .filter(item => item.comparison?.supported)
    .map(item => item.id);
}

export function createClusteringState(options = {}) {
  const modeCapabilities = productModeCapabilities(options);
  const modeIds = modeCapabilities.map(item => item.id);
  const defaultMode = modeIds.includes(options.defaults?.mode) ? options.defaults.mode : modeIds[0];
  const value = (modeId, name) => modeParameter(modeCapabilities, modeId, name)?.default;
  return {
    options,
    modeCapabilities,
    comparisonModeIds: modeCapabilities.filter(item => item.comparison?.supported).map(item => item.id),
    form: {
      origin: null,
      destinationRegion: '',
      periodTypes: [...(options.defaults?.period_types || ['current'])],
      priceTypes: [...(options.defaults?.price_types || ['spot'])],
      vehicleTypes: [],
      tonnageIds: [],
      mode: defaultMode,
      kMode: value('geography', 'k_mode'),
      k: modeParameter(modeCapabilities, 'geography', 'n_clusters')?.manual_default,
      costWeight: value('geo_cost', 'economics_weight'),
      volumeWeight: value('geo_volume', 'volume_weight'),
      bearThreshold: value('bear_zones', 'bear_threshold'),
      bearVolumeThreshold: value('bear_volume_zones', 'volume_threshold'),
      singletonThreshold: value('bear_zones', 'singleton_threshold'),
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
