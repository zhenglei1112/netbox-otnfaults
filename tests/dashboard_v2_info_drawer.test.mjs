import assert from 'node:assert/strict';
import test from 'node:test';

import {
  initializeDashboardV2InfoDrawer,
  renderDashboardV2InfoDrawer,
  showDashboardV2InfoDrawerError,
  updateDashboardV2Elapsed,
} from '../netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/info_drawer.js';


function createClassList() {
  const values = new Set();
  return {
    toggle(name, enabled) {
      if (enabled) values.add(name);
      else values.delete(name);
    },
    add(name) { values.add(name); },
    remove(name) { values.delete(name); },
    contains(name) {
      return values.has(name);
    },
  };
}


class FakeElement {
  constructor(tagName = 'div') {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.style = {};
    this.listeners = {};
    this.className = '';
    this.classList = createClassList();
    this.textContent = '';
    this.title = '';
  }

  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }

  insertBefore(child, before) {
    child.remove();
    const index = before ? this.children.indexOf(before) : this.children.length;
    this.children.splice(index, 0, child);
    child.parentElement = this;
  }

  remove() {
    if (this.parentElement) this.parentElement.children = this.parentElement.children.filter((node) => node !== this);
  }

  replaceChildren(...children) {
    this.children = children;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  addEventListener(name, callback) {
    this.listeners[name] = callback;
  }
}


function allText(element) {
  return [element.textContent, ...element.children.map(allText)].join(' ');
}


test('information drawer starts collapsed and toggles its visible and accessible state', () => {
  const drawer = { classList: createClassList() };
  const content = { attributes: {}, setAttribute(name, value) { this.attributes[name] = value; } };
  const toggle = {
    attributes: { 'aria-expanded': 'false' },
    listeners: {},
    title: '',
    addEventListener(name, callback) { this.listeners[name] = callback; },
    getAttribute(name) { return this.attributes[name]; },
    setAttribute(name, value) { this.attributes[name] = value; },
  };
  const elements = {
    'dashboard-v2-info-drawer': drawer,
    'dashboard-v2-info-drawer-toggle': toggle,
    'dashboard-v2-info-drawer-content': content,
  };
  globalThis.document = { getElementById: (id) => elements[id] || null };

  const controller = initializeDashboardV2InfoDrawer();
  assert.ok(controller);
  assert.equal(controller.isExpanded(), false);
  assert.equal(drawer.classList.contains('is-open'), false);
  assert.equal(content.attributes['aria-hidden'], 'true');
  assert.equal(toggle.attributes['aria-label'], '展开网络信息');

  toggle.listeners.click();
  assert.equal(controller.isExpanded(), true);
  assert.equal(drawer.classList.contains('is-open'), true);
  assert.equal(content.attributes['aria-hidden'], 'false');
  assert.equal(toggle.attributes['aria-expanded'], 'true');
  assert.equal(toggle.attributes['aria-label'], '收起网络信息');

  toggle.listeners.click();
  assert.equal(controller.isExpanded(), false);
  assert.equal(content.attributes['aria-hidden'], 'true');
});


test('information drawer renders four metrics and safe full fault cards', () => {
  const ids = [
    'dashboard-v2-info-total-faults',
    'dashboard-v2-info-processing-faults',
    'dashboard-v2-info-today-faults',
    'dashboard-v2-info-business-interruptions',
    'dashboard-v2-info-update-status',
    'dashboard-v2-info-fault-count',
    'dashboard-v2-info-fault-list',
  ];
  const elements = Object.fromEntries(ids.map((id) => [id, new FakeElement()]));
  globalThis.document = {
    getElementById: (id) => elements[id] || null,
    createElement: (tagName) => new FakeElement(tagName),
  };

  const rendered = renderDashboardV2InfoDrawer({
    timestamp: '2026-09-02T12:34:56+08:00',
    summary: {
      total_faults: 80,
      processing_faults: 2,
      today_faults: 3,
      active_business_interruptions: 4,
    },
    processing_faults: [{
      id: 1,
      url: '/plugins/otnfaults/faults/1/',
      fault_number: 'F20260902001',
      category_display: '光缆中断',
      urgency_display: '高',
      severity: 'critical',
      province: '北京',
      site_a: 'A站',
      sites_z: ['Z站'],
      occurrence_time_display: '09-02 10:00',
      duration: '2小时34分',
      handling_unit: '处置单位',
      handler: '张三',
      interrupted_business_count: 1,
      interrupted_business_names: ['<img src=x onerror=alert(1)>'],
      reason: '<script>alert(1)</script>',
      details: '此摘要不应显示',
    }],
  });

  assert.equal(rendered, 1);
  assert.equal(elements['dashboard-v2-info-total-faults'].textContent, '80');
  assert.equal(elements['dashboard-v2-info-processing-faults'].textContent, '2');
  assert.equal(elements['dashboard-v2-info-today-faults'].textContent, '3');
  assert.equal(elements['dashboard-v2-info-business-interruptions'].textContent, '4');
  assert.equal(elements['dashboard-v2-info-fault-count'].textContent, '1/1');
  const track = elements['dashboard-v2-info-fault-list'].children[0];
  const card = track.children[0];
  assert.equal(card.tagName, 'A');
  assert.equal(card.target, '_blank');
  assert.equal(card.rel, 'noopener');
  assert.equal(card.href, '/plugins/otnfaults/faults/1/');
  assert.match(allText(card), /<script>alert\(1\)<\/script>/);
  assert.doesNotMatch(allText(card), /摘要|此摘要不应显示/);
  assert.equal('innerHTML' in card, false);
});


