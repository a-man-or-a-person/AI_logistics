/** Product clustering request mapping, stable signatures and client cache. */

export const MODE_LABELS = {
  geography: 'По географии',
  geo_cost: 'География + стоимость',
  bear_zones: 'Медвежьи зоны',
};

export const PERIOD_LABELS = { retro: 'Архив', current: 'Текущий', forecast: 'Прогноз' };
export const PRICE_LABELS = { spot: 'Спот', tender: 'Тендер' };

export function createClusteringState() {
  return {
    options: null,
    contextOptions: null,
    result: null,
    resultRequest: null,
    selectedClusterId: null,
    resultCache: new Map(),
    comparisonCache: new Map(),
  };
}

export function requestSignature(request, includeMode = true) {
  const normalized = {
    origin_fias: request.origin_fias,
    destination_region: request.destination_region,
    filters: Object.fromEntries(
      Object.entries(request.filters || {}).map(([key, values]) => [key, [...values].sort()]),
    ),
  };
  if (includeMode) {
    normalized.mode = request.mode;
    normalized.parameters = request.parameters || {};
  }
  return JSON.stringify(normalized);
}

export function buildClusteringRequest(values) {
  const parameters = {};
  if (values.mode === 'bear_zones') {
    parameters.bear_threshold_pct = Number(values.bearThreshold || 35);
    parameters.singleton_threshold_pct = 70;
  } else {
    parameters.k_mode = values.kMode;
    if (values.kMode === 'manual') parameters.n_clusters = Number(values.k);
    if (values.mode === 'geo_cost') {
      parameters.geography_weight = 0.7;
      parameters.economics_weight = 0.3;
    }
  }
  return {
    origin_fias: values.originFias,
    destination_region: values.destinationRegion,
    mode: values.mode,
    filters: {
      period_types: [...values.periodTypes].sort(),
      price_types: [...values.priceTypes].sort(),
      vehicle_types: [...values.vehicleTypes].sort(),
      tonnage_ids: [...values.tonnageIds].sort(),
    },
    parameters,
  };
}

export function clusterTitle(cluster) {
  if (cluster.cluster_type === 'bear_zone') return 'Медвежья зона';
  if (cluster.cluster_type === 'expensive_singleton') return 'Аномально дорогая точка';
  return `Зона ${Number(cluster.cluster_id) + 1}`;
}
