import { MODES, warningKinds } from './state.js';
import { MODE_LABELS, PERIOD_LABELS, PRICE_LABELS, escapeHtml } from './formatters.js';

const $ = id => document.getElementById(id);

function checks(id, items, selected, labels = {}) {
  $(id).innerHTML = items.map(item => {
    const value = typeof item === 'string' ? item : item.value;
    const count = typeof item === 'string' ? '' : ` <small>${item.count}</small>`;
    return `<label class="check-chip"><input type="checkbox" value="${escapeHtml(value)}" ${selected.includes(value) ? 'checked' : ''}><span>${escapeHtml(labels[value] || value)}${count}</span></label>`;
  }).join('');
}

export function renderOptionControls(state) {
  const { options, form } = state;
  checks('cluster-periods', options.period_types || [], form.periodTypes, PERIOD_LABELS);
  checks('cluster-prices', options.price_types || [], form.priceTypes, PRICE_LABELS);
  checks('cluster-vehicles', options.vehicle_types || [], form.vehicleTypes);
  checks('cluster-tonnages', options.tonnage_ids || [], form.tonnageIds);
  $('mode-cards').innerHTML = Object.entries(MODES).map(([value, item]) => `
    <label class="mode-card mode-${value} ${form.mode === value ? 'selected' : ''}">
      <input type="radio" name="analysis-mode" value="${value}" ${form.mode === value ? 'checked' : ''}>
      <span class="mode-card-heading"><strong>${item.label}</strong><small>${item.badge}</small></span>
      <span>${item.description}</span>
    </label>`).join('');
  $('manual-k').min = options.k?.min ?? 2;
  $('manual-k').max = options.k?.max ?? 20;
  $('manual-k').value = form.k;
  const weightPresets = options.geo_cost_weights?.presets || [
    { geography: 0.8, economics: 0.2 },
    { geography: 0.7, economics: 0.3 },
    { geography: 0.6, economics: 0.4 },
  ];
  const weightLabels = { 0.2: 'Низкое', 0.3: 'Среднее', 0.4: 'Повышенное' };
  $('cost-weight-options').innerHTML = weightPresets.map(preset => `
    <label><input type="radio" name="cost-weight" value="${preset.economics}" ${Number(form.costWeight) === Number(preset.economics) ? 'checked' : ''}>
      <span><b>${weightLabels[preset.economics] || ''}</b>${Math.round(preset.economics * 100)}%<small>${Math.round(preset.geography * 100)}/${Math.round(preset.economics * 100)}</small></span>
    </label>`).join('');
  const volumePresets = options.geo_volume_weights?.presets || [
    { geography: 0.8, volume: 0.2 },
    { geography: 0.7, volume: 0.3 },
    { geography: 0.6, volume: 0.4 },
  ];
  const volumeLabels = { 0.2: 'Низкое', 0.3: 'Среднее', 0.4: 'Повышенное' };
  $('volume-weight-options').innerHTML = volumePresets.map(preset => `
    <label><input type="radio" name="volume-weight" value="${preset.volume}" ${Number(form.volumeWeight) === Number(preset.volume) ? 'checked' : ''}>
      <span><b>${volumeLabels[preset.volume] || ''}</b>${Math.round(preset.volume * 100)}%<small>${Math.round(preset.geography * 100)}/${Math.round(preset.volume * 100)}</small></span>
    </label>`).join('');
  const bearOptions = options.bear_thresholds?.zone_options || [0.2, 0.25, 0.3, 0.35, 0.4, 0.5];
  $('bear-threshold-options').innerHTML = bearOptions.map(value => `
    <label><input type="radio" name="bear-threshold" value="${value}" ${Number(form.bearThreshold) === Number(value) ? 'checked' : ''}>
      <span>+${Math.round(value * 100)}</span>
    </label>`).join('');
  const bearVolumeOptions = options.bear_volume_thresholds?.zone_options || [0.2, 0.25, 0.3, 0.35, 0.4, 0.5];
  $('bear-volume-threshold-options').innerHTML = bearVolumeOptions.map(value => `
    <label><input type="radio" name="bear-volume-threshold" value="${value}" ${Number(form.bearVolumeThreshold) === Number(value) ? 'checked' : ''}>
      <span>+${Math.round(value * 100)}</span>
    </label>`).join('');
}

