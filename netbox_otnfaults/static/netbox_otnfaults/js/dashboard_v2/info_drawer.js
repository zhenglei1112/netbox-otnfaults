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

function setMetric(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = String(Number(value) || 0);
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
  const track = document.createElement('div');
  track.className = 'dashboard-v2-fault-carousel-track';
  faults.forEach((fault) => track.appendChild(createFaultCard(fault || {})));
  list.replaceChildren(track);
  list.tabIndex = 0;
  list.onkeydown = null;
  list.setAttribute('role', 'region');
  list.setAttribute('aria-label', '处理中故障轮播');

  let currentIndex = 0;
  const showFault = (index) => {
    currentIndex = (index + faults.length) % faults.length;
    track.style.transform = `translateX(-${currentIndex * 100}%)`;
    if (count) count.textContent = `${currentIndex + 1}/${faults.length}`;
    onActiveFaultChange?.(faults[currentIndex], currentIndex);
  };
  if (faults.length > 1) {
    const previous = createCarouselButton('previous', () => showFault(currentIndex - 1));
    const next = createCarouselButton('next', () => showFault(currentIndex + 1));
    list.appendChild(previous);
    list.appendChild(next);
    list.onkeydown = (event) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault?.();
        showFault(currentIndex - 1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault?.();
        showFault(currentIndex + 1);
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
    updateStatus.textContent = data.simulated ? '模拟数据 · 5 条处理中' : formatUpdateTime(data.timestamp);
    updateStatus.classList.remove('is-error');
  }

  const faults = Array.isArray(data.processing_faults) ? data.processing_faults : [];
  const count = document.getElementById('dashboard-v2-info-fault-count');
  const list = document.getElementById('dashboard-v2-info-fault-list');
  if (!list) return 0;
  list.replaceChildren();
  list.onkeydown = null;
  if (!faults.length) {
    list.appendChild(createTextElement(
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

  toggle.addEventListener('click', () => {
    expanded = !expanded;
    applyState();
  });
  applyState();

  return {
    isExpanded: () => expanded,
    render: (data) => renderDashboardV2InfoDrawer(data, { onActiveFaultChange }),
    showError: showDashboardV2InfoDrawerError,
    setExpanded(value) {
      expanded = Boolean(value);
      applyState();
    },
  };
}
