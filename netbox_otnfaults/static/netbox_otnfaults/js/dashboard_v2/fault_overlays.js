import { leaderSegment, PROCESSING_FAULT_CALLOUT_WIDTH, PROCESSING_FAULT_CALLOUT_HEIGHT, expandRect, buildPlacementCandidates, scorePlacement, PROCESSING_FAULT_LAYOUT_GAP } from './fault_layout.js?v=20260910-presentation-v1';
const PROCESSING_FAULTS_SOURCE_ID = 'dashboard-v2-processing-faults';
import { CUTOVER_COLORS } from './cutovers.js?v=20260910-presentation-v1';
const SITES_SOURCE_ID = 'dashboard-v2-sites';
const OTN_PATHS_SOURCE_ID = 'dashboard-v2-otn-paths';
const SITES_CORE_LAYER_ID = 'dashboard-v2-sites-core';
const SITES_LABEL_LAYER_ID = 'dashboard-v2-sites-label';
const OTN_PATHS_MAIN_LAYER_ID = 'dashboard-v2-otn-paths-main';

export function createFaultOverlayController(setSourceDataIfChanged) {
  let processingFaultFocusMarkers = [];
  let processingFaultFocusMoveHandler = null;
  let processingFaultFocusEndHandler = null;
  let processingFaultFocusMap = null;
  let processingFaultFocusFrameId = null;
  let processingFaultFocusResizeObserver = null;
  let processingFaultNetworkLayoutDirty = true;
  const processingFaultFocusPlacements = new Map();
  const PROCESSING_FAULT_INFO_MIN_ZOOM = 3.9;
  const PROCESSING_FAULT_RADAR_RADIUS = 38;
  const PROCESSING_FAULT_NETWORK_CANDIDATE_LIMIT = 8;
  const PROCESSING_FAULT_NETWORK_LAYER_IDS = [
    OTN_PATHS_MAIN_LAYER_ID,
    SITES_CORE_LAYER_ID,
    SITES_LABEL_LAYER_ID,
  ];
  const CIRCLED_NUMBERS = [
    '', '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
    '⑪', '⑫', '⑬', '⑭', '⑮', '⑯', '⑰', '⑱', '⑲', '⑳',
  ];

  function processingFaultLabel(index) {
    const number = index + 1;
    return CIRCLED_NUMBERS[number] || `[${number}]`;
  }

  function renderDashboardV2ProcessingFaults(map, faults = []) {
    const source = map?.getSource?.(PROCESSING_FAULTS_SOURCE_ID);
    if (!source?.setData) {
      if (typeof map?.once === 'function' && !map.loaded?.()) {
        map.once('load', () => renderDashboardV2ProcessingFaults(map, faults));
      }
      return 0;
    }
    const features = faults.flatMap((fault, index) => {
      if (fault.mapDisplayMode === 'hidden') return [];
      if (fault?.lng == null || fault?.lat == null || fault.lng === '' || fault.lat === '') return [];
      const longitude = Number(fault.lng);
      const latitude = Number(fault.lat);
      if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return [];
      if (longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90) return [];
      return [{
        type: 'Feature',
        id: String(fault.id ?? index),
        geometry: { type: 'Point', coordinates: [longitude, latitude] },
        properties: {
          fault_number: String(fault.fault_number ?? ''),
          index_label: fault.kind === 'cutover' ? '⇄' : processingFaultLabel(index),
          color: fault.kind === 'cutover' ? CUTOVER_COLORS[fault.status_color] || CUTOVER_COLORS.gray : '#ff334f',
          severity: String(fault.severity || 'minor'),
        },
      }];
    });
    setSourceDataIfChanged(source, { type: 'FeatureCollection', features });
    renderProcessingFaultFocuses(map, faults);
    return features.length;
  }

  function createFaultFocusNode(tagName, className, text = null) {
    const node = document.createElement(tagName);
    node.className = className;
    if (text !== null) node.textContent = String(text);
    return node;
  }

  function updateFaultFocusElement(element, fault, index) {
    element.classList?.toggle('is-points-only', fault.mapDisplayMode === 'points');
    const values = {
      'dashboard-v2-fault-focus-core': fault.kind === 'cutover' ? '⇄' : processingFaultLabel(index),
      'dashboard-v2-fault-callout-identity': fault.kind === 'cutover' ? '⇄\n割\n接' : '⚠\n故\n障',
      'dashboard-v2-fault-focus-location': faultFocusLocation(fault),
      'dashboard-v2-fault-callout-route': faultFocusRoute(fault),
      'dashboard-v2-fault-callout-category': fault.category_display || '处理中故障',
      'dashboard-v2-fault-callout-number': fault.fault_number || '未编号故障',
      'dashboard-v2-fault-callout-meta': `${fault.province || '省份未设置'} · ${fault.duration || '历时未知'}`,
      'dashboard-v2-fault-callout-business': `影响业务 ${Number(fault.affected_business_count ?? fault.interrupted_business_count) || 0} 项${(fault.affected_business_names || fault.interrupted_business_names)?.length ? ` · ${(fault.affected_business_names || fault.interrupted_business_names).join('、')}` : ''}`,
    };
    if (fault.kind === 'cutover') {
      values['dashboard-v2-fault-callout-business'] = `主管 ${fault.supervisor || '—'}${fault.location ? ` · ${fault.location}` : ''}`;
      element.classList?.toggle('is-cutover', true);
      setFaultFocusStyle(element, '--cutover-color', CUTOVER_COLORS[fault.status_color] || CUTOVER_COLORS.gray);
    }
    const visit = (node) => {
      if (Object.hasOwn(values, node.className) && node.textContent !== values[node.className]) {
        node.textContent = values[node.className];
        node.title = values[node.className];
      }
      if (node.className === 'dashboard-v2-fault-callout-category') {
        const color = ['purple', 'teal', 'orange', 'cyan', 'pink', 'indigo', 'blue', 'green', 'red'].includes(fault.category_color) ? fault.category_color : 'gray';
        if (node.dataset.color !== color) node.dataset.color = color;
      }
      if (node.className === 'dashboard-v2-fault-callout-route') {
        node.title = [fault.site_a || fault.province || '未知站点', ...(fault.sites_z || [])].join(' → ');
      }
      Array.from(node.children || []).forEach(visit);
    };
    visit(element);
    const label = `${faultFocusLocation(fault)} ${fault.category_display || '处理中故障'}`;
    if (element.getAttribute?.('aria-label') !== label) element.setAttribute?.('aria-label', label);
  }

  function faultFocusLocation(fault) {
    return String(fault?.site_a || fault?.province || fault?.fault_number || '故障位置');
  }

  function faultFocusRoute(fault) {
    const aSite = String(fault?.site_a || fault?.province || '未知站点');
    const zSites = Array.isArray(fault?.sites_z) ? fault.sites_z.filter(Boolean) : [];
    if (!zSites.length) return `${aSite} OTN`;
    const suffix = zSites.length > 1 ? `${zSites[0]}等${zSites.length}站` : zSites[0];
    return `${aSite}-${suffix} OTN`;
  }

  function buildProcessingFaultFocusElement(fault, index) {
    const root = createFaultFocusNode('div', 'dashboard-v2-fault-focus');
    root.dataset.faultId = String(fault.id ?? '');
    root.setAttribute?.('aria-label', `${faultFocusLocation(fault)} ${fault?.category_display || '处理中故障'}`);

    const radar = createFaultFocusNode('div', 'dashboard-v2-fault-focus-radar');
    for (let ring = 1; ring <= 3; ring += 1) {
      radar.appendChild(createFaultFocusNode('span', `dashboard-v2-fault-focus-ring is-${ring}`));
    }
    radar.appendChild(createFaultFocusNode(
      'span',
      'dashboard-v2-fault-focus-core',
      processingFaultLabel(index),
    ));
    root.appendChild(radar);
    root.appendChild(createFaultFocusNode(
      'span',
      'dashboard-v2-fault-focus-location',
      faultFocusLocation(fault),
    ));
    root.appendChild(createFaultFocusNode('span', 'dashboard-v2-fault-focus-leader'));

    const callout = createFaultFocusNode('section', 'dashboard-v2-fault-callout');
    const alertRow = createFaultFocusNode('div', 'dashboard-v2-fault-callout-alert');
    alertRow.appendChild(createFaultFocusNode('strong', 'dashboard-v2-fault-callout-identity'));
    callout.appendChild(alertRow);
    alertRow.appendChild(createFaultFocusNode(
      'strong',
      'dashboard-v2-fault-callout-category',
      fault?.category_display || '处理中故障',
    ));
    alertRow.appendChild(createFaultFocusNode(
      'span',
      'dashboard-v2-fault-callout-number',
      fault?.fault_number || '未编号故障',
    ));
    callout.appendChild(createFaultFocusNode('div', 'dashboard-v2-fault-callout-route'));
    callout.appendChild(createFaultFocusNode('div', 'dashboard-v2-fault-callout-meta'));
    callout.appendChild(createFaultFocusNode('div', 'dashboard-v2-fault-callout-business'));
    root.appendChild(callout);
    updateFaultFocusElement(root, fault, index);
    return root;
  }

  function setFaultFocusStyle(element, property, value) {
    if (typeof element?.style?.setProperty === 'function') {
      element.style.setProperty(property, value);
    } else if (element?.style) {
      element.style[property] = value;
    }
  }

  function screenRectForElement(element, containerRect) {
    if (!element || element.hidden || typeof element.getBoundingClientRect !== 'function') return null;
    const rect = element.getBoundingClientRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) return null;
    return {
      left: rect.left - containerRect.left,
      top: rect.top - containerRect.top,
      right: rect.right - containerRect.left,
      bottom: rect.bottom - containerRect.top,
    };
  }

  function reservedInterfaceRects(containerRect) {
    const elements = [
      document.getElementById('dashboard-v2-info-drawer'),
      document.getElementById('dashboard-v2-debug-panel'),
      document.querySelector?.('.dashboard-v2-map-tools'),
    ];
    return elements
      .map((element) => screenRectForElement(element, containerRect))
      .filter(Boolean);
  }

  function networkObstructionScore(map, rect, cache) {
    if (typeof map?.queryRenderedFeatures !== 'function') return 0;
    const layers = PROCESSING_FAULT_NETWORK_LAYER_IDS.filter((layerId) => map.getLayer?.(layerId));
    if (!layers.length) return 0;
    const cacheKey = [rect.left, rect.top, rect.right, rect.bottom]
      .map((value) => Math.round(value / 4) * 4)
      .join(':');
    if (cache.has(cacheKey)) return cache.get(cacheKey);
    try {
      const features = map.queryRenderedFeatures(
        [[rect.left, rect.top], [rect.right, rect.bottom]],
        { layers },
      );
      const siteKeys = new Set();
      const pathKeys = new Set();
      features.forEach((feature, index) => {
        const layerId = feature?.layer?.id || '';
        const featureKey = String(feature?.id ?? feature?.properties?.id ?? index);
        if (layerId === SITES_CORE_LAYER_ID || layerId === SITES_LABEL_LAYER_ID) {
          siteKeys.add(featureKey);
        } else if (layerId === OTN_PATHS_MAIN_LAYER_ID) {
          pathKeys.add(featureKey);
        }
      });
      const score = (siteKeys.size * 240000) + (Math.min(pathKeys.size, 12) * 32000);
      cache.set(cacheKey, score);
      return score;
    } catch (_error) {
      cache.set(cacheKey, 0);
      return 0;
    }
  }

  function isCoordinateFrontFacing(map, coordinates) {
    const center = map?.getCenter?.();
    if (!center || !Number.isFinite(Number(center.lng)) || !Number.isFinite(Number(center.lat))) return true;
    const toRadians = (degrees) => (Number(degrees) * Math.PI) / 180;
    const centerLatitude = toRadians(center.lat);
    const latitude = toRadians(coordinates[1]);
    const longitudeDelta = toRadians(coordinates[0] - center.lng);
    const dot = (Math.sin(centerLatitude) * Math.sin(latitude))
      + (Math.cos(centerLatitude) * Math.cos(latitude) * Math.cos(longitudeDelta));
    return dot >= -0.01;
  }

  function applyProcessingFaultPlacement(entry, candidate) {
    const { element } = entry;
    const boxWidth = candidate.rect.right - candidate.rect.left;
    const boxHeight = candidate.rect.bottom - candidate.rect.top;
    setFaultFocusStyle(element, '--fault-callout-x', `${candidate.x}px`);
    setFaultFocusStyle(element, '--fault-callout-y', `${candidate.y}px`);
    const targetX = candidate.x > 0
      ? candidate.x
      : (candidate.x + boxWidth < 0
        ? candidate.x + boxWidth
        : 0);
    const targetY = candidate.y > 0
      ? candidate.y
      : (candidate.y + boxHeight < 0
        ? candidate.y + boxHeight
        : 0);
    const distance = Math.max(Math.hypot(targetX, targetY), 1);
    const unitX = targetX / distance;
    const unitY = targetY / distance;
    const leaderStart = candidate.leaderRadius || 14;
    setFaultFocusStyle(element, '--fault-leader-x', `${unitX * leaderStart}px`);
    setFaultFocusStyle(element, '--fault-leader-y', `${unitY * leaderStart}px`);
    setFaultFocusStyle(element, '--fault-leader-length', `${Math.max(distance - leaderStart, 0)}px`);
    setFaultFocusStyle(element, '--fault-leader-angle', `${Math.atan2(targetY, targetX)}rad`);
    element.dataset.placement = candidate.direction;
    element.classList?.toggle('is-left', targetX < 0);
    element.classList?.toggle('is-location-below', candidate.y + boxHeight < 0);
  }

  function removeProcessingFaultFocuses() {
    if (processingFaultFocusMap && processingFaultFocusMoveHandler) {
      processingFaultFocusMap.off?.('move', processingFaultFocusMoveHandler);
      processingFaultFocusMap.off?.('resize', processingFaultFocusEndHandler);
      processingFaultFocusMap.off?.('zoom', processingFaultFocusMoveHandler);
      processingFaultFocusMap.off?.('moveend', processingFaultFocusEndHandler);
      processingFaultFocusMap.off?.('zoomend', processingFaultFocusEndHandler);
      processingFaultFocusMap.off?.('sourcedata', processingFaultFocusEndHandler);
    }
    if (processingFaultFocusFrameId !== null) {
      globalThis.cancelAnimationFrame?.(processingFaultFocusFrameId);
      processingFaultFocusFrameId = null;
    }
    processingFaultFocusResizeObserver?.disconnect?.();
    processingFaultFocusMarkers.forEach(({ marker }) => marker?.remove?.());
    processingFaultFocusMarkers = [];
    processingFaultFocusMoveHandler = null;
    processingFaultFocusEndHandler = null;
    processingFaultFocusResizeObserver = null;
    processingFaultFocusMap = null;
  }

  function createProcessingFaultFocus(map, fault, index) {
    if (!fault || typeof maplibregl === 'undefined' || typeof maplibregl.Marker !== 'function') return false;
    if (fault.lng === null || fault.lng === undefined || fault.lng === ''
      || fault.lat === null || fault.lat === undefined || fault.lat === '') return false;
    const longitude = Number(fault.lng);
    const latitude = Number(fault.lat);
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return false;
    if (longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90) return false;

    const coordinates = [longitude, latitude];
    const element = buildProcessingFaultFocusElement(fault, index);
    try {
      const marker = new maplibregl.Marker({
        element,
        anchor: 'center',
        rotationAlignment: 'viewport',
        pitchAlignment: 'viewport',
        opacityWhenCovered: 0,
      }).setLngLat(coordinates).addTo(map);
      processingFaultFocusMarkers.push({
        marker,
        element,
        coordinates,
        faultId: String(fault.id ?? index),
      });
      return true;
    } catch (_error) {
      return false;
    }
  }

  function updateProcessingFaultFocuses(map) {
    const zoom = Number(map?.getZoom?.());
    const visible = Boolean(map.__dashboardPresentationScale) || !Number.isFinite(zoom) || zoom >= PROCESSING_FAULT_INFO_MIN_ZOOM;
    const container = map?.getContainer?.();
    const containerRect = container?.getBoundingClientRect?.() || {
      left: 0,
      top: 0,
      width: container?.clientWidth || 0,
      height: container?.clientHeight || 0,
    };
    const width = container?.clientWidth || containerRect.width || 0;
    const height = container?.clientHeight || containerRect.height || 0;
    const projected = processingFaultFocusMarkers.flatMap((entry) => {
      entry.element.classList?.toggle('is-presentation-active', entry.faultId === map.__dashboardPresentationFocus);
      if ((!visible && entry.mapDisplayMode !== 'points') || !isCoordinateFrontFacing(map, entry.coordinates)) {
        entry.element.hidden = true;
        return [];
      }
      try {
        const point = map.project(entry.coordinates);
        if (!Number.isFinite(point?.x) || !Number.isFinite(point?.y)
          || point.x < 0 || point.x > width || point.y < 0 || point.y > height) {
          entry.element.hidden = true;
          return [];
        }
        entry.element.hidden = false;
        return [{ ...entry, point }];
      } catch (_error) {
        entry.element.hidden = true;
        return [];
      }
    });
    const radius = PROCESSING_FAULT_RADAR_RADIUS * (map.__dashboardPresentationScale ? map.__dashboardPresentationScale * 1.6 : 1);
    const radarRects = projected.map(({ point }) => ({
      left: point.x - radius,
      top: point.y - radius,
      right: point.x + radius,
      bottom: point.y + radius,
    }));
    const context = {
      map,
      width,
      height,
      placedRects: [],
      placedLeaders: [],
      radarRects,
      reservedRects: reservedInterfaceRects(containerRect),
      networkScoreCache: new Map(),
      evaluateNetwork: processingFaultNetworkLayoutDirty,
    };
    projected.forEach((entry) => {
      if (entry.mapDisplayMode === 'points') return;
      const previous = processingFaultFocusPlacements.get(entry.faultId);
      const callout = entry.element.querySelector?.('.dashboard-v2-fault-callout');
      const box = map.__dashboardPresentationScale ? {
        width: callout?.offsetWidth || 352 * map.__dashboardPresentationScale,
        height: callout?.offsetHeight || 141 * map.__dashboardPresentationScale,
        scale: map.__dashboardPresentationScale * 1.6,
      } : {};
      const candidates = buildPlacementCandidates(entry.point, width, height, box).map((candidate) => ({
        ...candidate, leaderRadius: 14 * (box.scale || 1), leader: leaderSegment(entry.point, candidate.rect, 14 * (box.scale || 1)),
      }));
      const shortlist = candidates
        .map((candidate) => ({
          ...candidate,
          baseScore: scorePlacement(candidate, context, previous),
        }))
        .sort((first, second) => first.baseScore - second.baseScore)
        .slice(0, PROCESSING_FAULT_NETWORK_CANDIDATE_LIMIT);
      const candidate = shortlist.reduce((best, current) => {
        const score = current.baseScore + (context.evaluateNetwork
          ? networkObstructionScore(map, current.rect, context.networkScoreCache)
          : 0);
        return !best || score < best.score ? { ...current, score } : best;
      }, null);
      if (!candidate) return;
      applyProcessingFaultPlacement(entry, candidate);
      context.placedRects.push(expandRect(candidate.rect, PROCESSING_FAULT_LAYOUT_GAP));
      context.placedLeaders.push(candidate.leader);
      processingFaultFocusPlacements.set(entry.faultId, {
        direction: candidate.direction,
        tier: candidate.tier,
      });
    });
    processingFaultNetworkLayoutDirty = false;
  }

  function scheduleProcessingFaultFocusLayout(map) {
    if (processingFaultFocusFrameId !== null) return;
    if (typeof globalThis.requestAnimationFrame !== 'function') {
      updateProcessingFaultFocuses(map);
      return;
    }
    processingFaultFocusFrameId = globalThis.requestAnimationFrame(() => {
      processingFaultFocusFrameId = null;
      updateProcessingFaultFocuses(map);
    });
  }

  function observeProcessingFaultLayout(map) {
    if (typeof globalThis.ResizeObserver !== 'function') return;
    processingFaultFocusResizeObserver = new globalThis.ResizeObserver(() => {
      processingFaultNetworkLayoutDirty = true;
      scheduleProcessingFaultFocusLayout(map);
    });
    const targets = [
      map?.getContainer?.(),
      document.getElementById('dashboard-v2-info-drawer'),
      document.getElementById('dashboard-v2-debug-panel'),
      document.querySelector?.('.dashboard-v2-map-tools'),
    ].filter(Boolean);
    targets.forEach((target) => processingFaultFocusResizeObserver.observe(target));
  }

  function renderProcessingFaultFocuses(map, faults) {
    const sameMap = processingFaultFocusMap === map;
    if (!sameMap) removeProcessingFaultFocuses();
    processingFaultFocusMap = map;
    const previous = new Map(processingFaultFocusMarkers.map((entry) => [entry.faultId, entry]));
    processingFaultFocusMarkers = [];
    let changed = false;
    faults.forEach((fault, index) => {
      if (fault.mapDisplayMode === 'hidden') return;
      const id = String(fault.id ?? index);
      const coordinates = [Number(fault.lng), Number(fault.lat)];
      if (fault.lng == null || fault.lat == null || fault.lng === '' || fault.lat === ''
          || !coordinates.every(Number.isFinite) || Math.abs(coordinates[0]) > 180 || Math.abs(coordinates[1]) > 90) return;
      const entry = previous.get(id);
      const signature = JSON.stringify([index, coordinates, fault.site_a, fault.province, fault.sites_z, fault.fault_number, fault.category_display, fault.category_color, fault.duration, fault.interrupted_business_count, fault.interrupted_business_names, fault.affected_business_count, fault.affected_business_names, fault.kind, fault.status_color, fault.supervisor, fault.location, fault.mapDisplayMode]);
      if (entry) {
        entry.mapDisplayMode = fault.mapDisplayMode;
        previous.delete(id);
        if (entry.signature !== signature) {
          updateFaultFocusElement(entry.element, fault, index);
          if (entry.coordinates.some((value, i) => value !== coordinates[i])) entry.marker.setLngLat(coordinates);
          entry.coordinates = coordinates;
          entry.signature = signature;
          changed = true;
        }
        processingFaultFocusMarkers.push(entry);
      } else if (createProcessingFaultFocus(map, fault, index)) {
        processingFaultFocusMarkers.at(-1).signature = signature;
        processingFaultFocusMarkers.at(-1).mapDisplayMode = fault.mapDisplayMode;
        changed = true;
      }
    });
    previous.forEach((entry) => { entry.marker.remove(); changed = true; });
    const currentFaultIds = new Set(processingFaultFocusMarkers.map(({ faultId }) => faultId));
    [...processingFaultFocusPlacements.keys()].forEach((faultId) => {
      if (!currentFaultIds.has(faultId)) processingFaultFocusPlacements.delete(faultId);
    });
    if (sameMap) {
      if (changed) {
        processingFaultNetworkLayoutDirty = true;
        scheduleProcessingFaultFocusLayout(map);
      }
      return;
    }
    processingFaultNetworkLayoutDirty = true;
    processingFaultFocusMoveHandler = () => scheduleProcessingFaultFocusLayout(map);
    processingFaultFocusEndHandler = (event) => {
      if (event?.type === 'sourcedata' && ![SITES_SOURCE_ID, OTN_PATHS_SOURCE_ID].includes(event.sourceId)) return;
      processingFaultNetworkLayoutDirty = true;
      scheduleProcessingFaultFocusLayout(map);
    };
    map.on?.('move', processingFaultFocusMoveHandler);
    map.on?.('resize', processingFaultFocusEndHandler);
    map.on?.('zoom', processingFaultFocusMoveHandler);
    map.on?.('moveend', processingFaultFocusEndHandler);
    map.on?.('zoomend', processingFaultFocusEndHandler);
    map.on?.('sourcedata', processingFaultFocusEndHandler);
    observeProcessingFaultLayout(map);
    scheduleProcessingFaultFocusLayout(map);
  }


  return {
    render: renderDashboardV2ProcessingFaults,
    invalidate() { processingFaultFocusEndHandler?.(); },
    destroy() { removeProcessingFaultFocuses(); processingFaultFocusPlacements.clear(); },
  };
}
