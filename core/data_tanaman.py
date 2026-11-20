"""Data awal katalog tanaman (53 tanaman) beserta kontaminan dan referensinya.

Angka pH, tekstur, dan iklim adalah rentang umum untuk budidaya di Indonesia, diringkas dari
FAO EcoCrop, Petunjuk Teknis Evaluasi Lahan (BBSDLP, 2011), dan Agroforestree Database (ICRAF).
Ini data awal buat demo dan rekomendasi, bukan pengganti uji tanah atau saran ahli.

Kata di `fungsi` dan `deskripsi` dipakai mesin rekomendasi buat mencocokkan tujuan lahan
(erosi, hara/organik, pangan, kontaminan), jadi jangan diubah sembarangan.
Kata seperti "beracun" atau "invasif" di `risiko` membuat tanaman diblokir dari rekomendasi otomatis.
"""

ERO = 'pencegahan-erosi'
SUBUR = 'peningkatan-kesuburan'
AIR = 'konservasi-air'
PANGAN = 'pangan-keluarga'
PULIH = 'pemulihan-tanah-tercemar'

ECOCROP = ('FAO EcoCrop, database kebutuhan tumbuh tanaman', 'https://ecocrop.apps.fao.org/')
BBSDLP = ('Ritung dkk. (2011). Petunjuk Teknis Evaluasi Lahan untuk Komoditas Pertanian. BBSDLP, Kementerian Pertanian', None)
ICRAF = ('Orwa dkk. (2009). Agroforestree Database. World Agroforestry Centre (ICRAF)', None)
GISD = ('Global Invasive Species Database, IUCN Invasive Species Specialist Group', 'https://www.iucngisd.org/gisd/')

# Jenis kontaminan yang dikenal sistem
KONTAMINAN = {
    'Timbal (Pb)': 'Logam berat yang bisa berasal dari knalpot kendaraan, cat lama, dan limbah industri.',
    'Kadmium (Cd)': 'Logam berat yang bisa berasal dari pupuk fosfat tertentu, limbah baterai, dan industri.',
    'Arsenik (As)': 'Metaloid beracun yang bisa berasal dari batuan alami, pestisida lama, dan penambangan.',
    'Seng (Zn)': 'Logam yang dalam jumlah berlebih bisa mengganggu tanaman, biasanya dari limbah industri.',
}


def _t(nama, latin, kelompok, ph, tekstur, air, iklim, tujuan, fungsi, deskripsi, risiko='', refs=(), kontaminan=(), catatan=''):
    return {
        'nama': nama, 'nama_latin': latin, 'kelompok': kelompok,
        'kondisi_pertumbuhan': f'pH tanah {ph[0]} sampai {ph[1]}. Tekstur: {tekstur}. Kelembapan dan air: {air}. Iklim: {iklim}.',
        'tujuan': tujuan, 'fungsi': fungsi, 'deskripsi': deskripsi, 'risiko': risiko,
        'refs': list(refs), 'kontaminan': list(kontaminan), 'catatan': catatan,
    }


