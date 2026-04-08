(function () {
  var html = document.documentElement;
  var btn = document.getElementById('theme-toggle');

  function getPreferred() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function apply(theme) {
    html.setAttribute('data-theme', theme);
    if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
    try { localStorage.setItem('theme', theme); } catch (e) {}
  }

  // On load: use saved preference, fall back to OS preference
  var saved = null;
  try { saved = localStorage.getItem('theme'); } catch (e) {}
  apply(saved || getPreferred());

  if (btn) {
    btn.addEventListener('click', function () {
      apply(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  }
}());
