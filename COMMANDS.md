# 📚 Dokumentasi Perintah Bot (Bot Commands)

Dokumen ini berisi daftar lengkap perintah yang tersedia untuk **User Biasa** dan **Super Admin**.

---

## 👤 User Biasa (Member)

Perintah ini dapat diakses oleh semua pengguna yang memulai percakapan dengan bot.

| Perintah | Deskripsi | Contoh Penggunaan |
| :--- | :--- | :--- |
| `/start` | Memulai bot dan mendaftarkan diri ke sistem. | `/start` |
| `/help` | Menampilkan bantuan dan daftar perintah dasar. | `/help` |
| `/myprofile` | Mengecek status langganan aktif dan masa berlaku. | `/myprofile` |
| `/subscribe` | **Menu Utama Langganan**. Membuka menu interaktif untuk memilih paket (Aset & Durasi) dan melakukan pembayaran. | `/subscribe` |
| `/listpackages` | (Alias) Sama dengan fungsi `/subscribe`. | `/listpackages` |

---

## 🛠 Super Admin

Perintah ini **HANYA** dapat dijalankan oleh pengguna yang ID Telegram-nya terdaftar di `.env` (`ADMIN_USER_ID`). Bot akan menolak jika dijalankan oleh orang lain.

### 📦 Manajemen Paket (Packages)
Mengatur jenis paket langganan yang dijual.

| Perintah | Deskripsi | Contoh Penggunaan |
| :--- | :--- | :--- |
| `/createpackage` | Membuat paket baru dengan harga dan durasi tertentu. | `/createpackage "VIP Crypto 1 Bulan" 150000 30 crypto` |
| `/adminlistpackages` | Melihat daftar semua paket yang tersedia beserta ID-nya. | `/adminlistpackages` |
| `/delpackage` | Menghapus paket berdasarkan ID. | `/delpackage 5` |

> **Format `/createpackage`**: `/createpackage <Nama> <Harga> <Hari> [Aset]`
> *   **Aset**: `crypto`, `stocks`, `forex`, `gold`, atau `all`.

### 💳 Manajemen Pembayaran (Payment Methods)
Mengatur rekening atau metode pembayaran yang muncul saat user subscribe.

| Perintah | Deskripsi | Contoh Penggunaan |
| :--- | :--- | :--- |
| `/addpayment` | Menambah metode pembayaran baru. | `/addpayment bank BCA "123456789 A/N Admin"` |
| `/listpayments` | Melihat daftar metode pembayaran aktif. | `/listpayments` |
| `/delpayment` | Menghapus metode pembayaran berdasarkan ID. | `/delpayment 2` |

> **Format `/addpayment`**: `/addpayment <Tipe> <Nama> <Detail>`
> *   **Tipe**: `bank`, `crypto`, `qris`.

### 👥 Manajemen User & Role

| Perintah | Deskripsi | Contoh Penggunaan |
| :--- | :--- | :--- |
| `/addmember` | Menambahkan user manual ke database (tanpa bayar). | `/addmember 123456789 username Member` |
| `/createrole` | Membuat role baru (selain Admin/Member/Viewer). | `/createrole "VIP Gold"` |
| `/listroles` | Melihat daftar role yang ada di sistem. | `/listroles` |

### 📢 Komunikasi & Jadwal

| Perintah | Deskripsi | Contoh Penggunaan |
| :--- | :--- | :--- |
| `/announce` | Mengirim pesan broadcast ke **SEMUA** user di database. | `/announce Server maintenance jam 12.` |
| `/schedule` | Menjadwalkan pesan otomatis ke semua user. | `/schedule daily 08:00 Selamat Pagi Trader!` |

### ⚙️ Kontrol Sistem & Monitoring

| Perintah | Deskripsi | Contoh Penggunaan |
| :--- | :--- | :--- |
| `/status` | Cek status koneksi ke grup, jam server, dan job scheduler. | `/status` |
| `/forcecheck` | Memaksa bot cek sinyal/berita **SEKARANG** (Bypass timer). | `/forcecheck signal` atau `/forcecheck news` |
| `/checkuninvited` | **PENTING**: Cek user yang sudah bayar tapi **gagal** dapat link grup otomatis. | `/checkuninvited` |

---

## 🔄 Alur Kerja Admin (Workflow)

1.  **Setup Awal**:
    *   Buat paket langganan: `/createpackage ...`
    *   Isi nomor rekening: `/addpayment ...`
2.  **Operasional Harian**:
    *   Tunggu notifikasi pembayaran masuk (ada foto bukti transfer).
    *   Klik **✅ Confirm** jika uang masuk, atau **❌ Reject** jika tidak.
    *   Bot otomatis kirim link ke user.
3.  **Troubleshooting**:
    *   Jika ada user komplain belum dapat link, cek `/checkuninvited`.
    *   Jika pasar sedang volatile, gunakan `/forcecheck signal` untuk memicu analisa teknikal instan.
