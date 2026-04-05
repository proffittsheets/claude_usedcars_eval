/**
 * Accordion/dropdown for car detail pages.
 * Toggles the hidden attribute on accordion panels.
 */
(function () {
  'use strict';

  document.querySelectorAll('.accordion-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var expanded = btn.getAttribute('aria-expanded') === 'true';
      var panelId  = btn.getAttribute('aria-controls');
      var panel    = panelId ? document.getElementById(panelId) : null;
      var icon     = btn.querySelector('.accordion-icon');

      btn.setAttribute('aria-expanded', !expanded);
      if (panel) {
        if (expanded) {
          panel.hidden = true;
        } else {
          panel.hidden = false;
        }
      }
      if (icon) icon.textContent = expanded ? '\u002B' : '\u2212';
    });
  });
})();
