// Form daftar: meter kekuatan password sama ngecek dua password-nya sama atau nggak.
(function () {
  const password = document.getElementById('id_password1');
  const confirm = document.getElementById('id_password2');
  const meter = document.getElementById('password-strength');
  const mismatch = document.getElementById('password-mismatch');
  if (!password || !confirm || !meter || !mismatch) return;

  // Skor 0-4: panjang, huruf+angka, huruf besar/simbol, panjang 12+
  function strength(value) {
    if (!value) return 0;
    let score = 0;
    if (value.length >= 8) score++;
    if (/[A-Za-z]/.test(value) && /\d/.test(value)) score++;
    if (/[A-Z]/.test(value) || /[^A-Za-z0-9]/.test(value)) score++;
    if (value.length >= 12) score++;
    return Math.max(score, 1);
  }

  function checkMatch() {
    const differs = confirm.value !== '' && confirm.value !== password.value;
    mismatch.hidden = !differs;
    confirm.classList.toggle('is-invalid', differs);
  }

  password.addEventListener('input', () => {
    meter.dataset.level = strength(password.value);
    checkMatch();
  });
  confirm.addEventListener('input', checkMatch);
})();
