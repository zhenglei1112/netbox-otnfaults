export const PROCESSING_FAULT_CALLOUT_WIDTH = 220;
export const PROCESSING_FAULT_CALLOUT_HEIGHT = 88;
const PROCESSING_FAULT_LAYOUT_PADDING = 12;
export const PROCESSING_FAULT_LAYOUT_GAP = 10;

export function expandRect(rect, gap) {
  return {
    left: rect.left - gap,
    top: rect.top - gap,
    right: rect.right + gap,
    bottom: rect.bottom + gap,
  };
}

export function leaderSegment(point, rect, startRadius = 14) {
  const end = {
    x: Math.max(rect.left, Math.min(point.x, rect.right)),
    y: Math.max(rect.top, Math.min(point.y, rect.bottom)),
  };
  const length = Math.hypot(end.x - point.x, end.y - point.y);
  const ratio = length > startRadius ? startRadius / length : 1;
  return { start: { x: point.x + (end.x - point.x) * ratio, y: point.y + (end.y - point.y) * ratio }, end };
}

export function segmentsIntersect(a, b) {
  const cross = (p, q, r) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
  const on = (p, q, r) => Math.abs(cross(p, q, r)) < 1e-6
    && r.x >= Math.min(p.x, q.x) - 1e-6 && r.x <= Math.max(p.x, q.x) + 1e-6
    && r.y >= Math.min(p.y, q.y) - 1e-6 && r.y <= Math.max(p.y, q.y) + 1e-6;
  return (cross(a.start, a.end, b.start) * cross(a.start, a.end, b.end) < 0
    && cross(b.start, b.end, a.start) * cross(b.start, b.end, a.end) < 0)
    || on(a.start, a.end, b.start) || on(a.start, a.end, b.end)
    || on(b.start, b.end, a.start) || on(b.start, b.end, a.end);
}

function crossesRect(segment, rect) {
  const corners = [{ x: rect.left, y: rect.top }, { x: rect.right, y: rect.top },
    { x: rect.right, y: rect.bottom }, { x: rect.left, y: rect.bottom }];
  return corners.some((start, i) => segmentsIntersect(segment, { start, end: corners[(i + 1) % 4] }));
}

function overlapArea(first, second) {
  const width = Math.max(0, Math.min(first.right, second.right) - Math.max(first.left, second.left));
  const height = Math.max(0, Math.min(first.bottom, second.bottom) - Math.max(first.top, second.top));
  return width * height;
}

function candidateOffset(direction, tier, boxWidth, boxHeight, scale) {
  const sideGap = tier === 0 ? 88 : 168;
  const verticalGap = tier === 0 ? 56 : 126;
  const diagonalX = tier === 0 ? 76 : 138;
  const diagonalY = tier === 0 ? 34 : 96;
  const halfWidth = boxWidth / 2;
  const halfHeight = boxHeight / 2;
  const offsets = {
    e: [sideGap * scale, -halfHeight],
    w: [-sideGap * scale - boxWidth, -halfHeight],
    ne: [diagonalX * scale, -boxHeight - diagonalY * scale],
    nw: [-diagonalX * scale - boxWidth, -boxHeight - diagonalY * scale],
    se: [diagonalX * scale, diagonalY * scale],
    sw: [-diagonalX * scale - boxWidth, diagonalY * scale],
    n: [-halfWidth, -boxHeight - verticalGap * scale],
    s: [-halfWidth, verticalGap * scale],
  };
  return offsets[direction];
}

function placementDirections(point, width, height) {
  const horizontal = point.x <= width / 2 ? ['e', 'w'] : ['w', 'e'];
  const vertical = point.y <= height / 2 ? ['s', 'n'] : ['n', 's'];
  const diagonal = (verticalDirection, horizontalDirection) => `${verticalDirection}${horizontalDirection}`;
  return [
    horizontal[0],
    diagonal(vertical[0], horizontal[0]),
    vertical[0],
    diagonal(vertical[1], horizontal[0]),
    horizontal[1],
    diagonal(vertical[0], horizontal[1]),
    vertical[1],
    diagonal(vertical[1], horizontal[1]),
  ];
}

export function buildPlacementCandidates(point, width, height, box = {}) {
  const boxWidth = box.width || PROCESSING_FAULT_CALLOUT_WIDTH;
  const boxHeight = box.height || PROCESSING_FAULT_CALLOUT_HEIGHT;
  const directions = placementDirections(point, width, height);
  return [0, 1].flatMap((tier) => directions.map((direction, rank) => {
    const [x, y] = candidateOffset(direction, tier, boxWidth, boxHeight, box.scale || 1);
    return {
      direction,
      tier,
      rank: rank + (tier * directions.length),
      x,
      y,
      rect: {
        left: point.x + x,
        top: point.y + y,
        right: point.x + x + boxWidth,
        bottom: point.y + y + boxHeight,
      },
    };
  }));
}


export function scorePlacement(candidate, context, previous) {
  const { width, height, placedRects, radarRects, reservedRects } = context;
  const rect = candidate.rect;
  const overflow = Math.max(0, PROCESSING_FAULT_LAYOUT_PADDING - rect.left)
    + Math.max(0, PROCESSING_FAULT_LAYOUT_PADDING - rect.top)
    + Math.max(0, rect.right - width + PROCESSING_FAULT_LAYOUT_PADDING)
    + Math.max(0, rect.bottom - height + PROCESSING_FAULT_LAYOUT_PADDING);
  let score = overflow * 1000000;
  if (candidate.leader) {
    // Crossings outweigh network-density and direction preferences, but not severe overflow.
    for (const leader of context.placedLeaders || []) {
      if (segmentsIntersect(candidate.leader, leader)) score += 50000000;
      if (crossesRect(leader, rect)) score += 50000000;
    }
    for (const placed of [...placedRects, ...reservedRects]) {
      if (crossesRect(candidate.leader, placed)) score += 50000000;
    }
  }
  placedRects.forEach((placed) => {
    score += overlapArea(expandRect(rect, PROCESSING_FAULT_LAYOUT_GAP), placed) * 10000;
  });
  reservedRects.forEach((reserved) => {
    score += overlapArea(expandRect(rect, PROCESSING_FAULT_LAYOUT_GAP), reserved) * 12000;
  });
  radarRects.forEach((radar) => {
    score += overlapArea(expandRect(rect, 5), radar) * 5000;
  });
  score += candidate.rank * 20;
  score += Math.hypot(candidate.x, candidate.y) * 0.2;
  if (previous) {
    if (previous.direction !== candidate.direction) score += 2400;
    if (previous.tier !== candidate.tier) score += 600;
  }
  return score;
}
