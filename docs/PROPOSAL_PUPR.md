# PROPOSAL PENAWARAN
# Layanan OCR API untuk Digitalisasi Dokumen

---

**Diajukan Kepada:**  
Kementerian Pekerjaan Umum dan Perumahan Rakyat (PUPR)

**Diajukan Oleh:**  
[NAMA PERUSAHAAN ANDA]  
[Alamat Perusahaan]  
[No. Telepon] | [Email]

**Tanggal:**  
Januari 2026

---

## 1. RINGKASAN EKSEKUTIF

Kami menawarkan solusi **Layanan OCR (Optical Character Recognition) API** untuk mendukung proses digitalisasi dokumen di lingkungan Kementerian PUPR. Layanan ini memungkinkan ekstraksi teks otomatis dari dokumen scan, baik dalam format gambar maupun PDF, dengan akurasi tinggi dan waktu proses yang cepat.

**Keunggulan Utama:**
- ✅ Ekstraksi teks otomatis dari dokumen scan
- ✅ Support format gambar dan PDF multi-halaman
- ✅ Mendukung bahasa Indonesia dan Inggris
- ✅ Integrasi mudah via REST API
- ✅ Keamanan dengan autentikasi API Key
- ✅ Monitoring dan pelaporan penggunaan

---

## 2. LATAR BELAKANG

Kementerian PUPR memiliki volume dokumen yang besar, termasuk:
- Laporan proyek infrastruktur
- Dokumen perizinan
- Surat-menyurat
- Dokumen teknis dan gambar kerja

Proses input data manual dari dokumen scan memerlukan waktu dan sumber daya yang signifikan. Dengan teknologi OCR, proses ini dapat diotomatisasi sehingga meningkatkan efisiensi kerja.

---

## 3. SOLUSI YANG DITAWARKAN

### 3.1 Fitur Layanan

| Fitur | Deskripsi |
|-------|-----------|
| **Image OCR** | Ekstrak teks dari PNG, JPG, TIFF, BMP, GIF |
| **PDF OCR** | Proses PDF multi-halaman dengan output per halaman |
| **Multi Bahasa** | Mendukung Bahasa Indonesia dan English |
| **REST API** | Integrasi mudah dengan sistem existing |
| **API Key Auth** | Keamanan akses dengan API Key |
| **Rate Limiting** | Perlindungan dari overload |
| **History & Stats** | Monitoring penggunaan real-time |
| **Error Handling** | Kode error detail untuk debugging |

### 3.2 Arsitektur Sistem

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Aplikasi PUPR  │ ───► │    OCR API      │ ───► │   Tesseract     │
│  (Client)       │      │   (FastAPI)     │      │   OCR Engine    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
         │                        │
         │                        ▼
         │               ┌─────────────────┐
         │               │   Database      │
         │               │   (History)     │
         │               └─────────────────┘
         │
         ▼
┌─────────────────┐
│   MinIO         │
│   (Optional)    │
└─────────────────┘
```

### 3.3 Contoh Penggunaan

**Request:**
```bash
curl -X POST "https://api.example.com/api/ocr/extract" \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@dokumen.pdf" \
  -F "language=id"
