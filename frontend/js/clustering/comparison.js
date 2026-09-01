import { decimal, escapeHtml, fmt, MODE_LABELS, rubKm } from './formatters.js';

const $ = id => document.getElementById(id);

export function renderComparison(state, handlers = {}) {
  const comparison = state.comparison;
  $('comparison-view').classList.toggle('hidden', !comparison.open);
  $('workspace').classList.toggle('comparison-open', comparison.open);
  if (!comparison.open) return;
  $('comparison-stale').classList.toggle('hidden', !handlers.isStale?.());
  $('comparison-loading').classList.toggle('hidden', comparison.status !== 'loading');
  $('comparison-error').classList.toggle('hidden', comparison.status !== 'error');
  $('comparison-error').textContent = comparison.error?.message || '';
  $('comparison-context').innerHTML = context(comparison.contextDisplay);
  const modes = Object.keys(comparison.results);
  $('comparison-tabs').innerHTML = modes.map(mode => `
    <button type="button" data-comparison-mode="${mode}" class="${comparison.activeMode === mode ? 'active' : ''}" ${comparison.activeMode === mode ? 'aria-current="true"' : ''}>${MODE_LABELS[mode]}</button>`).join('');
  $('comparison-cards').innerHTML = modes.map(mode => card(comparison.results[mode])).join('');
  document.querySelectorAll('[data-comparison-mode]').forEach(button => button.addEventListener('click', () => handlers.onActivate?.(button.dataset.comparisonMode)));
  document.querySelectorAll('[data-show-on-map]').forEach(button => button.addEventListener('click', () => handlers.onShowMap?.(button.dataset.showOnMap)));
}

function context(display) {
  if (!display) return '';
  return `<strong>${escapeHtml(display.route)}</strong>
    <span>Источник: Pulse</span>
    <dl>
      <div><dt>Периоды</dt><dd>${escapeHtml(display.periods)}</dd></div>
      <div><dt>Цены</dt><dd>${escapeHtml(display.prices)}</dd></div>
      <div><dt>Кузов</dt><dd>${escapeHtml(display.vehicles)}</dd></div>
      <div><dt>Тоннаж</dt><dd>${escapeHtml(display.tonnages)}</dd></div>
    </dl>`;
}

function card(result) {
  const mode = result.analysis.mode;
  const metrics = result.metrics || {};
  const parameters = result.analysis.parameters || {};
  const quality = result.data_quality || {};
  const economicCoverage = quality.resolved_points
    ? (Number(quality.economic_valid_points || 0) / Number(quality.resolved_points)) * 100
    : 0;
  const bearModes = ['bear_zones', 'bear_volume_zones'];
  const threshold = mode === 'bear_volume_zones'
    ? parameters.volume_threshold
    : parameters.bear_threshold;
  const modeRows = bearModes.includes(mode)
    ? `
      <div><dt>Порог</dt><dd>+${Math.round((threshold ?? 0.35) * 100)}%</dd></div>
      <div><dt>Кандидаты</dt><dd>${fmt(metrics.candidate_count)}</dd></div>
      <div><dt>Зоны</dt><dd>${fmt(metrics.bear_zone_count)}</dd></div>
      <div><dt>Одиночные</dt><dd>${fmt(metrics.singleton_count)}</dd></div>
      <div><dt>Покрыто перевозок</dt><dd>${fmt(metrics.covered_trip_count)}</dd></div>`
    : `
      <div><dt>${parameters.k_mode === 'manual' ? 'K' : 'Auto K'}</dt><dd>${fmt(parameters.n_clusters)}</dd></div>
      ${mode === 'geo_cost' ? `<div><dt>Geo / Cost</dt><dd>${Math.round((parameters.geography_weight ?? 0.7) * 100)}/${Math.round((parameters.economics_weight ?? 0.3) * 100)}</dd></div>` : ''}
      ${mode === 'geo_volume' ? `<div><dt>Geo / Volume</dt><dd>${Math.round((parameters.geography_weight ?? 0.7) * 100)}/${Math.round((parameters.volume_weight ?? 0.3) * 100)}</dd></div>` : ''}
      <div><dt>P95 радиус</dt><dd>${decimal((metrics.p95_distance_to_medoid_m ?? 0) / 1000, 1)} км</dd></div>
      ${mode === 'geo_cost' ? `<div><dt>Экономическое покрытие</dt><dd>${decimal(economicCoverage, 1)}%</dd></div>
        <div><dt>Внутри кластеров</dt><dd>${rubKm(metrics.within_cluster_weighted_rubkm_mad)}</dd></div>
        <div><dt>Между кластерами</dt><dd>${rubKm(metrics.between_cluster_rate_spread)}</dd></div>` : ''}
      ${mode === 'geo_volume' ? `<div><dt>Внутри кластеров</dt><dd>${decimal(metrics.within_cluster_trip_count_mad, 1)} перевозки</dd></div>
        <div><dt>Между кластерами</dt><dd>${decimal(metrics.between_cluster_mean_trip_spread, 1)} перевозки</dd></div>` : ''}`;
  return `<article class="comparison-card ${comparisonClass(mode)}">
    <h3>${MODE_LABELS[mode]}</h3>
    <dl>
      ${modeRows}
      <div><dt>Точки</dt><dd>${fmt(quality.resolved_points)}</dd></div>
      <div><dt>Перевозки</dt><dd>${fmt(quality.trip_count_total)}</dd></div>
      <div><dt>Покрытие точек</dt><dd>${decimal(quality.point_coverage_pct, 1)}%</dd></div>
      <div><dt>Изолированные</dt><dd>${fmt(result.outliers?.length)}</dd></div>
    </dl>
    <button type="button" data-show-on-map="${mode}">Показать на карте</button>
  </article>`;
}

function comparisonClass(mode) {
  if (mode === 'bear_zones') return 'bear-comparison';
  if (mode === 'bear_volume_zones') return 'bear-comparison volume-bear-comparison';
  return '';
}
