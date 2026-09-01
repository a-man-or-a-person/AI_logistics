export const PERIOD_LABELS = { retro: 'Архив', current: 'Текущий', forecast: 'Прогноз' };
export const PRICE_LABELS = { spot: 'Спот', tender: 'Тендер' };
export const MODE_LABELS = {
  geography: 'По географии',
  geo_cost: 'География + стоимость',
  geo_volume: 'География + объём',
  bear_zones: 'Медвежьи зоны',
  bear_volume_zones: 'Медвежьи зоны по объёму',
};

export const fmt = value => Number(value || 0).toLocaleString('ru-RU');
export const decimal = (value, digits = 1) => value == null ? '—' : Number(value).toLocaleString('ru-RU', { maximumFractionDigits: digits });
export const percent = value => value == null ? '—' : `${decimal(Number(value) * 100, 0)}%`;
export const km = value => value == null ? '—' : `${decimal(value, 1)} км`;
export const rubKm = value => value == null ? '—' : `${decimal(value, 1)} ₽/км`;
export const clusterLabel = (cluster, mode) => {
  if (mode === 'bear_zones') {
    return cluster.cluster_type === 'expensive_singleton'
      ? 'Аномально дорогая точка'
      : `Медвежья зона B${Number(cluster.cluster_id) + 1}`;
  }
  if (mode === 'bear_volume_zones') {
    return cluster.cluster_type === 'high_volume_singleton'
      ? 'Аномально объёмная точка'
      : `Объёмная зона V${Number(cluster.cluster_id) + 1}`;
  }
  return `Зона ${Number(cluster.cluster_id) + 1}`;
};

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[char]);
}
