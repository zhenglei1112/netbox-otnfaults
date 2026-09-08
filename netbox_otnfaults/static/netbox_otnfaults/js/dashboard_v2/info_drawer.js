const carouselStates = new WeakMap();

function setText(element, text) {
  if (element && element.textContent !== text) element.textContent = text;
}

function cardSignature(fault) {
  if (fault.kind === 'cutover') return JSON.stringify(fault);
  return JSON.stringify([
    fault.url, fault.severity, fault.fault_number, fault.category_display, fault.urgency_display,
    fault.province, fault.site_a, fault.sites_z, fault.occurrence_time_display, fault.duration,
    fault.handling_unit, fault.handler, fault.interrupted_business_count,
    fault.interrupted_business_names, fault.reason,
  ]);
}

// Patch leaves in place so focus, the current card and animation state survive polling.
function patchCard(target, source) {
  if (target.className !== source.className) target.className = source.className;
  if (target.dataset.severity !== source.dataset.severity) target.dataset.severity = source.dataset.severity;
  for (const key of ['href', 'target', 'rel', 'title']) {
    if (target[key] !== source[key]) target[key] = source[key] || '';
  }
  const label = source.getAttribute?.('aria-label');
  if (label && target.getAttribute?.('aria-label') !== label) target.setAttribute('aria-label', label);
  const children = Array.from(source.children || []);
  if (!children.length) setText(target, source.textContent);
  else children.forEach((child, index) => patchCard(target.children[index], child));
}

function textValue(value, fallback = '—') {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text || fallback;
}

function createTextElement(tagName, className, value) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = textValue(value);
  return element;
}

function createDetailRow(label, value, extraClass = '') {
  const row = document.createElement('div');
  row.className = `dashboard-v2-fault-detail${extraClass ? ` ${extraClass}` : ''}`;
  row.appendChild(createTextElement('span', 'dashboard-v2-fault-detail-label', label));
  const valueNode = createTextElement('span', 'dashboard-v2-fault-detail-value', value);
  valueNode.title = valueNode.textContent;
  row.appendChild(valueNode);
  return row;
}

function faultLocation(fault) {
  const routeParts = [];
  if (fault.site_a) routeParts.push(textValue(fault.site_a));
  const zSites = Array.isArray(fault.sites_z) ? fault.sites_z.filter(Boolean) : [];
  if (zSites.length) routeParts.push(zSites.join('、'));
  const route = routeParts.length ? routeParts.join(' → ') : '站点未填写';
  return fault.province ? `${fault.province} · ${route}` : route;
}

function faultHandling(fault) {
  const parts = [fault.handling_unit, fault.handler].filter(Boolean);
  return parts.length ? parts.join(' · ') : '待分派';
}

function faultBusiness(fault) {
  const count = Number(fault.interrupted_business_count) || 0;
  const names = Array.isArray(fault.interrupted_business_names)
    ? fault.interrupted_business_names.filter(Boolean)
    : [];
  if (!count) return '未登记当前中断业务';
  return names.length ? `${count}项 · ${names.join('、')}` : `${count}项`;
}

