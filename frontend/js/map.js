/**
 * map.js — OpenLayers карта, маркеры, попапы
 */

const SHIP_COLOR    = '#3dd68c';
const DEL_COLOR     = '#f97316';
const PERIOD_COLORS = { retro: '#a78bfa', current: '#38bdf8', forecast: '#fbbf24' };
const PERIOD_NAMES  = { retro: 'Архив', current: 'Текущий', forecast: 'Прогноз' };

let _map = null;
let _vectorSource = null;
let _clusterSource = null;
let _vectorLayer = null;
let _overlay = null;
let _popupContainer = null;
let _popupContent = null;
let _popupCloser = null;
let _defaultLayer = null;
let _hybridLayer = null;

// ── Init ──────────────────────────────────────────────────────

/**
 * Инициализирует OpenLayers карту.
 * @param {string} containerId
 */
export function initMap(containerId) {
  _popupContainer = document.getElementById('popup');
  _popupContent = document.getElementById('popup-content');
  _popupCloser = document.getElementById('popup-closer');

  // Overlay для попапа
  _overlay = new ol.Overlay({
    element: _popupContainer,
    autoPan: {
      animation: { duration: 250 },
    },
    positioning: 'bottom-center',
    offset: [0, -20],
  });

  _popupCloser.onclick = function() {
    _overlay.setPosition(undefined);
    _popupCloser.blur();
    return false;
  };

  // Слои подложки
  _defaultLayer = new ol.layer.Tile({
    source: new ol.source.XYZ({
      url: 'https://tile2.maps.2gis.com/tiles?x={x}&y={y}&z={z}&v=1',
      attributions: '&copy; 2GIS'
    })
  });

  _hybridLayer = new ol.layer.Tile({
    source: new ol.source.XYZ({
      url: 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
      attributions: '&copy; Google'
    }),
    visible: false
  });

  // Векторный слой для маркеров
  _vectorSource = new ol.source.Vector();
  
  _clusterSource = new ol.source.Cluster({
    distance: 35, // Пикселей между маркерами для кластеризации
    source: _vectorSource,
  });

  _vectorLayer = new ol.layer.Vector({
    source: _clusterSource,
    style: clusterStyleFunction
  });

  // Инициализация карты
  _map = new ol.Map({
    target: containerId,
    layers: [_defaultLayer, _hybridLayer, _vectorLayer],
    overlays: [_overlay],
    view: new ol.View({
      center: ol.proj.fromLonLat([55.0, 58.0]),
      zoom: 4,
      maxZoom: 19,
    }),
    controls: ol.control.defaults.defaults({
      zoom: true,
      attribution: true
    })
  });

  // Логика переключателя слоев
  const layerSelect = document.getElementById('layer-select');
  if (layerSelect) {
    layerSelect.addEventListener('change', (e) => {
      const val = e.target.value;
      if (val === '2gis') {
        _defaultLayer.setVisible(true);
        _hybridLayer.setVisible(false);
        _map.getTargetElement().classList.remove('is-hybrid');
      } else {
        _defaultLayer.setVisible(false);
        _hybridLayer.setVisible(true);
        _map.getTargetElement().classList.add('is-hybrid');
      }
    });
  }

  // Обработка клика по маркеру
  _map.on('singleclick', function (evt) {
    const feature = _map.forEachFeatureAtPixel(evt.pixel, function (feat) {
      return feat;
    });

    if (feature) {
      const clusterFeatures = feature.get('features');
      
      // Если это кластер из нескольких точек — приближаем
      if (clusterFeatures && clusterFeatures.length > 1) {
        const extent = ol.extent.createEmpty();
        clusterFeatures.forEach((f) => ol.extent.extend(extent, f.getGeometry().getExtent()));
        
        _map.getView().fit(extent, {
          duration: 500,
          padding: [50, 50, 50, 50],
          maxZoom: _map.getView().getZoom() + 2
        });
        _overlay.setPosition(undefined); // Скрываем попап, если был открыт
      } 
      // Если это одиночная точка (или кластер из одной точки) — показываем попап
      else if (clusterFeatures && clusterFeatures.length === 1) {
        const ptFeature = clusterFeatures[0];
        const coordinates = feature.getGeometry().getCoordinates();
        const ptData = ptFeature.get('ptData');
        const kind = ptFeature.get('kind');
        
        // Ленивая генерация HTML попапа
        const popupHtml = _makePopupContent(ptData, kind);
        
        _popupContent.innerHTML = popupHtml;
        _popupContainer.classList.remove('hidden');
        _overlay.setPosition(coordinates);
        
        // Подключаем кнопку "Детализация" внутри попапа
        const btn = _popupContent.querySelector('.popup-btn-details');
        if (btn) {
          btn.addEventListener('click', () => {
            const event = new CustomEvent('show-records-modal', {
              detail: {
                town: ptData.town,
                region: ptData.region,
                type: kind === 'ship' ? 'shipment' : 'delivery'
              }
            });
            window.dispatchEvent(event);
          });
        }
        
        // Кнопка пересчета координат
        const btnRegeocode = _popupContent.querySelector('.popup-btn-regeocode');
        if (btnRegeocode) {
          btnRegeocode.addEventListener('click', () => {
            const event = new CustomEvent('regeocode-point', {
              detail: {
                town: ptData.town,
                region: ptData.region
              }
            });
            window.dispatchEvent(event);
            
            btnRegeocode.disabled = true;
            btnRegeocode.innerHTML = '⏳ Пересчет...';
            btnRegeocode.style.opacity = '0.7';
            btnRegeocode.style.cursor = 'wait';
          });
        }
      }
    } else {
      _overlay.setPosition(undefined);
    }
  });

  // Изменение курсора при наведении на маркер
  _map.on('pointermove', function (e) {
    if (e.dragging) return;
    const pixel = _map.getEventPixel(e.originalEvent);
    const hit = _map.hasFeatureAtPixel(pixel);
    _map.getTargetElement().style.cursor = hit ? 'pointer' : '';
  });

  return _map;
}

