# NetMon — Ringkasan Perjalanan Pembangunan (Bab 1–5)

*Dokumen ini merangkum setiap tahap pembangunan secara naratif, cocok
dijadikan dasar slide presentasi. Setiap bab ditulis dengan pola yang
sama: latar belakang masalah, apa yang dibangun, keputusan arsitektur
penting, dan bukti bahwa bagian tersebut benar-benar berfungsi.*

---

## Bab 1 — Fondasi: Struktur Proyek

Sebelum satu baris logika bisnis pun ditulis, pertanyaan pertama yang
harus dijawab adalah: bagaimana proyek ini akan tetap rapi lima tahun
dari sekarang, ketika sudah ada puluhan file dan mungkin kontributor
lain ikut mengerjakannya? Jawabannya adalah clean architecture —
backend dipecah menjadi lapisan-lapisan dengan arah ketergantungan yang
searah: `api/` memanggil `services/`, `services/` memanggil
`repositories/`, dan `monitors/` tidak pernah tahu siapa yang
mengonsumsi datanya karena semua komunikasi lewat event bus.

Setiap folder diberi dokumentasi kontrak sejak awal — bukan sekadar
folder kosong, tapi pernyataan eksplisit "boleh mengimpor apa, tidak
boleh berisi apa". Dependency management memakai `pyproject.toml` untuk
backend dan `package.json` untuk frontend, masing-masing dependency
diberi alasan penggunaan secara eksplisit. Strategi konfigurasi
ditetapkan lebih dulu lewat `.env.example` sebagai daftar resmi semua
parameter yang bisa diatur — target ping, interval, ambang batas
severity, retensi database — sehingga tidak ada satu pun angka yang
di-hardcode di kode nanti.

Hasil dari bab ini bukan aplikasi yang bisa dijalankan, melainkan
kerangka yang membuat setiap bab berikutnya punya tempat yang jelas
untuk diletakkan.

---

## Bab 2 — Sistem Konfigurasi yang Tervalidasi

Bab ini menjawab satu prinsip penting: konfigurasi yang salah harus
gagal saat aplikasi dinyalakan, bukan diam-diam menyebabkan perilaku
aneh jam 3 pagi. Dibangun kelas `Settings` yang membaca seluruh variabel
lingkungan, memvalidasi setiap nilai, dan menolak start jika ada yang
tidak masuk akal — misalnya ambang batas latency "warning" yang lebih
besar dari "critical".

Untuk menjaga keterbacaan kode di tahap-tahap berikutnya, konfigurasi
yang secara teknis flat (sesuai bentuk file `.env`) tetap diekspos
sebagai objek terkelompok — `settings.ping.interval_seconds`,
`settings.thresholds.latency_critical_ms` — sehingga kode monitor nanti
tidak perlu membaca lautan 30 variabel bercampur.

Satu bug nyata ditemukan dan diperbaiki di sini: pustaka
`pydantic-settings` ternyata mencoba men-decode nilai list sebagai JSON
sebelum validator kustom sempat berjalan, sehingga format sederhana
`1.1.1.1,8.8.8.8` di file `.env` malah gagal di-parse. Ini dibuktikan
lewat pengujian langsung terhadap `.env.example` yang sebenarnya, bukan
hanya lewat dugaan.

---

## Bab 3 — Lapisan Database

Sembilan tabel dirancang sesuai kebutuhan data masing-masing — bukan
satu tabel generik yang memaksakan semua jenis data ke bentuk yang sama.
`PingHistory` menyimpan bukan cuma angka mentah, tapi juga analitik
(jitter, rata-rata bergerak, persentase packet loss) yang nantinya
dihitung oleh monitor. `Incident` menjadi pusat siklus hidup insiden,
terhubung ke `TracerouteResult`, `TcpCapture`, dan `Alert` lewat relasi
yang otomatis terhapus bersih (cascade delete) saat sebuah insiden
dihapus.

Alembic — sistem migrasi skema — disambungkan penuh sejak bab ini,
bukan sekadar folder kosong, sehingga perubahan skema di masa depan
tetap tercatat dan bisa dibatalkan. Setiap kolom bertipe enum disimpan
sebagai VARCHAR, bukan tipe enum native database, supaya migrasi dari
SQLite ke PostgreSQL nanti tidak perlu operasi rumit `ALTER TYPE`.