function createFaultCard(fault) {
  if (fault.kind === 'cutover') return createCutoverCard(fault);
  const card = document.createElement(fault.url ? 'a' : 'article');
  card.className = 'dashboard-v2-fault-card';
  card.dataset.severity = textValue(fault.severity, 'minor');
  if (fault.url) {
    card.href = fault.url;
    card.target = '_blank';
    card.rel = 'noopener';
    card.setAttribute('aria-label', `打开故障 ${textValue(fault.fault_number)} 详情`);
  }

  const header = document.createElement('div');
  header.className = 'dashboard-v2-fault-card-header';
  const title = document.createElement('div');
  title.className = 'dashboard-v2-fault-card-title';
  const severityDot = document.createElement('span');
  severityDot.className = 'dashboard-v2-fault-severity-dot';
  severityDot.setAttribute('aria-hidden', 'true');
  title.appendChild(severityDot);
  title.appendChild(createTextElement('strong', 'dashboard-v2-fault-number', fault.fault_number));
  header.appendChild(title);

  const badges = document.createElement('div');
  badges.className = 'dashboard-v2-fault-badges';
  badges.appendChild(createTextElement('span', 'dashboard-v2-fault-badge', fault.category_display));
  badges.appendChild(createTextElement('span', 'dashboard-v2-fault-badge is-urgency', fault.urgency_display));
  header.appendChild(badges);
  card.appendChild(header);

  const details = document.createElement('div');
  details.className = 'dashboard-v2-fault-card-details';
  details.appendChild(createDetailRow('位置', faultLocation(fault), 'is-wide'));
  details.appendChild(createDetailRow(
    '发生/历时',
    `${textValue(fault.occurrence_time_display)} · ${textValue(fault.duration)}`,
  ));
  details.appendChild(createDetailRow('处置', faultHandling(fault)));
  details.appendChild(createDetailRow('中断业务', faultBusiness(fault), 'is-wide'));
  details.appendChild(createDetailRow('原因', fault.reason, 'is-wide'));
  card.appendChild(details);
  return card;
}

function createCutoverCard(task) {
  const card = document.createElement(task.url ? 'a' : 'article');
  card.className = 'dashboard-v2-fault-card dashboard-v2-cutover-card';
  card.dataset.severity = task.status_color || 'gray';
  if (task.url) { card.href = task.url; card.target = '_blank'; card.rel = 'noopener'; }
  const header = createTextElement('div', 'dashboard-v2-fault-card-title', `⇄ ${task.type_display || '割接'} · ${task.status_display || '未知状态'}`);
  card.appendChild(header);
  const details = document.createElement('div');
  details.className = 'dashboard-v2-fault-card-details';
  details.appendChild(createDetailRow('计划时间', `${task.day === 'today' ? '今日' : '明日'} ${task.planned_time_display}`, 'is-wide'));
  details.appendChild(createDetailRow('站点', faultLocation(task), 'is-wide'));
  details.appendChild(createDetailRow('位置', task.location, 'is-wide'));
  details.appendChild(createDetailRow('线路主管', `${task.supervisor || '—'}${task.is_my_task ? '（本人）' : ''}`));
  details.appendChild(createDetailRow('编号', task.cutover_no));
  card.appendChild(details);
  return card;
}

export function renderDashboardV2Cutovers(data) {
  const list = document.getElementById('dashboard-v2-info-cutover-list');
  if (!list) return;
  const tasks = (data.cutovers || []).map((task) => ({ ...task, kind: 'cutover' }));
  const count = document.getElementById('dashboard-v2-info-cutover-count');
  const summary = data.cutover_summary || {};
  setText(document.getElementById('dashboard-v2-info-cutover-summary'), `今日 ${summary.today || 0} · 明日 ${summary.tomorrow || 0}`);
  if (!tasks.length) {
    if (list.dataset.empty !== 'true') {
      list.replaceChildren(createTextElement('div', 'dashboard-v2-info-state', '今明无割接任务'));
      carouselStates.delete(list);
      list.onkeydown = null;
      list.dataset.empty = 'true';
    }
    setText(count, '0/0');
    return;
  }
  list.dataset.empty = 'false';
  renderFaultCarousel(list, tasks, count);
  list.setAttribute('aria-label', '今明割接轮播');
  const state = carouselStates.get(list);
  state.previous?.setAttribute('aria-label', '上一条割接');
  state.next?.setAttribute('aria-label', '下一条割接');
}

function setMetric(id, value) {
  const element = document.getElementById(id);
  setText(element, String(Number(value) || 0));
}

function createCarouselButton(direction, onActivate) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `dashboard-v2-fault-carousel-arrow is-${direction}`;
  button.textContent = direction === 'previous' ? '‹' : '›';
  button.setAttribute('aria-label', direction === 'previous' ? '上一条处理中故障' : '下一条处理中故障');
  button.addEventListener('click', (event) => {
    event.stopPropagation?.();
    onActivate();
  });
  return button;
}

