// Adapt cutovers to the shared map layout while retaining their own semantic fields.
export function cutoverMapItems(tasks = []) {
  return tasks.map((task) => ({
    ...task,
    id: `cutover-${task.id}`,
    kind: 'cutover',
    fault_number: task.cutover_no,
    category_display: `${task.type_display || '割接'} · ${task.status_display || '未知状态'}`,
    category_color: task.status_color,
    duration: `${task.day === 'today' ? '今日' : '明日'} ${task.planned_time_display || ''}`,
  }));
}

export const CUTOVER_COLORS = {
  blue: '#0d6efd', orange: '#fd7e14', green: '#198754', red: '#dc3545', gray: '#6c757d',
};
