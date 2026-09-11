import { leaderSegment, segmentsIntersect, expandRect } from './fault_layout.js?v=20260911-peripheral-v1';

function overlap(a, b) {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}
function crossesBox(line, box) {
  const corners = [{ x: box.left, y: box.top }, { x: box.right, y: box.top },
    { x: box.right, y: box.bottom }, { x: box.left, y: box.bottom }];
  const inside = (p) => p.x > box.left && p.x < box.right && p.y > box.top && p.y < box.bottom;
  return inside(line.start) || inside(line.end) || corners.some((start, i) =>
    segmentsIntersect(line, { start, end: corners[(i + 1) % 4] }));
}
export function peripheralCompatible(a, b) {
  return !overlap(expandRect(a.rect, 10), b.rect)
    && !segmentsIntersect(a.leader, b.leader)
    && !crossesBox(a.leader, b.rect) && !crossesBox(b.leader, a.rect);
}

// A bounded joint assignment, not a per-label weighted crossing penalty.
export function solvePeripheralLayout(entries, { width, height, reservedRects = [], radarRects = [], presentationScale = 0 }, budget = 2000) {
  if (!entries.length) return new Map();
  const cx = entries.reduce((sum, e) => sum + e.point.x, 0) / entries.length;
  const cy = entries.reduce((sum, e) => sum + e.point.y, 0) / entries.length;
  const scale = presentationScale || 1;
  const inset = Math.min(48 * scale, Math.min(width, height) * .08);
  const candidates = entries.map((entry) => {
    const { point, boxWidth: w, boxHeight: h, radius = 14 } = entry;
    const result = [];
    const add = (left, top, direction, ux, uy) => {
      const rect = { left, top, right: left + w, bottom: top + h };
      if (left < inset || top < inset || rect.right > width - inset || rect.bottom > height - inset) return;
      if ((direction === 'w' && rect.right >= point.x - radius)
        || (direction === 'e' && rect.left <= point.x + radius)
        || (direction === 'n' && rect.bottom >= point.y - radius)
        || (direction === 's' && rect.top <= point.y + radius)) return;
      if ([...reservedRects, ...radarRects].some((r) => overlap(expandRect(rect, 8), r))) return;
      const leader = leaderSegment(point, rect, radius);
      if (reservedRects.some((r) => crossesBox(leader, r))) return;
      const radialLength = Math.hypot(point.x - cx, point.y - cy);
      const alignment = radialLength ? (ux * (point.x - cx) + uy * (point.y - cy)) / radialLength : 1;
      if (alignment < -.15) return;
      const axialPenalty = direction.length === 1 ? (presentationScale ? 100 : 45) * scale : 0;
      result.push({ rect, leader, leaderRadius: radius, direction, tier: 2, x: left - point.x, y: top - point.y,
        cost: Math.hypot(leader.end.x - point.x, leader.end.y - point.y) + (1 - alignment) * 120 * scale + axialPenalty });
    };
    // Offset from each point, not the window perimeter. Diagonal leaders connect
    // to a corner with a short, deliberate gap; no rigid rows or edge rails.
    for (const distance of [72, 120, 184, 260]) {
      for (const degrees of [30, 45, 60, 120, 135, 150, 210, 225, 240, 300, 315, 330, 0, 90, 180, 270]) {
        const radians = degrees * Math.PI / 180;
        const ux = Math.abs(Math.cos(radians)) < 1e-6 ? 0 : Math.cos(radians);
        const uy = Math.abs(Math.sin(radians)) < 1e-6 ? 0 : Math.sin(radians);
        const direction = `${uy < 0 ? 'n' : uy > 0 ? 's' : ''}${ux < 0 ? 'w' : ux > 0 ? 'e' : ''}`;
        const left = point.x + ux * distance * scale + (ux < 0 ? -w : ux > 0 ? 0 : -w / 2);
        const top = point.y + uy * distance * scale + (uy < 0 ? -h : uy > 0 ? 0 : -h / 2);
        add(left, top, direction, ux, uy);
      }
    }
    return result.sort((a, b) => a.cost - b.cost).slice(0, 32);
  });
  const chosen = new Map();
  let remaining = budget;
  const search = () => {
    if (chosen.size === entries.length) return true;
    if (--remaining < 0) return false;
    // Most constrained label first; stable order resolves ties.
    let index = -1; let options;
    for (let i = 0; i < entries.length; i++) {
      if (chosen.has(i)) continue;
      const valid = candidates[i].filter((c) => [...chosen.values()].every((other) => peripheralCompatible(c, other)));
      if (!valid.length) return false;
      if (!options || valid.length < options.length) { index = i; options = valid; }
    }
    for (const candidate of options) {
      chosen.set(index, candidate);
      if (search()) return true;
      chosen.delete(index);
      if (remaining < 0) break;
    }
    return false;
  };
  if (!search()) return null;
  return new Map([...chosen].map(([i, candidate]) => [entries[i].faultId, candidate]));
}