function renderFaultCarousel(list, faults, count, onActiveFaultChange) {
  const existing = carouselStates.get(list);
  if (existing) {
    const selectedId = existing.faults[existing.currentIndex]?.id;
    const nextCards = new Map();
    faults.forEach((fault, index) => {
      const key = String(fault.id ?? index);
      const signature = cardSignature(fault);
      let entry = existing.cards.get(key);
      if (!entry || Boolean(entry.fault.url) !== Boolean(fault.url)) {
        entry = { node: createFaultCard(fault), signature, fault };
      } else if (entry.signature !== signature) {
        patchCard(entry.node, createFaultCard(fault));
      }
      entry.signature = signature;
      entry.fault = fault;
      nextCards.set(key, entry);
    });
    const nodes = [...nextCards.values()].map((entry) => entry.node);
    if (nodes.length !== existing.track.children.length
        || nodes.some((node, i) => node !== existing.track.children[i])) {
      // Move existing nodes rather than recreating cards.
      nodes.forEach((node, i) => {
        if (existing.track.children[i] !== node) existing.track.insertBefore(node, existing.track.children[i] || null);
      });
      Array.from(existing.track.children).slice(nodes.length).forEach((node) => node.remove());
    }
    existing.cards = nextCards;
    existing.faults = faults;
    existing.onActiveFaultChange = onActiveFaultChange;
    const selected = faults.findIndex((fault) => fault.id === selectedId);
    existing.show(selected < 0 ? Math.min(existing.currentIndex, faults.length - 1) : selected);
    return;
  }
  const track = document.createElement('div');
  track.className = 'dashboard-v2-fault-carousel-track';
  const cards = new Map();
  faults.forEach((fault, index) => {
    const node = createFaultCard(fault || {});
    track.appendChild(node);
    cards.set(String(fault.id ?? index), { node, signature: cardSignature(fault), fault });
  });
  list.replaceChildren(track);
  list.tabIndex = 0;
  list.onkeydown = null;
  list.setAttribute('role', 'region');
  list.setAttribute('aria-label', '处理中故障轮播');

  const state = { track, cards, faults, currentIndex: 0, onActiveFaultChange };
  carouselStates.set(list, state);
  const showFault = (index) => {
    state.currentIndex = (index + state.faults.length) % state.faults.length;
    const transform = `translateX(-${state.currentIndex * 100}%)`;
    if (track.style.transform !== transform) track.style.transform = transform;
    setText(count, `${state.currentIndex + 1}/${state.faults.length}`);
    state.onActiveFaultChange?.(state.faults[state.currentIndex], state.currentIndex);
    if (state.previous) state.previous.hidden = state.next.hidden = state.faults.length < 2;
  };
  state.show = showFault;
  {
    const previous = createCarouselButton('previous', () => showFault(state.currentIndex - 1));
    const next = createCarouselButton('next', () => showFault(state.currentIndex + 1));
    state.previous = previous;
    state.next = next;
    list.appendChild(previous);
    list.appendChild(next);
    list.onkeydown = (event) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault?.();
        showFault(state.currentIndex - 1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault?.();
        showFault(state.currentIndex + 1);
      }
    };
  }
  showFault(0);
}

function formatUpdateTime(timestamp) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '刚刚更新';
  return `更新 ${date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })}`;
}

