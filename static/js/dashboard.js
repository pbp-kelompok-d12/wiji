// Dashboard: laci sidebar di layar kecil, tab, dan grafik garis (data dari json_script di halaman)

// Buka dan tutup sidebar di layar kecil
const side = document.getElementById('side');
const backdrop = document.getElementById('side-backdrop');
const setSide = (open) => {
  if (!side) return;
  side.classList.toggle('is-open', open);
  if (backdrop) backdrop.classList.toggle('is-open', open);
};
document.querySelectorAll('[data-side-open]').forEach((el) => el.addEventListener('click', () => setSide(true)));
document.querySelectorAll('[data-side-close]').forEach((el) => el.addEventListener('click', () => setSide(false)));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setSide(false); });

// Tab grafik: sementara cuma ganti tampilan tabnya
document.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach((t) => t.classList.remove('is-on'));
  tab.classList.add('is-on');
}));

// Grafik area. Data: { labels, values, min, max, unit }
(function drawChart() {
  const svg = document.getElementById('chart');
  const dataEl = document.getElementById('chart-data');
  if (!svg || !dataEl) return;
  const { labels, values, min, max, unit } = JSON.parse(dataEl.textContent);

  const W = 640, H = 220, padL = 36, padR = 12, padT = 14, padB = 28;
  const x = (i) => padL + (i * (W - padL - padR)) / (values.length - 1);
  const y = (v) => padT + ((max - v) / (max - min)) * (H - padT - padB);
  const pts = values.map((v, i) => [x(i), y(v)]);

  // Garis dibuat melengkung halus (catmull-rom diubah ke bezier)
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0]},${c1[1]} ${c2[0]},${c2[1]} ${p2[0]},${p2[1]}`;
  }
  const area = `${d} L${pts[pts.length - 1][0]},${H - padB} L${pts[0][0]},${H - padB} Z`;

  let grid = '';
  for (let v = min; v <= max; v += 4) {
    grid += `<line x1="${padL}" x2="${W - padR}" y1="${y(v)}" y2="${y(v)}" stroke="#e2dccd" stroke-dasharray="3 4"/>`
          + `<text x="${padL - 8}" y="${y(v) + 3}" text-anchor="end" font-size="10" fill="#4f5a52">${v}${unit}</text>`;
  }
  const xl = labels.map((l, i) => `<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="10" fill="#4f5a52">${l}</text>`).join('');

  svg.innerHTML = `
    <defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f6b3f" stop-opacity=".28"/><stop offset="1" stop-color="#2f6b3f" stop-opacity="0"/></linearGradient></defs>
    ${grid}${xl}
    <path d="${area}" fill="url(#chart-fill)"/>
    <path d="${d}" fill="none" stroke="#2f6b3f" stroke-width="2.2" stroke-linecap="round"/>
    <line id="chart-line" x1="0" x2="0" y1="${padT}" y2="${H - padB}" stroke="#142019" stroke-opacity=".25" stroke-dasharray="3 3" opacity="0"/>
    <circle id="chart-dot" r="5" fill="#fff" stroke="#2f6b3f" stroke-width="2.5" opacity="0"/>`;

  const tip = document.getElementById('tip');
  const dot = svg.querySelector('#chart-dot');
  const line = svg.querySelector('#chart-line');
  svg.addEventListener('mousemove', (e) => {
    const box = svg.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * W;
    let nearest = 0, best = Infinity;
    pts.forEach((p, i) => { const dist = Math.abs(p[0] - px); if (dist < best) { best = dist; nearest = i; } });
    dot.setAttribute('cx', pts[nearest][0]); dot.setAttribute('cy', pts[nearest][1]); dot.setAttribute('opacity', 1);
    line.setAttribute('x1', pts[nearest][0]); line.setAttribute('x2', pts[nearest][0]); line.setAttribute('opacity', 1);
    tip.textContent = `${labels[nearest]} · ${values[nearest]}${unit}`;
    tip.style.left = (pts[nearest][0] / W) * box.width + 'px';
    tip.style.top = (pts[nearest][1] / H) * box.height + 'px';
    tip.style.opacity = 1;
  });
  svg.addEventListener('mouseleave', () => {
    tip.style.opacity = 0; dot.setAttribute('opacity', 0); line.setAttribute('opacity', 0);
  });
})();
