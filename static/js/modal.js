// Keyboard buat modal aksi (dikirim HTMX ke #modal-slot):
// fokus pindah ke dalam modal, Tab berputar di dalamnya, Esc menutup, fokus balik ke tombol pemicu.
(function () {
  var FOKUS = 'a[href], button:not([disabled]), input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])';
  var pemicu = null;
  var modalAktif = null;

  function tutup() {
    if (modalAktif) modalAktif.remove();
  }

  function buka(modal) {
    modalAktif = modal;
    var dalam = modal.querySelectorAll(FOKUS);
    if (dalam.length) dalam[0].focus();
    // Fokus balik ke pemicu pas modal hilang (Batal, klik luar, Esc, atau submit sukses)
    new MutationObserver(function (_, obs) {
      if (!document.contains(modal)) {
        obs.disconnect();
        modalAktif = null;
        if (pemicu && document.contains(pemicu)) pemicu.focus();
      }
    }).observe(document.body, { childList: true, subtree: true });
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest('[hx-target="#modal-slot"]');
    if (a) pemicu = a;
  });

  document.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target && e.detail.target.id === 'modal-slot') {
      var modal = e.detail.target.querySelector('.modal');
      if (modal) buka(modal);
    }
  });

  document.addEventListener('keydown', function (e) {
    if (!modalAktif) return;
    if (e.key === 'Escape') { e.preventDefault(); tutup(); return; }
    if (e.key !== 'Tab') return;
    var dalam = modalAktif.querySelectorAll(FOKUS);
    if (!dalam.length) return;
    var awal = dalam[0], akhir = dalam[dalam.length - 1];
    if (e.shiftKey && document.activeElement === awal) { e.preventDefault(); akhir.focus(); }
    else if (!e.shiftKey && document.activeElement === akhir) { e.preventDefault(); awal.focus(); }
  });
})();
