# MDVRP Solver

Aplikasi web berbasis Django untuk menyelesaikan **Multi-Depot Vehicle Routing Problem (MDVRP)** menggunakan tiga algoritma: Greedy, Hybrid Genetic Algorithm (HGA), dan MILP dengan Gurobi. Dibuat sebagai proyek skripsi.

---

## Prasyarat

- Python 3.11 atau lebih baru
- PostgreSQL 14 atau lebih baru
- Gurobi (lisensi akademik, lihat langkah di bawah)

---

## Mendapatkan Lisensi Akademik Gurobi

Gurobi gratis untuk mahasiswa dan staf akademik. Ikuti langkah berikut:

1. Daftar di [gurobi.com](https://www.gurobi.com) menggunakan email universitas kamu.
2. Verifikasi institusi akademik kamu. Gurobi biasanya merespons dalam beberapa menit.
3. Setelah disetujui, buka **User Portal > Licenses > Request License**.
4. Pilih **Academic Named-User License** lalu generate lisensinya.
5. Kamu akan mendapatkan perintah seperti ini:
   ```
   grbgetkey xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```
6. Jalankan perintah tersebut di terminal. File lisensi (`gurobi.lic`) akan tersimpan di direktori home kamu.
7. Verifikasi instalasi:
   ```bash
   python -c "import gurobipy; print(gurobipy.gurobi.version())"
   ```

Lisensi ini terikat ke satu mesin. Jika ganti komputer, ulangi langkah 3 sampai 6 untuk mesin baru.

---

## Instalasi

### 1. Clone repositori

```bash
git clone https://github.com/seanhw22/RouteOptimization.git
cd RouteOptimization
```

### 2. Buat virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependensi

```bash
pip install -r requirements.txt
```

### 4. Buat database PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE mdvrp;"
```

### 5. Konfigurasi environment variable

Salin file contoh lalu isi dengan nilai kamu:

```bash
cp .env.example .env
```

Edit `.env`:

```env
DJANGO_SECRET_KEY=isi-secret-key-kamu
DJANGO_DEBUG=true
DATABASE_URL=postgresql://postgres:password@localhost:5432/mdvrp
```

Untuk membuat secret key:

```bash
python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))"
```

### 6. Jalankan migrasi

```bash
python manage.py migrate
```

### 7. Jalankan server

```bash
python manage.py runserver
```

Buka [http://localhost:8000](http://localhost:8000).

---

## Cara Penggunaan

1. Daftar akun atau lanjutkan sebagai tamu.
2. Upload dataset dalam format XLSX atau lima file CSV (depots, customers, vehicles, orders, items).
3. Pilih algoritma dan jalankan solver.
4. Pantau progres secara langsung dan lihat hasil saat selesai.
5. Ekspor solusi dalam format CSV, PDF, atau GeoJSON.

---

## Struktur Proyek

```
.
├── accounts/           # Autentikasi pengguna
├── algorithms/         # Implementasi algoritma
│   ├── mdvrp_greedy.py #   Greedy (cheapest insertion)
│   ├── mdvrp_hga.py    #   Hybrid Genetic Algorithm (DEAP)
│   └── milp.py         #   MILP (Gurobi)
├── datasets/           # Upload dan manajemen dataset
├── mdvrp_web/          # Settings dan URL Django
├── results/            # Tampilan dan perbandingan hasil
├── runs/               # Pemicu dan pelacak eksekusi solver
├── src/                # Utilitas bersama
│   ├── data_loader.py  #   Pembaca CSV / XLSX / database
│   ├── distance_matrix.py
│   ├── exporter.py     #   Ekspor CSV / PDF / GeoJSON
│   └── solver_base.py
├── templates/          # Template HTML
├── static/             # Aset statis
├── requirements.txt
└── manage.py
```

---

## Perbandingan Algoritma

| Algoritma | Kecepatan | Kualitas Solusi | Keterangan |
|-----------|-----------|----------------|------------|
| Greedy | Sangat cepat | Baik | Heuristik konstruktif |
| HGA | Sedang | Sangat baik | Evolutif, menggunakan DEAP |
| MILP | Lambat | Optimal | Eksak, cocok untuk instans kecil |

---

## Lisensi

- **Gurobi** menggunakan lisensi akademik gratis (lihat di atas)
- Semua dependensi lain bersifat open-source (MIT / BSD)
