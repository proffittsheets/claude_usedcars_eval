(function () {
  var carousel = document.getElementById('featured-carousel');
  if (!carousel) return;

  var track = document.getElementById('carousel-track');
  var dots = document.querySelectorAll('.carousel-dot');
  var slides = track.querySelectorAll('.carousel-slide');
  var total = slides.length;
  if (total === 0) return;

  var current = 0;
  var autoTimer = null;
  var INTERVAL = 4500;

  function goTo(idx) {
    current = (idx + total) % total;
    track.style.transform = 'translateX(-' + (current * 100) + '%)';
    dots.forEach(function (d, i) {
      d.classList.toggle('carousel-dot-active', i === current);
    });
  }

  function startAuto() {
    stopAuto();
    autoTimer = setInterval(function () { goTo(current + 1); }, INTERVAL);
  }

  function stopAuto() {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
  }

  carousel.querySelector('.carousel-prev').addEventListener('click', function (e) {
    e.preventDefault();
    goTo(current - 1);
    startAuto();
  });

  carousel.querySelector('.carousel-next').addEventListener('click', function (e) {
    e.preventDefault();
    goTo(current + 1);
    startAuto();
  });

  dots.forEach(function (dot) {
    dot.addEventListener('click', function (e) {
      e.preventDefault();
      goTo(parseInt(dot.dataset.index, 10));
      startAuto();
    });
  });

  carousel.addEventListener('mouseenter', stopAuto);
  carousel.addEventListener('mouseleave', startAuto);

  // Touch/swipe support
  var touchStartX = 0;
  carousel.addEventListener('touchstart', function (e) {
    touchStartX = e.touches[0].clientX;
    stopAuto();
  }, { passive: true });
  carousel.addEventListener('touchend', function (e) {
    var dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 40) goTo(dx < 0 ? current + 1 : current - 1);
    startAuto();
  }, { passive: true });

  startAuto();
}());
