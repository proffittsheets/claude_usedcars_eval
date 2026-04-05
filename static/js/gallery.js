/**
 * Lightbox gallery for car detail pages.
 * Opens clicked .gallery-thumb images in a fullscreen lightbox.
 * Supports keyboard navigation (arrows, Escape) and prev/next buttons.
 */
(function () {
  'use strict';

  const lightbox   = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightbox-img');
  const closeBtn   = document.getElementById('lightbox-close');
  const prevBtn    = document.getElementById('lightbox-prev');
  const nextBtn    = document.getElementById('lightbox-next');

  if (!lightbox) return;

  let currentThumbs = [];
  let currentIndex  = 0;

  function open(thumbs, index) {
    currentThumbs = thumbs;
    currentIndex  = index;
    lightboxImg.src = currentThumbs[currentIndex].dataset.full || currentThumbs[currentIndex].src;
    lightboxImg.alt = currentThumbs[currentIndex].alt;
    lightbox.classList.add('open');
    document.body.style.overflow = 'hidden';
    prevBtn.style.display = currentThumbs.length > 1 ? '' : 'none';
    nextBtn.style.display = currentThumbs.length > 1 ? '' : 'none';
    closeBtn.focus();
  }

  function close() {
    lightbox.classList.remove('open');
    document.body.style.overflow = '';
  }

  function navigate(delta) {
    currentIndex = (currentIndex + delta + currentThumbs.length) % currentThumbs.length;
    lightboxImg.src = currentThumbs[currentIndex].dataset.full || currentThumbs[currentIndex].src;
    lightboxImg.alt = currentThumbs[currentIndex].alt;
  }

  // Wire up gallery strips
  document.querySelectorAll('.gallery-scroll').forEach(function (strip) {
    var thumbs = Array.from(strip.querySelectorAll('.gallery-thumb'));
    thumbs.forEach(function (thumb, idx) {
      thumb.addEventListener('click', function () { open(thumbs, idx); });
    });
  });

  // Controls
  closeBtn.addEventListener('click', close);
  prevBtn.addEventListener('click', function () { navigate(-1); });
  nextBtn.addEventListener('click', function () { navigate(1); });

  // Click outside image to close
  lightbox.addEventListener('click', function (e) {
    if (e.target === lightbox) close();
  });

  // Keyboard
  document.addEventListener('keydown', function (e) {
    if (!lightbox.classList.contains('open')) return;
    if (e.key === 'Escape')      close();
    if (e.key === 'ArrowLeft')   navigate(-1);
    if (e.key === 'ArrowRight')  navigate(1);
  });
})();