```

**Response:**
```json
{
  "success": true,
  "text": "SURAT KEPUTUSAN\nNomor: 123/SK/2026\n...",
  "pages": 2,
  "language": "id",
  "processing_time_ms": 3500
}
```

---

## 4. LINGKUP PEKERJAAN

### 4.1 Tahap 1: Setup & Deployment (Minggu 1-2)
- Instalasi server dan konfigurasi
- Setup database dan storage
- Konfigurasi keamanan
- Testing awal

### 4.2 Tahap 2: Integrasi (Minggu 3-4)
- Integrasi dengan sistem existing PUPR
- Pembuatan API Key untuk setiap unit
- Konfigurasi rate limiting sesuai kebutuhan
- Testing integrasi

### 4.3 Tahap 3: Training & Handover (Minggu 5)
- Training penggunaan API
- Training administrasi sistem
- Dokumentasi lengkap
- Handover ke tim IT PUPR

### 4.4 Tahap 4: Maintenance (Ongoing)
- Monitoring sistem
- Backup rutin
- Update keamanan
- Support teknis

---

## 5. BIAYA INVESTASI

### 5.1 Biaya Implementasi (One-Time)

| Item | Biaya (Rp) |
|------|------------|
| Setup & Deployment | 25.000.000 |
| Integrasi Sistem | 15.000.000 |
| Training (2 sesi) | 5.000.000 |
| Dokumentasi | 5.000.000 |
| **Total Implementasi** | **50.000.000** |

### 5.2 Biaya Berlangganan (Monthly)

| Paket | Request/Bulan | Biaya/Bulan (Rp) |
|-------|---------------|------------------|
| **Basic** | 5.000 | 5.000.000 |
| **Standard** | 20.000 | 15.000.000 |
| **Enterprise** | Unlimited | 30.000.000 |

### 5.3 Biaya Maintenance (Annual)

| Item | Biaya/Tahun (Rp) |
|------|------------------|
| Support & Maintenance | 10.000.000 |
| Update & Patch | Include |
| Backup Management | Include |

---

## 6. KEUNGGULAN KOMPETITIF

| Aspek | Kami | Kompetitor |
|-------|------|------------|
| **Deployment** | On-premise / Cloud | Umumnya Cloud saja |
| **Bahasa Indonesia** | ✅ Optimized | ❓ Terbatas |
| **Customization** | ✅ Fleksibel | ❌ Fixed |
| **Support Lokal** | ✅ 24/7 WIB | ⚠️ Timezone berbeda |
| **Data Privacy** | ✅ Data di Indonesia | ⚠️ Server luar negeri |
| **Harga** | Kompetitif | Lebih mahal |

---

## 7. TIMELINE IMPLEMENTASI

```
Minggu 1-2    │████████████│ Setup & Deployment
Minggu 3-4    │████████████│ Integrasi Sistem
Minggu 5      │██████      │ Training & Handover
Minggu 6+     │→→→→→→→→→→→→│ Maintenance & Support
```

**Total Waktu Implementasi: 5-6 Minggu**

---

## 8. GARANSI & SLA

### 8.1 Service Level Agreement (SLA)
- **Uptime**: 99.5% per bulan
- **Response Time API**: < 10 detik per request
- **Support Response**: 
  - Critical: < 2 jam
  - High: < 4 jam
  - Normal: < 1 hari kerja

### 8.2 Garansi
- Garansi perbaikan bug: 12 bulan
- Garansi performa sesuai spesifikasi
- Free minor update selama periode maintenance

---

## 9. SYARAT & KETENTUAN

1. Pembayaran implementasi: 50% DP, 50% setelah go-live
2. Pembayaran berlangganan: Bulanan di muka
3. Kontrak minimum: 12 bulan
4. Harga belum termasuk PPN 11%

---

## 10. TENTANG KAMI

**[NAMA PERUSAHAAN]** adalah perusahaan teknologi yang berfokus pada solusi digitalisasi dan otomatisasi proses bisnis. Kami telah berpengalaman dalam:

- Pengembangan sistem informasi pemerintahan
- Integrasi sistem enterprise
- Solusi AI dan Machine Learning
- Cloud infrastructure

**Klien Kami:**
- [Nama Klien 1]
- [Nama Klien 2]
- [Nama Klien 3]

---

## 11. PENUTUP

Kami yakin bahwa solusi OCR API yang kami tawarkan dapat membantu Kementerian PUPR dalam meningkatkan efisiensi proses digitalisasi dokumen. Kami siap untuk melakukan presentasi dan demo lebih lanjut sesuai dengan jadwal yang ditentukan.

**Kontak:**
- Nama: [Nama PIC]
- Jabatan: [Jabatan]
- Telepon: [No HP]
- Email: [Email]

---

*Proposal ini berlaku selama 30 hari sejak tanggal dikeluarkan.*
