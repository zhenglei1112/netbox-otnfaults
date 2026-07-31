(() => {
  if (window.otnCalendarNavigationInitialized) {
    return;
  }
  window.otnCalendarNavigationInitialized = true;

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-calendar-nav-url]');
    if (!button || button.disabled) {
      return;
    }

    const widget = button.closest('[data-calendar-widget]');
    if (!widget) {
      return;
    }

    button.disabled = true;
    const buttons = widget.querySelectorAll('[data-calendar-nav-url]');
    buttons.forEach((item) => {
      item.disabled = true;
    });

    try {
      const response = await fetch(button.dataset.calendarNavUrl, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!response.ok) {
        throw new Error(`Calendar request failed with ${response.status}`);
      }

      const template = document.createElement('template');
      template.innerHTML = (await response.text()).trim();
      const replacement = template.content.querySelector('[data-calendar-widget]');
      if (!replacement || !replacement.hasAttribute('data-calendar-widget')) {
        throw new Error('Calendar response did not contain a widget');
      }
      widget.replaceWith(replacement);
    } catch (error) {
      buttons.forEach((item) => {
        item.disabled = false;
      });
      console.error(error);
    }
  });
})();