Tiga bug nyata ditemukan lewat instalasi dan pengujian langsung: build
tool `hatchling` gagal mendeteksi struktur paket, referensi file
`README.md` yang salah lokasi, dan satu dependency pengembangan yang
ternyata tidak pernah ada di PyPI. Semua diperbaiki setelah dikonfirmasi
lewat instalasi bersih dari nol, bukan hanya tinjauan kode. Satu masalah
lain muncul belakangan dari pengguna sendiri: SQLite menolak membuat
database karena folder `data/` belum ada — ini diperbaiki dengan
membuat direktori tersebut secara otomatis sebelum koneksi pertama
dibuka.

---

## Bab 4 — Server Aplikasi (FastAPI)

Inilah titik proyek ini pertama kali benar-benar bisa dijalankan.
Sebuah *application factory* dibangun untuk merangkai konfigurasi,
logging, siklus hidup database, CORS, dan penanganan error jadi satu
kesatuan yang konsisten — dengan satu endpoint pertama, `/api/v1/health`,
yang memeriksa koneksi database secara nyata, bukan sekadar
mengembalikan "OK" tanpa makna.

Dua bug arsitektural yang cukup halus ditemukan lewat pengujian nyata:
mode debug bawaan FastAPI ternyata membuat Starlette (framework di
baliknya) melewati penanganan error kustom yang sudah dibuat, dan malah
mengembalikan halaman HTML traceback — jelas keliru untuk API berbasis
JSON. Perbaikannya membuat aplikasi ini selalu konsisten mengembalikan
error dalam format JSON, sementara detail teknisnya tetap disembunyikan
di lingkungan produksi.

Untuk membuktikan semuanya benar-benar bekerja, server dijalankan secara
nyata memakai `uvicorn`, lalu diuji dengan `curl` sungguhan terhadap
endpoint kesehatan dan dokumentasi API — bukan sekadar lolos dari test
suite otomatis.

---

## Bab 5 — Komunikasi Real-Time (WebSocket)

Di sinilah janji arsitektur dari Bab 1 dibuktikan secara konkret: sebuah
*event bus* in-process dibangun sehingga monitor (yang akan dibangun di
bab berikutnya) bisa mengumumkan hasil pengukurannya tanpa perlu tahu
sama sekali bahwa ada dashboard yang mendengarkan. Event bus ini
menjembatani ke *connection manager*, yang menyiarkan setiap event
sebagai pesan WebSocket ke semua klien yang terhubung — sesuai prinsip
dashboard yang wajib "push", bukan polling setiap detik.

Bagian tersulit dari bab ini adalah membuktikan bahwa rantai
"monitor → event bus → WebSocket" benar-benar tersambung ujung ke ujung,
bukan cuma masing-masing komponen berjalan sendiri-sendiri. Ini diuji
bertingkat: dari unit test komponen individual, ke test integrasi yang
mempublikasikan event dan memverifikasi klien menerimanya, hingga
akhirnya menjalankan server `uvicorn` sungguhan dan menyambungkan klien
WebSocket sungguhan lewat koneksi soket nyata — dan pesan heartbeat
benar-benar diterima.

Total pengujian otomatis proyek pada titik ini mencapai 79 test, seluruhnya
lolos, termasuk skenario kegagalan (koneksi mati di tengah siaran,
subscriber yang gagal tidak boleh mematikan subscriber lain).

---

## Benang Merah Lima Bab Ini

Setiap bab dibangun di atas kontrak yang ditetapkan bab sebelumnya, dan
setiap klaim "sudah berhasil" diverifikasi lewat eksekusi nyata —
instalasi bersih dari nol, server yang benar-benar dinyalakan, koneksi
jaringan yang benar-benar dibuka — bukan sekadar tinjauan kode yang
terlihat masuk akal. Tiga bug arsitektural cukup penting ditemukan
justru karena disiplin pengujian ini, dan seluruhnya diperbaiki sebelum
lanjut ke bab berikutnya.

**Selanjutnya (Bab 6):** Ping Monitor — komponen yang oleh brief awal
disebut sebagai "jantung aplikasi", sekaligus pembuktian pertama bahwa
seluruh rantai arsitektur (monitor → event bus → WebSocket → database)
bekerja bersama sebagai satu sistem utuh.
