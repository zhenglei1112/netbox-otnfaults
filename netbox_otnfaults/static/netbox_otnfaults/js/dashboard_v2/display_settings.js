export function applyDisplayModes(items, modes) {
  return items.map((item) => ({ ...item, mapDisplayMode: modes[item.kind === 'cutover' ? 'cutover' : 'fault'] || 'full' }));
}

export function initializeDisplaySettings(onChange) {
  const modes = { fault: 'full', cutover: 'full' };
  const disposers = [];
  const listen = (target, event, handler) => {
    target.addEventListener(event, handler);
    disposers.push(() => target.removeEventListener(event, handler));
  };
  for (const kind of ['fault', 'cutover']) {
    const button = document.getElementById(`dashboard-v2-${kind}-display`);
    if (!button) continue;
    const name = kind === 'fault' ? '故障' : '割接';
    const labels = { full: '显示', points: `只显示${name}点`, hidden: '不显示' };
    const update = () => {
      button.dataset.mode = modes[kind];
      button.setAttribute('aria-label', `${name} ${labels[modes[kind]]}，点击切换`);
      const status = document.getElementById(`dashboard-v2-${kind}-display-status`);
      if (status) status.textContent = `${name} ${labels[modes[kind]]}`;
    };
    update();
    listen(button, 'click', () => {
      const states = ['full', 'points', 'hidden'];
      modes[kind] = states[(states.indexOf(modes[kind]) + 1) % states.length];
      update();
      onChange({ ...modes });
    });
  }
  return { destroy() { disposers.forEach((dispose) => dispose()); } };
}
