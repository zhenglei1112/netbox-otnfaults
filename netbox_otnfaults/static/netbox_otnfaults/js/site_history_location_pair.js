(() => {
  const collator = new Intl.Collator('zh-CN-u-co-pinyin', { sensitivity: 'base' });
  document.querySelectorAll('[data-site-history-pair]').forEach((pair) => {
    const a = pair.querySelector('[data-endpoint="a"]');
    const z = pair.querySelector('[data-endpoint="z"]');
    if (!a || !z) return;
    const aLink = a.querySelector('a');
    const zLinks = z.querySelectorAll('a');
    if (aLink && zLinks.length === 1
        && collator.compare(aLink.textContent.trim(), zLinks[0].textContent.trim()) > 0) {
      // Keep the displayed A/Z labels and colors in order while swapping links.
      a.appendChild(zLinks[0]);
      z.appendChild(aLink);
    }
  });
})();
