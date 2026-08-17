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
let _mlVectorSource = null;
let _mlVectorLayer = null;
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
    style: clusterStyleFunction,
    zIndex: 2
  });

  // Векторный слой для ML-кластеров
  _mlVectorSource = new ol.source.Vector();
  _mlVectorLayer = new ol.layer.Vector({
    source: _mlVectorSource,
    style: mlClusterStyleFunction,
    zIndex: 1
  });

  // Инициализация карты
  _map = new ol.Map({
    target: containerId,
    layers: [_defaultLayer, _hybridLayer, _vectorLayer, _mlVectorLayer],
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
      
      // Если это кластер из нескольких точек
      if (clusterFeatures && clusterFeatures.length > 1) {
        const extent = ol.extent.createEmpty();
        clusterFeatures.forEach((f) => ol.extent.extend(extent, f.getGeometry().getExtent()));
        
        const currentZoom = _map.getView().getZoom();
        const maxZoom = _map.getView().getMaxZoom();
        // Проверяем, находятся ли точки в абсолютно одинаковых координатах (размер экстента = 0)
        const isPointExtent = ol.extent.getWidth(extent) === 0 && ol.extent.getHeight(extent) === 0;
        
        if (isPointExtent || currentZoom >= maxZoom - 1) {
          // Точки невозможно разделить зумом -> показываем список
          const popupHtml = _makeClusterPopupContent(clusterFeatures);
          _popupContent.innerHTML = popupHtml;
          _popupContainer.classList.remove('hidden');
          _overlay.setPosition(feature.getGeometry().getCoordinates());
          
          // Биндим кнопки списка
          const clusterBtns = _popupContent.querySelectorAll('.popup-btn-details-small');
          clusterBtns.forEach(b => {
            b.addEventListener('click', () => {
              const event = new CustomEvent('show-records-modal', {
                detail: {
                  town: b.dataset.town,
                  region: b.dataset.region,
                  type: b.dataset.type
                }
              });
              window.dispatchEvent(event);
            });
          });

          const regeocodeBtns = _popupContent.querySelectorAll('.popup-btn-regeocode-small');
          regeocodeBtns.forEach(b => {
            b.addEventListener('click', (e) => {
              e.stopPropagation();
              b.disabled = true;
              b.style.opacity = '0.5';
              b.style.cursor = 'wait';
              const event = new CustomEvent('regeocode-point', {
                detail: {
                  town: b.dataset.town,
                  region: b.dataset.region
                }
              });
              window.dispatchEvent(event);
            });
          });
        } else {
          // Обычный зум в кластер
          _map.getView().fit(extent, {
            duration: 500,
            padding: [50, 50, 50, 50],
            maxZoom: currentZoom + 2
          });
          _overlay.setPosition(undefined); // Скрываем попап, если был открыт
        }
      } 
      // Если это одиночная точка (или кластер из одной точки) — показываем обычный попап
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
  if (_mlVectorSource) {
    _mlVectorSource.clear();
  }
  if (_overlay) {
    _overlay.setPosition(undefined);
  }
}

// ── ML Clusters ───────────────────────────────────────────────

export function renderMlClusters(clustersData) {
  clearMarkers();

  const features = [];
  const colors = [
    'rgba(239, 68, 68, 0.4)', // red
    'rgba(59, 130, 246, 0.4)', // blue
    'rgba(16, 185, 129, 0.4)', // green
    'rgba(245, 158, 11, 0.4)', // yellow
    'rgba(139, 92, 246, 0.4)', // purple
    'rgba(236, 72, 153, 0.4)', // pink
    'rgba(20, 184, 166, 0.4)', // teal
    'rgba(249, 115, 22, 0.4)', // orange
    'rgba(99, 102, 241, 0.4)', // indigo
    'rgba(132, 204, 22, 0.4)'  // lime
  ];
  const strokeColors = [
    'rgba(239, 68, 68, 0.9)', 'rgba(59, 130, 246, 0.9)', 'rgba(16, 185, 129, 0.9)',
    'rgba(245, 158, 11, 0.9)', 'rgba(139, 92, 246, 0.9)', 'rgba(236, 72, 153, 0.9)',
    'rgba(20, 184, 166, 0.9)', 'rgba(249, 115, 22, 0.9)', 'rgba(99, 102, 241, 0.9)',
    'rgba(132, 204, 22, 0.9)'
  ];

  clustersData.forEach((c, idx) => {
    const color = colors[idx % colors.length];
    const strokeColor = strokeColors[idx % strokeColors.length];

    // Полигон
    if (c.polygon && c.polygon.length >= 3) {
      const polygonCoords = c.polygon.map(p => ol.proj.fromLonLat([p[1], p[0]]));
      polygonCoords.push(polygonCoords[0]); // Замыкаем
      
      const polyFeature = new ol.Feature({
        geometry: new ol.geom.Polygon([polygonCoords]),
        isMlPolygon: true,
        fillColor: color,
        strokeColor: strokeColor
      });
      features.push(polyFeature);
    }

    // Точки внутри кластера
    if (c.points) {
      c.points.forEach(pt => {
        const coords = ol.proj.fromLonLat([pt.lon, pt.lat]);
        const ptFeature = new ol.Feature({
          geometry: new ol.geom.Point(coords),
          isMlPoint: true,
          fillColor: strokeColor
        });
        features.push(ptFeature);
      });
    }

    // Центроид (текстовая метка)
    if (c.center) {
      const centerCoords = ol.proj.fromLonLat([c.center[1], c.center[0]]);
      const textFeature = new ol.Feature({
        geometry: new ol.geom.Point(centerCoords),
        isMlLabel: true,
        avgRubKm: c.avg_rub_km,
        bids: c.total_bids,
        fillColor: strokeColor
      });
      features.push(textFeature);
    }
  });

  _mlVectorSource.addFeatures(features);

  if (features.length > 0) {
    const extent = _mlVectorSource.getExtent();
    if (!ol.extent.isEmpty(extent)) {
      _map.getView().fit(extent, {
        padding: [50, 50, 50, 50],
        maxZoom: 10,
        duration: 500
      });
    }
  }
}

function mlClusterStyleFunction(feature) {
  if (feature.get('isMlPolygon')) {
    return new ol.style.Style({
      fill: new ol.style.Fill({ color: feature.get('fillColor') }),
      stroke: new ol.style.Stroke({ color: feature.get('strokeColor'), width: 2 })
    });
  }
  
  if (feature.get('isMlPoint')) {
    return new ol.style.Style({
      image: new ol.style.Circle({
        radius: 4,
        fill: new ol.style.Fill({ color: feature.get('fillColor') }),
        stroke: new ol.style.Stroke({ color: '#fff', width: 1 })
      })
    });
  }

  if (feature.get('isMlLabel')) {
    const avg = feature.get('avgRubKm');
    const bids = feature.get('bids');
    return new ol.style.Style({
      text: new ol.style.Text({
        text: `${avg} ₽/км\n(${bids} заяв.)`,
        font: 'bold 13px sans-serif',
        fill: new ol.style.Fill({ color: '#fff' }),
        backgroundFill: new ol.style.Fill({ color: feature.get('fillColor') }),
        padding: [4, 6, 4, 6],
        offsetY: -15
      })
    });
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

function _makeClusterPopupContent(features) {
  let listHtml = features.map(f => {
    const pt = f.get('ptData');
    const kind = f.get('kind');
    const typeEmoji = kind === 'ship' ? '📦' : '📍';
    const priceFormatted = pt.avg_price ? _fmt(pt.avg_price, 0) + ' ₽' : '—';
    return `
      <div class="cluster-popup-item" style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center; gap: 8px;">
        <div style="flex:1; min-width: 0;">
          <div style="font-weight: 600; font-size: 13px; color: var(--text-main); margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${typeEmoji} ${pt.town}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${priceFormatted} • ${pt.count} заяв.</div>
        </div>
        <div style="display: flex; gap: 4px;">
          <button class="popup-btn-regeocode-small" data-town="${pt.town}" data-region="${pt.region}" title="Пересчитать координаты" style="background: rgba(255,255,255,0.1); color: var(--text-main); border: 1px solid var(--border); padding: 6px; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s;">
            🔄
          </button>
          <button class="popup-btn-details-small" data-town="${pt.town}" data-region="${pt.region}" data-type="${kind === 'ship' ? 'shipment' : 'delivery'}" style="background: var(--accent); color: #fff; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 500; transition: background 0.2s;">
            Детали
          </button>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="popup-container" style="width: 300px; padding: 0;">
      <div class="popup-header" style="padding: 16px;">
        <span class="popup-type-icon">🧩</span>
        <div>
          <div class="popup-title">Объединенные точки</div>
          <div class="popup-subtitle">В этих координатах найдено ${features.length} городов</div>
        </div>
      </div>
      <div class="popup-body" style="max-height: 250px; overflow-y: auto; padding: 0; background: var(--bg-main);">
        ${listHtml}
      </div>
    </div>
  `;
}
