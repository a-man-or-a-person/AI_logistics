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
let _selectedMlZoneId = null;
let _hoveredMlZoneId = null;
let _mlResultIsStale = false;
const _mlLayerVisibility = { zones: true, cities: true, labels: true, centers: false };
const _clusteringLayerVisibility = { points: true, labels: true, centers: false, outliers: true, candidates: true };

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
      if (feature.get('isProductPoint') || feature.get('isProductCenter') || feature.get('isProductLabel')) {
        const clusterId = feature.get('clusterId');
        if (clusterId != null) selectMlZone(Number(clusterId), false);
        window.dispatchEvent(new CustomEvent('clustering-point-select', {
          detail: { clusterId: clusterId == null ? null : Number(clusterId), pointId: feature.get('pointId') || null },
        }));
        if (feature.get('isProductPoint')) {
          _popupContent.innerHTML = _productPointPopup(
            feature.get('pointData'),
            feature.get('analysisMode'),
          );
          _popupContainer.classList.remove('hidden');
          _overlay.setPosition(evt.coordinate);
        } else {
          _overlay.setPosition(undefined);
        }
        return;
      }
      if (feature.get('isMlPolygon') || feature.get('isMlLabel') || feature.get('isMlCenter')) {
        const clusterId = Number(feature.get('clusterId'));
        selectMlZone(clusterId, false);
        window.dispatchEvent(new CustomEvent('ml-zone-select', { detail: { clusterId } }));
        _overlay.setPosition(undefined);
        return;
      }

      // ML-точки не являются обычными OpenLayers-кластерами.
      if (feature.get('isMlPoint')) {
        const town    = feature.get('ptTown');
        const rubKm   = feature.get('ptRubKm');
        const bids    = feature.get('ptBids');
        const hasData = feature.get('ptHasData');
        const color   = feature.get('strokeColor');
        const coords  = feature.getGeometry().getCoordinates();

        const priceHtml = hasData
          ? `<div style="font-size:13px;color:${color};font-weight:700;margin-top:4px">${Number(rubKm).toFixed(1)} ₽/км</div>
             <div style="font-size:11px;color:var(--text-muted);margin-top:2px">${Number(bids).toLocaleString('ru-RU')} заявок</div>`
          : `<div style="font-size:11px;color:var(--text-muted);margin-top:4px">Цены по текущему фильтру недоступны</div>`;

        _popupContent.innerHTML = `
          <div class="popup-container" style="min-width:160px;padding:12px 14px">
            <div style="display:flex;align-items:center;gap:8px">
              <span style="width:10px;height:10px;border-radius:50%;background:${color};flex-shrink:0;display:inline-block"></span>
              <div style="font-weight:700;font-size:13px;color:var(--text-main)">${_escapeHtml(town)}</div>
            </div>
            ${priceHtml}
          </div>`;
        _popupContainer.classList.remove('hidden');
        _overlay.setPosition(coords);
        return;
      }

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

          const regeocodeAllBtn = _popupContent.querySelector('.popup-btn-regeocode-all');
          if (regeocodeAllBtn) {
            regeocodeAllBtn.addEventListener('click', (e) => {
              e.stopPropagation();
              regeocodeAllBtn.disabled = true;
              regeocodeAllBtn.style.opacity = '0.5';
              regeocodeAllBtn.style.cursor = 'wait';
              
              const points = clusterFeatures.map(f => {
                const pt = f.get('ptData');
                return { town: pt.town, region: pt.region };
              });
              
              // Optionally disable all individual buttons too
              regeocodeBtns.forEach(b => {
                b.disabled = true;
                b.style.opacity = '0.5';
              });
              
              const event = new CustomEvent('regeocode-all-points', {
                detail: { points }
              });
              window.dispatchEvent(event);
            });
          }
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
      } else {
        _overlay.setPosition(undefined);
      }
    } else {
      _overlay.setPosition(undefined);
    }
  });

  // Изменение курсора и синхронизация hover зоны с инспектором.
  _map.on('pointermove', function (e) {
    if (e.dragging) return;
    const pixel = _map.getEventPixel(e.originalEvent);
    const feature = _map.forEachFeatureAtPixel(pixel, candidate => candidate);
    const hit = Boolean(feature);
    const zoneFeature = feature && (
      feature.get('isMlPolygon') || feature.get('isMlLabel') || feature.get('isMlCenter') ||
      feature.get('isProductPoint') || feature.get('isProductLabel') || feature.get('isProductCenter')
    );
    const nextHover = zoneFeature ? Number(feature.get('clusterId')) : null;
    if (_hoveredMlZoneId !== nextHover) {
      _hoveredMlZoneId = nextHover;
      _mlVectorLayer?.changed();
      window.dispatchEvent(new CustomEvent('ml-zone-hover', { detail: { clusterId: nextHover } }));
    }
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
  if (_vectorSource)   _vectorSource.clear();
  if (_mlVectorSource) _mlVectorSource.clear();
  if (_overlay)        _overlay.setPosition(undefined);
}

/** Сбрасывает только ML-слой, оставляя обычные маркеры нетронутыми. */
export function clearMlClusters() {
  if (_mlVectorSource) _mlVectorSource.clear();
  if (_overlay)        _overlay.setPosition(undefined);
  _selectedMlZoneId = null;
  _hoveredMlZoneId = null;
}

// ── ML Clusters ───────────────────────────────────────────────

// Цвет дополняет устойчивый идентификатор Z1/Z2/... и не несёт смысл сам по себе.
const ML_PALETTE = [
  { fill: 'rgba(216,79,79,.18)',  stroke: '#d84f4f' },
  { fill: 'rgba(52,120,197,.18)', stroke: '#3478c5' },
  { fill: 'rgba(25,138,104,.18)', stroke: '#198a68' },
  { fill: 'rgba(210,138,24,.18)', stroke: '#d28a18' },
  { fill: 'rgba(122,90,200,.18)', stroke: '#7a5ac8' },
  { fill: 'rgba(197,74,136,.18)', stroke: '#c54a88' },
  { fill: 'rgba(29,150,144,.18)', stroke: '#1d9690' },
  { fill: 'rgba(213,102,42,.18)', stroke: '#d5662a' },
  { fill: 'rgba(90,97,197,.18)',  stroke: '#5a61c5' },
  { fill: 'rgba(117,166,44,.18)', stroke: '#75a62c' },
];

/** Render Product v1 analysis as points, representatives and outliers only. */
export function renderClusteringPoints(result) {
  clearMarkers();
  const features = [];
  const clusters = new Map((result.clusters || []).map((cluster, index) => {
    let color = ML_PALETTE[index % ML_PALETTE.length].stroke;
    if (result.analysis?.mode === 'bear_zones') {
      color = cluster.cluster_type === 'expensive_singleton' ? '#7c2f68' : '#b64040';
    }
    if (result.analysis?.mode === 'bear_volume_zones') {
      color = cluster.cluster_type === 'high_volume_singleton' ? '#5b4ca0' : '#176f8f';
    }
    return [Number(cluster.cluster_id), { ...cluster, color }];
  }));
  for (const point of result.points || []) {
    if (point.lat == null || point.lon == null) continue;
    const cluster = point.cluster_id == null ? null : clusters.get(Number(point.cluster_id));
    let color = cluster?.color || '#7b8798';
    if (result.analysis?.mode === 'bear_zones') {
      if (cluster?.cluster_type === 'bear_zone') color = '#b64040';
      else if (cluster?.cluster_type === 'expensive_singleton') color = '#7c2f68';
      else if (point.status === 'bear_candidate') color = '#d28a18';
      else if (point.status === 'ordinary') color = '#7b8798';
    }
    if (result.analysis?.mode === 'bear_volume_zones') {
      if (cluster?.cluster_type === 'bear_volume_zone') color = '#176f8f';
      else if (cluster?.cluster_type === 'high_volume_singleton') color = '#5b4ca0';
      else if (point.status === 'bear_volume_candidate') color = '#2b9cb8';
      else if (point.status === 'ordinary') color = '#7b8798';
    }
    const feature = new ol.Feature({
      geometry: new ol.geom.Point(ol.proj.fromLonLat([point.lon, point.lat])),
      isProductPoint: true,
      pointId: point.id,
      clusterId: point.cluster_id,
      pointData: point,
      pointStatus: point.status,
      analysisMode: result.analysis?.mode,
      clusterType: cluster?.cluster_type,
      strokeColor: color,
    });
    features.push(feature);
  }
  for (const cluster of clusters.values()) {
    const medoid = (result.points || []).find(point => point.id === (cluster.representative?.point_id || cluster.medoid_point_id));
    if (medoid?.lat == null || medoid?.lon == null) continue;
    const coordinates = ol.proj.fromLonLat([medoid.lon, medoid.lat]);
    features.push(new ol.Feature({
      geometry: new ol.geom.Point(coordinates),
      isProductLabel: true,
      clusterId: cluster.cluster_id,
      zoneLabel: result.analysis?.mode === 'bear_zones'
        ? (cluster.cluster_type === 'expensive_singleton' ? 'B•' : `B${Number(cluster.cluster_id) + 1}`)
        : result.analysis?.mode === 'bear_volume_zones'
          ? (cluster.cluster_type === 'high_volume_singleton' ? 'V•' : `V${Number(cluster.cluster_id) + 1}`)
          : `C${Number(cluster.cluster_id) + 1}`,
      strokeColor: cluster.color,
    }));
    features.push(new ol.Feature({
      geometry: new ol.geom.Point(coordinates),
      isProductCenter: true,
      clusterId: cluster.cluster_id,
      strokeColor: cluster.color,
    }));
  }
  _mlVectorSource.addFeatures(features);
  if (features.length) {
    const extent = _mlVectorSource.getExtent();
    if (!ol.extent.isEmpty(extent)) {
      _map.getView().fit(extent, { padding: [60, 60, 60, 60], maxZoom: 10, duration: 500 });
    }
  }
}

function _productPointPopup(point, mode) {
  const statuses = {
    normal: 'В кластере', ordinary: 'Обычная точка', bear_candidate: 'Кандидат',
    bear_zone: 'Медвежья зона', expensive_singleton: 'Аномально дорогая точка',
    bear_volume_candidate: 'Кандидат по объёму', bear_volume_zone: 'Объёмная медвежья зона', high_volume_singleton: 'Аномально объёмная точка',
    spatial_outlier: 'Пространственно изолирована', economic_unavailable: 'Нет экономики',
    unresolved: 'Нет координат',
  };
  const fact = (label, value) => `<div><dt>${label}</dt><dd>${value}</dd></div>`;
  const economics = !['geo_cost', 'bear_zones'].includes(mode) ? '' : [
    point.weighted_price == null ? '' : fact('Средневзвешенная цена', `${_fmt(point.weighted_price)} ₽`),
    point.weighted_rub_per_km == null ? '' : fact('Средневзвешенный ₽/км', `${_fmt(point.weighted_rub_per_km, 1)} ₽/км`),
    point.regional_weighted_rub_per_km == null ? '' : fact('Региональный ₽/км', `${_fmt(point.regional_weighted_rub_per_km, 1)} ₽/км`),
    point.relative_rate_delta == null ? '' : fact('Отклонение', `${_fmt(point.relative_rate_delta * 100, 1)}%`),
  ].join('');
  const volume = !['geo_volume', 'bear_volume_zones'].includes(mode) ? '' : [
    point.regional_mean_trip_count == null ? '' : fact('Средний объём региона', `${_fmt(point.regional_mean_trip_count, 1)} перевозки/точку`),
    point.relative_volume_delta == null ? '' : fact('Отклонение объёма', `${_fmt(point.relative_volume_delta * 100, 1)}%`),
  ].join('');
  return `<article class="product-point-popup">
    <span>Точка назначения</span>
    <h3>${_escapeHtml(point.name)}</h3>
    <dl>
      ${fact('Статус', _escapeHtml(statuses[point.status] || point.status))}
      ${fact('Кластер', point.cluster_id == null ? '—' : Number(point.cluster_id) + 1)}
      ${fact('Перевозки', _fmt(point.trip_count))}
      ${economics}
      ${volume}
    </dl>
  </article>`;
}

function mlClusterStyleFunction(feature) {
  if (feature.get('isProductPoint')) {
    const status = feature.get('pointStatus');
    if (!_clusteringLayerVisibility.points) return null;
    if (status === 'spatial_outlier' && !_clusteringLayerVisibility.outliers) return null;
    if (['bear_candidate', 'bear_volume_candidate'].includes(status) && !_clusteringLayerVisibility.candidates) return null;
    const clusterId = feature.get('clusterId');
    const selected = _selectedMlZoneId;
    const active = selected != null && Number(clusterId) === selected;
    const dimmed = selected != null && Number(clusterId) !== selected;
    const unavailable = ['spatial_outlier', 'economic_unavailable'].includes(status);
    return new ol.style.Style({
      image: new ol.style.Circle({
        radius: active ? 7 : ['expensive_singleton', 'high_volume_singleton'].includes(feature.get('clusterType')) ? 6.5 : 5,
        fill: new ol.style.Fill({ color: dimmed ? 'rgba(123,135,152,.28)' : feature.get('strokeColor') }),
        stroke: new ol.style.Stroke({ color: '#fff', width: active ? 2.5 : 1.2, lineDash: unavailable ? [3, 2] : undefined }),
      }),
    });
  }

  if (feature.get('isProductLabel')) {
    if (!_clusteringLayerVisibility.labels) return null;
    const active = Number(feature.get('clusterId')) === _selectedMlZoneId;
    return new ol.style.Style({
      text: new ol.style.Text({
        text: feature.get('zoneLabel'),
        font: `${active ? '700 13px' : '700 11px'} "Inter", "Segoe UI", sans-serif`,
        fill: new ol.style.Fill({ color: '#fff' }),
        backgroundFill: new ol.style.Fill({ color: feature.get('strokeColor') }),
        padding: [4, 6, 4, 6],
        offsetY: -18,
      }),
    });
  }

  if (feature.get('isProductCenter')) {
    if (!_clusteringLayerVisibility.centers) return null;
    return new ol.style.Style({
      image: new ol.style.RegularShape({
        points: 4, radius: 7, angle: Math.PI / 4,
        fill: new ol.style.Fill({ color: '#fff' }),
        stroke: new ol.style.Stroke({ color: feature.get('strokeColor'), width: 2 }),
      }),
    });
  }

  if (feature.get('isMlPolygon')) {
    if (!_mlLayerVisibility.zones) return null;
    const zoneId = Number(feature.get('clusterId'));
    const active = zoneId === _selectedMlZoneId || zoneId === _hoveredMlZoneId;
    const fillColor = feature.get('fillColor');
    return new ol.style.Style({
      fill: new ol.style.Fill({ color: _mlResultIsStale ? 'rgba(110,120,132,.10)' : fillColor }),
      stroke: new ol.style.Stroke({
        color: feature.get('strokeColor'),
        width: active ? 4 : 2,
        lineDash: _mlResultIsStale ? [7, 6] : undefined,
      }),
    });
  }

  if (feature.get('isMlPoint')) {
    if (!_mlLayerVisibility.cities) return null;
    const active = Number(feature.get('clusterId')) === _selectedMlZoneId;
    return new ol.style.Style({
      image: new ol.style.Circle({
        radius: active ? 6 : 4.5,
        fill: new ol.style.Fill({ color: feature.get('strokeColor') }),
        stroke: new ol.style.Stroke({ color: '#fff', width: active ? 2 : 1.2 }),
      }),
    });
  }

  if (feature.get('isMlLabel')) {
    if (!_mlLayerVisibility.labels) return null;
    const zoneId = Number(feature.get('clusterId'));
    const active = zoneId === _selectedMlZoneId || zoneId === _hoveredMlZoneId;
    const color  = feature.get('strokeColor');
    return new ol.style.Style({
      text: new ol.style.Text({
        text: feature.get('zoneLabel'),
        font: `${active ? '700 14px' : '700 12px'} "Inter", "Segoe UI", sans-serif`,
        fill: new ol.style.Fill({ color: '#ffffff' }),
        backgroundFill: new ol.style.Fill({ color }),
        backgroundStroke: new ol.style.Stroke({ color: '#ffffff', width: active ? 2 : 1 }),
        padding: active ? [6, 9, 6, 9] : [5, 7, 5, 7],
      }),
    });
  }

  if (feature.get('isMlCenter')) {
    if (!_mlLayerVisibility.centers) return null;
    return new ol.style.Style({
      image: new ol.style.RegularShape({
        points: 4,
        radius: 7,
        angle: Math.PI / 4,
        fill: new ol.style.Fill({ color: '#ffffff' }),
        stroke: new ol.style.Stroke({ color: feature.get('strokeColor'), width: 2 }),
      }),
    });
  }

  return null;
}

export function selectMlZone(clusterId, fit = false) {
  _selectedMlZoneId = clusterId == null ? null : Number(clusterId);
  _mlVectorLayer?.changed();
  if (fit && clusterId != null) focusMlZone(clusterId);
}

export function focusMlZone(clusterId) {
  if (!_map || !_mlVectorSource) return;
  const productFeatures = _mlVectorSource.getFeatures().filter(feature =>
    feature.get('isProductPoint') && Number(feature.get('clusterId')) === Number(clusterId)
  );
  if (productFeatures.length) {
    const extent = ol.extent.createEmpty();
    productFeatures.forEach(feature => ol.extent.extend(extent, feature.getGeometry().getExtent()));
    _map.getView().fit(extent, { padding: [70, 70, 70, 70], maxZoom: 11, duration: 450 });
    return;
  }
  const polygon = _mlVectorSource.getFeatures().find(feature =>
    feature.get('isMlPolygon') && Number(feature.get('clusterId')) === Number(clusterId)
  );
  if (!polygon) return;
  _map.getView().fit(polygon.getGeometry().getExtent(), {
    padding: [70, 70, 70, 70], maxZoom: 11, duration: 450,
  });
}

export function setMlLayerVisibility(layer, visible) {
  if (!(layer in _mlLayerVisibility)) return;
  _mlLayerVisibility[layer] = Boolean(visible);
  _mlVectorLayer?.changed();
}

export function setMlResultStale(stale) {
  _mlResultIsStale = Boolean(stale);
  _mlVectorLayer?.changed();
}

export function focusClusteringPoint(pointId) {
  if (!_map || !_mlVectorSource) return;
  const feature = _mlVectorSource.getFeatures().find(item => (
    item.get('isProductPoint') && item.get('pointId') === pointId
  ));
  if (!feature) return;
  _map.getView().animate({ center: feature.getGeometry().getCoordinates(), zoom: 11, duration: 350 });
}

export function highlightCluster(clusterId, fit = false) {
  selectMlZone(clusterId, fit);
}

export function clearClusteringResult() {
  clearMlClusters();
}

export function setClusteringLayers(layer, visible) {
  if (!(layer in _clusteringLayerVisibility)) return;
  _clusteringLayerVisibility[layer] = Boolean(visible);
  _mlVectorLayer?.changed();
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

function _escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;',
  })[char]);
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
          <div class="popup-title">${_escapeHtml(pt.town)}</div>
          <div class="popup-subtitle">${_escapeHtml(pt.region || 'Регион не указан')} • ${typeName}</div>
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
          <div style="font-weight: 600; font-size: 13px; color: var(--text-main); margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${typeEmoji} ${_escapeHtml(pt.town)}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${priceFormatted} • ${pt.count} заяв.</div>
        </div>
        <div style="display: flex; gap: 4px;">
          <button class="popup-btn-regeocode-small" data-town="${_escapeHtml(pt.town)}" data-region="${_escapeHtml(pt.region)}" title="Пересчитать координаты" style="background: rgba(255,255,255,0.1); color: var(--text-main); border: 1px solid var(--border); padding: 6px; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s;">
            🔄
          </button>
          <button class="popup-btn-details-small" data-town="${_escapeHtml(pt.town)}" data-region="${_escapeHtml(pt.region)}" data-type="${kind === 'ship' ? 'shipment' : 'delivery'}" style="background: var(--accent); color: #fff; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 500; transition: background 0.2s;">
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
      <div class="popup-footer" style="padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.1); text-align: center;">
        <button class="popup-btn-regeocode-all" style="width: 100%; background: rgba(255,255,255,0.1); color: var(--text-main); border: 1px solid var(--border); padding: 8px; border-radius: 4px; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px;">
          <span style="font-size: 14px;">🔄</span> Пересчитать все координаты
        </button>
      </div>
    </div>
  `;
}
