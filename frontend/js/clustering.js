/** Canonical request construction and stable stale-state signatures. */

export const PERIOD_LABELS = {
  retro: 'Архив',
  current: 'Текущий',
  forecast: 'Прогноз',
};

export const PRICE_LABELS = { spot: 'Спот', tender: 'Тендер' };

export function buildClusteringRequest(values) {
  return {
    origin_fias: values.originFias,
    destination_region: values.destinationRegion,
    period_types: [...values.periodTypes].sort(),
    price_types: [...values.priceTypes].sort(),
    algorithm: 'kmeans',
    parameters: {
      n_clusters: Number(values.nClusters),
      weight_mode: values.weightMode,
    },
  };
}

export function requestSignature(request) {
  return JSON.stringify({
    ...request,
    period_types: [...request.period_types].sort(),
    price_types: [...request.price_types].sort(),
    parameters: { ...request.parameters },
  });
}

export function zoneLabel(clusterId) {
  return `Z${Number(clusterId) + 1}`;
}
