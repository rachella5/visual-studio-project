from pathlib import Path
import difflib
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
import copy
import getpass
import shutil

LOKASI_SCRIPT_INI = Path.cwd()
BASE_DIR = LOKASI_SCRIPT_INI / "SMK_MART_Python"
DATA_DIR = BASE_DIR / "data"
FOLDER_STRUK = BASE_DIR / "struk"
FOLDER_LAPORAN = BASE_DIR / "laporan"
FOLDER_BACKUP = BASE_DIR / "backup_data"

BASE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
FOLDER_STRUK.mkdir(parents=True, exist_ok=True)
FOLDER_LAPORAN.mkdir(parents=True, exist_ok=True)

print(f"Folder database dan struk: {BASE_DIR}")

FILE_PENGGUNA = DATA_DIR / "pengguna.txt"
FILE_BARANG = DATA_DIR / "barang.txt"
FILE_KATEGORI = DATA_DIR / "kategori.txt"
FILE_TRANSAKSI = DATA_DIR / "transaksi.txt"
FILE_DETAIL = DATA_DIR / "detail_transaksi.txt"
FILE_MASUK = DATA_DIR / "barang_masuk.txt"
FILE_KELUAR = DATA_DIR / "barang_keluar.txt"
FILE_LOG = DATA_DIR / "log_aktivitas.txt"

data_barang = {}
data_kategori = {}
data_pengguna = {}
list_riwayat_stok = []
data_expired = {}
nomor_berikutnya = 1

ROLE = ("admin", "gudang", "kasir")
MAP_ROLE = {
    "a": "admin", "adm": "admin", "admin": "admin",
    "g": "gudang", "gdg": "gudang", "gudang": "gudang",
    "k": "kasir", "ksr": "kasir", "kasir": "kasir",
}

# ==========================================
# FUNGSI-FUNGSI PENDUKUNG
# ==========================================
def rupiah(nilai):
    return "Rp" + f"{nilai:,}".replace(",", ".")

def input_wajib(pesan):
    while True:
        hasil = input(pesan).strip()
        if not hasil:
            print("⚠️[ERROR] Input tidak boleh kosong.")
            continue
        if "|" in hasil:
            print("⚠️[ERROR] Input tidak boleh mengandung karakter '|'.")
            continue
        return hasil

def input_password_simple(pesan="Masukkan password: ", boleh_kosong=False):
    while True:
        password = getpass.getpass(pesan).strip()
        if not password:
          if boleh_kosong:
            return ""
          print("⚠️[ERROR] Password tidak boleh kosong.")
          continue

        password2= getpass.getpass("Ulangi password: ").strip()
        if password != password2:
            print("⚠️ [ERROR] Password pertama dan kedua tidak sama! Silahkan ulangi.")
            continue

        return password

def input_angka(pesan, minimum=0):
    while True:
        try:
            angka = int(input(pesan).strip())
            if angka < minimum:
                print(f"⚠️[ERROR] Angka minimal {minimum}.")
                continue
            return angka
        except ValueError:
            print("⚠️[ERROR] Masukkan bilangan bulat yang valid.")

def buat_hash_password(password):
    salt = secrets.token_hex(16)
    hasil = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 150_000)
    return f"{salt}${hasil.hex()}"

def cek_password(password, password_hash):
    if "$" not in password_hash:
        return password == password_hash
    try:
        salt, nilai = password_hash.split("$", 1)
        hasil = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 150_000)
        return hmac.compare_digest(hasil, bytes.fromhex(nilai))
    except (ValueError, TypeError):
        return False

def buat_id_dict_otomatis(dict_aktif, dict_arsip, prefix):
    nomor_terakhir = 0
    semua_kode = list(dict_aktif.keys()) + list(dict_arsip.keys())
    for kode in semua_kode:
        if kode.startswith(prefix) and kode[len(prefix):].isdigit():
            nomor_terakhir = max(nomor_terakhir, int(kode[len(prefix):]))
    return f"{prefix}{nomor_terakhir + 1:03d}"

def buat_id_file_otomatis(path_file, prefix):
    nomor_terakhir = 0
    if path_file.exists():
        for baris in path_file.read_text(encoding="utf-8").splitlines():
            kode = baris.split("|")[0].strip()
            if kode.startswith(prefix) and kode[len(prefix):].isdigit():
                nomor_terakhir = max(nomor_terakhir, int(kode[len(prefix):]))
    return f"{prefix}{nomor_terakhir + 1:03d}"

def input_password():
    while True:
        sandi = input_wajib("Password (minimal 4 karakter): ")
        if len(sandi) < 4:
            print("⚠️[ERROR] Password terlalu pendek.")
            continue
        ulang = input_wajib("Ulangi password: ")
        if sandi == ulang:
            return buat_hash_password(sandi)
        print("⚠️[ERROR] Kedua password tidak sama.")

def simpan_kategori():
    baris_kategori = [
        f"{id_kategori}|{nama_kategori}"
        for id_kategori, nama_kategori in sorted(data_kategori.items())
    ]
    FILE_KATEGORI.write_text(
        "\n".join(baris_kategori) + ("\n" if baris_kategori else ""),
        encoding="utf-8"
    )

def tampilkan_daftar_kategori():
    print("\n--- DAFTAR KATEGORI VALID ---")
    print(f"{'ID':<8} | {'NAMA KATEGORI':<25}")
    print("-" * 36)
    for id_kategori, nama_kategori in sorted(data_kategori.items()):
        print(f"{id_kategori:<8} | {nama_kategori:<25}")
    print("-" * 36)

def cari_kategori_valid(teks_input):
    kunci = teks_input.strip().casefold()
    for id_kategori, nama_kategori in data_kategori.items():
        if id_kategori.casefold() == kunci or nama_kategori.casefold() == kunci:
            return id_kategori, nama_kategori
    return None

def tambah_kategori_baru(nama_awal=None, oleh_admin=True):
    if not oleh_admin:
        print("⚠️ [DITOLAK] Hanya Admin yang dapat menambahkan kategori baru.")
        return None

    nama_kategori = nama_awal.strip() if nama_awal else input_wajib("Nama kategori baru: ").strip()
    nama_kategori_rapi = nama_kategori.title()

    if cari_kategori_valid(nama_kategori_rapi):
        print(f"⚠️ [ERROR] Kategori '{nama_kategori_rapi}' sudah terdaftar.")
        return None

    nomor_terakhir = 0
    for kode in data_kategori.keys():
        if kode.startswith("KAT") and kode[3:].isdigit():
            nomor_terakhir = max(nomor_terakhir, int(kode[3:]))
    id_baru = f"KAT{nomor_terakhir + 1:03d}"

    data_kategori[id_baru] = nama_kategori_rapi
    simpan_kategori()
    print(f"✅ [SUKSES] Kategori baru '{nama_kategori_rapi}' ({id_baru}) berhasil ditambahkan!")
    return nama_kategori_rapi

def pilih_kategori_valid(izin_tambah=True):
    while True:
        tampilkan_daftar_kategori()
        masukan = input_wajib("Pilih ID atau Nama kategori: ").strip()
        hasil = cari_kategori_valid(masukan)
        if hasil:
            return hasil[1]  # Mengembalikan nama kategori resmi (contoh: "Alat Kebersihan")

        print(f"⚠️ [PERINGATAN] Kategori '{masukan}' tidak ditemukan di daftar kategori valid!")
        if izin_tambah:
            if konfirmasi_default(f"Apakah kategori '{masukan.title()}' sudah valid dan ingin dibuat sebagai kategori baru?"):
                kategori_baru = tambah_kategori_baru(masukan, oleh_admin=True)
                if kategori_baru:
                    return kategori_baru
            else:
                print("❗ [INFO] Silakan ketik ulang kategori sesuai daftar yang tersedia (cek ejaan/typo).")
        else:
            print("❗ [INFO] Pilih salah satu kategori yang tersedia di atas (hubungi Admin untuk tambah kategori).")

def muat_data():
    global data_barang, data_pengguna, list_riwayat_stok, data_kategori
    
    for file_txt in (FILE_PENGGUNA, FILE_BARANG, FILE_KATEGORI, FILE_TRANSAKSI, FILE_DETAIL, FILE_MASUK, FILE_KELUAR, FILE_LOG):
        if not file_txt.exists():
            file_txt.write_text("", encoding="utf-8")

    data_kategori = {}
    for baris in FILE_KATEGORI.read_text(encoding="utf-8").splitlines():
        if not baris.strip():
            continue
        kolom = baris.split("|")
        if len(kolom) >= 2:
            data_kategori[kolom[0].strip()] = kolom[1].strip()

    if not data_kategori:
        data_kategori = {
            "KAT001": "Sembako",
            "KAT002": "Makanan",
            "KAT003": "Minuman",
            "KAT004": "Snack",
            "KAT005": "Alat Kebersihan",
        }
        simpan_kategori()

    pengguna_aktif = {}
    pengguna_arsip = {}

    baris_pengguna = [baris for baris in FILE_PENGGUNA.read_text(encoding="utf-8-sig").splitlines() if baris.strip()]
    if not baris_pengguna:
        pengguna_aktif["ADM001"] = {
            "nama": "Administrator SMK MART",
            "username": "admin utama",
            "password": buat_hash_password("admin123"),
            "role": "admin",
            "date_added": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "date_modified": "-",
            "date_deleted": "-"
        }
    else:
        for indeks, baris in enumerate(baris_pengguna, start=1):
            kolom = baris.split("|")
            if len(kolom) < 5:
                continue
            username_data, password_data, nama_data, role_data, status_data = kolom[:5]
            username_data =  username_data.lstrip("\ufeff").strip()
            tanggal_tambah = kolom[5] if len(kolom) > 5 else datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            tanggal_ubah = kolom[6] if len(kolom) > 6 else "-"
            tanggal_hapus = kolom[7] if len(kolom) > 7 else "-"
            id_pengguna = "ADM001" if username_data == "admin utama" else f"USR{indeks:03d}"
            password_tersimpan = password_data if "$" in password_data else buat_hash_password(password_data)
            objek_pengguna = {
                "nama": nama_data,
                "username": username_data,
                "password": password_tersimpan,
                "role": role_data,
                "date_added": tanggal_tambah,
                "date_modified": tanggal_ubah,
                "date_deleted": tanggal_hapus
            }
            if status_data.lower() == "aktif":
                pengguna_aktif[id_pengguna] = objek_pengguna
            else:
                pengguna_arsip[id_pengguna] = objek_pengguna

        if "ADM001" not in pengguna_aktif:
            akun_admin_lama = pengguna_arsip.pop("ADM001", None)
            pengguna_aktif["ADM001"] = {
                "nama": "Administrator SMK MART",
                "username": "admin utama",
                "password": akun_admin_lama["password"] if akun_admin_lama else buat_hash_password("admin123"),
                "role": "admin",
                "date_added": akun_admin_lama["date_added"] if akun_admin_lama else datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "date_modified": "-",
                "date_deleted": "-"
        }

    data_pengguna = {
                "pengguna": pengguna_aktif,
                "arsip_pengguna": pengguna_arsip
    }
        
    barang_aktif = {}
    for baris in FILE_BARANG.read_text(encoding="utf-8").splitlines():
        if not baris.strip():
            continue
        kolom = baris.split("|")
        if len(kolom) < 6:
            continue
        kode_barang, nama_barang, kategori_barang, harga_barang, stok_barang, stok_minimum = kolom[:6]
        harga_pabrik_val = int(kolom[6]) if len(kolom) > 6 and kolom[6].isdigit() else int(harga_barang)
        expired_val = kolom[7].strip() if len(kolom) > 7 and kolom[7].strip() else "31-12-2099"
        status_val = kolom[8].strip() if len(kolom) > 8 and kolom[8].strip() else "Aktif"
        laba_default = hitung_laba(harga_pabrik_val, int(harga_barang))
        laba_lama_val = int(kolom[9]) if len(kolom) > 9 and kolom[9].lstrip("-").isdigit() else laba_default

        barang_aktif[kode_barang] = {
            "nama_barang": nama_barang,
            "kategori": kategori_barang,
            "stok": int(stok_barang),
            "stok_min": int(stok_minimum),
            "harga": int(harga_barang),
            "harga_pabrik": harga_pabrik_val,
            "harga_jual": int(harga_barang),
            "laba_lama": laba_lama_val,
            "expired": expired_val,
            "status": status_val
        }

    detail_per_transaksi = {}
    for baris in FILE_DETAIL.read_text(encoding="utf-8").splitlines():
        if not baris.strip():
            continue
        kolom = baris.split("|")
        if len(kolom) < 6:
            continue
        nomor_trx, kode_brg, nama_brg, harga_satuan, jumlah_beli, subtotal_beli = kolom[:6]
        harga_modal = int(kolom[6]) if len(kolom) > 6 and kolom[6].isdigit() else int(harga_satuan)
        detail_per_transaksi.setdefault(nomor_trx, []).append({
            "id_barang": kode_brg,
            "nama_barang": nama_brg,
            "harga": int(harga_satuan),
            "harga_pabrik": harga_modal,
            "jumlah": int(jumlah_beli),
            "subtotal": int(subtotal_beli)
        })

    daftar_transaksi = []
    nomor_urut_terakhir = 0
    for baris in FILE_TRANSAKSI.read_text(encoding="utf-8").splitlines():
        if not baris.strip():
            continue
        kolom = baris.split("|")
        if len(kolom) < 7:
            continue
        nomor_trx, tanggal_trx, waktu_trx, kasir_username, total_trx, bayar_trx, kembalian_trx = kolom[:7]

        subtotal_trx = int(kolom[7]) if len(kolom) > 7 else int(total_trx)
        ppn_trx = int(kolom[8]) if len(kolom) > 8 else 0
        tarif_ppn_trx = int(kolom[9]) if len(kolom) > 9 else 0

        if nomor_trx.startswith("TRX") and nomor_trx[3:].isdigit():
            nomor_urut_terakhir = max(nomor_urut_terakhir, int(nomor_trx[3:]))

        try:
            tanggal_tampil = datetime.strptime(
                tanggal_trx, "%Y-%m-%d"
            ).strftime("%d-%m-%Y")
        except ValueError:
            tanggal_tampil = tanggal_trx

        daftar_transaksi.append({
            "nomor": nomor_trx,
            "tanggal": f"{tanggal_tampil} {waktu_trx}",
            "kasir_username": kasir_username,
            "kasir_nama": kasir_username,
            "item": detail_per_transaksi.get(nomor_trx, []),
            "subtotal": subtotal_trx,
            "ppn": ppn_trx,
            "tarif_ppn": tarif_ppn_trx,
            "total": int(total_trx),
            "bayar": int(bayar_trx),
            "kembalian": int(kembalian_trx)
        })

    data_barang = {
        "barang": barang_aktif,
        "arsip_barang": {},
        "transaksi": daftar_transaksi,
        "nomor_berikutnya": nomor_urut_terakhir + 1
    }

    migrasi_harga_barang()
    simpan_data()
    return data_pengguna

def simpan_data(data_baru=None):
    sumber_barang = data_baru if data_baru else data_barang
    try:
        baris_pengguna = []
        for pengguna in data_pengguna.get("pengguna", {}).values():
            baris_pengguna.append(
                f"{pengguna['username']}|{pengguna['password']}|{pengguna['nama']}|{pengguna['role']}|aktif|"
                f"{pengguna.get('date_added', '-')}|{pengguna.get('date_modified', '-')}|{pengguna.get('date_deleted', '-')}"
            )
        for pengguna in data_pengguna.get("arsip_pengguna", {}).values():
            baris_pengguna.append(
                f"{pengguna['username']}|{pengguna['password']}|{pengguna['nama']}|{pengguna['role']}|nonaktif|"
                f"{pengguna.get('date_added', '-')}|{pengguna.get('date_modified', '-')}|{pengguna.get('date_deleted', '-')}"
            )
        FILE_PENGGUNA.write_text("\n".join(baris_pengguna) + ("\n" if baris_pengguna else ""), encoding="utf-8")

        baris_barang = []
        for kode_barang, barang in sumber_barang.get("barang", {}).items():
            kategori = barang.get("kategori", "Umum")
            stok_minimum = barang.get("stok_min", 5)
            harga_pabrik = int(ambil_harga_pabrik(barang))
            harga_jual = int(ambil_harga_jual(barang))
            laba_sekarang = hitung_laba(harga_pabrik, harga_jual)
            laba_lama = int(barang.get("laba_lama", laba_sekarang))
            expired = barang.get("expired", "31-12-2099")
            status = barang.get("status", "Aktif")
            baris_barang.append(
                f"{kode_barang}|{barang['nama_barang']}|{kategori}|{harga_jual}|"
                f"{int(barang['stok'])}|{int(stok_minimum)}|{harga_pabrik}|{expired}|{status}|{laba_lama}"
            )
        FILE_BARANG.write_text("\n".join(baris_barang) + ("\n" if baris_barang else ""), encoding="utf-8")

        baris_transaksi = []
        baris_detail = []
        for transaksi in sumber_barang.get("transaksi", []):
            bagian_waktu = transaksi["tanggal"].split(" ")
            tanggal_str = bagian_waktu[0]
            waktu_str = bagian_waktu[1] if len(bagian_waktu) > 1 else "00:00:00"
            try:
                tanggal_simpan = datetime.strptime(tanggal_str, "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError:
                tanggal_simpan = tanggal_str

            baris_transaksi.append(
                f"{transaksi['nomor']}|{tanggal_simpan}|{waktu_str}|"
                f"{transaksi.get('kasir_username', '-')}|"
                f"{int(transaksi['total'])}|"
                f"{int(transaksi['bayar'])}|"
                f"{int(transaksi['kembalian'])}|"
                f"{int(transaksi.get('subtotal', transaksi['total']))}|"
                f"{int(transaksi.get('ppn', 0))}|"
                f"{int(transaksi.get('tarif_ppn', 0))}"
            )
            
             )
                
            for item in transaksi.get("item", []):
                harga_modal = int(item.get("harga_pabrik", item["harga"]))
                baris_detail.append(
                f"{transaksi['nomor']}|{item['id_barang']}|{item['nama_barang']}|"
                f"{int(item['harga'])}|{int(item['jumlah'])}|{int(item['subtotal'])}|{harga_modal}"
            )
                
        FILE_TRANSAKSI.write_text("\n".join(baris_transaksi) + ("\n" if baris_transaksi else ""), encoding="utf-8")
        FILE_DETAIL.write_text("\n".join(baris_detail) + ("\n" if baris_detail else ""), encoding="utf-8")
        return True
    except OSError as error:
        print(f"⚠️[ERROR] Gagal menyimpan database: {error}")
        return False

