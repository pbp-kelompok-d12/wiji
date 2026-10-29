// Interaksi khusus landing page: kalimat yang menyala kata demi kata, kata yang berganti, dan angka naik

const clamp01 = (n) => Math.min(1, Math.max(0, n));

// Kalimat besar: tiap kata menyala mengikuti scroll
const statement = document.getElementById('lp-statement');
if (statement) {
  // Teks dipecah per kata, elemen lain (foto pil) dibiarkan
  statement.innerHTML = [...statement.childNodes]
    .map((node) =>
      node.nodeType === 3
        ? node.textContent
            .split(/\s+/)
            .filter(Boolean)
            .map((w) => `<span class="w">${w}</span>`)
            .join(' ')
        : node.outerHTML
    )
    .join(' ');
  const words = [...statement.querySelectorAll('.w')];

  const paint = () => {
    const r = statement.getBoundingClientRect();
    const p = clamp01((innerHeight * 0.8 - r.top) / (r.height + innerHeight * 0.2));
    words.forEach((w, i) => w.classList.toggle('on', i / words.length < p));
  };
  addEventListener('scroll', paint, { passive: true });
  paint();
}

// Daftar kata: yang aktif ikut posisi scroll
const wordList = document.getElementById('lp-words');
if (wordList) {
  const items = [...wordList.children];
  const pick = () => {
    const box = wordList.getBoundingClientRect();
    const p = clamp01((innerHeight * 0.75 - box.top) / (box.height + innerHeight * 0.2));
    const now = Math.min(items.length - 1, Math.floor(p * items.length));
    items.forEach((el, i) => {
      el.className = i === now ? 'on' : Math.abs(i - now) === 1 ? 'near' : '';
    });
  };
  addEventListener('scroll', pick, { passive: true });
  pick();
}

// Angka menghitung naik sekali pas kelihatan
const counters = document.querySelectorAll('[data-count]');
if (counters.length && 'IntersectionObserver' in window) {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        io.unobserve(entry.target);
        const el = entry.target;
        const to = Number(el.dataset.count);
        const plus = el.hasAttribute('data-plus') ? '+' : '';
        if (reduce) {
          el.textContent = to + plus;
          return;
        }
        const t0 = performance.now();
        const tick = (t) => {
          const k = Math.min(1, (t - t0) / 1200);
          el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))) + (k === 1 ? plus : '');
          if (k < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
    },
    { threshold: 0.3 }
  );
  counters.forEach((el) => io.observe(el));
} else {
  counters.forEach((el) => (el.textContent = el.dataset.count + (el.hasAttribute('data-plus') ? '+' : '')));
}
