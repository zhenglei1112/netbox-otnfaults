// One status owner prevents map readiness from overwriting connection failures.
const states = new WeakMap();
export function updateDashboardStatus(patch) {
  const state = { mapState: 'loading', mapMessage: '地球初始化中...', dataState: 'loading', simulated: false,
    ...states.get(document), ...patch };
  states.set(document, state);
  const messages = [];
  if (state.mapState !== 'ready') messages.push(state.mapMessage);
  if (state.dataState === 'error') messages.push('数据断联');
  else if (state.dataState === 'online') messages.push('数据在线');
  else if (state.mapState === 'ready') messages.push('数据加载中...');
  if (state.simulated) messages.push('模拟数据');
  const text = document.getElementById('dashboard-v2-status-text');
  const dot = document.getElementById('dashboard-v2-status-dot');
  const message = messages.join(' · ');
  if (text) {
    if (text.textContent !== message) text.textContent = message;
    text.title = state.dataState === 'error' ? `${message}${state.dataError ? `：${state.dataError}` : ''}` : message;
  }
  dot?.classList.toggle('is-error', state.mapState === 'error' || state.dataState === 'error');
}
