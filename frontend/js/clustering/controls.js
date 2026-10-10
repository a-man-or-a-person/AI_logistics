import { MODES, modeParameter, modeResultKind, warningKinds } from './state.js';
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
  $('mode-cards').innerHTML = state.modeCapabilities.map(({ id: value }) => {
    const item = MODES[value];
    if (!item) return '';
    return `
    <label class="mode-card mode-${value} ${form.mode === value ? 'selected' : ''}">
      <input type="radio" name="analysis-mode" value="${value}" ${form.mode === value ? 'checked' : ''}>
      <span class="mode-card-heading"><strong>${item.label}</strong><small>${item.badge}</small></span>
      <span>${item.description}</span>
    </label>`;
  }).join('');
  const clusterCount = modeParameter(state.modeCapabilities, form.mode, 'n_clusters')
    || modeParameter(state.modeCapabilities, 'geography', 'n_clusters');
  $('manual-k').min = clusterCount?.min;
  $('manual-k').max = clusterCount?.max;
  $('manual-k').value = form.k;
  const weightPresets = (state.modeCapabilities.find(item => item.id === 'geo_cost')?.presets || []).map(preset => ({
    geography: preset.geography_weight,
    economics: preset.economics_weight,
  }));
  const weightLabels = { 0.2: 'Низкое', 0.3: 'Среднее', 0.4: 'Повышенное' };
  $('cost-weight-options').innerHTML = weightPresets.map(preset => `
    <label><input type="radio" name="cost-weight" value="${preset.economics}" ${Number(form.costWeight) === Number(preset.economics) ? 'checked' : ''}>
      <span><b>${weightLabels[preset.economics] || ''}</b>${Math.round(preset.economics * 100)}%<small>${Math.round(preset.geography * 100)}/${Math.round(preset.economics * 100)}</small></span>
    </label>`).join('');
  const volumePresets = (state.modeCapabilities.find(item => item.id === 'geo_volume')?.presets || []).map(preset => ({
    geography: preset.geography_weight,
    volume: preset.volume_weight,
  }));
  const volumeLabels = { 0.2: 'Низкое', 0.3: 'Среднее', 0.4: 'Повышенное' };
  $('volume-weight-options').innerHTML = volumePresets.map(preset => `
    <label><input type="radio" name="volume-weight" value="${preset.volume}" ${Number(form.volumeWeight) === Number(preset.volume) ? 'checked' : ''}>
      <span><b>${volumeLabels[preset.volume] || ''}</b>${Math.round(preset.volume * 100)}%<small>${Math.round(preset.geography * 100)}/${Math.round(preset.volume * 100)}</small></span>
    </label>`).join('');
  const bearOptions = modeParameter(state.modeCapabilities, 'bear_zones', 'bear_threshold')?.choices || [];
  const bearSingleton = modeParameter(state.modeCapabilities, 'bear_zones', 'singleton_threshold');
  $('bear-singleton-threshold').textContent = bearSingleton?.fixed
    ? Math.round(bearSingleton.default * 100)
    : '';
  $('bear-threshold-options').innerHTML = bearOptions.map(value => `
    <label><input type="radio" name="bear-threshold" value="${value}" ${Number(form.bearThreshold) === Number(value) ? 'checked' : ''}>
      <span>+${Math.round(value * 100)}</span>
    </label>`).join('');
  const bearVolumeOptions = modeParameter(state.modeCapabilities, 'bear_volume_zones', 'volume_threshold')?.choices || [];
  const bearVolumeSingleton = modeParameter(state.modeCapabilities, 'bear_volume_zones', 'singleton_threshold');
  $('bear-volume-singleton-threshold').textContent = bearVolumeSingleton?.fixed
    ? Math.round(bearVolumeSingleton.default * 100)
    : '';
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
  for (const [name, value] of [
    ['analysis-mode', form.mode], ['k-mode', form.kMode],
    ['cost-weight', form.costWeight], ['volume-weight', form.volumeWeight],
    ['bear-threshold', form.bearThreshold], ['bear-volume-threshold', form.bearVolumeThreshold],
  ]) {
    document.querySelectorAll(`input[name="${name}"]`).forEach(input => { input.checked = input.value === String(value); });
  }
  $('manual-k').value = form.k;
  const isZoneMode = modeResultKind(state.modeCapabilities, form.mode) === 'zones';
  document.querySelectorAll('.mode-card').forEach(card => card.classList.toggle('selected', card.querySelector('input').value === form.mode));
  $('k-controls').classList.toggle('hidden', isZoneMode);
  $('bear-controls').classList.toggle('hidden', form.mode !== 'bear_zones');
  $('bear-volume-controls').classList.toggle('hidden', form.mode !== 'bear_volume_zones');
  $('cost-controls').classList.toggle('hidden', form.mode !== 'geo_cost');
  $('volume-controls').classList.toggle('hidden', form.mode !== 'geo_volume');
  $('manual-k-row').classList.toggle('hidden', form.kMode !== 'manual');
  $('candidate-layer-option').classList.toggle('hidden', !isZoneMode);
  const threshold = form.mode === 'bear_volume_zones' ? form.bearVolumeThreshold : form.bearThreshold;
  const weightedCaption = form.mode === 'geo_cost'
    ? ` · ${Math.round((1 - form.costWeight) * 100)}/${Math.round(form.costWeight * 100)}`
    : form.mode === 'geo_volume'
      ? ` · ${Math.round((1 - form.volumeWeight) * 100)}/${Math.round(form.volumeWeight * 100)}`
      : '';
  $('run-caption').textContent = isZoneMode
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
  $('preview-parameters').textContent = isZoneMode
    ? `Порог +${Math.round(threshold * 100)}%`
    : `${form.kMode === 'auto' ? 'Auto K' : `K=${form.k}`}${weightPreview}`;
  const kinds = warningKinds(form, state.modeCapabilities);
  $('form-warnings').innerHTML = [
    kinds.includes('forecast') ? '<p>В анализ включены прогнозные данные Pulse.</p>' : '',
    kinds.includes('current_forecast') ? '<p>В одном анализе объединены текущие и прогнозные наблюдения.</p>' : '',
    kinds.includes('mixed_segment') ? '<p>Различия ₽/км могут быть связаны не только с территорией, но и со смешением тарифных сегментов.</p>' : '',
  ].join('');
  $('form-warnings').classList.toggle('hidden', !kinds.length);
}
