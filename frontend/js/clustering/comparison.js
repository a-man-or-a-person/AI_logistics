import { decimal, escapeHtml, fmt, MODE_LABELS, rubKm } from './formatters.js';

const $ = id => document.getElementById(id);

export function renderComparison(state, handlers = {}) {
  const comparison = state.comparison;
  $('comparison-view').classList.toggle('hidden', !comparison.open);
  $('workspace').classList.toggle('comparison-open', comparison.open);
  if (!comparison.open) return;
  const focusedMode = document.activeElement?.dataset.comparisonMode;
  $('comparison-stale').classList.toggle('hidden', !handlers.isStale?.());
  $('comparison-loading').classList.toggle('hidden', comparison.status !== 'loading');
  $('comparison-error').classList.toggle('hidden', comparison.status !== 'error');
  $('comparison-error').textContent = comparison.error?.message || '';
  $('comparison-context').innerHTML = context(comparison.contextDisplay);
  const resultModes = new Set(Object.keys(comparison.results));
  const modes = state.comparisonModeIds.filter(mode => resultModes.has(mode));
  $('comparison-tabs').innerHTML = modes.map(mode => `
    <button type="button" data-comparison-mode="${mode}" class="${comparison.activeMode === mode ? 'active' : ''}" ${comparison.activeMode === mode ? 'aria-current="true"' : ''}>${MODE_LABELS[mode]}</button>`).join('');
  $('comparison-cards').innerHTML = matrix(modes.map(mode => comparison.results[mode]));
  document.querySelectorAll('[data-comparison-mode]').forEach(button => button.addEventListener('click', () => handlers.onActivate?.(button.dataset.comparisonMode)));
  document.querySelectorAll('[data-show-on-map]').forEach(button => button.addEventListener('click', () => handlers.onShowMap?.(button.dataset.showOnMap)));
  if (focusedMode) [...document.querySelectorAll('[data-comparison-mode]')]
    .find(button => button.dataset.comparisonMode === focusedMode)?.focus({preventScroll: true});
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

function matrix(results) {
  if (!results.length) return '';
  const count = value => value == null ? '—' : fmt(value);
  const percentage = value => value == null ? '—' : `${decimal(value, 1)}%`;
  const parameter = (r, key) => percentage(r.analysis.parameters[key] == null ? null : r.analysis.parameters[key] * 100);
  const threshold = (r, key) => r.analysis.parameters[key] == null ? '—' : `+${parameter(r, key)}`;
  const bear = result => ['bear_zones', 'bear_volume_zones'].includes(result.analysis.mode);
  const na = 'Не применимо';
  const rows = [
    ['status', 'Результат', r => r.status === 'no_bears' ? 'Зоны не найдены' : r.status === 'success' ? 'Рассчитан' : escapeHtml(r.status || '—')],
    ['n_clusters', 'Кластеры K', r => bear(r) ? na : `${r.analysis.parameters.k_mode === 'manual' ? 'K' : 'Auto'} → ${count(r.analysis.parameters.n_clusters)}`],
    ['weights', 'Geo / Cost, Geo / Volume', r => ['geo_cost', 'geo_volume'].includes(r.analysis.mode)
      ? `${parameter(r, 'geography_weight')} / ${parameter(r, r.analysis.mode === 'geo_cost' ? 'economics_weight' : 'volume_weight')}` : na],
    ['p95_distance_to_medoid_m', 'P95 до medoid, км', r => bear(r) ? na : r.metrics?.p95_distance_to_medoid_m == null ? '—' : `${decimal(r.metrics.p95_distance_to_medoid_m / 1000, 1)} км`],
    ['economicCoverage', 'Экономическое покрытие<small>Точки с экономикой / точки с координатами</small>', r => r.analysis.mode !== 'geo_cost' ? na : r.data_quality?.economic_valid_points == null || !(r.data_quality.resolved_points > 0) ? '—' : percentage(r.data_quality.economic_valid_points / r.data_quality.resolved_points * 100)],
    ['within_cluster_weighted_rubkm_mad', 'Внутри кластеров, ₽/км<small>Алгоритмическое отклонение ставки; вес всех машин точек</small>', r => r.analysis.mode === 'geo_cost' ? rubKm(r.metrics?.within_cluster_weighted_rubkm_mad) : na],
    ['between_cluster_rate_spread', 'Между кластерами, ₽/км<small>Размах алгоритмических средних ставок</small>', r => r.analysis.mode === 'geo_cost' ? rubKm(r.metrics?.between_cluster_rate_spread) : na],
    ['within_cluster_trip_count_mad', 'Внутри кластеров, машины<small>Невзвешенное отклонение объёма точки</small>', r => r.analysis.mode === 'geo_volume' ? decimal(r.metrics?.within_cluster_trip_count_mad, 1) : na],
    ['between_cluster_mean_trip_spread', 'Между кластерами, машины<small>Размах средних машин на точку</small>', r => r.analysis.mode === 'geo_volume' ? decimal(r.metrics?.between_cluster_mean_trip_spread, 1) : na],
    ['threshold', 'Порог превышения Bear', r => bear(r) ? threshold(r, r.analysis.mode === 'bear_volume_zones' ? 'volume_threshold' : 'bear_threshold') : na],
    ['singleton_threshold', 'Порог одиночной точки Bear<small>Сохранённое правило режима</small>', r => bear(r) ? threshold(r, 'singleton_threshold') : na],
    ['candidate_count', 'Кандидаты Bear', r => bear(r) ? count(r.metrics?.candidate_count) : na],
    ['bear_zone_count', 'Зоны Bear', r => bear(r) ? count(r.metrics?.bear_zone_count) : na],
    ['singleton_count', 'Одиночные точки Bear', r => bear(r) ? count(r.metrics?.singleton_count) : na],
    ['covered_trip_count', 'Машины в зонах и одиночных точках Bear', r => bear(r) ? count(r.metrics?.covered_trip_count) : na],
    ['resolved_points', 'Точки с координатами', r => count(r.data_quality?.resolved_points)],
    ['trip_count_total', 'Все машины среза', r => count(r.data_quality?.trip_count_total)],
    ['point_coverage_pct', 'Покрытие точек координатами', r => percentage(r.data_quality?.point_coverage_pct)],
    ['trip_weight_coverage_pct', 'Покрытие машин координатами', r => percentage(r.data_quality?.trip_weight_coverage_pct)],
    ['outliers', 'Изолированные точки', r => count(r.outliers?.length)],
  ];
  return `<table class="comparison-matrix"><caption>Результаты на одном сохранённом срезе. Популяции режимов могут различаться.</caption>
    <thead><tr><th scope="col">Показатель</th>${results.map(r => `<th scope="col">${MODE_LABELS[r.analysis.mode]}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(([key, label, value]) => `<tr data-comparison-metric="${key}"><th scope="row">${label}</th>${results.map(r => `<td>${value(r)}</td>`).join('')}</tr>`).join('')}</tbody>
    <tfoot><tr><th scope="row">Сохранённый результат</th>${results.map(r => `<td><button type="button" data-show-on-map="${r.analysis.mode}">Показать на карте</button></td>`).join('')}</tr></tfoot>
  </table>`;
}
