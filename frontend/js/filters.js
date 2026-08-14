/**
 * filters.js — панель фильтров: регионы, типы периода, типы цены
 */

const PERIOD_LABELS = {
  retro:    'Архив',
  current:  'Текущий',
  forecast: 'Прогноз',
};

const PTYPE_LABELS = {
  spot:   'Спот',
  tender: 'Тендер',
};

/** Состояние фильтров */
const state = {
  fromRegions: new Set(),
  toRegions:   new Set(),
  periodTypes: new Set(['retro', 'current', 'forecast']),
  priceTypes:  new Set(['spot', 'tender']),
};

let _allShipRegions = [];
let _allDelRegions  = [];
let _onChangeCallback = null;

// ── DOM References ────────────────────────────────────────────

const $ = id => document.getElementById(id);

// ── Init ──────────────────────────────────────────────────────

/**
 * Инициализирует панель фильтров.
 * @param {string[]} shipRegions
 * @param {string[]} delRegions
 * @param {Function} onFilterChange — колбэк при изменении фильтров
 */
export function initFilters(shipRegions, delRegions, onFilterChange) {
  _allShipRegions = shipRegions;
  _allDelRegions  = delRegions;
  _onChangeCallback = onFilterChange;

  _buildPeriodToggles();
  _buildPriceToggles();
  _buildRegionList('ship', shipRegions);
  _buildRegionList('del', delRegions);
  _wireSearch('ship');
  _wireSearch('del');
  _wireCollapseSections();
}

// ── Period Toggles ────────────────────────────────────────────

function _buildPeriodToggles() {
  const container = $('period-toggles');
  if (!container) return;
  container.innerHTML = '';

  for (const [key, label] of Object.entries(PERIOD_LABELS)) {
    const btn = document.createElement('button');
    btn.className = 'toggle-btn active';
    btn.dataset.period = key;
    btn.id = `toggle-period-${key}`;
    btn.innerHTML = `<span class="btn-dot" data-period="${key}"></span>${label}`;
    btn.addEventListener('click', () => {
      if (state.periodTypes.has(key)) {
        state.periodTypes.delete(key);
        btn.classList.remove('active');
      } else {
        state.periodTypes.add(key);
        btn.classList.add('active');
      }
    });
    container.appendChild(btn);
  }
}

// ── Price Toggles ─────────────────────────────────────────────

function _buildPriceToggles() {
  const container = $('price-toggles');
  if (!container) return;
  container.innerHTML = '';

  for (const [key, label] of Object.entries(PTYPE_LABELS)) {
    const btn = document.createElement('button');
    btn.className = 'toggle-btn active';
    btn.dataset.ptype = key;
    btn.id = `toggle-ptype-${key}`;
    btn.innerHTML = `${label}`;
    btn.addEventListener('click', () => {
      if (state.priceTypes.has(key)) {
        state.priceTypes.delete(key);
        btn.classList.remove('active');
      } else {
        state.priceTypes.add(key);
        btn.classList.add('active');
      }
    });
    container.appendChild(btn);
  }
}

// ── Region Lists ──────────────────────────────────────────────

function _buildRegionList(kind, regions) {
  const listEl = $(`region-list-${kind}`);
  if (!listEl) return;
  listEl.innerHTML = '';

  for (const region of regions) {
    listEl.appendChild(_makeChip(kind, region));
  }
  _refreshTags(kind);
}

function _makeChip(kind, region) {
  const chip = document.createElement('div');
  chip.className = 'region-chip';
  chip.dataset.region = region;
  chip.dataset.kind = kind;

  const set = kind === 'ship' ? state.fromRegions : state.toRegions;
  const activeClass = kind === 'ship' ? 'selected' : 'selected-del';

  if (set.has(region)) chip.classList.add(activeClass);

  chip.innerHTML = `
    <div class="chip-check">${set.has(region) ? '✓' : ''}</div>
    <span>${region}</span>
  `;

  chip.addEventListener('click', () => {
    if (set.has(region)) {
      set.delete(region);
      chip.classList.remove(activeClass);
      chip.querySelector('.chip-check').textContent = '';
    } else {
      set.add(region);
      chip.classList.add(activeClass);
      chip.querySelector('.chip-check').textContent = '✓';
    }
    _refreshTags(kind);
  });

  return chip;
}

