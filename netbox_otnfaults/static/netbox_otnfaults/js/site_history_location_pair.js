(() => {
  const collator = new Intl.Collator('zh-CN-u-co-pinyin', { sensitivity: 'base' });
  document.querySelectorAll('[data-site-history-pair]').forEach((pair) => {
    const a = pair.querySelector('[data-endpoint="a"]');
    const z = pair.querySelector('[data-endpoint="z"]');
    const aLink = a.querySelector('a');
    const zLinks = z.querySelectorAll('a');
    if (aLink && zLinks.length === 1
        && collator.compare(aLink.textContent.trim(), zLinks[0].textContent.trim()) > 0) {
      // Move the endpoints with their links; keep the underlying A/Z data intact.
      pair.insertBefore(z, pair.firstChild);
      pair.appendChild(a);
    }
  });
})();
