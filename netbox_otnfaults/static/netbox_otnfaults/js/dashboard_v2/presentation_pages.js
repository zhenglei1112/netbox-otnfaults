// Pure allocation and page selection; the tour is the only playback clock.
export function pageRangeLabel(total, start, capacity) {
  return total <= capacity ? `共${total}条` : `${start + 1}–${Math.min(start + capacity, total)} / 共${total}条`;
}
export function allocatePageSlots(counts, available, cardHeight, gap) {
  const minimum = counts.filter(Boolean).length;
  const capacity = Math.max(minimum, Math.min(6, Math.floor((available + gap * minimum) / (cardHeight + gap))));
  const slots = counts.map((count) => count ? 1 : 0);
  while (slots.reduce((a, b) => a + b, 0) < capacity) {
    const candidates = counts.map((count, i) => i).filter((i) => slots[i] < counts[i]);
    if (!candidates.length) break;
    candidates.sort((a, b) => slots[a] - slots[b] || a - b);
    slots[candidates[0]]++;
  }
  return slots;
}

export function eventPage(ids, capacity, previous, activeId) {
  if (!ids.length || !capacity) return 0;
  const index = ids.indexOf(activeId);
  return index >= 0 ? Math.floor(index / capacity) : Math.min(previous, Math.ceil(ids.length / capacity) - 1);
}

export function createPresentationPages({ lists, content, scale, reduced }) {
  const pages = new Map();
  const animations = new Map();
  const countFor = (list) => document.getElementById(list.id.replace('-list', '-count'));
  function update(activeId, reset = false) {
    const panels = lists();
    if (!content) return;
    const cards = panels.map((list) => [...list.querySelectorAll('[data-event-id]')]);
    const fixed = [...content.children].filter((node) => !panels.includes(node)).reduce((sum, node) => {
      const style = getComputedStyle(node);
      const listHeight = panels.filter((list) => node.contains?.(list))
        .reduce((height, list) => height + list.getBoundingClientRect().height, 0);
      return sum + node.getBoundingClientRect().height - listHeight + parseFloat(style.marginTop || 0) + parseFloat(style.marginBottom || 0);
    }, 0);
    const style = getComputedStyle(content);
    const emptyHeight = 30 * scale();
    // Capacity comes from the viewport limit, never the current content height:
    // a short page must not permanently reduce capacity after new data arrives.
    const maximumHeight = parseFloat(style.maxHeight) || content.clientHeight;
    const available = maximumHeight - fixed - parseFloat(style.paddingTop || 0) - parseFloat(style.paddingBottom || 0)
      - parseFloat(style.borderTopWidth || 0) - parseFloat(style.borderBottomWidth || 0)
      - cards.filter((group) => !group.length).length * emptyHeight;
    const height = 114 * scale();
    const gap = 6 * scale();
    const slots = allocatePageSlots(cards.map((group) => group.length), available, height, gap);
    panels.forEach((list, i) => {
      const previous = pages.get(list) || 0;
      const page = eventPage(cards[i].map((card) => card.dataset.eventId), slots[i], reset ? 0 : previous, activeId);
      pages.set(list, page);
      const start = page * slots[i];
      cards[i].forEach((card, index) => {
        card.dataset.presentationHidden = String(index < start || index >= start + slots[i]);
      });
      const visibleCount = Math.min(slots[i], cards[i].length - start);
      list.style.height = `${cards[i].length ? Math.max(0, visibleCount * (height + gap) - gap) : emptyHeight}px`;
      list.scrollTop = 0;
      list.dataset.presentationRange = pageRangeLabel(cards[i].length, start, slots[i]);
      const count = countFor(list);
      if (count) count.dataset.presentationRange = list.dataset.presentationRange;
      if (page !== previous) {
        animations.get(list)?.cancel();
        if (!reduced()) animations.set(list, list.animate?.([{ opacity: .3 }, { opacity: 1 }], { duration: 180 }));
      }
    });
  }
  function clear() {
    animations.forEach((animation) => animation?.cancel()); animations.clear(); pages.clear();
    lists().forEach((list) => {
      list.style.height = ''; list.scrollTop = 0;
      list.querySelectorAll('[data-event-id]').forEach((card) => { delete card.dataset.presentationHidden; });
      const count = countFor(list);
      if (count) delete count.dataset.presentationRange;
    });
  }
  return { update, clear };
}
