// Navbar dapet garis tipis dan bayangan setelah halaman di-scroll.
// Di landing (data-overlay) navbar transparan di atas hero, baru jadi solid setelah hero lewat
const header = document.getElementById('site-header');
if (header) {
  const overlay = header.hasAttribute('data-overlay');
  const onScroll = () => {
    header.classList.toggle('is-scrolled', window.scrollY > 8);
    if (overlay) header.classList.toggle('is-solid', window.scrollY > window.innerHeight - 90);
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
}

// Elemen .reveal muncul sekali pas masuk layar. Selama user belum scroll sama sekali,
// isi di bawah layar pertama sengaja disembunyiin, baru muncul (dengan animasi) pas mulai scroll
const revealItems = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
  // Kalau halaman dibuka di tengah (misalnya lewat link #katalog), langsung dianggap sudah scroll
  let started = window.scrollY > 4;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && started) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -6% 0px' }
  );
  revealItems.forEach((el) => observer.observe(el));

  if (!started) {
    const start = () => {
      started = true;
      window.removeEventListener('scroll', start);
      // Observe ulang supaya yang sudah kelihatan di layar langsung dihitung
      revealItems.forEach((el) => {
        observer.unobserve(el);
        observer.observe(el);
      });
    };
    window.addEventListener('scroll', start, { passive: true });
  }
} else {
  revealItems.forEach((el) => el.classList.add('is-visible'));
}