def username_terpakai(username, kecuali_id=None):
    dipakai_aktif = any(
        pengguna["username"] == username and id_pengguna != kecuali_id
        for id_pengguna, pengguna in data_pengguna["pengguna"].items()
    )
    dipakai_arsip = any(
        pengguna["username"] == username and id_pengguna != kecuali_id
        for id_pengguna, pengguna in data_pengguna.get("arsip_pengguna", {}).items()
    )
    return dipakai_aktif or dipakai_arsip

def catat_log(role, aktivitas, username="sistem"):
    sekarang = datetime.now()
    tanggal_iso = sekarang.strftime("%Y-%m-%d")
    waktu_jam = sekarang.strftime("%H:%M:%S")

    try:
        with FILE_LOG.open("a", encoding="utf-8") as file_utama:
            file_utama.write(f"{tanggal_iso}|{waktu_jam}|{username}|{aktivitas}\n")

        nama_file_role = DATA_DIR / f"log_{role.lower()}.txt"
        with nama_file_role.open("a", encoding="utf-8") as file_role:
            file_role.write(f"[{sekarang.strftime('%d-%m-%Y %H:%M:%S')}] ({username}) {aktivitas}\n")
    except OSError:
        pass

def konfirmasi_default(pesan):
    while True:
        jawab = input(f"{pesan} [Y/t]: ").strip().lower()
        if jawab in ("y", ""):
            return True
        elif jawab == "t":
            return False
        print("⚠️[ERROR] Tekan Enter / 'y' untuk Ya, atau ketik 't' untuk Tidak.")

def input_rentang_tanggal():
    while True:
        tgl_awal_str = input_wajib("Tanggal awal (DD-MM-YYYY): ")
        tgl_akhir_str = input_wajib("Tanggal akhir (DD-MM-YYYY): ")
        try:
            tgl_awal = datetime.strptime(tgl_awal_str, "%d-%m-%Y").date()
            tgl_akhir = datetime.strptime(tgl_akhir_str, "%d-%m-%Y").date()
            if tgl_awal > tgl_akhir:
                print("⚠️[ERROR] Tanggal awal tidak boleh lebih besar dari tanggal akhir!")
                continue
            return tgl_awal, tgl_akhir
        except ValueError:
            print("⚠️[ERROR] Format tanggal harus DD-MM-YYYY.")

def simpan_teks_laporan(nama_file, isi_laporan):
    if konfirmasi_default("Simpan laporan ini ke file .txt di folder laporan?"):
        FOLDER_LAPORAN.mkdir(parents=True, exist_ok=True)
        path_file = FOLDER_LAPORAN / nama_file
        path_file.write_text(isi_laporan, encoding="utf-8")
        print(f"✅[SUKSES] Laporan disimpan ke: {path_file}")