export function renderDashboardV2InfoDrawer(data = {}, { onActiveFaultChange } = {}) {
  const summary = data.summary || {};
  setMetric('dashboard-v2-info-total-faults', summary.total_faults);
  setMetric('dashboard-v2-info-processing-faults', summary.processing_faults);
  setMetric('dashboard-v2-info-today-faults', summary.today_faults);
  setMetric(
    'dashboard-v2-info-business-interruptions',
    summary.active_business_interruptions,
  );

  const updateStatus = document.getElementById('dashboard-v2-info-update-status');
  if (updateStatus) {
    if (updateStatus.classList.contains('is-error') || !updateStatus.textContent
        || updateStatus.dataset.simulated !== String(Boolean(data.simulated))) {
      setText(updateStatus, data.simulated ? '模拟数据 · 5 条处理中' : formatUpdateTime(data.timestamp));
      updateStatus.dataset.simulated = String(Boolean(data.simulated));
    }
    updateStatus.classList.remove('is-error');
  }

  const faults = Array.isArray(data.processing_faults) ? data.processing_faults : [];
  const count = document.getElementById('dashboard-v2-info-fault-count');
  const list = document.getElementById('dashboard-v2-info-fault-list');
  if (!list) return 0;
  if (!faults.length) {
    carouselStates.delete(list);
    list.onkeydown = null;
    if (list.children.length !== 1 || list.children[0].textContent !== '当前无处理中故障') list.replaceChildren(createTextElement(
      'div',
      'dashboard-v2-info-state',
      '当前无处理中故障',
    ));
    if (count) count.textContent = '0起';
    onActiveFaultChange?.(null, -1);
    return 0;
  }
  renderFaultCarousel(list, faults, count, onActiveFaultChange);
  return faults.length;
}

export function showDashboardV2InfoDrawerError({ preserveData = false } = {}) {
  const updateStatus = document.getElementById('dashboard-v2-info-update-status');
  if (updateStatus) {
    updateStatus.textContent = '更新失败';
    updateStatus.classList.add('is-error');
  }
  if (preserveData) return;
  const list = document.getElementById('dashboard-v2-info-fault-list');
  if (list) {
    list.replaceChildren(createTextElement(
      'div',
      'dashboard-v2-info-state is-error',
      '故障数据加载失败',
    ));
  }
}

export function updateDashboardV2Elapsed(now = Date.now()) {
  const list = document.getElementById('dashboard-v2-info-fault-list');
  const state = list && carouselStates.get(list);
  state?.cards.forEach(({ fault, node }) => {
    const start = Date.parse(fault.occurrence_time);
    if (!Number.isFinite(start)) return;
    const totalMinutes = Math.max(0, Math.floor((now - start) / 60000));
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor(totalMinutes / 60) % 24;
    const minutes = totalMinutes % 60;
    const duration = `${days ? `${days}天` : ''}${days || hours ? `${hours}小时` : ''}${minutes}分`;
    const value = node.children[1].children[1].children[1];
    setText(value, `${textValue(fault.occurrence_time_display)} · ${duration}`);
    if (value.title !== value.textContent) value.title = value.textContent;
  });
}

export function initializeDashboardV2InfoDrawer({ onActiveFaultChange } = {}) {
  const drawer = document.getElementById('dashboard-v2-info-drawer');
  const toggle = document.getElementById('dashboard-v2-info-drawer-toggle');
  const content = document.getElementById('dashboard-v2-info-drawer-content');
  if (!drawer || !toggle || !content) return null;

  let expanded = toggle.getAttribute('aria-expanded') === 'true';

  const applyState = () => {
    drawer.classList.toggle('is-open', expanded);
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.setAttribute('aria-label', expanded ? '收起网络信息' : '展开网络信息');
    toggle.title = expanded ? '收起网络信息' : '展开网络信息';
    content.setAttribute('aria-hidden', String(!expanded));
  };

  const onToggle = () => {
    expanded = !expanded;
    applyState();
  };
  toggle.addEventListener('click', onToggle);
  applyState();

  return {
    isExpanded: () => expanded,
    render: (data) => renderDashboardV2InfoDrawer(data, { onActiveFaultChange }),
    showError: showDashboardV2InfoDrawerError,
    updateElapsed: updateDashboardV2Elapsed,
    destroy() {
      const cutoverList = document.getElementById('dashboard-v2-info-cutover-list');
      if (cutoverList) { carouselStates.delete(cutoverList); cutoverList.onkeydown = null; }
      toggle.removeEventListener?.('click', onToggle);
      const list = document.getElementById('dashboard-v2-info-fault-list');
      if (list) { carouselStates.delete(list); list.onkeydown = null; }
    },
    setExpanded(value) {
      expanded = Boolean(value);
      applyState();
    },
  };
}
