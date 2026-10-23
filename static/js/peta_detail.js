(function () {
  'use strict';

  const element = document.getElementById('peta-detail');
  if (!element || typeof L === 'undefined') {
    return;
  }

  const lat = Number.parseFloat(element.dataset.lat);
  const lng = Number.parseFloat(element.dataset.lng);

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return;
  }

  const map = L.map(element, { scrollWheelZoom: false }).setView([lat, lng], 16);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  L.marker([lat, lng]).addTo(map);

  window.setTimeout(function () {
    map.invalidateSize();
  }, 100);
})();