export function setThemeLayer(theme) {
  // CSS фильтры обрабатывают темную тему для .ol-layer
}

// ── Markers ───────────────────────────────────────────────────

export function renderPoints(shipPoints, delPoints) {
  clearMarkers();

  const features = [];

  for (const pt of shipPoints) {
    const feature = _createFeature(pt, 'ship');
    features.push(feature);
  }

  for (const pt of delPoints) {
    const feature = _createFeature(pt, 'del');
    features.push(feature);
  }

  _vectorSource.addFeatures(features);

  // Подогнать карту под маркеры
  if (features.length > 0) {
    const extent = _vectorSource.getExtent();
    if (!ol.extent.isEmpty(extent)) {
      _map.getView().fit(extent, {
        padding: [50, 50, 50, 50],
        maxZoom: 10,
        duration: 500
      });
    }
  }
}

export function clearMarkers() {
  if (_vectorSource) {
    _vectorSource.clear();
  }
  if (_overlay) {
    _overlay.setPosition(undefined);
  }
}

// ── Marker creation ───────────────────────────────────────────

const _styleCache = {};

function clusterStyleFunction(feature) {
  const features = feature.get('features');
  const size = features.length;

  if (size === 1) {
    // Стиль одиночной точки
    const ptFeature = features[0];
    const kind = ptFeature.get('kind');
    const ptData = ptFeature.get('ptData');
    const ptSize = _markerSize(ptData.count);
    
    const cacheKey = `${kind}_${ptSize}`;
    if (!_styleCache[cacheKey]) {
      const color = kind === 'ship' ? SHIP_COLOR : DEL_COLOR;
      const emoji = kind === 'ship' ? '📦' : '📍';
      _styleCache[cacheKey] = new ol.style.Style({
        image: new ol.style.Circle({
          radius: ptSize / 2,
          fill: new ol.style.Fill({ color: color }),
          stroke: new ol.style.Stroke({ color: 'rgba(255,255,255,0.4)', width: 2.5 }),
        }),
        text: new ol.style.Text({
          text: emoji,
          font: `${Math.round(ptSize * 0.42)}px sans-serif`,
          fill: new ol.style.Fill({ color: '#fff' }),
          offsetY: 1
        })
      });
    }
    return _styleCache[cacheKey];
  } else {
    // Стиль кластера
    const cacheKey = `cluster_${size}`;
    if (!_styleCache[cacheKey]) {
      const radius = 16 + Math.min(size.toString().length * 2, 10);
      _styleCache[cacheKey] = new ol.style.Style({
        image: new ol.style.Circle({
          radius: radius,
          fill: new ol.style.Fill({ color: 'rgba(56, 189, 248, 0.9)' }),
          stroke: new ol.style.Stroke({ color: 'rgba(255, 255, 255, 0.5)', width: 2 })
        }),
        text: new ol.style.Text({
          text: size.toString(),
          font: 'bold 12px sans-serif',
          fill: new ol.style.Fill({ color: '#fff' })
        })
      });
    }
    return _styleCache[cacheKey];
  }
}

function _createFeature(pt, kind) {
  const coords = ol.proj.fromLonLat([pt.lon, pt.lat]);
  // В фичу пишем только данные. Никаких стилей и HTML-строк.
  const feature = new ol.Feature({
    geometry: new ol.geom.Point(coords),
    ptData: pt,
    kind: kind
  });

  return feature;
}

