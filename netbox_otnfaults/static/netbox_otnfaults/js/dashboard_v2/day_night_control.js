export function initializeDashboardV2DayNightControl(dayNight) {
  const button = document.getElementById('dashboard-v2-map-day-night');
  const status = document.getElementById('dashboard-v2-day-night-status');
  if (!button || !dayNight) return null;

  let enabled = dayNight.getEnabled?.() ?? true;
  const applyState = () => {
    const label = enabled ? '开启' : '关闭';
    dayNight.setEnabled?.(enabled);
    button.setAttribute('aria-pressed', String(enabled));
    button.title = `昼夜 ${label}`;
    button.setAttribute('aria-label', `昼夜 ${label}，点击切换`);
    if (status) status.textContent = `昼夜 ${label}`;
    return enabled;
  };

  applyState();
  const onClick = () => {
    enabled = !enabled;
    applyState();
  };
  button.addEventListener('click', onClick);
  return { getEnabled: () => enabled, destroy: () => button.removeEventListener('click', onClick) };
}
