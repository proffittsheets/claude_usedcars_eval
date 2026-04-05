/**
 * Client-side filtering for the car grid on the homepage.
 * Reads data-* attributes on .car-card elements and toggles .hidden class.
 */
(function () {
  'use strict';

  var grid    = document.getElementById('car-grid');
  var noResults = document.getElementById('no-results');
  var summary = document.getElementById('filter-summary');
  var clearBtn = document.getElementById('clear-filters');

  if (!grid) return;

  // Active filter state
  var filters = { make: '', tier: '', body: '', hybrid: false };

  function applyFilters() {
    var cards = grid.querySelectorAll('.car-card');
    var visible = 0;

    cards.forEach(function (card) {
      var makeOk   = !filters.make   || card.dataset.make  === filters.make;
      var tierOk   = !filters.tier   || card.dataset.tier  === filters.tier;
      var bodyOk   = !filters.body   || card.dataset.body  === filters.body;
      var hybridOk = !filters.hybrid || card.dataset.hybrid === 'true';

      var show = makeOk && tierOk && bodyOk && hybridOk;
      card.classList.toggle('hidden', !show);
      if (show) visible++;
    });

    if (noResults) noResults.style.display = visible === 0 ? '' : 'none';
    if (summary)   summary.textContent = visible + ' of ' + cards.length + ' vehicles';
  }

  // Filter pill groups
  document.querySelectorAll('.filter-pills').forEach(function (group) {
    var filterKey = group.dataset.filter;
    group.querySelectorAll('.pill').forEach(function (pill) {
      pill.addEventListener('click', function () {
        group.querySelectorAll('.pill').forEach(function (p) { p.classList.remove('pill-active'); });
        pill.classList.add('pill-active');
        filters[filterKey] = pill.dataset.value;
        applyFilters();
      });
    });
  });

  // Hybrid toggle
  var hybridCheckbox = document.getElementById('hybrid-only');
  if (hybridCheckbox) {
    hybridCheckbox.addEventListener('change', function () {
      filters.hybrid = hybridCheckbox.checked;
      applyFilters();
    });
  }

  // Clear all
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      filters = { make: '', tier: '', body: '', hybrid: false };
      if (hybridCheckbox) hybridCheckbox.checked = false;
      document.querySelectorAll('.pill').forEach(function (p) { p.classList.remove('pill-active'); });
      document.querySelectorAll('.filter-pills').forEach(function (group) {
        var first = group.querySelector('.pill');
        if (first) first.classList.add('pill-active');
      });
      applyFilters();
    });
  }

  // Initialize summary
  applyFilters();
})();