function _markerSize(count) {
  if (count > 10000) return 38;
  if (count > 5000)  return 34;
  if (count > 1000)  return 30;
  if (count > 100)   return 26;
  return 22;
}

// ── Formatter helpers ──────────────────────────────────────────

function _fmt(val, fractionDigits = 0) {
  if (val == null) return '—';
  return Number(val).toLocaleString('ru-RU', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function _makePopupContent(pt, kind) {
  const typeName  = kind === 'ship' ? 'Отгрузка' : 'Доставка';
  const typeEmoji = kind === 'ship' ? '📦' : '📍';

  const priceFormatted  = pt.avg_price  ? _fmt(pt.avg_price, 0) + ' ₽'  : '—';
  const rubKmFormatted  = pt.rub_per_km ? _fmt(pt.rub_per_km, 1) + ' ₽/км' : '—';
  const lengthFormatted = pt.avg_length ? _fmt(pt.avg_length, 0) + ' км' : '—';
  const bidsFormatted   = pt.avg_bids   ? _fmt(pt.avg_bids, 0) + ' шт.' : '—';

  // Min/Max цены
  const minPrice = pt.min_price ? _fmt(pt.min_price, 0) : '—';
  const maxPrice = pt.max_price ? _fmt(pt.max_price, 0) : '—';
  const priceRange = (pt.min_price && pt.max_price && pt.min_price !== pt.max_price)
    ? `${minPrice} — ${maxPrice} ₽`
    : priceFormatted;

  // Min/Max расстояния
  const minLen = pt.min_length ? _fmt(pt.min_length, 0) : '—';
  const maxLen = pt.max_length ? _fmt(pt.max_length, 0) : '—';
  const lenRange = (pt.min_length && pt.max_length && pt.min_length !== pt.max_length)
    ? `${minLen} — ${maxLen} км`
    : lengthFormatted;

  // Секция разбивки по периодам
  let periodsHtml = '';
  if (pt.by_period && Object.keys(pt.by_period).length > 0) {
    const rows = Object.entries(pt.by_period).map(([ptype, pdata]) => {
      const pName  = PERIOD_NAMES[ptype] || ptype;
      const pColor = PERIOD_COLORS[ptype] || '#fff';
      const pPrice = pdata.avg_price ? _fmt(pdata.avg_price, 0) + ' ₽' : '—';
      const pRubKm = pdata.rub_per_km ? _fmt(pdata.rub_per_km, 1) + ' ₽/км' : '';
      return `
        <div class="period-detail">
          <div class="pd-name">
            <div class="period-dot ${ptype}" style="background-color:${pColor};box-shadow:0 0 4px ${pColor}"></div>
            <span style="color:${pColor}">${pName}</span>
            <span style="color:#4d5a73;font-size:11px">(${pdata.count} зап.)</span>
          </div>
          <div class="pd-vals">
            <span class="pd-val">${pPrice}</span>
            <span class="pd-sub">${pRubKm}</span>
          </div>
        </div>
      `;
    }).join('');

    periodsHtml = `
      <div class="popup-periods">
        <div class="popup-sec-title">В разрезе периодов:</div>
        ${rows}
      </div>
    `;
  }

  return `
    <div class="popup-container">
      <div class="popup-header">
        <span class="popup-type-icon">${typeEmoji}</span>
        <div>
          <div class="popup-title">${pt.town}</div>
          <div class="popup-subtitle">${pt.region || 'Регион не указан'} • ${typeName}</div>
        </div>
      </div>

      <div class="popup-body">
        <div class="popup-stat-grid">
          <div class="popup-stat-box">
            <div class="stat-lbl">Средняя ставка</div>
            <div class="stat-val highlight">${priceFormatted}</div>
            <div class="stat-sub">М/М: ${priceRange}</div>
          </div>
          <div class="popup-stat-box">
            <div class="stat-lbl">Цена за км</div>
            <div class="stat-val">${rubKmFormatted}</div>
          </div>
          <div class="popup-stat-box">
            <div class="stat-lbl">Расстояние</div>
            <div class="stat-val">${lengthFormatted}</div>
            <div class="stat-sub">М/М: ${lenRange}</div>
          </div>
          <div class="popup-stat-box">
            <div class="stat-lbl">Средне заявок</div>
            <div class="stat-val">${bidsFormatted}</div>
          </div>
        </div>

        ${periodsHtml}
      </div>

      <div class="popup-footer">
        <button class="popup-btn-regeocode" style="margin-bottom: 6px; background: rgba(255,255,255,0.1); border: 1px solid var(--border);">
          🔄 Пересчитать координаты
        </button>
        <button class="popup-btn-details">
          📄 Детализация записей (${pt.count} шт.)
        </button>
      </div>
    </div>
  `;
}