TANAMAN = [
    # ---- Pangan keluarga ----
    _t('Kangkung darat', 'Ipomoea reptans', 'pangan', (5.5, 7.0), 'lempung sampai lempung berpasir, gembur', 'butuh air cukup, tahan lembap', 'dataran rendah, hangat', [PANGAN],
       'Pangan keluarga: sayuran daun cepat panen', 'Sayuran daun yang tumbuh cepat, panen pertama sekitar 3 sampai 4 minggu. Cocok buat lahan pekarangan.', refs=[ECOCROP, BBSDLP]),
    _t('Bayam', 'Amaranthus tricolor', 'pangan', (6.0, 7.0), 'gembur dan subur, kaya bahan organik', 'butuh air teratur, drainase baik', 'dataran rendah sampai menengah', [PANGAN],
       'Pangan keluarga: sayuran daun', 'Sayuran daun umur pendek yang mudah ditanam di pekarangan. Responsif terhadap tanah yang kaya bahan organik.', refs=[ECOCROP, BBSDLP]),
    _t('Caisim', 'Brassica rapa var. parachinensis', 'pangan', (6.0, 7.0), 'lempung gembur', 'butuh air teratur, tidak tahan genangan', 'dataran rendah sampai tinggi', [PANGAN],
       'Pangan keluarga: sayuran daun', 'Sayuran sawi yang panen sekitar 30 sampai 40 hari. Cocok buat bedengan kecil.', refs=[ECOCROP, BBSDLP]),
    _t('Bawang daun', 'Allium fistulosum', 'pangan', (6.0, 7.0), 'lempung berpasir, gembur', 'butuh air teratur, drainase baik', 'dataran menengah sampai tinggi', [PANGAN],
       'Pangan keluarga: bumbu dapur', 'Bumbu dapur yang bisa dipanen berulang dari rumpun yang sama.', refs=[ECOCROP, BBSDLP]),
    _t('Cabai rawit', 'Capsicum frutescens', 'pangan', (5.5, 7.0), 'lempung berpasir, drainase baik', 'butuh air cukup, tidak tahan genangan', 'dataran rendah sampai 1.200 mdpl, hangat', [PANGAN],
       'Pangan keluarga: bumbu dapur bernilai tinggi', 'Tanaman bumbu yang berbuah terus sepanjang tahun kalau dirawat. Cocok di pekarangan dan pot besar.', refs=[ECOCROP, BBSDLP]),
    _t('Tomat', 'Solanum lycopersicum', 'pangan', (5.5, 7.0), 'lempung gembur, kaya bahan organik', 'butuh air teratur, drainase baik', 'suhu sejuk sampai hangat, sekitar 20 sampai 27 derajat', [PANGAN],
       'Pangan keluarga: sayuran buah', 'Sayuran buah yang butuh sinar matahari penuh dan penopang. Rawan layu kalau tanah tergenang.', refs=[ECOCROP, BBSDLP]),
    _t('Terong', 'Solanum melongena', 'pangan', (5.5, 6.8), 'lempung berpasir, subur', 'butuh air cukup, drainase baik', 'dataran rendah, hangat', [PANGAN],
       'Pangan keluarga: sayuran buah', 'Sayuran buah yang tahan panas dan bisa dipanen berkali-kali dalam satu musim.', refs=[ECOCROP, BBSDLP]),
    _t('Mentimun', 'Cucumis sativus', 'pangan', (6.0, 7.0), 'lempung berpasir, gembur', 'butuh air teratur, tidak tahan genangan', 'dataran rendah sampai menengah', [PANGAN],
       'Pangan keluarga: sayuran buah merambat', 'Sayuran buah merambat yang cepat panen, sekitar 45 sampai 55 hari.', refs=[ECOCROP, BBSDLP]),
    _t('Labu kuning', 'Cucurbita moschata', 'pangan', (5.5, 7.0), 'lempung berpasir, gembur', 'cukup toleran kekeringan ringan', 'dataran rendah sampai menengah', [PANGAN],
       'Pangan keluarga: buah tahan simpan', 'Tanaman merambat yang buahnya tahan disimpan berbulan-bulan, cocok buat cadangan pangan keluarga.', refs=[ECOCROP, BBSDLP]),
    _t('Kacang panjang', 'Vigna unguiculata subsp. sesquipedalis', 'pangan', (5.5, 7.0), 'lempung berpasir, drainase baik', 'cukup toleran kekeringan', 'dataran rendah, hangat', [PANGAN, SUBUR],
       'Pangan keluarga: kacang-kacangan yang menambah unsur hara tanah', 'Kacang merambat yang polongnya dimakan muda. Bintil akarnya mengikat nitrogen sehingga ikut menambah hara tanah.', refs=[ECOCROP, BBSDLP]),
    _t('Buncis', 'Phaseolus vulgaris', 'pangan', (5.5, 6.5), 'lempung gembur', 'butuh air teratur, tidak tahan genangan', 'dataran menengah sampai tinggi, 300 sampai 1.500 mdpl', [PANGAN, SUBUR],
       'Pangan keluarga: kacang-kacangan yang menambah unsur hara tanah', 'Kacang yang polongnya dimakan muda. Akarnya mengikat nitrogen dari udara.', refs=[ECOCROP, BBSDLP]),
    _t('Kacang tanah', 'Arachis hypogaea', 'pangan', (5.5, 6.5), 'berpasir sampai lempung berpasir, gembur, cukup kalsium', 'butuh air cukup saat berbunga, tidak tahan genangan', 'dataran rendah, hangat', [PANGAN, SUBUR],
       'Pangan keluarga: kacang-kacangan yang menambah unsur hara tanah', 'Kacang yang polongnya terbentuk di dalam tanah. Bintil akarnya mengikat nitrogen sehingga bagus buat rotasi tanam.', refs=[ECOCROP, BBSDLP]),
    _t('Kedelai', 'Glycine max', 'pangan', (5.8, 7.0), 'lempung berpasir sampai lempung, drainase baik', 'butuh air cukup, tidak tahan genangan', 'dataran rendah sampai menengah', [PANGAN, SUBUR],
       'Pangan keluarga: kacang-kacangan yang menambah unsur hara tanah', 'Sumber protein nabati yang akarnya mengikat nitrogen, bagus buat rotasi dengan jagung atau padi.', refs=[ECOCROP, BBSDLP]),
    _t('Kacang hijau', 'Vigna radiata', 'pangan', (5.8, 7.0), 'lempung berpasir, drainase baik', 'cukup toleran kekeringan', 'dataran rendah, hangat', [PANGAN, SUBUR],
       'Pangan keluarga: kacang-kacangan yang menambah unsur hara tanah', 'Kacang umur pendek, sekitar 60 sampai 70 hari, yang cocok ditanam di sela musim.', refs=[ECOCROP, BBSDLP]),
    _t('Kacang gude', 'Cajanus cajan', 'pangan', (5.0, 7.5), 'berbagai tekstur, tahan tanah kurang subur', 'tahan kekeringan', 'dataran rendah sampai menengah, hangat', [PANGAN, SUBUR, ERO],
       'Pangan keluarga: kacang-kacangan tahan kering yang menambah unsur hara tanah', 'Semak kacang berumur panjang yang tahan kering. Menambah hara tanah, dan perakarannya dalam membantu menahan tanah.', refs=[ECOCROP, ICRAF]),
    _t('Jagung', 'Zea mays', 'pangan', (5.5, 7.0), 'lempung berpasir sampai lempung, subur', 'butuh air cukup saat berbunga', 'dataran rendah sampai 1.800 mdpl', [PANGAN],
       'Pangan keluarga: serealia sumber karbohidrat', 'Serealia yang tumbuh di banyak jenis tanah dan bisa dipanen muda atau dipipil kering.', refs=[ECOCROP, BBSDLP]),
    _t('Sorgum', 'Sorghum bicolor', 'pangan', (5.5, 8.5), 'lempung sampai lempung berliat, toleran tanah kurang subur', 'tahan kekeringan', 'dataran rendah, hangat dan kering', [PANGAN],
       'Pangan keluarga: serealia tahan kekeringan', 'Serealia yang jauh lebih tahan kering daripada jagung, cocok buat lahan dengan air terbatas.', refs=[ECOCROP, BBSDLP]),
    _t('Ubi jalar', 'Ipomoea batatas', 'pangan', (5.0, 6.5), 'berpasir sampai lempung berpasir, gembur', 'cukup tahan kering, tidak tahan genangan', 'dataran rendah sampai menengah', [PANGAN, ERO],
       'Pangan keluarga: umbi yang juga menjadi penutup tanah', 'Umbi dan daunnya bisa dimakan. Sulurnya menutupi tanah sehingga ikut mengurangi erosi.', refs=[ECOCROP, BBSDLP]),
    _t('Singkong', 'Manihot esculenta', 'pangan', (5.0, 7.0), 'berpasir sampai lempung, toleran tanah kurang subur', 'tahan kekeringan', 'dataran rendah, hangat', [PANGAN],
       'Pangan keluarga: umbi sumber karbohidrat', 'Umbi yang bisa tumbuh di tanah kurang subur. Terus menguras hara kalau ditanam berulang tanpa pupuk.',
       risiko='Varietas pahit mengandung senyawa sianogenik, jadi umbi dan daunnya harus diolah dulu sebelum dimakan.', refs=[ECOCROP, BBSDLP]),
    _t('Talas', 'Colocasia esculenta', 'pangan', (5.5, 6.5), 'lempung, kaya bahan organik', 'suka lembap, tahan genangan dangkal', 'dataran rendah sampai menengah, lembap', [PANGAN],
       'Pangan keluarga: umbi buat lahan lembap', 'Umbi yang cocok buat bagian lahan yang lembap dan sulit ditanami yang lain.',
       risiko='Umbi dan daun mentah mengandung kalsium oksalat yang membuat gatal, jadi harus dimasak matang.', refs=[ECOCROP, BBSDLP]),
    _t('Pisang', 'Musa x paradisiaca', 'pangan', (5.5, 7.0), 'lempung subur, drainase baik', 'butuh air cukup, tidak tahan genangan', 'dataran rendah sampai menengah, hangat', [PANGAN, AIR],
       'Pangan keluarga: buah, juga membantu konservasi air', 'Buah yang berbuah sepanjang tahun. Rumpunnya rapat dan menyimpan air, cocok di pinggir lahan.', refs=[ECOCROP, BBSDLP]),
    _t('Pepaya', 'Carica papaya', 'pangan', (6.0, 6.5), 'lempung berpasir, drainase sangat baik', 'butuh air cukup, sangat tidak tahan genangan', 'dataran rendah, hangat', [PANGAN],
       'Pangan keluarga: buah cepat berbuah', 'Buah yang mulai berbuah sekitar 8 sampai 12 bulan. Akarnya mudah busuk kalau tergenang.', refs=[ECOCROP, BBSDLP]),
    _t('Nanas', 'Ananas comosus', 'pangan', (4.5, 6.5), 'berpasir sampai lempung berpasir, cocok untuk tanah agak masam', 'tahan kekeringan, tidak tahan genangan', 'dataran rendah sampai menengah, hangat', [PANGAN, ERO],
       'Pangan keluarga: buah untuk tanah masam, juga membantu menahan erosi', 'Buah yang cocok buat tanah agak masam. Ditanam rapat pada lereng, rumpunnya membantu menahan tanah.', refs=[ECOCROP, BBSDLP]),
    _t('Jahe', 'Zingiber officinale', 'pangan', (5.5, 6.5), 'lempung gembur, kaya bahan organik', 'butuh air teratur, tidak tahan genangan', 'dataran rendah sampai menengah, lembap dan teduh sebagian', [PANGAN],
       'Pangan keluarga: rimpang bumbu dan jamu', 'Rimpang bumbu dan jamu yang tumbuh baik di tanah gembur dan kaya bahan organik.', refs=[ECOCROP, BBSDLP]),
    _t('Kunyit', 'Curcuma longa', 'pangan', (5.0, 7.5), 'lempung gembur', 'butuh air cukup, tidak tahan genangan', 'dataran rendah sampai menengah, boleh agak teduh', [PANGAN],
       'Pangan keluarga: rimpang bumbu dan jamu', 'Rimpang bumbu dan jamu yang toleran terhadap naungan ringan, cocok di bawah pohon.', refs=[ECOCROP, BBSDLP]),
    _t('Lengkuas', 'Alpinia galanga', 'pangan', (5.5, 7.0), 'lempung gembur', 'butuh air cukup, tidak tahan genangan', 'dataran rendah sampai menengah', [PANGAN],
       'Pangan keluarga: rimpang bumbu dapur', 'Rimpang bumbu yang mudah ditanam di pekarangan dan berumpun rapat.', refs=[ECOCROP, BBSDLP]),
    _t('Sereh dapur', 'Cymbopogon citratus', 'pangan', (5.0, 7.5), 'berbagai tekstur, drainase baik', 'cukup tahan kering', 'dataran rendah sampai menengah, hangat', [PANGAN, ERO],
       'Pangan keluarga: bumbu dapur, perakaran rapat membantu menahan tanah', 'Rumpun rumput bumbu dengan perakaran rapat yang bisa ditanam di tepi bedengan untuk menahan tanah.', refs=[ECOCROP, BBSDLP]),

    # ---- Penutup tanah, pencegah erosi, dan pupuk hijau ----
    _t('Akar wangi', 'Chrysopogon zizanioides', 'remediasi', (4.0, 9.0), 'berbagai tekstur, sangat toleran', 'tahan kekeringan dan genangan sementara', 'dataran rendah sampai tinggi', [ERO, AIR, PULIH],
       'Pencegah erosi dengan perakaran dalam, dan kandidat fitoremediasi', 'Rumput berakar serabut sampai sekitar 3 meter yang ditanam rapat sebagai pagar rumput di lereng buat menahan erosi dan konservasi air. Juga diteliti buat fitoremediasi logam berat karena toleran terhadap tanah tercemar.',
       risiko='Kalau dipakai di tanah tercemar, biomassanya menyimpan logam di akar dan harus dikelola sebagai limbah, bukan dipakai sebagai pakan.',
       refs=[('Truong, Van, dan Pinners (2008). Vetiver System Applications Technical Reference Manual (membahas Timbal (Pb), Kadmium (Cd), dan Seng (Zn)). The Vetiver Network International', None), ICRAF],
       kontaminan=[('Timbal (Pb)', 'Toleran, penyerapan terbatas', 'Sebagian besar logam tertahan di akar'), ('Kadmium (Cd)', 'Toleran, penyerapan terbatas', 'Sebagian besar logam tertahan di akar'), ('Seng (Zn)', 'Toleran, penyerapan terbatas', 'Sebagian besar logam tertahan di akar')],
       catatan='Dasar klaim toleransi: manual teknis Vetiver System. Efektivitas di lapangan bergantung kondisi tanah dan perlu uji.'),
    _t('Rumput gajah', 'Pennisetum purpureum', 'penutup', (4.5, 8.0), 'berbagai tekstur, subur lebih baik', 'butuh air cukup, tahan kering sebentar', 'dataran rendah sampai menengah, hangat', [ERO, SUBUR],
       'Pencegah erosi dan penghasil biomassa organik', 'Rumput tinggi berumpun yang ditanam sebagai strip di lereng buat menahan erosi dan menghasilkan bahan organik buat pupuk atau pakan.', refs=[ECOCROP, ICRAF]),
    _t('Rumput signal', 'Urochloa decumbens', 'penutup', (4.5, 6.5), 'berbagai tekstur, tahan tanah masam', 'tahan kering, cukup tahan lembap', 'dataran rendah sampai menengah', [ERO],
       'Penutup tanah dan pencegah erosi', 'Rumput penutup tanah yang rapat dan tahan tanah masam, cocok buat lereng dan lahan kosong.', refs=[ECOCROP, ICRAF]),
    _t('Centrosema', 'Centrosema pubescens', 'penutup', (4.5, 7.5), 'berbagai tekstur, tahan tanah masam', 'tahan kekeringan sedang', 'dataran rendah, lembap', [ERO, SUBUR],
       'Kacang penutup tanah, mencegah erosi dan menambah unsur hara', 'Kacang merambat penutup tanah yang mengikat nitrogen, sering ditanam di bawah kebun sawit atau karet.', refs=[ECOCROP, ICRAF]),
    _t('Calopogonium', 'Calopogonium mucunoides', 'penutup', (5.0, 7.0), 'berbagai tekstur', 'cukup tahan kering', 'dataran rendah, lembap', [ERO, SUBUR],
       'Kacang penutup tanah, mencegah erosi dan menambah unsur hara', 'Kacang penutup tanah yang tumbuh cepat dan menekan gulma, sekaligus mengikat nitrogen.', refs=[ECOCROP, ICRAF]),
    _t('Kudzu tropis', 'Neustanthus phaseoloides', 'penutup', (4.5, 7.0), 'berbagai tekstur, tahan tanah masam', 'butuh curah hujan cukup', 'dataran rendah, lembap', [ERO, SUBUR],
       'Kacang penutup tanah, mencegah erosi dan menambah unsur hara', 'Kacang merambat tebal yang menutupi tanah rapat, banyak dipakai di kebun tahunan.', refs=[ECOCROP, ICRAF]),
    _t('Kacang pinto', 'Arachis pintoi', 'penutup', (5.0, 7.0), 'lempung berpasir sampai lempung', 'butuh curah hujan cukup, tahan teduh', 'dataran rendah sampai menengah', [ERO, SUBUR],
       'Penutup tanah rendah, mencegah erosi dan menambah unsur hara', 'Kacang hias rendah yang membentuk hamparan rapat, tahan naungan, cocok di bawah pohon dan tepi taman.', refs=[ECOCROP, ICRAF]),
    _t('Sereh wangi', 'Cymbopogon nardus', 'penutup', (5.0, 7.0), 'berbagai tekstur, drainase baik', 'cukup tahan kering', 'dataran rendah sampai menengah', [ERO],
       'Pencegah erosi lewat perakaran rapat, penghasil minyak atsiri', 'Rumput berumpun dengan perakaran rapat, bisa ditanam sebagai strip di tepi teras sambil dipanen daunnya buat minyak atsiri.', refs=[ECOCROP, ICRAF]),
    _t('Bambu apus', 'Gigantochloa apus', 'penutup', (5.0, 7.0), 'berbagai tekstur, subur lebih baik', 'butuh air cukup, tahan lembap', 'dataran rendah sampai menengah, lembap', [ERO, AIR],
       'Penahan erosi tebing dan konservasi air', 'Rumpun bambu dengan akar rapat yang menahan tanah di tebing dan tepi sungai, dan membantu resapan air.', refs=[ICRAF]),
    _t('Kaliandra', 'Calliandra calothyrsus', 'penutup', (4.5, 6.5), 'berbagai tekstur, tahan tanah masam', 'tahan kekeringan sedang', 'dataran menengah, 200 sampai 1.800 mdpl', [ERO, SUBUR],
       'Pagar hidup pencegah erosi dan penghasil pupuk hijau', 'Perdu kacang untuk pagar hidup di lorong tanaman. Daunnya dipangkas jadi pupuk hijau penambah unsur hara dan bahan organik.', refs=[ICRAF, ECOCROP]),
    _t('Gamal', 'Gliricidia sepium', 'penutup', (5.0, 8.5), 'berbagai tekstur, toleran', 'tahan kekeringan', 'dataran rendah sampai menengah', [ERO, SUBUR],
       'Pagar hidup pencegah erosi dan penghasil pupuk hijau', 'Pohon kacang yang ditanam sebagai pagar hidup atau tanaman lorong. Daunnya kaya nitrogen buat pupuk hijau.',
       risiko='Daun dan kulit batangnya bersifat racun bagi tikus. Kalau dipakai sebagai pakan ternak, porsinya perlu dibatasi dan diolah dulu.', refs=[ICRAF, ECOCROP]),
    _t('Lamtoro', 'Leucaena leucocephala', 'penutup', (5.5, 8.0), 'berbagai tekstur, toleran', 'tahan kekeringan', 'dataran rendah sampai menengah', [ERO, SUBUR],
       'Pagar hidup pencegah erosi dan penghasil pupuk hijau', 'Pohon kacang yang tumbuh cepat dan kaya nitrogen, lama dipakai buat konservasi lahan kering.',
       risiko='Tergolong spesies invasif yang mudah menyebar ke luar lahan budidaya, dan daun mudanya mengandung mimosin yang bisa merugikan ternak.', refs=[GISD, ICRAF]),
    _t('Sengon', 'Falcataria moluccana', 'penutup', (5.0, 7.0), 'lempung berpasir sampai lempung, drainase baik', 'butuh curah hujan cukup', 'dataran rendah sampai menengah, hingga sekitar 1.600 mdpl', [AIR, SUBUR],
       'Pohon pelindung, konservasi air, dan penambah unsur hara', 'Pohon cepat tumbuh yang mengikat nitrogen, ditanam sebagai tanaman pelindung dan hutan rakyat.',
       risiko='Kayunya lunak dan cabangnya mudah patah kena angin, serta rentan penyakit karat tumor.', refs=[ICRAF, ECOCROP]),
    _t('Turi', 'Sesbania grandiflora', 'penutup', (5.5, 7.0), 'lempung sampai lempung berliat, tahan agak basah', 'tahan genangan sebentar', 'dataran rendah, hangat', [SUBUR, PANGAN, ERO],
       'Pagar hidup penambah unsur hara, bunga dan daunnya dimakan sebagai pangan keluarga', 'Pohon kacang cepat tumbuh buat pagar hidup. Bunga dan daun mudanya bisa dimasak, daunnya jadi pupuk hijau.', refs=[ICRAF, ECOCROP]),
    _t('Orok-orok', 'Crotalaria juncea', 'penutup', (5.0, 7.5), 'berbagai tekstur', 'cukup tahan kekeringan', 'dataran rendah, hangat', [SUBUR],
       'Pupuk hijau, menambah unsur hara dan bahan organik', 'Tanaman pupuk hijau umur pendek yang dibenamkan saat berbunga buat menambah nitrogen dan bahan organik tanah.',
       risiko='Mengandung alkaloid pirolizidin, jadi jangan dipakai sebagai pakan ternak atau pangan.', refs=[ECOCROP, ICRAF]),
    _t('Kara benguk', 'Mucuna pruriens', 'penutup', (5.0, 7.5), 'berbagai tekstur, tahan tanah masam', 'cukup tahan kekeringan', 'dataran rendah, hangat', [SUBUR, ERO],
       'Penutup tanah dan pupuk hijau, menambah unsur hara dan bahan organik', 'Kacang merambat yang menutupi tanah dan menekan gulma, juga mengikat nitrogen.',
       risiko='Bulu polongnya menyebabkan gatal, dan bijinya perlu diolah dulu sebelum dimakan.', refs=[ECOCROP, ICRAF]),
    _t('Kembang bulan', 'Tithonia diversifolia', 'penutup', (5.0, 7.5), 'berbagai tekstur', 'cukup tahan kering', 'dataran rendah sampai menengah', [SUBUR],
       'Pupuk hijau, biomassa kaya unsur hara', 'Semak yang daunnya kaya nitrogen dan fosfor, dipangkas buat pupuk hijau dan dibenamkan ke tanah.',
       risiko='Bisa menjadi gulma kalau dibiarkan menyebar, jadi rutin dipangkas sebelum berbunga.', refs=[ICRAF]),
    _t('Mahoni', 'Swietenia macrophylla', 'penutup', (5.5, 7.5), 'lempung, drainase baik', 'butuh curah hujan cukup, tahan kemarau sedang', 'dataran rendah sampai menengah', [AIR, ERO],
       'Pohon penahan erosi di lereng dan konservasi air', 'Pohon berakar kuat yang ditanam di lereng dan tepi lahan buat menahan tanah dan menjaga resapan air.', refs=[ICRAF, ECOCROP]),
    _t('Alpukat', 'Persea americana', 'penutup', (5.5, 7.0), 'lempung berpasir, drainase sangat baik', 'butuh air cukup, tidak tahan genangan', 'dataran menengah, 200 sampai 1.500 mdpl', [PANGAN, AIR],
       'Pohon buah untuk pangan keluarga dan konservasi air', 'Pohon buah berakar dalam yang menjaga resapan air, cocok di lahan miring dengan drainase baik.', refs=[ECOCROP, ICRAF]),
    _t('Kopi robusta', 'Coffea canephora', 'penutup', (5.5, 6.5), 'lempung gembur, kaya bahan organik', 'butuh curah hujan merata', 'dataran rendah sampai menengah, hingga sekitar 800 mdpl', [ERO, AIR],
       'Tanaman kebun naungan, membantu menahan erosi dan konservasi air', 'Tanaman kebun yang ditanam di bawah pohon pelindung, tajuk berlapis membantu menahan erosi di lahan miring.', refs=[ECOCROP, ICRAF]),
    _t('Kopi arabika', 'Coffea arabica', 'penutup', (5.0, 6.5), 'lempung gembur, kaya bahan organik', 'butuh curah hujan merata', 'dataran tinggi, sekitar 1.000 sampai 2.000 mdpl', [ERO, AIR],
       'Tanaman kebun dataran tinggi, membantu menahan erosi dan konservasi air', 'Tanaman kebun dataran tinggi yang ditanam di bawah naungan, tajuknya membantu menahan erosi di lahan miring.', refs=[ECOCROP, ICRAF]),
    _t('Kakao', 'Theobroma cacao', 'penutup', (5.0, 7.5), 'lempung subur, drainase baik', 'butuh curah hujan merata', 'dataran rendah, lembap dan ternaungi', [ERO, SUBUR],
       'Tanaman kebun naungan, serasah menambah bahan organik', 'Tanaman kebun yang tumbuh di bawah naungan dan menghasilkan serasah daun buat bahan organik tanah.', refs=[ECOCROP, ICRAF]),
    _t('Kelapa', 'Cocos nucifera', 'penutup', (5.0, 8.0), 'berpasir sampai lempung, toleran tanah agak asin', 'tahan kekeringan sedang', 'dataran rendah dan pesisir, hangat', [PANGAN, ERO],
       'Pohon pangan keluarga dan penahan erosi di pesisir', 'Pohon serbaguna yang toleran tanah berpasir pesisir, akarnya membantu menahan tanah.', refs=[ECOCROP, ICRAF]),

    # ---- Fitoremediasi (kandidat) ----
    _t('Bunga matahari', 'Helianthus annuus', 'remediasi', (6.0, 7.5), 'lempung berpasir sampai lempung', 'butuh air cukup, tahan kering sedang', 'dataran rendah sampai menengah, sinar matahari penuh', [PULIH],
       'Kandidat fitoremediasi logam berat', 'Tanaman tinggi berakar dalam yang diteliti buat fitoremediasi logam berat dan penelitian rizofiltrasi. Hasilnya sangat bergantung kondisi tanah.',
       risiko='Biomassa dari tanah tercemar menyimpan logam berat dan tidak aman dimakan atau dijadikan pakan.',
       refs=[('Dushenkov dkk. (1995). Rhizofiltration: the use of plants to remove heavy metals from aqueous streams (membahas Timbal (Pb) dan Kadmium (Cd)). Environmental Science and Technology 29(5)', None)],
       kontaminan=[('Timbal (Pb)', 'Terbatas, perlu dipantau', 'Terbukti di penelitian air dan skala kecil, hasil di lapangan bervariasi'), ('Kadmium (Cd)', 'Terbatas, perlu dipantau', 'Terbukti di penelitian skala kecil, hasil di lapangan bervariasi')],
       catatan='Bukan jaminan membersihkan tanah. Perlu uji ulang tanah dan pendampingan ahli.'),
    _t('Sawi india', 'Brassica juncea', 'remediasi', (5.5, 7.5), 'lempung berpasir sampai lempung', 'butuh air cukup', 'dataran menengah sampai tinggi', [PULIH],
       'Kandidat fitoremediasi logam berat', 'Sawi yang diteliti menyerap timbal dan logam lain dalam biomassa, terutama dengan tambahan pengkhelat yang sendirinya berisiko mencemari air tanah.',
       risiko='Biomassa dari tanah tercemar menyimpan logam berat dan tidak aman dimakan atau dijadikan pakan.',
       refs=[('Blaylock dkk. (1997). Enhanced accumulation of Pb in Indian mustard by soil-applied chelating agents (membahas Timbal (Pb)). Environmental Science and Technology 31(3)', None)],
       kontaminan=[('Timbal (Pb)', 'Terbatas, perlu dipantau', 'Hasil penelitian memakai pengkhelat, yang berisiko mencuci logam ke air tanah')],
       catatan='Bukan jaminan membersihkan tanah. Perlu uji ulang tanah dan pendampingan ahli.'),
    _t('Pakis arsenik', 'Pteris vittata', 'remediasi', (6.0, 8.0), 'berbatu atau berkapur, drainase baik', 'cukup lembap, tahan teduh sebagian', 'dataran rendah sampai menengah, hangat', [PULIH],
       'Kandidat fitoremediasi arsenik', 'Pakis yang tercatat menimbun arsenik dalam daunnya, diteliti khusus buat tanah tercemar arsenik.',
       risiko='Daun menyimpan arsenik dan tidak aman dimakan atau dijadikan pakan, dan harus dikelola sebagai limbah.',
       refs=[('Ma dkk. (2001). A fern that hyperaccumulates arsenic (membahas Arsenik (As)). Nature 409', None)],
       kontaminan=[('Arsenik (As)', 'Menjanjikan di penelitian', 'Menimbun arsenik dalam daun, diuji di tanah dan skala terbatas')],
       catatan='Bukan jaminan membersihkan tanah. Perlu uji ulang tanah dan pendampingan ahli.'),
]
