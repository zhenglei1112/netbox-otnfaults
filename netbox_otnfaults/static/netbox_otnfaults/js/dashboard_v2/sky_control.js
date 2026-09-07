const SKY_MODES = ['full', 'primary', 'off'];
const SKY_MODE_LABELS = {
  full: '开启',
  primary: '主星',
  off: '关闭',
};

export function initializeDashboardV2SkyControl(galaxy, starfield) {
  const button = document.getElementById('dashboard-v2-map-sky');
  const status = document.getElementById('dashboard-v2-sky-status');
  if (!button) return null;
  let modeIndex = 0;

  const applyMode = () => {
    const mode = SKY_MODES[modeIndex];
    const label = SKY_MODE_LABELS[mode];
    galaxy?.setVisible?.(mode === 'full');
    starfield?.setMode?.(mode);
    button.dataset.skyMode = mode;
    button.title = `天空 ${label}`;
    button.setAttribute('aria-label', `天空 ${label}，点击切换`);
    if (status) status.textContent = `天空 ${label}`;
    return mode;
  };

  applyMode();
  button.addEventListener('click', () => {
    modeIndex = (modeIndex + 1) % SKY_MODES.length;
    applyMode();
  });
  return { getMode: () => SKY_MODES[modeIndex] };
}