function _wireSearch(kind) {
  const searchInput = $(`search-${kind}`);
  const listEl = $(`region-list-${kind}`);
  if (!searchInput || !listEl) return;

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.toLowerCase().trim();
    const regions = kind === 'ship' ? _allShipRegions : _allDelRegions;
    const filtered = q ? regions.filter(r => r.toLowerCase().includes(q)) : regions;
    listEl.innerHTML = '';
    for (const region of filtered) {
      listEl.appendChild(_makeChip(kind, region));
    }
  });
}

function _refreshTags(kind) {
  const tagsEl = $(`tags-${kind}`);
  if (!tagsEl) return;
  const set = kind === 'ship' ? state.fromRegions : state.toRegions;
  tagsEl.innerHTML = '';

  for (const region of set) {
    const tag = document.createElement('div');
    tag.className = `tag tag-${kind}`;
    tag.innerHTML = `<span>${_shortRegionName(region)}</span><span class="tag-remove">×</span>`;
    tag.querySelector('.tag-remove').addEventListener('click', () => {
      set.delete(region);
      _refreshTags(kind);
      // Обновить чипы
      const chip = document.querySelector(`#region-list-${kind} [data-region="${CSS.escape(region)}"]`);
      if (chip) {
        const activeClass = kind === 'ship' ? 'selected' : 'selected-del';
        chip.classList.remove(activeClass);
        chip.querySelector('.chip-check').textContent = '';
      }
    });
    tagsEl.appendChild(tag);
  }
}

function _shortRegionName(name) {
  return name
    .replace('область', 'обл.')
    .replace('Республика ', 'Респ. ')
    .replace('Краснодарский край', 'Краснодарский кр.')
    .replace('Пермский край', 'Пермский кр.')
    .replace('Приморский край', 'Приморский кр.')
    .replace('Хабаровский край', 'Хабаровский кр.')
    .replace('Красноярский край', 'Красноярский кр.')
    .replace('Ставропольский край', 'Ставропольский кр.');
}

// ── Collapse Sections ─────────────────────────────────────────

function _wireCollapseSections() {
  document.querySelectorAll('.section-header').forEach(header => {
    header.addEventListener('click', () => {
      const section = header.closest('.panel-section');
      section.classList.toggle('collapsed');
    });
  });
}

// ── Public API ────────────────────────────────────────────────

/** Возвращает текущее состояние фильтров */
export function getFilters() {
  return {
    fromRegions: [...state.fromRegions],
    toRegions:   [...state.toRegions],
    periodTypes: [...state.periodTypes],
    priceTypes:  [...state.priceTypes],
  };
}

/** Сбрасывает все фильтры */
export function resetFilters() {
  state.fromRegions.clear();
  state.toRegions.clear();
  state.periodTypes = new Set(['retro', 'current', 'forecast']);
  state.priceTypes  = new Set(['spot', 'tender']);

  // Сбросить чипы
  document.querySelectorAll('.region-chip').forEach(chip => {
    const kind = chip.dataset.kind;
    const activeClass = kind === 'ship' ? 'selected' : 'selected-del';
    chip.classList.remove(activeClass);
    const check = chip.querySelector('.chip-check');
    if (check) check.textContent = '';
  });

  // Сбросить теги
  ['ship', 'del'].forEach(kind => _refreshTags(kind));

  // Сбросить period toggles
  document.querySelectorAll('.toggle-btn[data-period]').forEach(btn => {
    const key = btn.dataset.period;
    state.periodTypes.add(key);
    btn.classList.add('active');
  });

  // Сбросить price toggles
  document.querySelectorAll('.toggle-btn[data-ptype]').forEach(btn => {
    const key = btn.dataset.ptype;
    state.priceTypes.add(key);
    btn.classList.add('active');
  });

  // Очистить поиск
  ['ship', 'del'].forEach(kind => {
    const searchInput = $(`search-${kind}`);
    if (searchInput) searchInput.value = '';
    const regions = kind === 'ship' ? _allShipRegions : _allDelRegions;
    _buildRegionList(kind, regions);
  });
}
