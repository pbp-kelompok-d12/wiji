// Slider "Cara pakai": tombol panah, titik, klik langkah, panah keyboard, dan geser di layar sentuh
(function () {
  const sec = document.getElementById('langkah');
  if (!sec) return;

  const items = [...sec.querySelectorAll('.steps__item')];
  const dots = [...sec.querySelectorAll('.steps__dots button')];
  const prev = sec.querySelector('[data-dir="-1"]');
  const next = sec.querySelector('[data-dir="1"]');
  const stage = sec.querySelector('.steps__stage');
  const total = items.length;
  let current = 0;

  // Pindah ke langkah ke-k. --i dipakai CSS buat geser slide
  function go(k) {
    current = Math.max(0, Math.min(total - 1, k));
    sec.style.setProperty('--i', current);
    items.forEach((el, j) => el.classList.toggle('is-active', j === current));
    dots.forEach((el, j) => {
      el.classList.toggle('is-on', j === current);
      el.setAttribute('aria-current', j === current ? 'true' : 'false');
    });
    prev.disabled = current === 0;
    next.disabled = current === total - 1;
  }

  prev.addEventListener('click', () => go(current - 1));
  next.addEventListener('click', () => go(current + 1));
  items.forEach((el, j) => el.querySelector('button').addEventListener('click', () => go(j)));
  dots.forEach((el, j) => el.addEventListener('click', () => go(j)));

  sec.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') go(current + 1);
    if (e.key === 'ArrowLeft') go(current - 1);
  });

  // Geser jari ke kiri atau kanan di layar sentuh
  let startX = null;
  stage.addEventListener('pointerdown', (e) => { startX = e.clientX; });
  stage.addEventListener('pointerup', (e) => {
    if (startX === null) return;
    const dx = e.clientX - startX;
    startX = null;
    if (Math.abs(dx) > 50) go(current + (dx < 0 ? 1 : -1));
  });

  go(0);
})();
