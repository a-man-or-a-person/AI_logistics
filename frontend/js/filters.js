/** Independent legacy Data Map filters. Product clustering never imports this state. */

const PERIOD_LABELS = { retro: 'Архив', current: 'Текущий', forecast: 'Прогноз' };
const PRICE_LABELS = { spot: 'Спот', tender: 'Тендер' };
const $ = id => document.getElementById(id);
const state = {
  fromRegions: new Set(),
  toRegions: new Set(),
  periodTypes: new Set(['retro', 'current', 'forecast']),
  priceTypes: new Set(['spot', 'tender']),
};
let shipRegions = [];
let deliveryRegions = [];
let onChange = () => {};

export function initFilters(ship, delivery, callback = () => {}) {
  shipRegions = ship;
  deliveryRegions = delivery;
  onChange = callback;
  renderToggles('period-toggles', PERIOD_LABELS, state.periodTypes, 'period');
  renderToggles('price-toggles', PRICE_LABELS, state.priceTypes, 'ptype');
  renderRegions('ship', shipRegions);
  renderRegions('del', deliveryRegions);
  wireSearch('ship');
  wireSearch('del');
  document.querySelectorAll('.section-header').forEach(header => header.addEventListener('click', () => {
    const section = header.closest('.legacy-section');
    if (!section) return;
    section.classList.toggle('collapsed');
    header.setAttribute('aria-expanded', String(!section.classList.contains('collapsed')));
  }));
}

function renderToggles(id, labels, selected, dataName) {
  const container = $(id);
  container.innerHTML = '';
  Object.entries(labels).forEach(([value, label]) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `toggle-btn ${selected.has(value) ? 'active' : ''}`;
    button.dataset[dataName] = value;
    button.textContent = label;
    button.addEventListener('click', () => {
      if (selected.has(value)) selected.delete(value);
      else selected.add(value);
      button.classList.toggle('active', selected.has(value));
      onChange(getFilters());
    });
    container.appendChild(button);
  });
}

function renderRegions(kind, regions) {
  const container = $(`region-list-${kind}`);
  container.innerHTML = '';
  regions.forEach(region => container.appendChild(regionButton(kind, region)));
  renderTags(kind);
}

function regionButton(kind, region) {
  const selected = kind === 'ship' ? state.fromRegions : state.toRegions;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `region-chip ${selected.has(region) ? 'selected' : ''}`;
  button.dataset.region = region;
  button.innerHTML = `<span class="chip-check">${selected.has(region) ? '✓' : ''}</span><span></span>`;
  button.lastElementChild.textContent = region;
  button.addEventListener('click', () => {
    if (selected.has(region)) selected.delete(region);
    else selected.add(region);
    button.classList.toggle('selected', selected.has(region));
    button.querySelector('.chip-check').textContent = selected.has(region) ? '✓' : '';
    renderTags(kind);
    onChange(getFilters());
  });
  return button;
}

function wireSearch(kind) {
  $(`search-${kind}`).addEventListener('input', event => {
    const query = event.target.value.trim().toLocaleLowerCase('ru');
    const source = kind === 'ship' ? shipRegions : deliveryRegions;
    renderRegions(kind, source.filter(region => region.toLocaleLowerCase('ru').includes(query)));
  });
}

function renderTags(kind) {
  const container = $(`tags-${kind}`);
  const selected = kind === 'ship' ? state.fromRegions : state.toRegions;
  container.innerHTML = '';
  selected.forEach(region => {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.textContent = region;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.setAttribute('aria-label', `Убрать ${region}`);
    remove.textContent = '×';
    remove.addEventListener('click', () => {
      selected.delete(region);
      renderRegions(kind, kind === 'ship' ? shipRegions : deliveryRegions);
      onChange(getFilters());
    });
    tag.appendChild(remove);
    container.appendChild(tag);
  });
}

export function getFilters() {
  return {
    fromRegions: [...state.fromRegions],
    toRegions: [...state.toRegions],
    periodTypes: [...state.periodTypes],
    priceTypes: [...state.priceTypes],
  };
}

export function resetFilters() {
  state.fromRegions.clear();
  state.toRegions.clear();
  state.periodTypes = new Set(Object.keys(PERIOD_LABELS));
  state.priceTypes = new Set(Object.keys(PRICE_LABELS));
  renderToggles('period-toggles', PERIOD_LABELS, state.periodTypes, 'period');
  renderToggles('price-toggles', PRICE_LABELS, state.priceTypes, 'ptype');
  renderRegions('ship', shipRegions);
  renderRegions('del', deliveryRegions);
  onChange(getFilters());
}
