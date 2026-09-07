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

function overlapArea(first, second) {
  const width = Math.max(0, Math.min(first.right, second.right) - Math.max(first.left, second.left));
  const height = Math.max(0, Math.min(first.bottom, second.bottom) - Math.max(first.top, second.top));
  return width * height;
}

function candidateOffset(direction, tier) {
  const sideGap = tier === 0 ? 88 : 168;
  const verticalGap = tier === 0 ? 56 : 126;
  const diagonalX = tier === 0 ? 76 : 138;
  const diagonalY = tier === 0 ? 34 : 96;
  const halfWidth = PROCESSING_FAULT_CALLOUT_WIDTH / 2;
  const halfHeight = PROCESSING_FAULT_CALLOUT_HEIGHT / 2;
  const offsets = {
    e: [sideGap, -halfHeight],
    w: [-sideGap - PROCESSING_FAULT_CALLOUT_WIDTH, -halfHeight],
    ne: [diagonalX, -PROCESSING_FAULT_CALLOUT_HEIGHT - diagonalY],
    nw: [-diagonalX - PROCESSING_FAULT_CALLOUT_WIDTH, -PROCESSING_FAULT_CALLOUT_HEIGHT - diagonalY],
    se: [diagonalX, diagonalY],
    sw: [-diagonalX - PROCESSING_FAULT_CALLOUT_WIDTH, diagonalY],
    n: [-halfWidth, -PROCESSING_FAULT_CALLOUT_HEIGHT - verticalGap],
    s: [-halfWidth, verticalGap],
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

export function buildPlacementCandidates(point, width, height) {
  const directions = placementDirections(point, width, height);
  return [0, 1].flatMap((tier) => directions.map((direction, rank) => {
    const [x, y] = candidateOffset(direction, tier);
    return {
      direction,
      tier,
      rank: rank + (tier * directions.length),
      x,
      y,
      rect: {
        left: point.x + x,
        top: point.y + y,
        right: point.x + x + PROCESSING_FAULT_CALLOUT_WIDTH,
        bottom: point.y + y + PROCESSING_FAULT_CALLOUT_HEIGHT,
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