test('information drawer cycles fault cards with hover arrows and keyboard controls', () => {
  const list = new FakeElement();
  const count = new FakeElement();
  const elements = {
    'dashboard-v2-info-update-status': new FakeElement(),
    'dashboard-v2-info-fault-list': list,
    'dashboard-v2-info-fault-count': count,
    'dashboard-v2-info-total-faults': new FakeElement(),
    'dashboard-v2-info-processing-faults': new FakeElement(),
    'dashboard-v2-info-today-faults': new FakeElement(),
    'dashboard-v2-info-business-interruptions': new FakeElement(),
  };
  globalThis.document = {
    getElementById: (id) => elements[id] || null,
    createElement: (tagName) => new FakeElement(tagName),
  };
  const faults = ['F001', 'F002', 'F003'].map((faultNumber) => ({
    id: faultNumber,
    fault_number: faultNumber,
    severity: 'minor',
  }));
  const activeFaults = [];

  renderDashboardV2InfoDrawer(
    { summary: {}, processing_faults: faults },
    { onActiveFaultChange: (fault, index) => activeFaults.push([fault?.fault_number, index]) },
  );

  assert.equal(count.textContent, '1/3');
  assert.equal(list.attributes.role, 'region');
  assert.equal(list.children.length, 3);
  const [track, previous, next] = list.children;
  assert.equal(track.children.length, 3);
  assert.equal(track.style.transform, 'translateX(-0%)');
  assert.deepEqual(activeFaults, [['F001', 0]]);
  assert.equal(previous.attributes['aria-label'], '上一条处理中故障');
  assert.equal(next.attributes['aria-label'], '下一条处理中故障');

  next.listeners.click({ stopPropagation() {} });
  assert.equal(count.textContent, '2/3');
  assert.equal(track.style.transform, 'translateX(-100%)');
  assert.deepEqual(activeFaults.at(-1), ['F002', 1]);
  next.listeners.click({ stopPropagation() {} });
  next.listeners.click({ stopPropagation() {} });
  assert.equal(count.textContent, '1/3');
  assert.equal(track.style.transform, 'translateX(-0%)');

  list.onkeydown({ key: 'ArrowLeft', preventDefault() {} });
  assert.equal(count.textContent, '3/3');
  assert.equal(track.style.transform, 'translateX(-200%)');
  const originalCards = [...track.children];
  renderDashboardV2InfoDrawer({ summary: {}, processing_faults: faults });
  assert.equal(list.children[0], track);
  assert.deepEqual(track.children, originalCards);
  assert.equal(count.textContent, '3/3');
  renderDashboardV2InfoDrawer({ summary: {}, processing_faults: [faults[2], faults[0], faults[1]] });
  assert.equal(count.textContent, '1/3');
  assert.equal(track.children[0], originalCards[2]);
});


test('information drawer shows empty and error states while preserving valid data', () => {
  const status = new FakeElement();
  const list = new FakeElement();
  const count = new FakeElement();
  const metrics = [
    'dashboard-v2-info-total-faults',
    'dashboard-v2-info-processing-faults',
    'dashboard-v2-info-today-faults',
    'dashboard-v2-info-business-interruptions',
  ];
  const elements = {
    'dashboard-v2-info-update-status': status,
    'dashboard-v2-info-fault-list': list,
    'dashboard-v2-info-fault-count': count,
    ...Object.fromEntries(metrics.map((id) => [id, new FakeElement()])),
  };
  globalThis.document = {
    getElementById: (id) => elements[id] || null,
    createElement: (tagName) => new FakeElement(tagName),
  };

  renderDashboardV2InfoDrawer({ summary: {}, processing_faults: [] });
  assert.match(allText(list), /当前无处理中故障/);
  const previousChildren = list.children;
  showDashboardV2InfoDrawerError({ preserveData: true });
  assert.equal(status.textContent, '更新失败');
  assert.equal(list.children, previousChildren);
  showDashboardV2InfoDrawerError({ preserveData: false });
  assert.match(allText(list), /故障数据加载失败/);
});


test('information drawer identifies simulated fault data', () => {
  const status = new FakeElement();
  const list = new FakeElement();
  const elements = {
    'dashboard-v2-info-update-status': status,
    'dashboard-v2-info-fault-list': list,
    'dashboard-v2-info-fault-count': new FakeElement(),
    'dashboard-v2-info-total-faults': new FakeElement(),
    'dashboard-v2-info-processing-faults': new FakeElement(),
    'dashboard-v2-info-today-faults': new FakeElement(),
    'dashboard-v2-info-business-interruptions': new FakeElement(),
  };
  globalThis.document = {
    getElementById: (id) => elements[id] || null,
    createElement: (tagName) => new FakeElement(tagName),
  };

  renderDashboardV2InfoDrawer({
    simulated: true,
    summary: { processing_faults: 5 },
    processing_faults: [],
  });

  assert.equal(status.textContent, '模拟数据 · 5 条处理中');
});
