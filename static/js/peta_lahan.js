(function () {
  'use strict';

  const root = document.querySelector('[data-peta-lokasi]');
  const mapElement = document.getElementById('peta-lahan');

  if (!root || !mapElement || typeof L === 'undefined') {
    return;
  }

  const searchInput = document.getElementById('lokasi-search');
  const searchButton = document.getElementById('lokasi-search-btn');
  const resultsBox = document.getElementById('lokasi-results');
  const statusBox = document.getElementById('lokasi-status');
  const locationButton = document.getElementById('pakai-lokasi');
  const addressInput = document.getElementById('id_alamat');
  const latitudeInput = document.getElementById('id_latitude');
  const longitudeInput = document.getElementById('id_longitude');

  let marker = null;
  let searchTimer = null;
  let searchController = null;
  let reverseToken = 0;

  function parseCoordinate(value) {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    const number = Number.parseFloat(value);
    return Number.isFinite(number) ? number : null;
  }

  function isValidCoordinate(lat, lng) {
    return lat !== null && lng !== null && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
  }

  function setStatus(message, tone) {
    if (!statusBox) {
      return;
    }
    statusBox.textContent = message;
    statusBox.classList.remove('text-ink-soft', 'text-moss', 'text-brick');
    statusBox.classList.add(tone === 'ok' ? 'text-moss' : tone === 'error' ? 'text-brick' : 'text-ink-soft');
  }

  const initialLat = parseCoordinate(root.dataset.lat);
  const initialLng = parseCoordinate(root.dataset.lng);
  const hasInitialPoint = isValidCoordinate(initialLat, initialLng);
  const initialCenter = hasInitialPoint ? [initialLat, initialLng] : [-2.5, 118];

  const map = L.map(mapElement, { scrollWheelZoom: true })
    .setView(initialCenter, hasInitialPoint ? 16 : 5);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  function updateCoordinateInputs(lat, lng) {
    if (latitudeInput) {
      latitudeInput.value = lat.toFixed(6);
    }
    if (longitudeInput) {
      longitudeInput.value = lng.toFixed(6);
    }
  }

  function focusPoint(lat, lng) {
    const zoom = map.getZoom() < 14 ? 16 : map.getZoom();
    map.setView([lat, lng], zoom);
  }

  function placeMarker(lat, lng, withReverse) {
    if (!isValidCoordinate(lat, lng)) {
      setStatus('Koordinat tidak valid.', 'error');
      return;
    }

    if (!marker) {
      marker = L.marker([lat, lng], { draggable: true }).addTo(map);
      marker.on('dragend', function () {
        const position = marker.getLatLng();
        updateCoordinateInputs(position.lat, position.lng);
        reverseGeocode(position.lat, position.lng);
      });
    } else {
      marker.setLatLng([lat, lng]);
    }

    focusPoint(lat, lng);
    updateCoordinateInputs(lat, lng);

    if (withReverse) {
      reverseGeocode(lat, lng);
    }
  }

  function hideResults() {
    if (resultsBox) {
      resultsBox.classList.add('hidden');
      resultsBox.innerHTML = '';
    }
  }

  function renderResults(items) {
    if (!resultsBox) {
      return;
    }

    resultsBox.innerHTML = '';
    resultsBox.classList.remove('hidden');

    if (!items.length) {
      const empty = document.createElement('p');
      empty.className = 'lokasi-empty';
      empty.textContent = 'Lokasi tidak ditemukan. Coba kata kunci lain.';
      resultsBox.appendChild(empty);
      return;
    }

    items.forEach(function (item) {
      const lat = parseCoordinate(item.lat);
      const lng = parseCoordinate(item.lon);
      if (!isValidCoordinate(lat, lng)) {
        return;
      }

      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'lokasi-result';

      const title = document.createElement('strong');
      title.textContent = item.display_name || 'Lokasi tanpa nama';

      const detail = document.createElement('span');
      detail.textContent = item.type ? 'Titik ' + item.type : 'Pilih lokasi ini';

      button.appendChild(title);
      button.appendChild(detail);
      button.addEventListener('click', function () {
        hideResults();
        if (addressInput) {
          addressInput.value = item.display_name || '';
        }
        placeMarker(lat, lng, false);
        setStatus('Lokasi dipilih. Geser penanda bila titiknya kurang tepat.', 'ok');
      });

      resultsBox.appendChild(button);
    });
  }

  async function searchLocation(query) {
    const keyword = query.trim();
    if (keyword.length < 3) {
      setStatus('Kata kunci minimal 3 karakter.', 'error');
      hideResults();
      return;
    }

    if (searchController) {
      searchController.abort();
    }
    const controller = new AbortController();
    searchController = controller;

    if (searchButton) {
      searchButton.disabled = true;
    }
    setStatus('Mencari lokasi...', '');

    try {
      const response = await fetch(
        root.dataset.cariUrl + '?q=' + encodeURIComponent(keyword),
        {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          signal: controller.signal,
        }
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Pencarian lokasi gagal.');
      }
      if (!Array.isArray(data)) {
        throw new Error('Format hasil pencarian tidak dikenal.');
      }

      renderResults(data);
      setStatus(data.length ? 'Pilih salah satu hasil pencarian.' : 'Lokasi tidak ditemukan.', data.length ? '' : 'error');
    } catch (error) {
      if (error.name === 'AbortError') {
        return;
      }
      hideResults();
      setStatus(error.message || 'Layanan pencarian lokasi sedang tidak tersedia.', 'error');
    } finally {
      if (searchButton && searchController === controller) {
        searchButton.disabled = false;
      }
    }
  }

  async function reverseGeocode(lat, lng) {
    const token = ++reverseToken;
    setStatus('Mencari alamat untuk titik ini...', '');

    try {
      const response = await fetch(
        root.dataset.reverseUrl + '?lat=' + encodeURIComponent(lat) + '&lon=' + encodeURIComponent(lng),
        { headers: { 'X-Requested-With': 'XMLHttpRequest' } }
      );
      const data = await response.json();

      if (token !== reverseToken) {
        return;
      }
      if (!response.ok) {
        throw new Error(data.error || 'Alamat tidak ditemukan.');
      }

      if (addressInput && data.display_name) {
        addressInput.value = data.display_name;
      }
      setStatus('Koordinat dan alamat sudah terisi.', 'ok');
    } catch (error) {
      if (token !== reverseToken) {
        return;
      }
      setStatus('Koordinat tersimpan, tetapi alamat gagal diambil. Isi alamat manual bila perlu.', 'error');
    }
  }

  if (hasInitialPoint) {
    placeMarker(initialLat, initialLng, false);
    setStatus('Lokasi tersimpan. Geser penanda bila perlu diperbarui.', '');
  }

  map.on('click', function (event) {
    placeMarker(event.latlng.lat, event.latlng.lng, true);
  });

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      window.clearTimeout(searchTimer);
      const keyword = searchInput.value.trim();

      if (keyword.length < 3) {
        hideResults();
        return;
      }

      searchTimer = window.setTimeout(function () {
        searchLocation(keyword);
      }, 600);
    });

    searchInput.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') {
        event.preventDefault();
        window.clearTimeout(searchTimer);
        searchLocation(searchInput.value);
      }
    });
  }

  if (searchButton) {
    searchButton.addEventListener('click', function () {
      searchLocation(searchInput ? searchInput.value : '');
    });
  }

  if (locationButton) {
    locationButton.addEventListener('click', function () {
      if (!navigator.geolocation) {
        setStatus('Browser ini tidak mendukung lokasi otomatis.', 'error');
        return;
      }

      setStatus('Mengambil lokasi perangkat...', '');
      navigator.geolocation.getCurrentPosition(
        function (position) {
          placeMarker(position.coords.latitude, position.coords.longitude, true);
        },
        function (error) {
          const messages = {
            1: 'Izin lokasi ditolak. Aktifkan izin lokasi di browser.',
            2: 'Lokasi perangkat tidak tersedia.',
            3: 'Pengambilan lokasi terlalu lama. Coba lagi.',
          };
          setStatus(messages[error.code] || 'Lokasi perangkat gagal diambil.', 'error');
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    });
  }

  window.setTimeout(function () {
    map.invalidateSize();
  }, 100);
})();