export function readChecks(id) {
  return [...document.querySelectorAll(`#${id} input:checked`)].map(input => input.value);
}

export function renderFormState(state) {
  const { form } = state;
  const bearModes = ['bear_zones', 'bear_volume_zones'];
  document.querySelectorAll('.mode-card').forEach(card => card.classList.toggle('selected', card.querySelector('input').value === form.mode));
  $('k-controls').classList.toggle('hidden', bearModes.includes(form.mode));
  $('bear-controls').classList.toggle('hidden', form.mode !== 'bear_zones');
  $('bear-volume-controls').classList.toggle('hidden', form.mode !== 'bear_volume_zones');
  $('cost-controls').classList.toggle('hidden', form.mode !== 'geo_cost');
  $('volume-controls').classList.toggle('hidden', form.mode !== 'geo_volume');
  $('manual-k-row').classList.toggle('hidden', form.kMode !== 'manual');
  $('candidate-layer-option').classList.toggle('hidden', !bearModes.includes(form.mode));
  const threshold = form.mode === 'bear_volume_zones' ? form.bearVolumeThreshold : form.bearThreshold;
  const weightedCaption = form.mode === 'geo_cost'
    ? ` · ${Math.round((1 - form.costWeight) * 100)}/${Math.round(form.costWeight * 100)}`
    : form.mode === 'geo_volume'
      ? ` · ${Math.round((1 - form.volumeWeight) * 100)}/${Math.round(form.volumeWeight * 100)}`
      : '';
  $('run-caption').textContent = bearModes.includes(form.mode)
    ? `${MODE_LABELS[form.mode]} · +${Math.round(threshold * 100)}%`
    : `${MODE_LABELS[form.mode]} · ${form.kMode === 'auto' ? 'Auto K' : `K=${form.k}`}${weightedCaption}`;
  const route = `${form.origin?.name || 'Точка не выбрана'} → ${form.destinationRegion || 'Регион не выбран'}`;
  $('filter-route').textContent = route;
  const labels = [
    ...form.periodTypes.map(value => PERIOD_LABELS[value] || value),
    ...form.priceTypes.map(value => PRICE_LABELS[value] || value),
    ...form.vehicleTypes, ...form.tonnageIds.map(value => `${value} т`),
  ];
  $('filter-summary').textContent = labels.length ? labels.join(' · ') : 'Фильтры не выбраны';
  $('preview-periods').textContent = form.periodTypes.map(value => PERIOD_LABELS[value] || value).join(', ') || '—';
  $('preview-prices').textContent = form.priceTypes.map(value => PRICE_LABELS[value] || value).join(', ') || '—';
  $('preview-vehicles').textContent = form.vehicleTypes.join(', ') || 'Все';
  $('preview-tonnages').textContent = form.tonnageIds.map(value => `${value} т`).join(', ') || 'Все';
  $('preview-mode').textContent = MODE_LABELS[form.mode] || form.mode;
  const weightPreview = form.mode === 'geo_cost'
    ? ` · Geo/Cost ${Math.round((1 - form.costWeight) * 100)}/${Math.round(form.costWeight * 100)}`
    : form.mode === 'geo_volume'
      ? ` · Geo/Volume ${Math.round((1 - form.volumeWeight) * 100)}/${Math.round(form.volumeWeight * 100)}`
      : '';
  $('preview-parameters').textContent = bearModes.includes(form.mode)
    ? `Порог +${Math.round(threshold * 100)}%`
    : `${form.kMode === 'auto' ? 'Auto K' : `K=${form.k}`}${weightPreview}`;
  const kinds = warningKinds(form);
  $('form-warnings').innerHTML = [
    kinds.includes('forecast') ? '<p>В анализ включены прогнозные данные Pulse.</p>' : '',
    kinds.includes('current_forecast') ? '<p>В одном анализе объединены текущие и прогнозные наблюдения.</p>' : '',
    kinds.includes('mixed_segment') ? '<p>Различия ₽/км могут быть связаны не только с территорией, но и со смешением тарифных сегментов.</p>' : '',
  ].join('');
  $('form-warnings').classList.toggle('hidden', !kinds.length);
}