# ==========================================
# FITUR ADMIN (PENGGUNA)
# ==========================================
def tampilkan_data_pengguna():
    print("\n" + "=" * 128)
    print("TAMPILAN SEMUA AKUN / USER (TERURUT BERDASARKAN ROLE)".center(128))
    print("=" * 128)

    semua_akun = []
    for id_pengguna, pengguna in data_pengguna.get("pengguna", {}).items():
        semua_akun.append((id_pengguna, pengguna, "AKTIF"))
    for id_pengguna, pengguna in data_pengguna.get("arsip_pengguna", {}).items():
        semua_akun.append((id_pengguna, pengguna, "NONAKTIF"))

    if not semua_akun:
        print("❗[INFO] Belum ada data pengguna yang tersimpan.")
        return

    urutan_role = {"admin": 1, "gudang": 2, "kasir": 3}

    def kunci_urut(item):
        id_pengguna, pengguna, status = item
        prioritas = urutan_role.get(pengguna.get("role", "").lower(), 99)
        return (prioritas, id_pengguna)

    n = len(semua_akun)

    def heapify(arr, n, i):
        terbesar = i
        kiri = 2 * i + 1
        kanan = 2 * i + 2

        if kiri < n and kunci_urut(arr[kiri]) > kunci_urut(arr[terbesar]):
            terbesar = kiri
        if kanan < n and kunci_urut(arr[kanan]) > kunci_urut(arr[terbesar]):
            terbesar = kanan

        if terbesar != i:
            arr[i], arr[terbesar] = arr[terbesar], arr[i]
            heapify(arr, n, terbesar)

    for i in range(n // 2 - 1, -1, -1):
        heapify(semua_akun, n, i)

    for i in range(n - 1, 0, -1): 
        semua_akun[0], semua_akun[i] = semua_akun[i], semua_akun[0]
        heapify(semua_akun, i, 0)

    print(
        f"{'ID':<9} | {'NAMA':<18} | {'ROLE':<8} | {'STATUS':<9} | "
        f"{'DATE_ADDED':<22} | {'DATE_MODIFIED':<22} | {'DATE_DELETED':<22}"
    )
    print("=" * 128)

    for id_pengguna, pengguna, status in semua_akun:
        print(
            f"{id_pengguna:<9} | "
            f"{pengguna['nama'][:18]:<18} | "
            f"{pengguna.get('role', '-').upper():<8} | "
            f"{status:<9} | "
            f"{pengguna.get('date_added', '-'):<22} | "
            f"{pengguna.get('date_modified', '-'):<22} | "
            f"{pengguna.get('date_deleted', '-'):<22}"
        )

    print("=" * 128)
    total_aktif = len(data_pengguna.get("pengguna", {}))
    total_nonaktif = len(data_pengguna.get("arsip_pengguna", {}))
    total_semua = total_aktif + total_nonaktif
    print(f"Total: {total_semua} Akun ({total_aktif} Aktif, {total_nonaktif} Nonaktif)")
    print("=" * 128)
    
def tambah_pengguna():
    lebar = 108
    print("=" * 108)
    print("--- TAMBAH DATA PENGGUNA ---".center(108))
    print("=" * 108)
    
    while True:
      id_pengguna = buat_id_dict_otomatis(
        data_pengguna["pengguna"], data_pengguna.get("arsip_pengguna", {}), "USR"
    )
      if (
            id_pengguna not in data_pengguna["pengguna"]
            and id_pengguna not in data_pengguna.get("arsip_pengguna", {})
        ):
        break

    print(f"❗[INFO] ID Pengguna berhasil dibuat otomatis: {id_pengguna}")
    nama = input_wajib("Silahkan masukkan nama anda : ").strip()
    while True:
      username = input_wajib("Masukkan username anda : ").strip().lower()
      if username_terpakai(username):
          print("⚠️ [ERROR] Username sudah dipakai.")
          continue
      break
    
    while True:
        password = input_password_simple("Masukkan password anda : ")
        if len(password) >= 6:
            break
        print("⚠️ [ERROR] Password minimal 6 karakter!")

    while True:
        kode_role = input_wajib("Pilih role ([A]dmin / [G]udang / [K]asir): ").strip().lower()
        if kode_role in MAP_ROLE:
            role = MAP_ROLE[kode_role]
            break
        print("⚠️ [ERROR] Role tidak valid. Ketik A, G, atau K.")

    data_pengguna["pengguna"][id_pengguna] = {
        "nama" : nama,
        "username" : username,
        "password" : buat_hash_password(password),
        "role" : role,
        "date_added": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "date_modified": "-",
        "date_deleted": "-"
            }

    if simpan_data():
        print( "=" * lebar)
        print(f"✅[SUKSES] Pengguna '{nama}' berhasil ditambahkan!")
        print( "=" * lebar)
    else:
        del data_pengguna["pengguna"][id_pengguna]
    

def edit_pengguna():
    tampilkan_data_pengguna()
    lebar = 55
    print("=" * lebar)
    print("--- EDIT DATA PENGGUNA ---".center(lebar))
    print("=" * lebar)
    
    id_pengguna = input("Masukkan ID pengguna yang ingin diedit: ").strip().upper()

    if id_pengguna in data_pengguna["pengguna"]:
        pengguna = data_pengguna["pengguna"][id_pengguna]

        print("Kosongkan input jika tidak ingin diubah.")
        print("=" * lebar)
        
        nama_baru = input(f"Nama baru [{pengguna['nama']}]: ").strip()
        username_baru = input(f"Username baru [{pengguna['username']}]: ").strip().lower()
        print("=" * lebar)
        
        if username_baru and username_terpakai(username_baru, id_pengguna):
            print("⚠️[ERROR] Username sudah digunakan pengguna lain.")
            return

        password_baru = input_password_simple("Password baru [Kosongkan jika tetap]: ", boleh_kosong=True)
        role_input = input(f"Role baru [{pengguna['role']}] ([A]dmin / [G]udang / [K]asir): ").strip().lower()

        role_baru_final = pengguna['role']
        if role_input:
            if role_input in MAP_ROLE:
                pengguna['role'] = MAP_ROLE[role_input]
            else:
                print("=" * lebar)
                print("⚠️ [GAGAL] Role tidak valid. Gunakan A (admin), G (gudang), atau K (kasir).")
                print("=" * lebar)
                return

        nama_baru_final = nama_baru if nama_baru else pengguna['nama']
        username_baru_final = username_baru if username_baru else pengguna['username']
        status_password_baru = "Diubah" if password_baru else "Tetap"

        print("\n" + "=" * 65)
        print(f"📋 PRATINJAU PERUBAHAN DATA PENGGUNA (ID: {id_pengguna})")
        print("=" * 65)
        print(f"{'Kategori':<15} | {'Data Lama':<20} | {'Data Baru':<20}")
        print("-" * 65)
        print(f"{'Nama':<15} | {str(pengguna['nama']):<20} | {str(nama_baru_final):<20}")
        print(f"{'Username':<15} | {str(pengguna['username']):<20} | {str(username_baru_final):<20}")
        print(f"{'Role':<15} | {str(pengguna['role']):<20} | {str(role_baru_final):<20}")
        print(f"{'Password':<15} | {'********':<20} | {status_password_baru:<20}")
        print("=" * 65)

        if not konfirmasi_default("Apakah Anda yakin ingin menyimpan perubahan ini?"):
            print("❌ Perubahan dibatalkan.")
            return
        # ---------------------------------------------------

        if nama_baru:
            pengguna['nama'] = nama_baru
        if username_baru:
            pengguna['username'] = username_baru
        if password_baru:
            pengguna['password'] = buat_hash_password(password_baru)
        if role_input:
            pengguna['role'] = role_baru_final

        pengguna['date_modified'] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        pengguna['date_deleted'] = "-"

        if simpan_data():
            print("=" * lebar)
            print("✅[SUKSES] Data pengguna berhasil diedit")
            print("=" * lebar)
    else:
        print("=" * lebar)
        print("⚠️ [ERROR] ID pengguna tidak ditemukan.")
        print("=" * lebar)

def hapus_pengguna(admin_login):
    lebar = 55
    print("=" * lebar)
    print("--- HAPUS DATA PENGGUNA ---".center(lebar))
    print("=" * lebar)
    
    id_pengguna = input("Masukkan ID pengguna yang ingin dihapus: ").strip().upper()

    if id_pengguna in data_pengguna["pengguna"]:
        if id_pengguna == admin_login:
            print("=" * lebar)
            print("⚠️ [ERROR] Tidak boleh menghapus akun admin yang sedang dipakai.")
            print("=" * lebar)
            return

        pengguna_dihapus = data_pengguna["pengguna"].pop(id_pengguna)
        data_pengguna.setdefault("arsip_pengguna", {})[id_pengguna] = pengguna_dihapus
        pengguna_dihapus["date_deleted"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        if simpan_data():
          print("=" * lebar)
          print(f"Data '{pengguna_dihapus['nama']}' berhasil diarsipkan.")
          print("=" * lebar)   
          catat_log("admin", f"Menghapus pengguna {pengguna_dihapus['nama']} ({id_pengguna})")
     
        else:
         print("=" * lebar)
         print("⚠️ [ERROR] ID pengguna tidak ditemukan.")
         print("=" * lebar)
            
def cari_pengguna():
 lebar = 108
 print( "="  * lebar )  
 print("PENCARIAN DATA PENGGUNA".center(lebar))
 print( "="  * lebar )  

 keyword = input_wajib(
     "Masukkan nama atau ID pengguna: "
 ).strip()

 # 1. Prioritaskan pencarian berdasarkan ID
 id_pengguna = keyword.upper()
 pengguna = data_pengguna["pengguna"].get(id_pengguna)

 if pengguna:
     print( "="  * lebar )  
     print("[DATA PENGGUNA DITEMUKAN]".center(lebar))
     print( "="  * lebar )  
     print(f"ID PENGGUNA : {id_pengguna}")
     print(f"NAMA        : {pengguna['nama']}")
     print(f"USERNAME    : @{pengguna.get('username', '-')}")
     print(f"ROLE        : {pengguna['role']}")
     print( "="  * lebar )  
     return

 # 2. Jika bukan ID, cari berdasarkan nama
 hasil = [
     (kunci, pengguna)
     for kunci, pengguna in data_pengguna["pengguna"].items()
     if keyword.casefold() in pengguna["nama"].casefold()
 ]

 if not hasil:
     print( "="  * lebar )  
     print("⚠️[ERROR] Pengguna tidak ditemukan.")
     print( "="  * lebar )  
     return
     
 print( "="  * lebar )  
 print("=== HASIL PENCARIAN PENGGUNA ===".center(lebar))
 print( "="  * lebar )  
 for id_pengguna, pengguna in hasil:
     print( "="  * lebar )  
     print(f"ID PENGGUNA : {id_pengguna}")
     print(f"NAMA        : {pengguna['nama']}")
     print(f"USERNAME    : @{pengguna.get('username', '-')}")
     print(f"ROLE        : {pengguna['role']}")
     print( "="  * lebar )  

def tampilkan_data_terhapus():
    lebar = 108
    print( "=" *lebar)
    print("DATA YANG TELAH DIHAPUS".center(lebar))
    print( "=" * lebar )   
          
    for id_pengguna, pengguna in data_pengguna.get("arsip_pengguna", {}).items():
        print(
            f"ID: {id_pengguna:<8} | "
            f"Nama: {pengguna['nama'][:18]:<18} | "
            f"Role: {pengguna['role']:<7}"
        )
        print( "=" * lebar )
    for id_barang, barang in data_barang.get("arsip_barang", {}).items():
     
        print(
            f"ID: {id_barang:<8} | "
            f"Nama: {barang['nama_barang'][:20]:<20} | "
            f"Stok: {barang['stok']:>4} | "
            f"Harga: {rupiah(barang['harga']):>10}"
        )
    print("=" * lebar)

def hapus_transaksi():
    lebar = 88
    print ( "=" * lebar )
    print("=== HAPUS DATA TRANSAKSI ===".center(lebar))
    print ( "=" * lebar )

    if not data_barang["transaksi"]:
        print ( "=" * lebar )
        print("❗[INFO] Belum ada riwayat transaksi yang tersimpan.")
        print ( "=" * lebar )
        return

    riwayat_transaksi()
    nomor = input_wajib("Masukkan Nomor Transaksi yang ingin dihapus(contoh: TRX001): ").upper()

    transaksi_ditemukan = None
    for t in data_barang["transaksi"]:
        if t["nomor"] == nomor:
            transaksi_ditemukan = t
            break

    if not transaksi_ditemukan:
        print(f"⚠️[ERROR] Transaksi dengan nomor '{nomor}' tidak ditemukan.")
        return
        
    print( "=" * lebar ) 
    print(f"--- DETAIL TRANSAKSI ---".center(lebar))
    print ( "-" * lebar )
    print(f"No. Transaksi : {transaksi_ditemukan['nomor']}")
    print(f"Tanggal       : {transaksi_ditemukan['tanggal']}")
    print(f"Kasir         : {transaksi_ditemukan['kasir_nama']}")
    print(f"Total         : {rupiah(transaksi_ditemukan['total'])}")
    print( "=" * lebar )

    kembalikan_stok = konfirmasi_default("Kembalikan stok pada transaksi ini ke gudang?")
    if konfirmasi_default(f"Yakin ingin menghapus transaksi {nomor}?"):
        if kembalikan_stok:
            for item in transaksi_ditemukan["item"]:
                id_brg = item["id_barang"]
                jml = item["jumlah"]
                if id_brg in data_barang["barang"]:
                    data_barang["barang"][id_brg]["stok"] += jml
            print( "=" * lebar )        
            print("[INFO] Stok barang berhasil dikembalikan ke gudang.")
            print( "=" * lebar ) 
            
        data_barang["transaksi"].remove(transaksi_ditemukan)

        if simpan_data(): 
            print(f"✅[SUKSES] Transaksi {nomor} berhasil dihapus dari database.")
        else:
            print("❌[ERROR] Gagal menyimpan perubahan ke database.")
    else:
        print("[INFO] Penghapusan transaksi dibatalkan.")
    print( "=" * lebar ) 

def riwayat_transaksi():
    lebar = 68
    print("\n" + "=" * lebar)
    print("RIWAYAT TRANSAKSI".center(lebar))
    print("=" * lebar)
    if not data_barang["transaksi"]:
        print("😕Belum ada transaksi.")
        return

    print(f"{'NO. TRX':<10} | {'TANGGAL':<19} | {'KASIR':<16} | {'TOTAL':>12}")
    print("-" * lebar)
    for data_transaksi in data_barang["transaksi"]:
        print(
            f"{data_transaksi['nomor']:<10} | "
            f"{data_transaksi['tanggal']:<19} | "
            f"{data_transaksi['kasir_nama'][:16]:<16} | "
            f"{rupiah(data_transaksi['total']):>12}"
        )
    print("=" * lebar)

def laporan_penjualan_admin():
    lebar = 76
    baris_laporan = [
        "=" * lebar,
        "LAPORAN PENJUALAN".center(lebar)
    ]

    if not data_barang["transaksi"]:
        print("\n".join(baris_laporan))
        print("[INFO] Belum ada transaksi penjualan.")
        return

    print("\nPilih Mode Laporan Penjualan:")
    print("1. Ringkasan Otomatis (Hari Ini, Minggu Ini, Bulan Ini)")
    print("2. Filter Rentang Tanggal (Sesuai Ketentuan SAS)")
    mode = input("Pilih mode laporan (1/2): ").strip()

    hari_ini = datetime.now().date()
    awal_minggu = hari_ini - timedelta(days=hari_ini.weekday())
    awal_bulan = hari_ini.replace(day=1)

    periode = {}
    if mode == "1":
        periode = {
            "PENJUALAN HARI INI": [],
            "PENJUALAN MINGGU INI": [],
            "PENJUALAN BULAN INI": []
        }
        for transaksi in data_barang["transaksi"]:
            try:
                tanggal_transaksi = datetime.strptime(
                    transaksi["tanggal"], "%d-%m-%Y %H:%M:%S"
                ).date()
            except (ValueError, KeyError):
                continue

            if tanggal_transaksi == hari_ini:
                periode["PENJUALAN HARI INI"].append(transaksi)
            if awal_minggu <= tanggal_transaksi <= hari_ini:
                periode["PENJUALAN MINGGU INI"].append(transaksi)
            if awal_bulan <= tanggal_transaksi <= hari_ini:
                periode["PENJUALAN BULAN INI"].append(transaksi)
    elif mode == "2":
        tgl_awal, tgl_akhir = input_rentang_tanggal()
        periode_teks = f"PERIODE: {tgl_awal.strftime('%d-%m-%Y')} s.d. {tgl_akhir.strftime('%d-%m-%Y')}"
        daftar_filter = []
        for transaksi in data_barang["transaksi"]:
            try:
                tanggal_transaksi = datetime.strptime(
                    transaksi["tanggal"], "%d-%m-%Y %H:%M:%S"
                ).date()
            except (ValueError, KeyError):
                continue
            if tgl_awal <= tanggal_transaksi <= tgl_akhir:
                daftar_filter.append(transaksi)
        periode[periode_teks] = daftar_filter
    else:
        print("Pilihan mode tidak valid.")
        return

    for judul, daftar_transaksi in periode.items():
        total_penjualan = sum(
            transaksi["total"] for transaksi in daftar_transaksi
        )
        transaksi_lengkap = [
            transaksi
            for transaksi in daftar_transaksi
            if hitung_laba_kotor_transaksi(transaksi) is not None
        ]
        total_laba_kotor = sum(
            hitung_laba_kotor_transaksi(transaksi)
            for transaksi in transaksi_lengkap
        )

        baris_laporan.append("=" * lebar)
        baris_laporan.append(f" {judul}".center(lebar))
        baris_laporan.append("-" * lebar)

        if not daftar_transaksi:
            baris_laporan.append("Belum ada transaksi pada periode ini.")
            baris_laporan.append("=" * lebar)
            baris_laporan.append("Jumlah transaksi : 0")
            baris_laporan.append(f"Total penjualan  : {rupiah(0)}")
            baris_laporan.append(f"Laba kotor       : {rupiah(0)}")
            continue

        rekap_kasir = {}
        rekap_barang = {}
        for transaksi in daftar_transaksi:
            baris_laporan.append(
                f"{transaksi['nomor']} | "
                f"{transaksi['tanggal']} | "
                f"{transaksi['kasir_nama']} | "
                f"{rupiah(transaksi['total'])}"
            )

            kasir_username = transaksi.get("kasir_username", "-")
            if kasir_username not in rekap_kasir:
                rekap_kasir[kasir_username] = {
                    "jumlah_transaksi": 0,
                    "total_penjualan": 0
                }
            rekap_kasir[kasir_username]["jumlah_transaksi"] += 1
            rekap_kasir[kasir_username]["total_penjualan"] += int(transaksi["total"])

            for item in transaksi.get("item", []):
                id_barang = item["id_barang"]
                if id_barang not in rekap_barang:
                    rekap_barang[id_barang] = {
                        "nama_barang": item["nama_barang"],
                        "jumlah_terjual": 0
                    }
                rekap_barang[id_barang]["jumlah_terjual"] += int(item["jumlah"])

        baris_laporan.append("=" * lebar)
        baris_laporan.append(f"Jumlah transaksi : {len(daftar_transaksi)}")
        baris_laporan.append(f"Total penjualan  : {rupiah(total_penjualan)}")
        baris_laporan.append(f"Laba kotor       : {rupiah(total_laba_kotor)}")
        if len(transaksi_lengkap) < len(daftar_transaksi):
            baris_laporan.append(
                "[PERINGATAN] Sebagian transaksi lama "
                "belum memiliki data modal."
            )

        baris_laporan.append("-" * lebar)
        baris_laporan.append("5 BARANG TERLARIS".center(lebar))
        baris_laporan.append("-" * lebar)
        barang_urut = sorted(
            rekap_barang.items(),
            key=lambda x: (-x[1]["jumlah_terjual"], x[0])
        )[:5]
        for peringkat, (id_barang, info_barang) in enumerate(barang_urut, start=1):
            baris_laporan.append(
                f"{peringkat}. {id_barang} | {info_barang['nama_barang']} : {info_barang['jumlah_terjual']} unit"
            )

        baris_laporan.append("-" * lebar)
        baris_laporan.append("TOTAL PENJUALAN PER KASIR".center(lebar))
        baris_laporan.append("-" * lebar)
        for kasir_username, info_kasir in sorted(rekap_kasir.items()):
            baris_laporan.append(
                f"{kasir_username:<20} : {info_kasir['jumlah_transaksi']} transaksi ({rupiah(info_kasir['total_penjualan'])})"
            )

    baris_laporan.append("=" * lebar)
    baris_laporan.append("LAPORAN SELESAI".center(lebar))
    baris_laporan.append("=" * lebar)

    isi_laporan = "\n".join(baris_laporan)
    print("\n" + isi_laporan)

    nama_file = f"laporan_penjualan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    simpan_teks_laporan(nama_file, isi_laporan)

def kelola_status_barang():
    lebar = 66
    while True:
        lebar = 68
        print("\n" + "=" * lebar)
        print("KELOLA STATUS BARANG".center(lebar))
        print("=" * lebar)

        barang_aktif = data_barang.get("barang", {})
        barang_arsip = data_barang.get("arsip_barang", {})

        if not barang_aktif and not barang_arsip:
            print("❗[INFO] Belum ada data barang yang tersimpan.")
            print("=" * lebar)
            return

        print("--- [ BARANG DI ETALASE / GUDANG ] ---")
        if not barang_aktif:
            print("(Kosong)")
        else:
            print(f"{'ID':<9} | {'NAMA BARANG':<22} | {'STOK':>6} | {'STATUS':<10}")
            print("-" * 56)
            for id_barang, barang in barang_aktif.items():
                status = barang.get("status", "Aktif")
                print(
                    f"{id_barang:<9} | "
                    f"{barang['nama_barang'][:22]:<22} | "
                    f"{barang['stok']:>6} | "
                    f"{status:<10}"
                )

        print("\n--- [ BARANG NONAKTIF / RUSAK ] ---")
        if not barang_arsip:
            print("(Kosong)")
        else:
            print(f"{'ID':<9} | {'NAMA BARANG':<22} | {'STOK':>6} | {'STATUS':<10}")
            print("-" * 56)
            for id_barang, barang in barang_arsip.items():
                status = barang.get("status", "Nonaktif")
                print(
                    f"{id_barang:<9} | "
                    f"{barang['nama_barang'][:22]:<22} | "
                    f"{barang['stok']:>6} | "
                    f"{status:<10}"
                )

        print("MENU STATUS BARANG".center(lebar))
        print("-" * lebar)
        print("1. Ubah status barang (Aktif/Nonaktif/Rusak)")
        print("2. Aktifkan kembali barang dari arsip")
        print("0. Kembali ke menu admin")
        print("=" * lebar)

        pilihan = input("Masukkan pilihan (0-2): ").strip()
        if pilihan == "0":
            break

        elif pilihan == "1":
            id_barang = input("Masukkan ID barang yang ingin diubah statusnya: ").strip().upper()
            if id_barang not in barang_aktif:
                print("⚠️ [ERROR] ID barang tidak ditemukan di etalase/gudang.")
                continue

            print("-" * lebar)
            print("Pilih status baru:")
            print("1. Aktif (layak jual)")
            print("2. Rusak (tidak layak jual)")
            print("3. Nonaktif (pindahkan ke arsip / off)")
            print("0. Batal")
            print("-" * lebar)
            pilihan_status = input("Masukkan pilihan status (0-3): ").strip()

            if pilihan_status == "0":
                print("❗[INFO] Perubahan status dibatalkan.")
                continue

            if pilihan_status == "1":
                status_lama = barang_aktif[id_barang].get("status", "Aktif")
                barang_aktif[id_barang]["status"] = "Aktif"
                if simpan_data():
                    print(f"✅ [SUKSES] Status '{barang_aktif[id_barang]['nama_barang']}' diubah menjadi Aktif.")
                    catat_log("admin", f"Mengubah status barang {barang_aktif[id_barang]['nama_barang']} ({id_barang}) menjadi Aktif")
                else:
                    barang_aktif[id_barang]["status"] = status_lama
                    print("⚠️ [ERROR] Gagal menyimpan perubahan ke database.")

            elif pilihan_status == "2":
                status_lama = barang_aktif[id_barang].get("status", "Aktif")
                barang_aktif[id_barang]["status"] = "Rusak"
                if simpan_data():
                    print(f"✅ [SUKSES] Status '{barang_aktif[id_barang]['nama_barang']}' diubah menjadi Rusak.")
                    catat_log("admin", f"Mengubah status barang {barang_aktif[id_barang]['nama_barang']} ({id_barang}) menjadi Rusak")
                else:
                    barang_aktif[id_barang]["status"] = status_lama
                    print("⚠️ [ERROR] Gagal menyimpan perubahan ke database.")

            elif pilihan_status == "3":
                status_lama = barang_aktif[id_barang].get("status", "Aktif")
                barang_dihapus = barang_aktif.pop(id_barang)
                barang_dihapus["status"] = "Nonaktif"
                data_barang.setdefault("arsip_barang", {})[id_barang] = barang_dihapus
                if simpan_data():
                    print(f"✅ [SUKSES] Barang '{barang_dihapus['nama_barang']}' dipindahkan ke arsip (Nonaktif).")
                    catat_log("admin", f"Memindahkan barang {barang_dihapus['nama_barang']} ({id_barang}) ke arsip (Nonaktif)")
                else:
                    # Rollback jika gagal simpan
                    barang_dihapus["status"] = status_lama
                    barang_aktif[id_barang] = data_barang["arsip_barang"].pop(id_barang)
                    print("⚠️ [ERROR] Gagal menyimpan perubahan ke database.")

            else:
                print("⚠️ [ERROR] Pilihan status tidak valid.")

        elif pilihan == "2":
            id_barang = input("Masukkan ID barang yang ingin diaktifkan kembali dari arsip: ").strip().upper()
            if id_barang not in barang_arsip:
                print("⚠️ [ERROR] ID barang tidak ditemukan di arsip.")
                continue

            status_lama = barang_arsip[id_barang].get("status", "Nonaktif")
            barang_aktif[id_barang] = barang_arsip.pop(id_barang)
            barang_aktif[id_barang]["status"] = "Aktif"
            if simpan_data():
                print(f"✅ [SUKSES] Barang '{barang_aktif[id_barang]['nama_barang']}' diaktifkan kembali dari arsip.")
                catat_log("admin", f"Mengaktifkan kembali barang {barang_aktif[id_barang]['nama_barang']} ({id_barang}) dari arsip")
            else:
                # Rollback jika gagal simpan
                barang_aktif[id_barang]["status"] = status_lama
                barang_arsip[id_barang] = barang_aktif.pop(id_barang)
                print("⚠️ [ERROR] Gagal menyimpan perubahan ke database.")
        else:
            print("⚠️ [ERROR] Pilihan menu tidak valid (pilih 0-2).")

def reset_password_pengguna(admin_login):
    tampilkan_data_pengguna()
    id_pengguna = input_wajib("Masukkan ID pengguna yang akan di-reset passwordnya: ").upper()
    if id_pengguna not in data_pengguna["pengguna"]:
        print("⚠️[ERROR] ID pengguna tidak ditemukan.")
        return
    while True:
        password_baru = input_password_simple("Masukkan password baru (minimal 6 karakter): ")
        if len(password_baru) >= 6:
            break
        print("⚠️[ERROR] Password minimal 6 karakter.")
    data_pengguna["pengguna"][id_pengguna]["password"] = buat_hash_password(password_baru)
    data_pengguna["pengguna"][id_pengguna]["date_modified"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    if simpan_data():
        pelaku = data_pengguna["pengguna"][admin_login]["username"]
        catat_log("admin", f"Reset password pengguna {id_pengguna}", pelaku)
        print(f"✅[SUKSES] Password untuk {id_pengguna} berhasil di-reset.")

# ==========================================
# FITUR GUDANG
# ==========================================
def tampilkan_barang():
    lebar = 148
    print("=" * lebar)
    print("TAMPILAN DATA BARANG (TERURUT BERDASARKAN NAMA A-Z)".center(lebar))
    print("=" * lebar)
    
    if not data_barang["barang"]:
        print("❗[INFO] Belum ada data barang yang tersimpan.")
        return

    semua_barang = list(data_barang["barang"].items())
    jumlah_data = len(semua_barang)

    def heapify(arr, n, i):
        terbesar = i
        kiri = 2 * i + 1
        kanan = 2 * i + 2
        if kiri < n and arr[kiri][1]["nama_barang"].casefold() > arr[terbesar][1]["nama_barang"].casefold():
            terbesar = kiri
        if kanan < n and arr[kanan][1]["nama_barang"].casefold() > arr[terbesar][1]["nama_barang"].casefold():
            terbesar = kanan
        if terbesar != i:
            arr[i], arr[terbesar] = arr[terbesar], arr[i]
            heapify(arr, n, terbesar)

    for i in range(jumlah_data // 2 - 1, -1, -1):
        heapify(semua_barang, jumlah_data, i)
    for i in range(jumlah_data - 1, 0, -1):
        semua_barang[0], semua_barang[i] = semua_barang[i], semua_barang[0]
        heapify(semua_barang, i, 0)

    print(
            f"{'ID':<7} | {'NAMA BARANG':<18} | {'KATEGORI':<15} | {'STOK':>4} | "
            f"{'HARGA PABRIK':>12} | {'HARGA JUAL':>12} | {'LABA LAMA':>11} | {'LABA BARU':>11} | "
            f"{'EXPIRED':<10} | {'STATUS DISKON':<16}"
        )
    
    print("-" * lebar)

    for id_barang, barang in semua_barang:
        pabrik = ambil_harga_pabrik(barang)
        jual = ambil_harga_jual(barang)
        laba_baru = hitung_laba(pabrik, jual)
        laba_lama = barang.get("laba_lama", laba_baru)
        sisa_hari, potongan, harga_akhir = hitung_diskon_expired(barang)

        if sisa_hari is not None and 1 <= sisa_hari <= 5:
            status_diskon = f"MENDAPAT DISKON 4% ({rupiah(harga_akhir)})"
        elif sisa_hari is not None and sisa_hari <= 0:
            status_diskon = "BARANG SUDAH EXPIRED"
        else:
            status_diskon = "TIDAK ADA DISKON"

        print(
            f"{id_barang:<7} | {barang['nama_barang'][:18]:<18} | {barang.get('kategori', '-')[:14]:<14} | {barang['stok']:>4} | "
            f"{rupiah(pabrik):>12} | {rupiah(jual):>12} | {rupiah(laba_lama):>11} | {rupiah(laba_baru):>11} | "
            f"{barang.get('expired', '-'):<10} | {status_diskon:<16}"
        )

    print("=" * lebar)
    print(f"Total Barang: {jumlah_data} Item")
    print("=" * lebar)


def tambah_barang():
    lebar = 77
    print("=" * lebar)
    print("=== TAMBAH BARANG ===".center(lebar))
    print("=" * lebar)

    while True:
        id_barang = buat_id_dict_otomatis(
        data_barang["barang"], data_barang.get("arsip_barang", {}), "BRG"
    )
        if (
            id_barang not in data_barang["barang"]
            and id_barang not in data_barang.get("arsip_barang", {})
        ):
            break

    print(f"❗[INFO] ID Barang otomatis: {id_barang}")
    print("-" * lebar)

    print("(Ketik 0 pada input mana saja untuk membatalkan)")
    nama = input_wajib("Nama barang (0 untuk batal): ")
    if nama == "0":
        print("❗[INFO] Tambah barang dibatalkan.")
        return

    kategori = pilih_kategori_valid(izin_tambah=True)
    if kategori == "0":
        print("❗[INFO] Tambah barang dibatalkan.")
        return

    stok_min = input_angka("Stok minimum (minimal 0): ", 0)
    harga_pabrik = input_angka("Harga dari pabrik (Rp, 0 untuk batal): ", 0)
    if harga_pabrik == 0:
        print("❗[INFO] Tambah barang dibatalkan.")
        return

    harga_jual = input_angka("Harga jual (Rp, 0 untuk batal): ", 0)
    if harga_jual == 0:
        print("❗[INFO] Tambah barang dibatalkan.")
        return

    while True:
        tanggal_str = input_wajib("Tanggal expired (DD-MM-YYYY, 0 untuk batal): ").strip()
        if tanggal_str == "0":
            print("❗[INFO] Tambah barang dibatalkan.")
            return
        try:
            datetime.strptime(tanggal_str, "%d-%m-%Y")
            break
        except ValueError:
            print("⚠️ [ERROR] Format tanggal tidak valid (contoh: 25-12-2026).")

    while True:
        tanggal_str = input_wajib("Tanggal expired (DD-MM-YYYY): ").strip()
        try:
            datetime.strptime(tanggal_str, "%d-%m-%Y")
            break
        except ValueError:
            print("⚠️ [ERROR] Format tanggal tidak valid (contoh: 25-12-2026).")

    laba = hitung_laba(harga_pabrik, harga_jual)

    data_barang["barang"][id_barang] = {
        "nama_barang": nama,
        "kategori": kategori,
        "stok": 0,
        "stok_min": stok_min,
        "harga": harga_jual,
        "harga_pabrik": harga_pabrik,
        "harga_jual": harga_jual,
        "laba_per_barang": laba,
        "expired": tanggal_str,
        "status": "Aktif"
    }

    if simpan_data():
        print("=" * lebar)
        print(f"✅ [BERHASIL] '{nama}' ({id_barang}) ditambahkan.")
        print("-" * lebar)
        print(f"Harga pabrik  : {rupiah(harga_pabrik)}")
        print(f"Harga jual    : {rupiah(harga_jual)}")
        print(f"Laba per unit : {rupiah(laba)}")
        print("=" * lebar)
    else:
        del data_barang["barang"][id_barang]
        print("⚠️ [ERROR] Gagal menyimpan data barang ke database.")
        print("=" * lebar)

def edit_barang():
    tampilkan_barang()
    id_barang = input_wajib("\nID barang yang diedit: ").upper()
    barang = data_barang["barang"].get(id_barang)
    if not barang:
        print("⚠️[ERROR] ID barang tidak ditemukan.")
        return

    print("\nKosongkan input jika tidak ingin mengubah data.")

    print("\nKosongkan input jika tidak ingin mengubah data (Ketik 0 untuk batal).")

    nama = input(f"Nama barang [{barang['nama_barang']}]: ").strip()
    if nama == "0":
        print("❗[INFO] Edit barang dibatalkan.")
        return

    if konfirmasi_default(f"Ubah kategori barang? (Saat ini: {barang.get('kategori', '-')})"):
        barang["kategori"] = pilih_kategori_valid(izin_tambah=True)

    harga_pabrik = input(f"Harga pabrik [{ambil_harga_pabrik(barang)}]: ").strip()
    if harga_pabrik == "0":
        print("❗[INFO] Edit barang dibatalkan.")
        return

    harga_jual = input(f"Harga jual [{ambil_harga_jual(barang)}]: ").strip()
    if harga_jual == "0":
        print("❗[INFO] Edit barang dibatalkan.")
        return

    expired = input(f"Expired [{barang.get('expired', '')}]: ").strip()
    if expired == "0":
        print("❗[INFO] Edit barang dibatalkan.")
        return
    try:
        pabrik_baru = (
            int(harga_pabrik)
            if harga_pabrik
            else ambil_harga_pabrik(barang)
        )

        jual_baru = (
            int(harga_jual)
            if harga_jual
            else ambil_harga_jual(barang)
        )

        if pabrik_baru < 1 or jual_baru < 1:
            raise ValueError

    except ValueError:
        print("⚠️[ERROR] Data angka tidak valid.")
        return

    if expired:
        try:
            datetime.strptime(expired, "%d-%m-%Y")
        except ValueError:
            print("⚠️[ERROR] Format tanggal expired salah.")
            return

    # Menyiapkan data baru untuk pratinjau
    nama_baru_final = nama or barang["nama_barang"]
    expired_baru_final = expired or barang.get("expired", "31-12-2099")
    laba_baru = hitung_laba(pabrik_baru, jual_baru)
    laba_lama = barang.get('laba_per_barang', hitung_laba(ambil_harga_pabrik(barang), ambil_harga_jual(barang)))

    # --- INOVASI: Menampilkan Pratinjau dalam Bentuk Tabel ---
    print("\n" + "="*65)
    print(f"📋 PRATINJAU PERUBAHAN DATA BARANG (ID: {id_barang})")
    print("="*65)
    print(f"{'Kategori':<15} | {'Data Lama':<20} | {'Data Baru':<20}")
    print("-" * 65)
    print(f"{'Nama Barang':<15} | {str(barang['nama_barang']):<20} | {str(nama_baru_final):<20}")
    print(f"{'Harga Pabrik':<15} | {str(ambil_harga_pabrik(barang)):<20} | {str(pabrik_baru):<20}")
    print(f"{'Harga Jual':<15} | {str(ambil_harga_jual(barang)):<20} | {str(jual_baru):<20}")
    print(f"{'Laba':<15} | {str(laba_lama):<20} | {str(laba_baru):<20}")
    print(f"{'Expired':<15} | {str(barang.get('expired', '')):<20} | {str(expired_baru_final):<20}")
    print("="*65)

    if not konfirmasi_default("Apakah Anda yakin ingin menyimpan perubahan ini?"):
        print("❌ Perubahan dibatalkan.")
        return
    # --------------------------------------------------------

    data_lama = copy.deepcopy(barang)

    barang.update({
        "nama_barang": nama_baru_final,
        "harga_pabrik": pabrik_baru,
        "harga_jual": jual_baru,
        "harga": jual_baru,
        "laba_lama": laba_lama,
        "laba_per_barang": laba_baru,
        "expired": expired_baru_final
    })

    if simpan_data():
        print("\n[SUKSES] Data barang berhasil diperbarui.")
    else:
        barang.clear()
        barang.update(data_lama)

def hapus_barang():
    tampilkan_barang()
    id_barang = input_wajib("ID barang yang dihapus: ").upper()
    if id_barang in data_barang["barang"]:

      def barang_pernah_dipakai(id_barang):
                  for trx in data_barang["transaksi"]:
                      if any(item["id_barang"] == id_barang for item in trx.get("item", [])):
                          return True
                  for file_cek in (FILE_MASUK, FILE_KELUAR):
                      if file_cek.exists():
                          for baris in file_cek.read_text(encoding="utf-8").splitlines():
                              kolom = baris.split("|")
                              if len(kolom) >= 3 and kolom[2] == id_barang:
                                  return True
                  return False
      
      if barang_pernah_dipakai(id_barang):
                  print("⚠️[DITOLAK] Barang sudah pernah tercatat di transaksi atau riwayat gudang, tidak dapat dihapus!")
                  return
      
      if konfirmasi_default("Yakin hapus barang?"):
        
        barang_dihapus = data_barang["barang"].pop(id_barang)
        barang_dihapus["status"] = "Nonaktif"
        data_barang.setdefault("arsip_barang", {})[id_barang] = barang_dihapus

        if simpan_data():
          print(f"[SUKSES] barang diarsipkan.")
          catat_log("gudang", f"Menghapus barang {barang_dihapus['nama_barang']} ({id_barang})")
    else:
        print("⚠️[ERROR] ID barang tidak ditemukan.")

def cari_barang():
    print("\n" + "=" * 50)
    print("           PENCARIAN DATA BARANG")
    print("=" * 50)

    keyword = input_wajib(
        "Masukkan nama atau ID barang: "
    ).strip()

    # 1. Prioritaskan pencarian berdasarkan ID
    id_barang = keyword.upper()
    barang = data_barang["barang"].get(id_barang)

    if barang:
        pabrik = ambil_harga_pabrik(barang)
        jual = ambil_harga_jual(barang)

        print("\n[DATA BARANG DITEMUKAN]")
        print("-" * 50)
        print(f"ID BARANG       : {id_barang}")
        print(f"NAMA BARANG     : {barang['nama_barang']}")
        print(f"STOK            : {barang['stok']}")
        print(f"HARGA PABRIK    : {rupiah(pabrik)}")
        print(f"HARGA JUAL      : {rupiah(jual)}")
        print(f"LABA PER UNIT   : {rupiah(jual - pabrik)}")
        print(f"EXPIRED         : {barang.get('expired', '-')}")
        print("-" * 50)
        return

    # 2. Jika bukan ID, cari berdasarkan nama
    hasil = [
        (kunci, barang)
        for kunci, barang in data_barang["barang"].items()
        if keyword.casefold() in barang["nama_barang"].casefold()
    ]

    if not hasil:
        print("\n[ERROR] Barang tidak ditemukan.")
        return

    print("\n=== HASIL PENCARIAN BARANG ===")

    for id_barang, barang in hasil:
        pabrik = ambil_harga_pabrik(barang)
        jual = ambil_harga_jual(barang)

        print("-" * 50)
        print(f"ID BARANG       : {id_barang}")
        print(f"NAMA BARANG     : {barang['nama_barang']}")
        print(f"STOK            : {barang['stok']}")
        print(f"HARGA PABRIK    : {rupiah(pabrik)}")
        print(f"HARGA JUAL      : {rupiah(jual)}")
        print(f"LABA PER UNIT   : {rupiah(jual - pabrik)}")
        print(f"EXPIRED         : {barang.get('expired', '-')}")
    
    print("-" * 50)

def filter_kategori_barang():
    kategori_dicari = pilih_kategori_valid(izin_tambah=False)
    hasil = [
        (kode, barang) for kode, barang in data_barang["barang"].items()
        if barang.get("kategori", "").casefold() == kategori_dicari.casefold()
    ]
    if not hasil:
        print("❗[INFO] Tidak ada barang pada kategori tersebut.")
        return
    print(f"\n=== BARANG KATEGORI: {kategori_dicari.upper()} ===")
    print(f"{'ID':<8} | {'NAMA BARANG':<22} | {'KATEGORI':<16} | {'HARGA':>12} | {'STOK':>5}")
    print("-" * 72)
    for kode, barang in hasil:
        print(f"{kode:<8} | {barang['nama_barang'][:22]:<22} | {barang.get('kategori','-'):<16} | {rupiah(barang['harga']):>12} | {barang['stok']:>5}")


def cek_dan_urutkan_expired():
    lebar = 115

    print("\n" + "=" * lebar)
    print("LAPORAN CEK DAN URUTAN EXPIRED BARANG".center(lebar))
    print("=" * lebar)
    if not data_barang["barang"]:
        print("❗[INFO] Belum ada data barang.")
        print("=" * lebar)
        return
    hari_ini = datetime.now().date()
    daftar_expired = []
    # 1. Mengambil data dan menghitung sisa hari expired
    for id_barang, barang in data_barang["barang"].items():
        tanggal_str = barang.get("expired", "31-12-2099")
        try:
            tanggal_expired = datetime.strptime(
                tanggal_str, "%d-%m-%Y"
            ).date()
        except ValueError:
            print(
                f"[PERINGATAN] Tanggal expired barang "
                f"{barang['nama_barang']} tidak valid."
            )
            continue
        sisa_hari = (tanggal_expired - hari_ini).days
        # 2. Menentukan status barang
        if sisa_hari <= 0:
            status = "EXPIRED"
            diskon = 0
        elif sisa_hari <= 5:
            status = "MENDEKATI"
            diskon = 4

        else:
            status = "NORMAL"
            diskon = 0
        # 3. tempat penghitungan harga setelah diskon
        harga = ambil_harga_jual(barang)
        potongan = round(harga * diskon / 100)
        harga_akhir = harga - potongan
        # 4. hasile disempen nang list
        daftar_expired.append({
            "id": id_barang,
            "nama": barang["nama_barang"],
            "tanggal": tanggal_expired,
            "sisa_hari": sisa_hari,
            "status": status,
            "diskon": diskon,
            "harga_awal": harga,
            "potongan": potongan,
            "harga_akhir": harga_akhir
        })
    if not daftar_expired:
        print("❗[INFO] Tidak ada tanggal expired yang valid.")
        return
    # 5. pengurutan barang e katek heapsrot 
    n = len(daftar_expired)
    def heapify(arr, n, i):
        terbesar = i
        kiri = 2 * i + 1
        kanan = 2 * i + 2
        if kiri < n and arr[kiri]["tanggal"] > arr[terbesar]["tanggal"]:
            terbesar = kiri
        if kanan < n and arr[kanan]["tanggal"] > arr[terbesar]["tanggal"]:
            terbesar = kanan
        if terbesar != i:
            arr[i], arr[terbesar] = arr[terbesar], arr[i]
            heapify(arr, n, terbesar)
    # Membentuk Max Heap
    for i in range(n // 2 - 1, -1, -1):
        heapify(daftar_expired, n, i)
    # Proses Heap Sort
    for i in range(n - 1, 0, -1):
        daftar_expired[0], daftar_expired[i] = (
            daftar_expired[i], daftar_expired[0]
        )
        heapify(daftar_expired, i, 0)
    # 6. Menampilkan hasil pengurutan
    print("\nURUTAN BARANG DARI EXPIRED TERDEKAT")
    print("=" * lebar)

    print(
        f"{'ID BARANG':<11} | "
        f"{'NAMA BARANG':<20} | "
        f"{'TANGGAL EXPIRED':<17} | "
        f"{'SISA HARI':<11} | "
        f"{'STATUS':<12} | "
        f"{'DISKON':<8} | "
        f"{'HARGA AKHIR':>13}"
    )

    print("-" * lebar)

    for barang in daftar_expired:
        print(
            f"{barang['id']:<11} | "
            f"{barang['nama'][:20]:<20} | "
            f"{barang['tanggal'].strftime('%d-%m-%Y'):<17} | "
            f"{barang['sisa_hari']:>11} | "
            f"{barang['status']:<12} | "
            f"{str(barang['diskon']) + '%':<8} | "
            f"{rupiah(barang['harga_akhir']):>13}"
        )
    print("=" * lebar)
    # 7. Ringkasane kondisi barang
    total_expired = sum(
        1 for b in daftar_expired if b["status"] == "EXPIRED"
    )
    total_mendekati = sum(
        1 for b in daftar_expired if b["status"] == "MENDEKATI"
    )
    total_normal = sum(
        1 for b in daftar_expired if b["status"] == "NORMAL"
    )
    print("\nRINGKASAN KONDISI BARANG")
    print("-" * 40)
    print(f"Total barang diperiksa : {len(daftar_expired)}")
    print(f"Barang sudah expired   : {total_expired}")
    print(f"Mendekati expired      : {total_mendekati}")
    print(f"Barang normal          : {total_normal}")
    print("=" * lebar)
          
def riwayat_stok():
    lebar = 88
    print("\n" + "=" * lebar)
    print("RIWAYAT PERUBAHAN STOK".center(lebar))
    print("=" * lebar)

    if not list_riwayat_stok:
        print("Belum Ada Riwayat Perubahan Stok.")
        return

    print(f"{'NO':<4} | {'ID':<8} | {'NAMA BARANG':<20} | {'JENIS':<24} | {'JUMLAH':>6} | {'STOK':>11}")
    print("-" * lebar)
    for nomor, riwayat in enumerate(list_riwayat_stok, start=1):
        perubahan_stok = f"{riwayat['stok_sebelum']} -> {riwayat['stok_sesudah']}"
        print(
            f"{nomor:<4} | "
            f"{riwayat['id_barang']:<8} | "
            f"{riwayat['nama_barang'][:20]:<20} | "
            f"{riwayat['jenis'][:24]:<24} | "
            f"{riwayat['jumlah']:>6} | "
            f"{perubahan_stok:>11}"
        )
    print("=" * lebar)

def laporan_barang():
    lebar = 96
    print("\n" + "-" * lebar)
    print("LAPORAN STOK DAN AKTIVITAS GUDANG".center(lebar))
    print("=" * lebar)

    if not data_barang["barang"]:
        print("Barang Belum Tersedia!")
        return

    tgl_awal, tgl_akhir = input_rentang_tanggal()
    periode_teks = f"{tgl_awal.strftime('%d-%m-%Y')} s.d. {tgl_akhir.strftime('%d-%m-%Y')}"

    hari_ini = datetime.now().date()
    normal = 0
    mendekati_expired = 0
    sudah_expired = 0
    stok_menipis = 0

    baris_laporan = [
        "=" * lebar,
        "LAPORAN STOK DAN AKTIVITAS GUDANG".center(lebar),
        f"Periode Aktivitas: {periode_teks}".center(lebar),
        "=" * lebar,
        f"{'ID':<9} | {'NAMA BARANG':<22} | {'STOK':>5} | {'STATUS':<11} | {'EXPIRED':<12} | {'KONDISI':<12}",
        "=" * lebar
    ]

    for id_barang, barang in data_barang["barang"].items():
        stok = int(barang["stok"])
        status_stok = status_stok_barang(barang)
        tanggal_str = barang.get("expired", "31-12-2099")

        try:
            tanggal_expired = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
        except ValueError:
            tanggal_expired = hari_ini

        sisa_hari = (tanggal_expired - hari_ini).days

        if sisa_hari <= 0:
            status = "⚠️ EXPIRED"
            sudah_expired += 1
        elif sisa_hari <= 5:
            status = "⚠️ MENDEKATI EXPIRED"
            mendekati_expired += 1
        else:
            status = "NORMAL"
            normal += 1

        if stok <= 5:
            stok_menipis += 1

        baris_laporan.append(
            f"{id_barang:<9} | "
            f"{barang['nama_barang'][:22]:<22} | "
            f"{stok:>5} | "
            f"{status_stok:<11} | "
            f"{tanggal_str:<12} | "
            f"{status:<12}"
        )

    baris_laporan.append("=" * lebar)
    baris_laporan.append("RINGKASAN LAPORAN KONDISI BARANG".center(lebar))
    baris_laporan.append("-" * lebar)
    baris_laporan.append(f"{'Total Jenis Barang':<28} : {len(data_barang['barang'])} item")
    baris_laporan.append(f"{'Barang Kondisi Normal':<28} : {normal} item")
    baris_laporan.append(f"{'Barang Mendekati Expired':<28} : {mendekati_expired} item")
    baris_laporan.append(f"{'Barang Sudah Expired':<28} : {sudah_expired} item")
    baris_laporan.append(f"{'Barang Stok Menipis (<= 5)':<28} : {stok_menipis} item")
    baris_laporan.append("=" * lebar)

    # Tambahan: Daftar Barang Masuk pada Rentang Tanggal
    daftar_masuk = []
    total_masuk = 0
    if FILE_MASUK.exists():
        for baris in FILE_MASUK.read_text(encoding="utf-8").splitlines():
            kolom = baris.split("|")
            if len(kolom) < 6:
                continue
            try:
                tanggal_masuk = datetime.strptime(kolom[1], "%Y-%m-%d").date()
            except ValueError:
                continue
            if tgl_awal <= tanggal_masuk <= tgl_akhir:
                jumlah = int(kolom[3])
                total_masuk += jumlah
                nama_barang = data_barang["barang"].get(kolom[2], {}).get("nama_barang", kolom[2])
                daftar_masuk.append(
                    f"{kolom[0]:<10} | {tanggal_masuk.strftime('%d-%m-%Y'):<12} | {kolom[2]:<8} | {nama_barang[:22]:<22} | +{jumlah:<5} | {kolom[4]}"
                )

    baris_laporan.append(f"DAFTAR BARANG MASUK ({periode_teks})".center(lebar))
    baris_laporan.append("-" * lebar)
    if not daftar_masuk:
        baris_laporan.append("Tidak ada data barang masuk pada rentang tanggal ini.")
    else:
        baris_laporan.extend(daftar_masuk)

    # Tambahan: Daftar Barang Keluar pada Rentang Tanggal
    daftar_keluar = []
    total_keluar = 0
    if FILE_KELUAR.exists():
        for baris in FILE_KELUAR.read_text(encoding="utf-8").splitlines():
            kolom = baris.split("|")
            if len(kolom) < 7:
                continue
            try:
                tanggal_keluar = datetime.strptime(kolom[1], "%Y-%m-%d").date()
            except ValueError:
                continue
            if tgl_awal <= tanggal_keluar <= tgl_akhir:
                jumlah = int(kolom[3])
                total_keluar += jumlah
                nama_barang = data_barang["barang"].get(kolom[2], {}).get("nama_barang", kolom[2])
                daftar_keluar.append(
                    f"{kolom[0]:<10} | {tanggal_keluar.strftime('%d-%m-%Y'):<12} | {kolom[2]:<8} | {nama_barang[:22]:<22} | -{jumlah:<5} | {kolom[4]}"
                )

    baris_laporan.append("=" * lebar)
    baris_laporan.append(f"DAFTAR BARANG KELUAR ({periode_teks})".center(lebar))
    baris_laporan.append("-" * lebar)
    if not daftar_keluar:
        baris_laporan.append("Tidak ada data barang keluar pada rentang tanggal ini.")
    else:
        baris_laporan.extend(daftar_keluar)

    baris_laporan.append("=" * lebar)
    baris_laporan.append(f"Total Catatan Barang Masuk  : {len(daftar_masuk)} catatan ({total_masuk} unit)")
    baris_laporan.append(f"Total Catatan Barang Keluar : {len(daftar_keluar)} catatan ({total_keluar} unit)")
    baris_laporan.append("=" * lebar)

    isi_laporan = "\n".join(baris_laporan)
    print("\n" + isi_laporan)

    nama_file = f"laporan_gudang_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    simpan_teks_laporan(nama_file, isi_laporan)

def notifikasi_barang():
    print("\n" + "-" * 30)
    print("\n ---- NOTIFIKASI BARANG ---- ")

    if not data_barang["barang"]:
        print("Barang Belum Tersedia!")
        return

    hari_ini = datetime.now().date()
    ada_notifikasi = False

    for id_barang, barang in data_barang["barang"].items():
        stok = int(barang["stok"])
        tanggal_str = barang.get("expired", "31-12-2099")

        try:
            tanggal_expired = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
        except ValueError:
            tanggal_expired = hari_ini

        sisa_hari = (tanggal_expired - hari_ini).days

        if sisa_hari <= 0:
            print(f"⚠️[BAHAYA] {barang['nama_barang']} sudah expired!")
            ada_notifikasi = True
        elif sisa_hari <= 3:
            print(f"⚠️[PERINGATAN] {barang['nama_barang']} akan expired dalam {sisa_hari} hari!")
            ada_notifikasi = True

        if stok <= 5:
            print(f"⚠️[STOK MENIPIS] {barang['nama_barang']} tersisa {stok} buah.")
            ada_notifikasi = True

    if not ada_notifikasi:
        print("Semua barang dalam kondisi aman!")
    print("-" * 35)


def status_stok_barang(barang):
    stok = int(barang["stok"])
    stok_minimum = int(barang.get("stok_min", 5))
    if stok == 0:
        return "HABIS"
    elif stok <= stok_minimum:
        return "MINIMUM"
    return "AMAN"

def peringatan_stok_otomatis():
    print("\n--- PERINGATAN STOK MINIMUM & HABIS ---")
    ada_peringatan = False
    for kode_barang, barang in data_barang["barang"].items():
        status = status_stok_barang(barang)
        if status in ("HABIS", "MINIMUM"):
            print(f"[{status:<7}] {kode_barang} | {barang['nama_barang']:<22} | Stok: {barang['stok']} | Min: {barang.get('stok_min', 5)}")
            ada_peringatan = True
    if not ada_peringatan:
        print("Semua stok barang dalam kondisi AMAN.")

def catat_barang_masuk(id_login):
    print("\n=== CATAT BARANG MASUK ===")
    if not data_barang["barang"]:
        print("⚠️[ERROR] Belum ada data barang. Minta Admin menambahkan barang terlebih dahulu.")
        return

    tampilkan_barang()
    id_barang = input_wajib("Masukkan kode barang (contoh BRG001): ").upper()
    if id_barang not in data_barang["barang"]:
        print("⚠️[ERROR] Kode barang tidak ditemukan.")
        return

    barang = data_barang["barang"][id_barang]
    stok_sebelum = int(barang["stok"])
    print(f"Barang dipilih : {barang['nama_barang']} (Stok saat ini: {stok_sebelum})")

    jumlah = input_angka("Jumlah barang masuk (> 0): ", minimum=1)
    pemasok = input_wajib("Nama pemasok: ")

    pabrik_sekarang = ambil_harga_pabrik(barang)
    jual_sekarang = ambil_harga_jual(barang)
    input_pabrik_baru = input(f"Harga pabrik terbaru [Enter jika tetap {rupiah(pabrik_sekarang)}]: ").strip()
    if input_pabrik_baru.isdigit() and int(input_pabrik_baru) >= 1:
        pabrik_baru = int(input_pabrik_baru)
        if pabrik_baru != pabrik_sekarang:
            barang["laba_lama"] = hitung_laba(pabrik_sekarang, jual_sekarang)
            barang["harga_pabrik"] = pabrik_baru
            barang["laba_per_barang"] = hitung_laba(pabrik_baru, jual_sekarang)

    id_masuk = buat_id_file_otomatis(FILE_MASUK, "MASUK")
    tanggal_iso = datetime.now().strftime("%Y-%m-%d")
    petugas = data_pengguna["pengguna"][id_login]["username"]

    barang["stok"] = stok_sebelum + jumlah
    if not simpan_data():
        barang["stok"] = stok_sebelum
        print("⚠️[ERROR] Gagal menyimpan perubahan stok.")
        return

    baris_masuk = f"{id_masuk}|{tanggal_iso}|{id_barang}|{jumlah}|{pemasok}|{petugas}\n"
    with FILE_MASUK.open("a", encoding="utf-8") as file_masuk:
        file_masuk.write(baris_masuk)

    list_riwayat_stok.append({
        "id_barang": id_barang,
        "nama_barang": barang["nama_barang"],
        "jenis": f"Masuk ({id_masuk} - {pemasok})",
        "jumlah": jumlah,
        "stok_sebelum": stok_sebelum,
        "stok_sesudah": int(barang["stok"])
    })

    catat_log("gudang", f"BARANG MASUK {id_masuk} {id_barang} +{jumlah} dari {pemasok}", petugas)
    print(f"✅[SUKSES] {id_masuk} tersimpan. Stok '{barang['nama_barang']}' sekarang: {barang['stok']}.")

def catat_barang_keluar(id_login):
    print("\n=== CATAT BARANG KELUAR (NON-PENJUALAN) ===")
    if not data_barang["barang"]:
        print("⚠️[ERROR] Belum ada data barang.")
        return

    tampilkan_barang()
    id_barang = input_wajib("Masukkan kode barang (contoh BRG001): ").upper()
    if id_barang not in data_barang["barang"]:
        print("⚠️[ERROR] Kode barang tidak ditemukan.")
        return

    barang = data_barang["barang"][id_barang]
    stok_sebelum = int(barang["stok"])
    if stok_sebelum <= 0:
        print("⚠️[ERROR] Stok barang habis (0), tidak bisa dicatat keluar.")
        return

    print(f"Barang dipilih : {barang['nama_barang']} (Stok tersedia: {stok_sebelum})")
    jumlah = input_angka(f"Jumlah barang keluar (1 - {stok_sebelum}): ", minimum=1)
    if jumlah > stok_sebelum:
        print(f"⚠️[ERROR] Jumlah keluar melebihi stok tersedia ({stok_sebelum}).")
        return

    alasan_valid = ("RUSAK", "KADALUARSA", "RETUR", "LAINNYA")
    while True:
        alasan = input_wajib("Alasan keluar (RUSAK / KADALUARSA / RETUR / LAINNYA): ").upper()
        if alasan in alasan_valid:
            break
        print("⚠️[ERROR] Alasan harus salah satu dari: RUSAK, KADALUARSA, RETUR, atau LAINNYA.")

    keterangan = input_wajib("Keterangan detail: ")

    id_keluar = buat_id_file_otomatis(FILE_KELUAR, "KELUAR")
    tanggal_iso = datetime.now().strftime("%Y-%m-%d")
    petugas = data_pengguna["pengguna"][id_login]["username"]

    barang["stok"] = stok_sebelum - jumlah
    if not simpan_data():
        barang["stok"] = stok_sebelum
        print("⚠️[ERROR] Gagal menyimpan perubahan stok.")
        return

    baris_keluar = f"{id_keluar}|{tanggal_iso}|{id_barang}|{jumlah}|{alasan}|{keterangan}|{petugas}\n"
    with FILE_KELUAR.open("a", encoding="utf-8") as file_keluar:
        file_keluar.write(baris_keluar)

    list_riwayat_stok.append({
        "id_barang": id_barang,
        "nama_barang": barang["nama_barang"],
        "jenis": f"Keluar ({id_keluar} - {alasan})",
        "jumlah": jumlah,
        "stok_sebelum": stok_sebelum,
        "stok_sesudah": int(barang["stok"])
    })

    catat_log("gudang", f"BARANG KELUAR {id_keluar} {id_barang} -{jumlah} ({alasan})", petugas)
    print(f"✅[SUKSES] {id_keluar} tersimpan. Stok '{barang['nama_barang']}' sekarang: {barang['stok']}.")

def kartu_stok_barang():
    id_barang = input_wajib("Masukkan kode barang untuk Kartu Stok (contoh BRG001): ").upper()
    barang = data_barang["barang"].get(id_barang)
    if not barang:
        print("⚠️[ERROR] Kode barang tidak ditemukan.")
        return

    riwayat = []
    if FILE_MASUK.exists():
        for baris in FILE_MASUK.read_text(encoding="utf-8").splitlines():
            kolom = baris.split("|")
            if len(kolom) >= 6 and kolom[2] == id_barang:
                riwayat.append((kolom[1], "MASUK", f"+{kolom[3]}", f"{kolom[0]} ({kolom[4]})"))

    if FILE_KELUAR.exists():
        for baris in FILE_KELUAR.read_text(encoding="utf-8").splitlines():
            kolom = baris.split("|")
            if len(kolom) >= 7 and kolom[2] == id_barang:
                riwayat.append((kolom[1], "KELUAR", f"-{kolom[3]}", f"{kolom[0]} ({kolom[4]})"))

    for transaksi in data_barang["transaksi"]:
        tanggal_str = transaksi["tanggal"].split(" ")[0]
        try:
            tanggal_iso = datetime.strptime(tanggal_str, "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            tanggal_iso = tanggal_str
        for item in transaksi.get("item", []):
            if item["id_barang"] == id_barang:
                riwayat.append((tanggal_iso, "TERJUAL", f"-{item['jumlah']}", transaksi["nomor"]))

    riwayat.sort(key=lambda data: data[0])
    lebar = 68
    print("\n" + "=" * lebar)
    print(f"KARTU STOK: {id_barang} - {barang['nama_barang']}".center(lebar))
    print("=" * lebar)
    print(f"Stok Saat Ini: {barang['stok']} | Status: {status_stok_barang(barang)}")
    print("-" * lebar)
    if not riwayat:
        print("Belum ada riwayat masuk, keluar, atau penjualan untuk barang ini.")
        print("=" * lebar)
        return

    print(f"{'TANGGAL':<12} | {'JENIS':<10} | {'JUMLAH':>8} | {'KETERANGAN':<29}")
    print("-" * lebar)
    for tanggal_iso, jenis_aktivitas, jumlah_unit, keterangan_detail in riwayat:
        try:
            tanggal_tampil = datetime.strptime(tanggal_iso, "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            tanggal_tampil = tanggal_iso
        print(f"{tanggal_tampil:<12} | {jenis_aktivitas:<10} | {jumlah_unit:>8} | {keterangan_detail[:29]:<29}")
    print("=" * lebar)

def stok_opname(id_login):
    lebar = 82
    print("\n" + "=" * lebar)
    print("STOK OPNAME (PENCOCOKAN STOK FISIK VS SISTEM)".center(lebar))
    print("=" * lebar)

    if not data_barang["barang"]:
        print("❗[INFO] Belum ada data barang yang tersimpan.")
        return

    tampilkan_barang()
    print("\nMasukkan kode barang yang ingin dicek stok fisiknya (ketik 'selesai' jika sudah).")

    hasil_opname = []
    petugas = data_pengguna["pengguna"][id_login]["username"]
    role_petugas = data_pengguna["pengguna"][id_login]["role"]

    while True:
        id_barang = input("\nKode barang / selesai: ").strip().upper()
        if id_barang == "SELESAI":
            break
        if id_barang not in data_barang["barang"]:
            print("⚠️[ERROR] Kode barang tidak ditemukan.")
            continue

        barang = data_barang["barang"][id_barang]
        stok_sistem = int(barang["stok"])
        print(f"Barang      : {barang['nama_barang']}")
        print(f"Stok Sistem : {stok_sistem}")

        stok_fisik = input_angka("Stok Fisik (hasil hitungan nyata): ", minimum=0)
        selisih = stok_fisik - stok_sistem

        if selisih == 0:
            keterangan_selisih = "SESUAI (0)"
            print("✅[INFO] Stok fisik sesuai dengan stok sistem.")
        elif selisih > 0:
            keterangan_selisih = f"LEBIH (+{selisih})"
            print(f"⚠️[SELISIH] Stok fisik lebih banyak {selisih} unit dari sistem.")
        else:
            keterangan_selisih = f"KURANG ({selisih})"
            print(f"⚠️[SELISIH] Stok fisik kurang {abs(selisih)} unit dari sistem.")

        catatan = input("Catatan opname (opsional, Enter untuk '-'): ").strip() or "-"

        if selisih != 0:
            if konfirmasi_default(f"Sesuaikan stok sistem '{barang['nama_barang']}' menjadi {stok_fisik}?"):
                barang["stok"] = stok_fisik
                list_riwayat_stok.append({
                    "id_barang": id_barang,
                    "nama_barang": barang["nama_barang"],
                    "jenis": f"Stok Opname ({keterangan_selisih})",
                    "jumlah": abs(selisih),
                    "stok_sebelum": stok_sistem,
                    "stok_sesudah": stok_fisik
                })
                catat_log(
                    role_petugas,
                    f"STOK OPNAME {id_barang}: sistem {stok_sistem} -> fisik {stok_fisik} ({keterangan_selisih}) | {catatan}",
                    petugas
                )

        hasil_opname.append({
            "id": id_barang,
            "nama": barang["nama_barang"],
            "sistem": stok_sistem,
            "fisik": stok_fisik,
            "selisih": selisih,
            "catatan": catatan
        })

    if not hasil_opname:
        print("❗[INFO] Tidak ada barang yang diperiksa pada sesi stok opname ini.")
        return

    simpan_data()

    baris_laporan = [
        "=" * lebar,
        "BERITA ACARA STOK OPNAME SMK MART".center(lebar),
        f"Tanggal : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | Petugas: {petugas}".center(lebar),
        "=" * lebar,
        f"{'ID':<8} | {'NAMA BARANG':<22} | {'SISTEM':>7} | {'FISIK':>7} | {'SELISIH':>8} | {'CATATAN':<15}",
        "-" * lebar
    ]

    for item in hasil_opname:
        tanda_selisih = f"+{item['selisih']}" if item["selisih"] > 0 else str(item["selisih"])
        baris_laporan.append(
            f"{item['id']:<8} | {item['nama'][:22]:<22} | {item['sistem']:>7} | "
            f"{item['fisik']:>7} | {tanda_selisih:>8} | {item['catatan'][:15]:<15}"
        )

    baris_laporan.append("=" * lebar)
    isi_laporan = "\n".join(baris_laporan)
    print("\n" + isi_laporan)
    simpan_teks_laporan(f"stok_opname_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", isi_laporan)

def laporan_nilai_persediaan():
    lebar = 96
    if not data_barang["barang"]:
        print("❗[INFO] Belum ada data barang yang tersimpan.")
        return

    baris_laporan = [
        "=" * lebar,
        "LAPORAN NILAI PERSEDIAAN BARANG SMK MART".center(lebar),
        f"Tanggal Cetak: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}".center(lebar),
        "=" * lebar,
        f"{'ID':<8} | {'NAMA BARANG':<22} | {'STOK':>5} | {'HARGA JUAL':>13} | {'NILAI JUAL':>15} | {'NILAI MODAL':>15}",
        "-" * lebar
    ]

    total_unit = 0
    total_nilai_jual = 0
    total_nilai_modal = 0

    for id_barang, barang in sorted(data_barang["barang"].items()):
        stok = int(barang["stok"])
        harga_jual = int(ambil_harga_jual(barang))
        harga_modal = int(ambil_harga_pabrik(barang))

        nilai_jual = stok * harga_jual
        nilai_modal = stok * harga_modal

        total_unit += stok
        total_nilai_jual += nilai_jual
        total_nilai_modal += nilai_modal

        baris_laporan.append(
            f"{id_barang:<8} | {barang['nama_barang'][:22]:<22} | {stok:>5} | "
            f"{rupiah(harga_jual):>13} | {rupiah(nilai_jual):>15} | {rupiah(nilai_modal):>15}"
        )

    baris_laporan.extend([
        "=" * lebar,
        f"Total Jenis Barang       : {len(data_barang['barang'])} item",
        f"Total Seluruh Unit Stok  : {total_unit} unit",
        f"Total Nilai Persediaan   : {rupiah(total_nilai_jual)} (berdasarkan harga jual)",
        f"Total Nilai Modal Pabrik : {rupiah(total_nilai_modal)} (berdasarkan harga pabrik)",
        f"Potensi Laba Persediaan  : {rupiah(total_nilai_jual - total_nilai_modal)}",
        "=" * lebar
    ])

    isi_laporan = "\n".join(baris_laporan)
    print("\n" + isi_laporan)
    simpan_teks_laporan(f"laporan_nilai_persediaan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", isi_laporan)

def analisis_spldv_harga_barang():
    print("\n=== ANALISIS HARGA BARANG (SPLDV) ===")
    print("Gunakan metode ini untuk menentukan harga satuan dua barang (Barang X dan Barang Y)")
    print("berdasarkan 2 paket kombinasi pembelian.")
    print("\nContoh Persamaan:")
    print("  Paket 1: a1(Barang X) + b1(Barang Y) = Total Harga 1")
    print("  Paket 2: a2(Barang X) + b2(Barang Y) = Total Harga 2\n")

    try:
        print("Masukkan koefisien Paket 1:")
        a1 = float(input_angka("Jumlah Barang X di Paket 1: ", 0))
        b1 = float(input_angka("Jumlah Barang Y di Paket 1: ", 0))
        c1 = float(input_angka("Total Harga Paket 1 (Rp): ", 1))

        print("\nMasukkan koefisien Paket 2:")
        a2 = float(input_angka("Jumlah Barang X di Paket 2: ", 0))
        b2 = float(input_angka("Jumlah Barang Y di Paket 2: ", 0))
        c2 = float(input_angka("Total Harga Paket 2 (Rp): ", 1))

        # iki spldv ne
        determinan = (a1 * b2) - (a2 * b1)

        if determinan == 0:
            print("⚠️[ERROR] Sistem persamaan tidak memiliki solusi unik (determinan = 0). Periksa kembali nilai input.")
            return

        det_x = (c1 * b2) - (c2 * b1)
        det_y = (a1 * c2) - (a2 * c1)

        harga_x = det_x / determinan
        harga_y = det_y / determinan

        print(f"\n[SUKSES] Hasil dari perhitungan SPLDV : ")
        print(f"\n Harga Barang X : {rupiah(int(harga_x))}")
        print(f"\n Harga Barang Y : {rupiah(int(harga_y))}")

    except ValueError:
          print("⚠️[ERROR] Terjadi kesalahan input. Pastikan memasukkan angka yang benar!")

def hitung_laba(harga_pabrik,harga_jual):
    return harga_jual - harga_pabrik

def hitung_laba_kotor_transaksi(transaksi):
    total_laba = 0

    for item in transaksi.get("item", []):

        # Transaksi lama mungkin belum memiliki data modal
        if "harga_pabrik" not in item:
            return None

        laba_item = (
            item["subtotal"]
            - (item["harga_pabrik"] * item["jumlah"])
        )

        total_laba += laba_item

    return total_laba

def ambil_harga_pabrik(barang):
    return barang.get("harga_pabrik",barang.get("harga",0))

def ambil_harga_jual(barang):
    return barang.get("harga_jual", barang.get("harga", 0))

def hitung_diskon_expired(barang):
    hari_ini = datetime.now().date()

    tanggal_str = barang.get("expired", "")

    try:
        tanggal_expired = datetime.strptime(
            tanggal_str, "%d-%m-%Y"
        ).date()
    except ValueError:
        return 0, 0, ambil_harga_jual(barang)

    sisa_hari = (tanggal_expired - hari_ini).days

    harga_normal = ambil_harga_jual(barang)

    if sisa_hari <= 0:
        diskon = 0
    elif sisa_hari <= 5:
        diskon = 0.04
    else:
        diskon = 0

    potongan = round(harga_normal * diskon)
    harga_akhir = harga_normal - potongan

    return sisa_hari, potongan, harga_akhir

def migrasi_harga_barang():
    for barang in data_barang["barang"].values():

        harga_lama = barang.get("harga", 0)

        barang.setdefault("harga_pabrik", harga_lama)
        barang.setdefault("harga_jual", harga_lama)
        barang.setdefault("status", "Aktif")

        barang["harga"] = barang["harga_jual"]

        barang["laba_per_barang"] = hitung_laba(
            barang["harga_pabrik"],
            barang["harga_jual"]
        )
# ==========================================
# PERHITUNGAN PPN
# ==========================================
TARIF_PPN = 11

def hitung_ppn(subtotal):
    return round(subtotal * TARIF_PPN / 100)
# ==========================================
# FITUR KASIR
# ==========================================
def tampil_keranjang(keranjang):
    print("\n=== KERANJANG BELANJA ===")
    if not keranjang:
        print("Keranjang masih kosong.")
        return 0
    total = 0

    for id_barang, jumlah in keranjang.items():
        barang = data_barang["barang"][id_barang]
        sisa_hari, potongan, harga_akhir = hitung_diskon_expired(barang)
        subtotal = jumlah * harga_akhir
        total += subtotal

        print(f"\nNama Barang : {barang['nama_barang']}")
        print(f"Jumlah      : {jumlah}")
        print(f"Harga Awal  : {rupiah(ambil_harga_jual(barang))}")
        if potongan > 0:
            print("Diskon      : 4%")
            print(f"Potongan    : {rupiah(potongan)}")
        print(f"Harga Akhir : {rupiah(harga_akhir)}")
        print(f"Subtotal    : {rupiah(subtotal)}")

    print("-" * 40)
    print(f"TOTAL BELANJA: {rupiah(total)}")

    return total

def format_struk(data_transaksi):
    garis = "=" * 46
    baris = [garis, "SMK MART".center(46), "STRUK PEMBELIAN".center(46), garis,
             f"No. Transaksi : {data_transaksi['nomor']}",
             f"Tanggal       : {data_transaksi['tanggal']}",
             f"Kasir         : {data_transaksi['kasir_nama']} (@{data_transaksi['kasir_username']})",
             "-" * 46]

    total_hemat = 0

    for item in data_transaksi["item"]:
        baris.append(item["nama_barang"])
        diskon_persen = item.get("diskon_persen", 0)
        potongan = item.get("potongan", 0)

        if diskon_persen > 0 and potongan > 0:
            harga_normal = item.get("harga_normal", item["harga"] + potongan)
            kiri = f"  {item['jumlah']} x {rupiah(harga_normal)}"
            kanan = rupiah(item["jumlah"] * harga_normal)
            baris.append(f"{kiri:<27}{kanan:>19}")

            potongan_item = potongan * item["jumlah"]
            total_hemat += potongan_item
            kiri_disc = f"  Diskon Expired ({diskon_persen}%)"
            kanan_disc = f"-{rupiah(potongan_item)}"
            baris.append(f"{kiri_disc:<27}{kanan_disc:>19}")
        else:
            kiri = f"   {item['jumlah']} x {rupiah(item['harga'])}"
            kanan = rupiah(item["subtotal"])
            baris.append(f"{kiri:<27}{kanan:>19}")

    metode_bayar = data_transaksi.get("metode", "TUNAI")
    tarif_ppn = data_transaksi.get("tarif_ppn", TARIF_PPN)
    label_ppn = f"PPN {tarif_ppn}%"

    baris.append("-" * 46)
    if total_hemat > 0:
        baris.append(f"{'TOTAL HEMAT DISKON':<25}{rupiah(total_hemat):>21}")
    baris += [
      "-" * 46,
      f"{'SUBTOTAL':<25}{rupiah(data_transaksi.get('subtotal', data_transaksi['total'])):>21}",
      f"{'PPN 11%':<25}{rupiah(data_transaksi.get('ppn', 0)):>21}",
      f"{'TOTAL BAYAR':<25}{rupiah(data_transaksi['total']):>21}",
      f"{metode_bayar:<25}{rupiah(data_transaksi['bayar']):>21}",
      f"{'KEMBALIAN':<25}{rupiah(data_transaksi['kembalian']):>21}",
     garis,
     "Terima kasih sudah berbelanja!".center(46),
      garis
      ] 
    return "\n".join(baris)
    
def cetak_struk(data_transaksi):
    isi = format_struk(data_transaksi)
    print("\n" + isi)
    try:
        FOLDER_STRUK.mkdir(parents=True, exist_ok=True)
        lokasi_struk = FOLDER_STRUK / f"{data_transaksi['nomor']}.txt"
        lokasi_struk.write_text(isi + "\n", encoding="utf-8")
        print(f"✅[SUKSES] File nota disimpan: {lokasi_struk}")
      
    except OSError as error:
        print(f"⚠️[PERINGATAN] Struk tampil, tetapi gagal tersimpan: {error}")

def transaksi_penjualan(kasir):
    if not data_barang["barang"]:
        print("⚠️[ERROR] Belum ada barang. Minta bagian gudang menambahkan barang.")
        return
    keranjang = {}
    print("\n=== TRANSAKSI PENJUALAN ===")
    print("Masukkan ID barang, ketik 'selesai' untuk bayar, 'batal' untuk membatalkan.")
    while True:
        tampilkan_barang()
        tampil_keranjang(keranjang)
        id_barang = input("ID barang / selesai / batal: ").strip().upper()

        if id_barang == "BATAL":
            print("Transaksi dibatalkan. Stok tidak berubah.")
            return
        
        if id_barang == "SELESAI":
            if not keranjang:
                print("⚠️[ERROR] Keranjang kosong.")
                continue
            break

        if id_barang == "HAPUS":
            hapus_id = input_wajib("Masukkan ID barang di keranjang yang ingin dihapus: ").upper()
            if keranjang.pop(hapus_id, None):
                print("✅[SUKSES] Item dihapus dari keranjang.")
            else:
                print("⚠️[ERROR] Item tidak ada di keranjang.")
            continue

        if id_barang == "UBAH":
            ubah_id = input_wajib("Masukkan ID barang di keranjang yang ingin diubah: ").upper()
            if ubah_id not in keranjang:
                print("⚠️[ERROR] Item tidak ada di keranjang.")
                continue
            
            maks_stok = data_barang["barang"][ubah_id]["stok"]
            jumlah_baru = input_angka(f"Jumlah baru (0 untuk hapus, maks {maks_stok}): ", 0)

            if jumlah_baru == 0:
                del keranjang[ubah_id]
            elif jumlah_baru <= maks_stok:
                keranjang[ubah_id] = jumlah_baru
            else:
                print("⚠️[ERROR] Jumlah melebihi stok tersedia.")
            continue

        if id_barang not in data_barang["barang"]:
            print("⚠️[ERROR] ID barang tidak ditemukan.")
            continue

        barang = data_barang["barang"][id_barang]
        if  barang.get("status", "Aktif") != "Aktif":
            print(f"⚠️[ERROR] Barang berstatus '{barang.get('status')}', tidak bisa dijual.")
            continue

        hari_ini = datetime.now().date()
        if "expired" in barang:
            try:
                tanggal_expired = datetime.strptime(barang["expired"], "%d-%m-%Y").date()
                if tanggal_expired <= hari_ini:
                    print("⚠️[ERROR] BARANG SUDAH EXPIRED TIDAK BOLEH DIJUAL!")
                    continue
            except ValueError:
                pass

        tersedia = barang["stok"] - keranjang.get(id_barang, 0)
        if tersedia <= 0:
            print("⚠️[ERROR] Stok untuk barang ini sudah habis/terpakai di keranjang.")
            continue

        print(f"Stok yang masih bisa ditambahkan: {tersedia}")
        jumlah = input_angka("Jumlah tambahan: ", 1)
        if jumlah > tersedia:
            print(f"⚠️[ERROR] Stok tidak cukup, maksimal tambahan {tersedia}.")
            continue
        keranjang[id_barang] = keranjang.get(id_barang, 0) + jumlah
        print("[SUKSES] Barang masuk keranjang.")
        
    subtotal_transaksi = tampil_keranjang(keranjang)

    ppn = hitung_ppn(subtotal_transaksi)

    total = subtotal_transaksi + ppn

    print("\n=== RINCIAN PEMBAYARAN ===")
    print(f"Subtotal : {rupiah(subtotal_transaksi)}")
    print(f"PPN {TARIF_PPN}% : {rupiah(ppn)}")
    print("-" * 35)
    print(f"TOTAL    : {rupiah(total)}")
    print("1. Tunai (Cash)")
    print("2. Debit")
    print("Ketik 0 pada pembayaran untuk membatalkan transaksi.")
    while True:
        pilih_metode = input("Pilih metode (0-2): ").strip()
        if pilih_metode == "0":
            print("Transaksi dibatalkan. Stok tidak berubah.")
            return

        elif pilih_metode == "1":
            metode = "TUNAI"
            bayar = input_angka("Uang yang dibayarkan (Rp): ")
            if bayar < total:
                print(f"⚠️[ERROR] Uang kurang {rupiah(total - bayar)}.")
                continue
            kembalian = bayar - total
            break

        elif pilih_metode == "2":
            metode = "DEBIT"
            print(f"❗[INFO] Memproses pembayaran Debit sebesar {rupiah(total)} ")
            bayar = total
            kembalian = 0
            break
        else:
            print("⚠️[ERROR] Pilihan tidak valid.")

    baru = copy.deepcopy(data_barang)
    daftar_item = []
    for id_barang, jumlah in keranjang.items():
        barang = baru["barang"][id_barang]
        if jumlah > barang["stok"]:
            print("⚠️[ERROR] Stok berubah; transaksi tidak dapat diselesaikan.")
            return
        barang["stok"] -= jumlah
        sisa_hari, potongan, harga_akhir = hitung_diskon_expired(barang)
        harga_normal = ambil_harga_jual(barang)
        subtotal = jumlah * harga_akhir
        daftar_item.append({
          "id_barang": id_barang,
          "nama_barang": barang["nama_barang"],
          "jumlah": jumlah,

          # Harga jual dan modal saat transaksi
          "harga_normal": harga_normal,
          "harga_pabrik": ambil_harga_pabrik(barang),

          "diskon_persen": 4 if potongan > 0 else 0,
          "potongan": potongan,
          "harga": harga_akhir,
          "subtotal": subtotal,

          # Laba kotor dari barang yang terjual
          "laba_kotor": subtotal - (
              ambil_harga_pabrik(barang) * jumlah
)
        })

    data_transaksi = {
        "nomor": f"TRX{baru['nomor_berikutnya']:03d}",
        "tanggal": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "kasir_id": kasir[0],
        "kasir_nama": kasir[1]["nama"],
        "kasir_username": kasir[1]["username"],
        "item": daftar_item,

        "subtotal": subtotal_transaksi,
        "ppn": ppn,
        "tarif_ppn": TARIF_PPN,
        "total": total,

        "metode": metode,
        "bayar": bayar,
        "kembalian": kembalian
    }

    baru["transaksi"].append(data_transaksi)
    baru["nomor_berikutnya"] += 1
    if not simpan_data(baru):
        print("⚠️[ERROR] Transaksi gagal disimpan. Stok belum dikurangi.")
        return

    data_barang.clear()
    data_barang.update(baru)

    for item in daftar_item:
                barang = data_barang["barang"][item["id_barang"]]
                if barang["stok"] <= barang.get("stok_min", 5):
                    print(f"⚠️[PERINGATAN STOK] '{barang['nama_barang']}' tersisa {barang['stok']} (batas minimum: {barang.get('stok_min', 5)})!")

    print("\n[SUKSES] Pembayaran berhasil dan stok otomatis berkurang.")
    cetak_struk(data_transaksi)


def cetak_ulang_struk():
    riwayat_transaksi()
    if not data_barang["transaksi"]:
        return
    nomor = input_wajib("Nomor transaksi untuk cetak ulang: ").upper()
    data_transaksi = next((t for t in data_barang["transaksi"] if t["nomor"] == nomor), None)
    if data_transaksi:
        cetak_struk(data_transaksi)
    else:
        print("⚠️ [ERROR] Nomor transaksi tidak ditemukan.")

def retur_penjualan(id_login):
    lebar = 76
    print("\n" + "=" * lebar)
    print("RETUR PENJUALAN (PEMBATALAN SEBAGIAN / SELURUH TRANSAKSI)".center(lebar))
    print("=" * lebar)

    if not data_barang["transaksi"]:
        print("❗[INFO] Belum ada riwayat transaksi penjualan.")
        return

    riwayat_transaksi()
    nomor = input_wajib("Masukkan Nomor Transaksi yang diretur (contoh: TRX001): ").upper()

    transaksi = next((t for t in data_barang["transaksi"] if t["nomor"] == nomor), None)
    if not transaksi:
        print(f"⚠️[ERROR] Transaksi '{nomor}' tidak ditemukan.")
        return

    if not transaksi.get("item"):
        print("⚠️[ERROR] Transaksi ini tidak memiliki detail item.")
        return

    print("\n--- ITEM DALAM TRANSAKSI ---")
    for idx, item in enumerate(transaksi["item"], start=1):
        print(f"{idx}. [{item['id_barang']}] {item['nama_barang']} | Qty: {item['jumlah']} | Harga: {rupiah(item['harga'])} | Subtotal: {rupiah(item['subtotal'])}")

    print("\nPilih jenis retur:")
    print("1. Retur Sebagian Item")
    print("2. Retur Seluruh Transaksi")
    print("0. Batal")
    jenis_retur = input("Pilihan (0-2): ").strip()

    if jenis_retur == "0":
        print("❗[INFO] Retur penjualan dibatalkan.")
        return

    petugas = data_pengguna["pengguna"][id_login]["username"]
    role_petugas = data_pengguna["pengguna"][id_login]["role"]
    alasan_retur = input_wajib("Alasan retur dari pembeli: ")

    if jenis_retur == "2":
        if not konfirmasi_default(f"Yakin retur SELURUH transaksi {nomor} dan kembalikan semua stok?"):
            return

        total_refund = transaksi["total"]
        for item in transaksi["item"]:
            id_brg = item["id_barang"]
            jml = int(item["jumlah"])
            if id_brg in data_barang["barang"]:
                stok_awal = int(data_barang["barang"][id_brg]["stok"])
                data_barang["barang"][id_brg]["stok"] = stok_awal + jml
                list_riwayat_stok.append({
                    "id_barang": id_brg,
                    "nama_barang": item["nama_barang"],
                    "jenis": f"Retur Penjualan ({nomor})",
                    "jumlah": jml,
                    "stok_sebelum": stok_awal,
                    "stok_sesudah": stok_awal + jml
                })

        data_barang["transaksi"].remove(transaksi)
        if simpan_data():
            catat_log(role_petugas, f"RETUR PENUH {nomor} | Refund: {rupiah(total_refund)} | Alasan: {alasan_retur}", petugas)
            print(f"✅[SUKSES] Seluruh transaksi {nomor} diretur. Stok dikembalikan & uang kembali: {rupiah(total_refund)}.")

    elif jenis_retur == "1":
        id_brg_retur = input_wajib("Masukkan ID Barang yang diretur (contoh BRG001): ").upper()
        item_target = next((i for i in transaksi["item"] if i["id_barang"] == id_brg_retur), None)
        if not item_target:
            print("⚠️[ERROR] Barang tersebut tidak ada di dalam transaksi ini.")
            return

        maks_qty = int(item_target["jumlah"])
        qty_retur = input_angka(f"Jumlah yang diretur (1 - {maks_qty}): ", minimum=1)
        if qty_retur > maks_qty:
            print(f"⚠️[ERROR] Jumlah retur tidak boleh melebihi jumlah beli ({maks_qty}).")
            return

        if not konfirmasi_default(f"Konfirmasi retur {qty_retur} unit '{item_target['nama_barang']}' dari {nomor}?"):
            return

        # Kembalikan stok barang
        if id_brg_retur in data_barang["barang"]:
            stok_awal = int(data_barang["barang"][id_brg_retur]["stok"])
            data_barang["barang"][id_brg_retur]["stok"] = stok_awal + qty_retur
            list_riwayat_stok.append({
                "id_barang": id_brg_retur,
                "nama_barang": item_target["nama_barang"],
                "jenis": f"Retur Sebagian ({nomor})",
                "jumlah": qty_retur,
                "stok_sebelum": stok_awal,
                "stok_sesudah": stok_awal + qty_retur
            })

        # Hitung pengurangan transaksi & PPN proporsional
        total_lama = int(transaksi["total"])
        if qty_retur == maks_qty:
            transaksi["item"].remove(item_target)
        else:
            item_target["jumlah"] = maks_qty - qty_retur
            item_target["subtotal"] = item_target["jumlah"] * int(item_target["harga"])
            if "laba_kotor" in item_target:
                item_target["laba_kotor"] = item_target["subtotal"] - (int(item_target.get("harga_pabrik", item_target["harga"])) * item_target["jumlah"])

        if not transaksi["item"]:
            data_barang["transaksi"].remove(transaksi)
            uang_kembali = total_lama
        else:
            subtotal_baru = sum(int(i["subtotal"]) for i in transaksi["item"])
            tarif_ppn = int(transaksi.get("tarif_ppn", 0))
            ppn_baru = round(subtotal_baru * tarif_ppn / 100) if tarif_ppn > 0 else 0
            total_baru = subtotal_baru + ppn_baru
            uang_kembali = max(0, total_lama - total_baru)

            transaksi["subtotal"] = subtotal_baru
            transaksi["ppn"] = ppn_baru
            transaksi["total"] = total_baru
            if transaksi["bayar"] >= total_baru:
                transaksi["kembalian"] = transaksi["bayar"] - total_baru

        if simpan_data():
            catat_log(role_petugas, f"RETUR SEBAGIAN {nomor} {id_brg_retur} ({qty_retur} unit) | Refund: {rupiah(uang_kembali)} | Alasan: {alasan_retur}", petugas)
            print(f"✅[SUKSES] Retur {qty_retur} unit '{item_target['nama_barang']}' berhasil.")
            print(f"💰 Uang dikembalikan ke pembeli: {rupiah(uang_kembali)}")
    else:
        print("⚠️[ERROR] Pilihan tidak valid.")

def riwayat_transaksi_tanggal():
    print("\n=== RIWAYAT TRANSAKSI ===")

    if not data_barang["transaksi"]:
        print("Belum ada transaksi.")
        return

    print("Masukkan tanggal dengan format DD-MM-YYYY")
    print("Ketik 0 untuk kembali.")
    tanggal_cari = input("Tanggal: ").strip()
    if tanggal_cari == "0":
        return

    try:
        datetime.strptime(tanggal_cari, "%d-%m-%Y")
    except ValueError:
        print("⚠️  [ERROR] Format tanggal tidak valid.")
        print("Gunakan format DD-MM-YYYY, contoh: 11-11-2026")
        return

    hasil = []

    for data_transaksi in data_barang["transaksi"]:
        tanggal_transaksi = data_transaksi["tanggal"][:10]

        if tanggal_transaksi == tanggal_cari:
            hasil.append(data_transaksi)

    if not hasil:
        print(f"\nTidak ada transaksi pada tanggal {tanggal_cari}.")
        return

    print(f"\n=== RIWAYAT TRANSAKSI {tanggal_cari} ===")
    lebar = 68
    print("-" * lebar)

    total_penjualan = 0

    for data_transaksi in hasil:
        print(
            f"{data_transaksi['nomor']:<10} | "
            f"{data_transaksi['tanggal']:<19} | "
            f"{data_transaksi['kasir_nama'][:16]:<16} | "
            f"{rupiah(data_transaksi['total']):>12}"
        )

        total_penjualan += data_transaksi["total"]

    print("-" * lebar)
    print(f"Jumlah transaksi : {len(hasil)}")
    print(f"Total penjualan  : {rupiah(total_penjualan)}")


def rekomendasi_barang_terlaris():
    lebar = 70
    print("\n" + "=" * lebar)
    print(" REKOMENDASI BARANG TERLARIS".center(lebar))
    print("=" * lebar)

    if not data_barang["transaksi"]:
        print("❗[INFO] Belum ada transaksi penjualan.")
        print("Belum tersedia data untuk rekomendasi barang.")
        return

    data_rekomendasi = {}
    #ngitung lek tuku (ben sisteme kenek ditumpuk )
    for transaksi in data_barang["transaksi"]:
        barang_dalam_transaksi = set()
        for item in transaksi.get("item", []):
            id_barang = item.get("id_barang", "")
            nama_barang = item.get("nama_barang", "Tidak diketahui")
            jumlah = int(item.get("jumlah", 0))
            subtotal = int(item.get(
                "subtotal",
                item.get("harga", 0) * jumlah
            ))
            if not id_barang:
                continue

            if id_barang not in data_rekomendasi:
                data_rekomendasi[id_barang] = {
                    "nama_barang": nama_barang,
                    "jumlah_terjual": 0,
                    "jumlah_transaksi": 0,
                    "total_pendapatan": 0
                }

            data_rekomendasi[id_barang]["jumlah_terjual"] += jumlah

            data_rekomendasi[id_barang]["total_pendapatan"] += subtotal

            barang_dalam_transaksi.add(id_barang)

        # Menghitung berapa transaksi yang membeli barang tersebut
        for id_barang in barang_dalam_transaksi:
            data_rekomendasi[id_barang]["jumlah_transaksi"] += 1

    if not data_rekomendasi:
        print("❗[INFO] Belum ada data penjualan barang.")
        return

  #angon ge ngurutke
    barang_urut = sorted(
        data_rekomendasi.items(),
        key=lambda x: (
            x[1]["jumlah_terjual"],
            x[1]["total_pendapatan"]
        ),
        reverse=True
    )

    print("\n=== DAFTAR BARANG PALING LARIS ===")

    print(
        f"{'RANK':<7}"
        f"{'NAMA BARANG':<20}"
        f"{'TERJUAL':>10}"
        f"{'TRANSAKSI':>12}"
    )

    print("-" * lebar)

   #sing ditampilan 5 barang teratas sing paling laris terbeli (ikin panggone ngurutke )
    for peringkat, (id_barang, barang) in enumerate(
        barang_urut[:5], start=1
    ):

        print(
            f"{peringkat:<7}"
            f"{barang['nama_barang'][:19]:<20}"
            f"{barang['jumlah_terjual']:>10}"
            f"{barang['jumlah_transaksi']:>12}"
        )

    print("-" * lebar)

    #iki sing digawe nampilke
    print("\n=== DETAIL REKOMENDASI BARANG ===")

    for peringkat, (id_barang, barang) in enumerate(
        barang_urut[:5], start=1
    ):
        barang_sekarang = data_barang["barang"].get(id_barang)
        if barang_sekarang:
            stok = barang_sekarang["stok"]
            harga = ambil_harga_jual(barang_sekarang)
            if stok > 0:
                status = "TERSEDIA"
            else:
                status = "STOK HABIS"
        else:
            stok = 0
            harga = 0
            status = "BARANG SUDAH DIHAPUS"

        print("\n" + "=" * 50)
        print(f"Peringkat          : {peringkat}")
        print(f"ID Barang          : {id_barang}")
        print(f"Nama Barang        : {barang['nama_barang']}")
        print(f"Jumlah Terjual     : {barang['jumlah_terjual']} buah")
        print(f"Jumlah Transaksi   : {barang['jumlah_transaksi']}")
        print(f"Harga Saat Ini     : {rupiah(harga)}")
        print(f"Total Pendapatan   : {rupiah(barang['total_pendapatan'])}")
        print(f"Stok Saat Ini      : {stok}")
        print(f"Status             : {status}")
        if peringkat == 1 and stok > 0:
            print("REKOMENDASI        : BARANG PALING LARIS!")
        elif stok > 0:
            print("REKOMENDASI        : LAYAK DIREKOMENDASIKAN")
        else:
            print("REKOMENDASI        : PERLU RESTOCK")

    print("\n" + "=" * lebar)
    print("Data rekomendasi berdasarkan seluruh riwayat transaksi.")
    print("=" * lebar)


# ==========================================
# PENGATURAN MENU (ROLE)
# ==========================================

def aktifkan_pengguna(admin_login):
    arsip = data_pengguna.get("arsip_pengguna", {})
    if not arsip:
        print("[INFO] Tidak ada akun nonaktif.")
        return
    tampilkan_data_pengguna()
    id_pengguna = input_wajib("Masukkan ID pengguna yang ingin diaktifkan kembali: ").upper()
    if id_pengguna not in arsip:
        print("⚠️ [ERROR] ID pengguna tidak ditemukan di daftar nonaktif.")
        return
    pengguna_aktif = arsip.pop(id_pengguna)
    pengguna_aktif["date_deleted"] = "-"
    pengguna_aktif["date_modified"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    data_pengguna["pengguna"][id_pengguna] = pengguna_aktif
    if simpan_data():
        pelaku = data_pengguna["pengguna"][admin_login]["username"]
        catat_log("admin", f"Mengaktifkan kembali pengguna {pengguna_aktif['username']} ({id_pengguna})", pelaku)
        print(f"✅[SUKSES] Akun '{pengguna_aktif['nama']}' kembali aktif.")

def ganti_password_sendiri(id_login):
    pengguna = data_pengguna["pengguna"][id_login]
    print("\n=== GANTI PASSWORD SENDIRI ===")
    password_lama = getpass.getpass("Masukkan password lama: ").strip()
    if not cek_password(password_lama, pengguna["password"]):
        print("⚠️ [ERROR] Password lama salah.")
        return
    password_baru = input_password_simple("Masukkan password baru (minimal 6 karakter): ")
    if len(password_baru) < 6:
        print("⚠️ [ERROR] Password baru minimal 6 karakter.")
        return
    pengguna["password"] = buat_hash_password(password_baru)
    pengguna["date_modified"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    if simpan_data():
        catat_log(pengguna["role"], "Mengganti password akun sendiri", pengguna["username"])
        print("✅[SUKSES] Password Anda berhasil diperbarui.")

def lihat_log_aktivitas():
    print("\n=== LOG AKTIVITAS (20 TERAKHIR) ===")
    print("1. Semua Aktivitas (log_aktivitas.txt)")
    print("2. Khusus Admin (log_admin.txt)")
    print("3. Khusus Gudang (log_gudang.txt)")
    print("4. Khusus Kasir (log_kasir.txt)")
    pilihan = input("Pilih log (1-4): ").strip()
    peta_file = {
        "1": FILE_LOG,
        "2": DATA_DIR / "log_admin.txt",
        "3": DATA_DIR / "log_gudang.txt",
        "4": DATA_DIR / "log_kasir.txt"
    }
    target_file = peta_file.get(pilihan)
    if not target_file or not target_file.exists():
        print("[INFO] File log belum tersedia.")
        return
    semua_baris = [baris for baris in target_file.read_text(encoding="utf-8").splitlines() if baris.strip()]
    if not semua_baris:
        print("[INFO] Belum ada catatan log.")
        return
    for baris in semua_baris[-20:]:
        print(baris)

# ==========================================
# SUBMENU TERPADU (PENGGABUNGAN FITUR BERCABANG)
# ==========================================
def submenu_kelola_pengguna(id_login):
    while True:
        print("\n=== KELOLA PENGGUNA ===")
        print("1. Tampilkan Semua Pengguna")
        print("2. Tambah Pengguna")
        print("3. Edit Pengguna")
        print("4. Nonaktifkan Pengguna")
        print("5. Aktifkan Kembali Pengguna")
        print("6. Cari Pengguna")
        print("7. Reset Password Pengguna")
        print("0. Kembali")
        pilih = input("Pilih fitur (0-7): ").strip()
        if pilih == "0":
            break
        elif pilih == "1":
            tampilkan_data_pengguna()
        elif pilih == "2":
            tambah_pengguna()
        elif pilih == "3":
            edit_pengguna()
        elif pilih == "4":
            hapus_pengguna(id_login)
        elif pilih == "5":
            aktifkan_pengguna(id_login)
        elif pilih == "6":
            cari_pengguna()
        elif pilih == "7":
            reset_password_pengguna(id_login)
        else:
            print("Pilihan tidak valid.")

def submenu_kelola_barang_admin():
    while True:
        print("\n=== KELOLA DATA BARANG ===")
        print("1. Tampilkan Data Barang")
        print("2. Tambah Barang")
        print("3. Edit Barang")
        print("4. Hapus Barang")
        print("5. Kelola Status Barang")
        print("6. Kelola & Tambah Kategori Barang")
        print("0. Kembali")
        pilih = input("Pilih fitur (0-6): ").strip()
        if pilih == "0":
            break
        elif pilih == "1":
            tampilkan_barang()
        elif pilih == "2":
            tambah_barang()
        elif pilih == "3":
            edit_barang()
        elif pilih == "4":
            hapus_barang()
        elif pilih == "5":
            kelola_status_barang()
        elif pilih == "6":
            tampilkan_daftar_kategori()
            if konfirmasi_default("Tambah kategori baru?"):
                tambah_kategori_baru(oleh_admin=True)
        else:
            print("Pilihan tidak valid.")

def submenu_lihat_cari_barang():
    while True:
        print("\n=== LIHAT & CARI BARANG ===")
        print("1. Tampilkan Data Barang")
        print("2. Cari Barang (Kode / Nama)")
        print("3. Kategori Barang")
        print("0. Kembali")
        pilih = input("Pilih fitur (0-2): ").strip()
        if pilih == "0":
            break
        elif pilih == "1":
            tampilkan_barang()
        elif pilih == "2":
            cari_barang()
        elif pilih == "3":
            filter_kategori_barang()
        else:
            print("Pilihan tidak valid.")

def submenu_laporan_admin():
    while True:
        print("\n=== LAPORAN PENJUALAN & AKTIVITAS GUDANG ===")
        print("1. Laporan Penjualan (Harian / Mingguan / Bulanan)")
        print("2. Rekomendasi 5 Barang Terlaris")
        print("3. Laporan Kondisi Stok & Expired")
        print("4. Riwayat Perubahan Stok")
        print("5. Hapus Transaksi Penjualan")
        print("6. Laporan Nilai Persediaan")
        print("7. Retur Penjualan")
        print("0. Kembali")
        pilih = input("Pilih fitur (0-7): ").strip()
        if pilih == "0":
            break
        elif pilih == "1":
            laporan_penjualan_admin()
        elif pilih == "2":
            rekomendasi_barang_terlaris()
        elif pilih == "3":
            laporan_barang()
        elif pilih == "4":
            riwayat_stok()
        elif pilih == "5":
            hapus_transaksi()
        elif pilih == "6":
            laporan_nilai_persediaan()
        elif pilih == "7":
            id_admin = next(iter(data_pengguna["pengguna"]))
            retur_penjualan(id_admin)
        else:
            print("Pilihan tidak valid.")

# ==========================================
# MENU UTAMA PER ROLE (SUDAH DISATUKAN)
# ==========================================
def tampilkan_ringkasan_login(id_login):
    pengguna = data_pengguna["pengguna"][id_login]
    hari_ini_tampil = datetime.now().strftime("%d-%m-%Y")

    # 1. Mengumpulkan semua transaksi yang terjadi hari ini
    transaksi_hari_ini = []
    for transaksi in data_barang["transaksi"]:
        if transaksi["tanggal"].startswith(hari_ini_tampil):
            transaksi_hari_ini.append(transaksi)

    print("\n" + "=" * 56)
    print(f"Pengguna : {pengguna['nama']} ({pengguna['role']})")
    print(f"Tanggal  : {hari_ini_tampil}")
    print("-" * 56)

    # 2. Tampilan ringkasan khusus untuk Admin dan Gudang
    if pengguna["role"] == "admin" or pengguna["role"] == "gudang":
        jumlah_jenis_barang = len(data_barang["barang"])
        jumlah_stok_minimum = 0
        jumlah_stok_habis = 0

        # Menghitung barang yang stoknya menipis atau habis
        for barang in data_barang["barang"].values():
            batas_minimum = barang.get("stok_min", 5)
            if barang["stok"] == 0:
                jumlah_stok_habis += 1
            elif barang["stok"] <= batas_minimum:
                jumlah_stok_minimum += 1

        # Menghitung total uang penjualan hari ini
        total_penjualan_hari_ini = 0
        for transaksi in transaksi_hari_ini:
            total_penjualan_hari_ini += transaksi["total"]

        print(f"Jenis barang         : {jumlah_jenis_barang}")
        print(f"Stok minimum / habis : {jumlah_stok_minimum} / {jumlah_stok_habis}")
        print(f"Penjualan hari ini   : {len(transaksi_hari_ini)} transaksi, {rupiah(total_penjualan_hari_ini)}")

    # 3. Tampilan ringkasan khusus untuk Kasir
    else:
        jumlah_transaksi_kasir = 0
        total_penjualan_kasir = 0

        # Menghitung transaksi hari ini milik kasir yang sedang login saja
        for transaksi in transaksi_hari_ini:
            if transaksi.get("kasir_username") == pengguna["username"]:
                jumlah_transaksi_kasir += 1
                total_penjualan_kasir += transaksi["total"]

        print(f"Transaksi Anda hari ini : {jumlah_transaksi_kasir} transaksi ({rupiah(total_penjualan_kasir)})")

    print("=" * 56)

def backup_data_sistem(id_login):
    lebar = 64
    print("\n" + "=" * lebar)
    print("BACKUP DATA SISTEM".center(lebar))
    print("=" * lebar)

    if not simpan_data():
        print("⚠️ [ERROR] Gagal menyimpan data terbaru sebelum backup.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tujuan_backup = FOLDER_BACKUP / f"backup_{timestamp}"

    try:
        FOLDER_BACKUP.mkdir(parents=True, exist_ok=True)
        shutil.copytree(DATA_DIR, tujuan_backup / "data")
        if FOLDER_STRUK.exists():
            shutil.copytree(FOLDER_STRUK, tujuan_backup / "struk")

        pelaku = data_pengguna["pengguna"][id_login]["username"]
        catat_log("admin", f"Membuat backup data ke tujuan {tujuan_backup.name}", pelaku)
        print(f"✅ [SUKSES] Seluruh data berhasil di-backup ke:\n   {tujuan_backup}")
        
    except Exception as error:
        print(f"⚠️ [ERROR] Gagal membuat backup: {error}")

def restore_data_sistem(id_login):
    lebar = 64
    print("\n" + "=" * lebar)
    print("RESTORE DATA SISTEM (SHUTIL)".center(lebar))
    print("=" * lebar)

    if not FOLDER_BACKUP.exists():
        print("❗[INFO] Belum ada folder backup yang tersimpan.")
        return

    daftar_backup = sorted(
        [folder for folder in FOLDER_BACKUP.iterdir() if folder.is_dir()],
        reverse=True
    )

    if not daftar_backup:
        print("❗[INFO] Belum ada folder backup yang tersedia.")
        return

    print("Daftar Backup Tersedia:")
    for idx, folder in enumerate(daftar_backup, start=1):
        print(f"{idx}. {folder.name}")

    pilih = input("\nPilih nomor backup yang ingin di-restore (0 untuk batal): ").strip()
    if pilih == "0" or not pilih:
        print("❗[INFO] Restore dibatalkan.")
        return

    try:
        indeks = int(pilih) - 1
        if indeks < 0 or indeks >= len(daftar_backup):
            raise ValueError
    except ValueError:
        print("⚠️ [ERROR] Nomor backup tidak valid.")
        return

    sumber_backup = daftar_backup[indeks]
    if not konfirmasi_default(f"Yakin menimpa data saat ini dengan '{sumber_backup.name}'?"):
        print("❗[INFO] Restore dibatalkan.")
        return

    try:
        sumber_data = sumber_backup / "data"
        if sumber_data.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            for item in sumber_data.iterdir():
                if item.is_file():
                    shutil.copy2(item, DATA_DIR / item.name)

        sumber_struk = sumber_backup / "struk"
        if sumber_struk.exists():
            FOLDER_STRUK.mkdir(parents=True, exist_ok=True)
            for item in sumber_struk.iterdir():
                if item.is_file():
                    shutil.copy2(item, FOLDER_STRUK / item.name)

        global data_pengguna
        data_pengguna = muat_data()

        pelaku = data_pengguna["pengguna"][id_login]["username"]
        catat_log("admin", f"Melakukan restore data dari {sumber_backup.name}", pelaku)
        print(f"✅ [SUKSES] Data berhasil dipulihkan dari '{sumber_backup.name}'.")
    except Exception as error:
        print(f"⚠️ [ERROR] Gagal melakukan restore data: {error}")

def menu_admin(id_login):
    peringatan_stok_otomatis()
    while True:
        print("\n=== MENU ADMIN ===")
        print("1. Ringkasan Login")
        print("2. Kelola Pengguna")
        print("3. Kelola Data Barang")
        print("4. Lihat & Cari Barang")
        print("5. Daftar Stok & Kartu Stok")
        print("6. Laporan Penjualan & Gudang")
        print("7. Log Aktivitas")
        print("8. Ganti Password")
        print("9. Menu Gudang")
        print("10. Menu Kasir")
        print("11. Backup Data Sistem")
        print("12. Restore Data Sistem")
        print("0. Logout")
        pilih = input("Pilih fitur yang ingin digunakan (0-12): ").strip()
        if pilih == "1":
            tampilkan_ringkasan_login(id_login)
        elif pilih == "2":
            submenu_kelola_pengguna(id_login)
        elif pilih == "3":
            submenu_kelola_barang_admin()
        elif pilih == "4":
            submenu_lihat_cari_barang()
        elif pilih == "5":
            peringatan_stok_otomatis()
            kartu_stok_barang()
        elif pilih == "6":
            submenu_laporan_admin()
        elif pilih == "7":
            lihat_log_aktivitas()
        elif pilih == "8":
            ganti_password_sendiri(id_login)
        elif pilih == "9":
            menu_gudang(id_login)
        elif pilih == "10":
            menu_kasir(id_login)
        elif pilih == "11":
            backup_data_sistem(id_login)
        elif pilih == "12":
            restore_data_sistem(id_login)
        elif pilih == "0":
            catat_log("admin", "Logout dari sistem", data_pengguna["pengguna"][id_login]["username"])
            print("\n" + "=" * 64)
            print("BERHASIL LOGOUT DARI AKUN".center(64))
            print("=" * 64)
            break
        else:
            print("Pilihan tidak valid.")

def menu_gudang(id_login):
    peringatan_stok_otomatis()
    while True:
        print("\n=== MENU GUDANG ===")
        print("1. Ringkasan Login")
        print("2. Lihat & Cari Barang")
        print("3. Catat Barang Masuk")
        print("4. Catat Barang Keluar")
        print("5. Daftar Stok, Kartu Stok & Cek Expired")
        print("6. Laporan Stok & Analisis Harga (SPLDV)")
        print("7. Ganti Password")
        print("8. Stok Opname (Cek Stok Fisik)")
        print("9. Laporan Nilai Persediaan")
        print("0. Logout")
        pilih = input("Pilih fitur yang ingin digunakan (0-9): ").strip()
        if pilih == "1":
            tampilkan_ringkasan_login(id_login)
        elif pilih == "2":
            submenu_lihat_cari_barang()
        elif pilih == "3":
            catat_barang_masuk(id_login)
        elif pilih == "4":
            catat_barang_keluar(id_login)
        elif pilih == "5":
            peringatan_stok_otomatis()
            kartu_stok_barang()
            cek_dan_urutkan_expired()
        elif pilih == "6":
            laporan_barang()
            notifikasi_barang()
            if konfirmasi_default("Jalankan analisis harga satuan SPLDV?"):
                analisis_spldv_harga_barang()
        elif pilih == "7":
            ganti_password_sendiri(id_login)
        elif pilih == "8":
            stok_opname(id_login)
        elif pilih == "9":
            laporan_nilai_persediaan()
        elif pilih == "0":
            catat_log("gudang", "Logout dari sistem", data_pengguna["pengguna"][id_login]["username"])
            print("\n" + "=" * 64)
            print("BERHASIL LOGOUT DARI AKUN".center(64))
            print("=" * 64)
            break
        else:
            print("Pilihan tidak valid.")

def menu_kasir(id_login):
    while True:
        kasir = (id_login, data_pengguna["pengguna"][id_login])
        print(f"\n=== MENU KASIR | {kasir[1]['nama']} ===")
        print("1. Ringkasan Login")
        print("2. Transaksi Penjualan dan Cetak Nota")
        print("3. Lihat & Cari Barang")
        print("4. Cetak Ulang Struk & Riwayat Tanggal")
        print("5. Rekomendasi 5 Barang Terlaris")
        print("6. Ganti Password")
        print("7. Retur Penjualan")
        print("0. Logout")
        pilih = input("Pilih fitur yang ingin digunakan (0-7): ").strip()
        if pilih == "1":
            tampilkan_ringkasan_login(id_login)
        elif pilih == "2":
            transaksi_penjualan(kasir)
        elif pilih == "3":
            submenu_lihat_cari_barang()
        elif pilih == "4":
            cetak_ulang_struk()
            riwayat_transaksi_tanggal()
        elif pilih == "5":
            rekomendasi_barang_terlaris()
        elif pilih == "6":
            ganti_password_sendiri(id_login)
        elif pilih == "7":
            retur_penjualan(id_login)
        elif pilih == "0":
            catat_log("kasir", "Logout dari sistem", kasir[1]["username"])
            print("\n" + "=" * 64)
            print("BERHASIL LOGOUT DARI AKUN".center(64))
            print("=" * 64)
            break
        else:
            print("Pilihan tidak valid.")

def main():
    lebar = 64
    print("\n" + "=" * lebar)
    print("SELAMAT DATANG DI APLIKASI KASIR & GUDANG SMK MART".center(lebar))
    print("SMKN 1 BOYOLANGU - SISTEM MANAJEMEN RITEL TERPADU".center(lebar))
    print("=" * lebar)

    global data_pengguna
    data_pengguna = muat_data()

    percobaan_gagal = 0
    while True:
        print("\n" + "=" * lebar)
        print("LOGIN PENGGUNA SMK MART".center(lebar))
        print("=" * lebar)
        username = input_wajib("Username (ketik 0 untuk keluar): ").strip().lower()
        if username == "0":
            print("\n" + "=" * lebar)
            print("TERIMA KASIH TELAH MENGGUNAKAN SMK MART".center(lebar))
            print("Program selesai. Sampai jumpa kembali!".center(lebar))
            print("=" * lebar)
            break

        password = getpass.getpass("Masukkan password anda          : ").strip()

        akun_nonaktif = any(
            pengguna["username"] == username
            for pengguna in data_pengguna.get("arsip_pengguna", {}).values()
        )
        if akun_nonaktif:
            print("-" * lebar)
            print("⚠️ [DITOLAK] Akun Anda berstatus NONAKTIF. Hubungi Admin.")
            print("-" * lebar)
            continue

        login = next(
            (
                (id_pengguna, pengguna)
                for id_pengguna, pengguna in data_pengguna["pengguna"].items()
                if pengguna["username"] == username and cek_password(password, pengguna["password"])
            ),
            None
        )

        if not login:
            percobaan_gagal += 1
            print("-" * lebar)
            print(f"⚠️ [ERROR] Username atau password salah ({percobaan_gagal}/3).")
            if percobaan_gagal >= 3:
                id_target = next(
                (
                        id_pengguna
                        for id_pengguna, data_akun in data_pengguna["pengguna"].items()
                        if data_akun["username"].strip().lower() == username
                    ),
                    None
                )

                if id_target and username not in ("admin utama", "admin_utama"):
                    akun_nonaktif = data_pengguna["pengguna"].pop(id_target)
                    akun_nonaktif["date_deleted"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    data_pengguna.setdefault("arsip_pengguna", {})[id_target] = akun_nonaktif
                    simpan_data()
                    catat_log("sistem", f"Akun {username} dinonaktifkan otomatis (3x gagal login)", username)
                    print(f"⚠️ [DITOLAK] Salah 3 kali. Akun '{username}' telah DINONAKTIFKAN otomatis. Hubungi Admin Utama.")
                    percobaan_gagal = 0
                    print("=" * lebar)
                    continue
                else:
                    print("⚠️ [DITOLAK] Salah 3 kali. Akses ditolak dan program berhenti.")
                    print("=" * lebar)
                    print("PROGRAM DIHENTIKAN DEMI KEAMANAN SISTEM".center(lebar))
                    print("=" * lebar)
                    break
                
            print("=" * lebar)
            continue
            
        percobaan_gagal = 0
        id_login, pengguna = login

        catat_log(pengguna["role"], "Login ke sistem", pengguna["username"])
        print("-" * lebar)
        print(f"✅ [SUKSES] Halo, {pengguna['nama']}! Login sebagai {pengguna['role'].upper()}.")
        print("-" * lebar)

        if pengguna["role"] == "admin":
            menu_admin(id_login)
        elif pengguna["role"] == "gudang":
            menu_gudang(id_login)
        elif pengguna["role"] == "kasir":
            menu_kasir(id_login)

try:
    main()
except (KeyboardInterrupt, EOFError):
    lebar = 64
    print("\n" + "=" * lebar)
    print("PROGRAM SMK MART DIHENTIKAN".center(lebar))
    print("=" * lebar)
