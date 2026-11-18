from pathlib import Path
import hashlib
import hmac
import os
import secrets
from datetime import datetime
import copy
import getpass
import random

# ==========================================
# KONFIGURASI FOLDER & FILE .TXT (STANDAR SAS)
# ==========================================
LOKASI_SCRIPT_INI = Path.cwd()
BASE_DIR = LOKASI_SCRIPT_INI / "SMK_MART_Python"
DATA_DIR = BASE_DIR / "data"
FOLDER_STRUK = BASE_DIR / "struk"
FOLDER_LAPORAN = BASE_DIR / "laporan"

for folder in (BASE_DIR, DATA_DIR, FOLDER_STRUK, FOLDER_LAPORAN):
    folder.mkdir(parents=True, exist_ok=True)

FILE_PENGGUNA = DATA_DIR / "pengguna.txt"
FILE_BARANG = DATA_DIR / "barang.txt"
FILE_TRANSAKSI = DATA_DIR / "transaksi.txt"
FILE_DETAIL = DATA_DIR / "detail_transaksi.txt"
FILE_MASUK = DATA_DIR / "barang_masuk.txt"
FILE_KELUAR = DATA_DIR / "barang_keluar.txt"
FILE_LOG = DATA_DIR / "log_aktivitas.txt"

data_barang = {}
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
    return "Rp " + f"{int(nilai):,}".replace(",", ".")

def input_wajib(pesan):
    while True:
        hasil = input(pesan).strip()
        if not hasil:
            print("⚠️ [ERROR] Input tidak boleh kosong.")
            continue
        if "|" in hasil:
            print("⚠️ [ERROR] Input tidak boleh mengandung karakter '|'.")
            continue
        return hasil

def input_password_simple(pesan="Masukkan password: ", boleh_kosong=False):
    while True:
        password = getpass.getpass(pesan).strip()
        if not password:
            if boleh_kosong:
                return ""
            print("⚠️ [ERROR] Password tidak boleh kosong.")
            continue

        if "|" in password:
            print("⚠️ [ERROR] Password tidak boleh mengandung karakter '|'.")
            continue

        password2 = getpass.getpass("Ulangi password: ").strip()
        if password != password2:
            print("⚠️ [ERROR] Password pertama dan kedua tidak sama! Silakan ulangi.")
            continue

        return password

def input_angka(pesan, minimum=0):
    while True:
        try:
            angka = int(input(pesan).strip())
            if angka < minimum:
                print(f"⚠️ [ERROR] Angka minimal {minimum}.")
                continue
            return angka
        except ValueError:
            print("⚠️ [ERROR] Masukkan bilangan bulat yang valid.")

def buat_hash_password(password):
    salt = secrets.token_hex(16)
    hasil = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 150_000)
    return f"{salt}${hasil.hex()}"

def cek_password(password, password_tersimpan):
    if "$" not in password_tersimpan:
        return password == password_tersimpan
    try:
        salt, nilai = password_tersimpan.split("$", 1)
        hasil = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 150_000)
        return hmac.compare_digest(hasil, bytes.fromhex(nilai))
    except (ValueError, TypeError):
        return False

def buat_id_otomatis(file_path, prefix):
    nomor_terakhir = 0
    if file_path.exists():
        for baris in file_path.read_text(encoding="utf-8").splitlines():
            if baris.strip():
                kode_awal = baris.split("|")[0]
                if kode_awal.startswith(prefix) and kode_awal[len(prefix):].isdigit():
                    nomor_terakhir = max(nomor_terakhir, int(kode_awal[len(prefix):]))
    return f"{prefix}{nomor_terakhir + 1:03d}"

def catat_log(role, aktivitas, username="sistem"):
    sekarang = datetime.now()
    tgl_iso = sekarang.strftime("%Y-%m-%d")
    jam = sekarang.strftime("%H:%M:%S")

    try:
        # 1. File utama sesuai spesifikasi SAS: tanggal|waktu|username|aksi
        with FILE_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{tgl_iso}|{jam}|{username}|{aktivitas}\n")

        # 2. File log terpisah per role (log_admin.txt, log_gudang.txt, log_kasir.txt)
        nama_file_role = DATA_DIR / f"log_{role.lower()}.txt"
        with nama_file_role.open("a", encoding="utf-8") as f:
            f.write(f"[{sekarang.strftime('%d-%m-%Y %H:%M:%S')}] ({username}) {aktivitas}\n")
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

# ==========================================
# MUAT & SIMPAN DATA (.TXT FORMAT PIPE '|')
# ==========================================
def muat_data():
    global data_barang, data_pengguna, list_riwayat_stok

    for f_txt in (FILE_PENGGUNA, FILE_BARANG, FILE_TRANSAKSI, FILE_DETAIL, FILE_MASUK, FILE_KELUAR, FILE_LOG):
        if not f_txt.exists():
            f_txt.write_text("", encoding="utf-8")

    pengguna_aktif = {}
    pengguna_arsip = {}

    baris_user = [b for b in FILE_PENGGUNA.read_text(encoding="utf-8").splitlines() if b.strip()]
    if not baris_user:
        pengguna_aktif["ADM001"] = {
            "nama": "Administrator SMK MART",
            "username": "admin",
            "password": buat_hash_password("admin123"),
            "role": "admin",
            "date_added": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "date_modified": "-",
            "date_deleted": "-"
        }
    else:
        for idx, baris in enumerate(baris_user, start=1):
            bagian = baris.split("|")
            if len(bagian) < 5:
                continue
            uname, pw, nama, role, status = bagian[:5]
            id_usr = "ADM001" if uname == "admin" else f"USR{idx:03d}"
            pw_tersimpan = pw if "$" in pw else buat_hash_password(pw)
            obj_user = {
                "nama": nama,
                "username": uname,
                "password": pw_tersimpan,
                "role": role,
                "date_added": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "date_modified": "-",
                "date_deleted": "-"
            }
            if status.lower() == "aktif":
                pengguna_aktif[id_usr] = obj_user
            else:
                pengguna_arsip[id_usr] = obj_user

    data_pengguna = {
        "pengguna": pengguna_aktif,
        "arsip_pengguna": pengguna_arsip
    }

    barang_aktif = {}
    for baris in FILE_BARANG.read_text(encoding="utf-8").splitlines():
        if not baris.strip():
            continue
        bagian = baris.split("|")
        if len(bagian) < 6:
            continue
        kode, nama_brg, kategori, harga, stok, stok_min = bagian[:6]
        barang_aktif[kode] = {
            "nama_barang": nama_brg,
            "kategori": kategori,
            "stok": int(stok),
            "stok_min": int(stok_min),
            "harga": int(harga),
            "harga_pabrik": int(harga),
            "harga_jual": int(harga),
            "expired": "31-12-2099",
            "status": "Aktif"
        }

    detail_per_trx = {}
    for baris in FILE_DETAIL.read_text(encoding="utf-8").splitlines():
        if not baris.strip():
            continue
        no_trx, kd_brg, nm_brg, hrg, jml, sub = baris.split("|")[:6]
        detail_per_trx.setdefault(no_trx, []).append({
            "id_barang": kd_brg,
            "nama_barang": nm_brg,
            "harga": int(hrg),
            "jumlah": int(jml),
            "subtotal": int(sub)
        })

    daftar_trx = []
    nomor_urut_terakhir = 0
    for baris in FILE_TRANSAKSI.read_text(encoding="utf-8").splitlines():
        if not baris.strip():
            continue
        no_trx, tgl, wkt, kasir_u, tot, byr, kmb = baris.split("|")[:7]
        if no_trx.startswith("TRX") and no_trx[3:].isdigit():
            nomor_urut_terakhir = max(nomor_urut_terakhir, int(no_trx[3:]))
        try:
            tgl_tampil = datetime.strptime(tgl, "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            tgl_tampil = tgl
        daftar_trx.append({
            "nomor": no_trx,
            "tanggal": f"{tgl_tampil} {wkt}",
            "kasir_username": kasir_u,
            "kasir_nama": kasir_u,
            "item": detail_per_trx.get(no_trx, []),
            "total": int(tot),
            "bayar": int(byr),
            "kembalian": int(kmb)
        })

    data_barang = {
        "barang": barang_aktif,
        "arsip_barang": {},
        "transaksi": daftar_trx,
        "nomor_berikutnya": nomor_urut_terakhir + 1
    }

    migrasi_harga_barang()
    simpan_data()
    return data_pengguna

def simpan_data(data_baru=None):
    sumber_barang = data_baru if data_baru else data_barang
    try:
        # 1. Simpan pengguna.txt -> username|password|nama_lengkap|peran|status
        baris_usr = []
        for u in data_pengguna.get("pengguna", {}).values():
            baris_usr.append(f"{u['username']}|{u['password']}|{u['nama']}|{u['role']}|aktif")
        for u in data_pengguna.get("arsip_pengguna", {}).values():
            baris_usr.append(f"{u['username']}|{u['password']}|{u['nama']}|{u['role']}|nonaktif")
        FILE_PENGGUNA.write_text("\n".join(baris_usr) + ("\n" if baris_usr else ""), encoding="utf-8")

        # 2. Simpan barang.txt -> kode|nama|kategori|harga|stok|stok_min
        baris_brg = []
        for kode, b in sumber_barang.get("barang", {}).items():
            kategori = b.get("kategori", "Umum")
            stok_min = b.get("stok_min", 5)
            baris_brg.append(f"{kode}|{b['nama_barang']}|{kategori}|{int(b['harga'])}|{int(b['stok'])}|{int(stok_min)}")
        FILE_BARANG.write_text("\n".join(baris_brg) + ("\n" if baris_brg else ""), encoding="utf-8")

        # 3. Simpan transaksi.txt & detail_transaksi.txt
        baris_trx = []
        baris_det = []
        for t in sumber_barang.get("transaksi", []):
            bagian_waktu = t["tanggal"].split(" ")
            tgl_str = bagian_waktu[0]
            jam_str = bagian_waktu[1] if len(bagian_waktu) > 1 else "00:00:00"
            try:
                tgl_iso = datetime.strptime(tgl_str, "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError:
                tgl_iso = tgl_str
            baris_trx.append(
                f"{t['nomor']}|{tgl_iso}|{jam_str}|{t.get('kasir_username', '-')}|"
                f"{int(t['total'])}|{int(t['bayar'])}|{int(t['kembalian'])}"
            )
            for it in t.get("item", []):
                baris_det.append(
                    f"{t['nomor']}|{it['id_barang']}|{it['nama_barang']}|"
                    f"{int(it['harga'])}|{int(it['jumlah'])}|{int(it['subtotal'])}"
                )
        FILE_TRANSAKSI.write_text("\n".join(baris_trx) + ("\n" if baris_trx else ""), encoding="utf-8")
        FILE_DETAIL.write_text("\n".join(baris_det) + ("\n" if baris_det else ""), encoding="utf-8")
        return True
    except OSError as error:
        print(f"⚠️[ERROR] Gagal menyimpan database .txt: {error}")
        return False

def username_terpakai(username, kecuali_id=None):
    aktif = any(p["username"] == username and id_p != kecuali_id for id_p, p in data_pengguna["pengguna"].items())
    arsip = any(p["username"] == username and id_p != kecuali_id for id_p, p in data_pengguna.get("arsip_pengguna", {}).items())
    return aktif or arsip

# ==========================================
# FITUR ADMIN (KELOLA PENGGUNA)
# ==========================================
def tampilkan_data_pengguna():
    print("\n" + "=" * 108)
    print("TAMPILAN SEMUA AKUN / USER (TERURUT BERDASARKAN ROLE)".center(108))
    print("=" * 108)

    semua_akun = []
    for id_pengguna, pengguna in data_pengguna.get("pengguna", {}).items():
        semua_akun.append((id_pengguna, pengguna, "AKTIF"))
    for id_pengguna, pengguna in data_pengguna.get("arsip_pengguna", {}).items():
        semua_akun.append((id_pengguna, pengguna, "NONAKTIF"))

    if not semua_akun:
        print("[INFO] Belum ada data pengguna yang tersimpan.")
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
        f"{'ID':<9} | {'NAMA':<18} | {'USERNAME':<12} | {'ROLE':<8} | {'STATUS':<9} | {'DATE_MODIFIED':<22}"
    )
    print("=" * 108)

    for id_pengguna, pengguna, status in semua_akun:
        print(
            f"{id_pengguna:<9} | "
            f"{pengguna['nama'][:18]:<18} | "
            f"{pengguna['username'][:12]:<12} | "
            f"{pengguna.get('role', '-').upper():<8} | "
            f"{status:<9} | "
            f"{pengguna.get('date_modified', '-'):<22}"
        )

    print("=" * 108)
    total_aktif = len(data_pengguna.get("pengguna", {}))
    total_nonaktif = len(data_pengguna.get("arsip_pengguna", {}))
    print(f"Total: {total_aktif + total_nonaktif} Akun ({total_aktif} Aktif, {total_nonaktif} Nonaktif)")
    print("=" * 108)

def tambah_pengguna(admin_login):
    lebar = 60
    print("=" * lebar)
    print("--- TAMBAH DATA PENGGUNA ---".center(lebar))
    print("=" * lebar)

    while True:
        angka_acak = random.randint(1000, 9999)
        id_pengguna = f"USR{angka_acak}"
        if id_pengguna not in data_pengguna["pengguna"] and id_pengguna not in data_pengguna.get("arsip_pengguna", {}):
            break

    print(f"❗[INFO] ID Pengguna otomatis: {id_pengguna}")
    nama = input_wajib("Masukkan nama anda: ")
    while True:
        username = input_wajib("Masukkan username: ").lower()
        if username_terpakai(username):
            print("⚠️ [ERROR] Username sudah dipakai.")
            continue
        break

    while True:
        password = input_password_simple("Masukkan password (minimal 6 karakter): ")
        if len(password) >= 6:
            break
        print("⚠️ [ERROR] Password minimal 6 karakter.")

    while True:
        kode_role = input_wajib("Pilih role ([A]dmin / [G]udang / [K]asir): ").lower()
        if kode_role in MAP_ROLE:
            role = MAP_ROLE[kode_role]
            break
        print("⚠️ [ERROR] Role tidak valid. Ketik A, G, atau K.")

    data_pengguna["pengguna"][id_pengguna] = {
        "nama": nama,
        "username": username,
        "password": buat_hash_password(password),
        "role": role,
        "date_added": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "date_modified": "-",
        "date_deleted": "-"
    }

    if simpan_data():
        pelaku = data_pengguna["pengguna"][admin_login]["username"]
        catat_log("admin", f"Menambah pengguna {username} ({role})", pelaku)
        print( "=" * lebar)
        print(f"✅[SUKSES] Pengguna '{nama}' berhasil ditambahkan!")
        print("=" * lebar)
    else:
        del data_pengguna["pengguna"][id_pengguna]

def edit_pengguna(admin_login):
    lebar = 70
    print("=" * lebar)
    print("EDIT DATA PENGGUNA".center(lebar))
    print("=" * lebar)

    tampilkan_data_pengguna()
    id_pengguna = input_wajib("Masukkan ID pengguna yang ingin diedit: ").upper()

    if id_pengguna in data_pengguna["pengguna"]:
        pengguna = data_pengguna["pengguna"][id_pengguna]
        print("Kosongkan input jika tidak ingin diubah.")

        nama_baru = input(f"Nama baru [{pengguna['nama']}]: ").strip()
        username_baru = input(f"Username baru [{pengguna['username']}]: ").strip().lower()

        if "|" in nama_baru or "|" in username_baru:
            print("⚠️[ERROR] Input tidak boleh mengandung '|'.")
            return

        if username_baru and username_terpakai(username_baru, id_pengguna):
            print("⚠️[ERROR] Username sudah digunakan pengguna lain.")
            return

        password_baru = input_password_simple("Password baru [Kosongkan jika tetap]: ", boleh_kosong=True)
        if password_baru and len(password_baru) < 6:
            print("⚠️[ERROR] Password baru minimal 6 karakter.")
            return

        role_input = input(f"Role baru [{pengguna['role']}] ([A]dmin / [G]udang / [K]asir): ").strip().lower()

        if nama_baru:
            pengguna["nama"] = nama_baru
        if username_baru:
            pengguna["username"] = username_baru
        if password_baru:
            pengguna["password"] = buat_hash_password(password_baru)
        if role_input:
            if role_input in MAP_ROLE:
                pengguna["role"] = MAP_ROLE[role_input]
            else:
                print("⚠️[GAGAL] Role tidak valid.")
                return

        pengguna["date_modified"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        if simpan_data():
            pelaku = data_pengguna["pengguna"][admin_login]["username"]
            catat_log("admin", f"Mengedit pengguna {pengguna['username']} ({id_pengguna})", pelaku)
            print("✅[SUKSES] Data pengguna berhasil diedit.")
    else:
        print("⚠️[ERROR] ID pengguna tidak ditemukan di daftar aktif.")

def hapus_pengguna(admin_login):
    lebar = 70
    print("=" * lebar)
    print("NONAKTIFKAN DATA PENGGUNA".center(lebar))
    print("=" * lebar)
    
    tampilkan_data_pengguna()
    id_pengguna = input_wajib("Masukkan ID pengguna yang ingin dinonaktifkan: ").upper()

    if id_pengguna in data_pengguna["pengguna"]:
        if id_pengguna == admin_login:
            print("⚠️[ERROR] Tidak boleh menonaktifkan akun admin yang sedang dipakai.")
            return

        target = data_pengguna["pengguna"][id_pengguna]
        if target["role"] == "admin":
            jml_admin = sum(1 for p in data_pengguna["pengguna"].values() if p["role"] == "admin")
            if jml_admin <= 1:
                print("⚠️[ERROR] Minimal satu akun admin aktif harus selalu ada.")
                return

        pengguna_dihapus = data_pengguna["pengguna"].pop(id_pengguna)
        data_pengguna.setdefault("arsip_pengguna", {})[id_pengguna] = pengguna_dihapus
        pengguna_dihapus["date_deleted"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        if simpan_data():
            pelaku = data_pengguna["pengguna"][admin_login]["username"]
            catat_log("admin", f"Menonaktifkan pengguna {pengguna_dihapus['username']} ({id_pengguna})", pelaku)
            print(f"✅[SUKSES] Akun '{pengguna_dihapus['nama']}' dinonaktifkan.")
    else:
        print("⚠️[ERROR] ID pengguna tidak ditemukan.")

def aktifkan_pengguna(admin_login):
    lebar = 70
    print("=" * lebar)
    print("AKTIFKAN DATA PENGGUNA".center(lebar))
    print("=" * lebar)

    arsip = data_pengguna.get("arsip_pengguna", {})
    if not arsip:
        print("[INFO] Tidak ada akun nonaktif.")
        return
    tampilkan_data_pengguna()
    id_pengguna = input_wajib("Masukkan ID pengguna yang ingin diaktifkan kembali: ").upper()
    if id_pengguna not in arsip:
        print("⚠️[ERROR] ID tidak ditemukan di daftar nonaktif.")
        return
    user_aktif = arsip.pop(id_pengguna)
    user_aktif["date_deleted"] = "-"
    user_aktif["date_modified"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    data_pengguna["pengguna"][id_pengguna] = user_aktif
    if simpan_data():
        pelaku = data_pengguna["pengguna"][admin_login]["username"]
        catat_log("admin", f"Mengaktifkan kembali pengguna {user_aktif['username']} ({id_pengguna})", pelaku)
        print(f"✅[SUKSES] Akun '{user_aktif['nama']}' kembali aktif.")

def cari_pengguna():
    lebar = 70
    print("=" * lebar)
    print("PENCARIAN DATA PENGGUNA".center(lebar))
    print("=" * lebar)
    keyword = input_wajib("Masukkan nama atau ID pengguna: ")

    id_pengguna = keyword.upper()
    pengguna = data_pengguna["pengguna"].get(id_pengguna)
    if pengguna:
        print(f"ID: {id_pengguna} | Nama: {pengguna['nama']} | @{pengguna['username']} | Role: {pengguna['role']}")
        return

    hasil = [
        (kunci, p) for kunci, p in data_pengguna["pengguna"].items()
        if keyword.casefold() in p["nama"].casefold() or keyword.casefold() in p["username"].casefold()
    ]
    if not hasil:
        print("⚠️[ERROR] Pengguna tidak ditemukan.")
        return
    for id_p, p in hasil:
        print(f"ID: {id_p} | Nama: {p['nama']} | @{p['username']} | Role: {p['role']}")

# ==========================================
# FITUR DATA BARANG & STOK
# ==========================================
def status_stok_barang(barang):
    stok = int(barang["stok"])
    stok_min = int(barang.get("stok_min", 5))
    if stok == 0:
        return "HABIS"
    elif stok <= stok_min:
        return "MINIMUM"
    return "AMAN"

def peringatan_stok_otomatis():
    print("\n--- PERINGATAN STOK MINIMUM & HABIS ---")
    ada = False
    for kd, b in data_barang["barang"].items():
        st = status_stok_barang(b)
        if st in ("HABIS", "MINIMUM"):
            print(f"[{st:<7}] {kd} | {b['nama_barang']:<20} (Stok: {b['stok']}, Min: {b.get('stok_min', 5)})")
            ada = True
    if not ada:
        print("Semua stok barang dalam batas AMAN.")

def daftar_barang():
    print("\n" + "=" * 96)
    print("DATA BARANG".center(96))
    print("=" * 96)
    if not data_barang["barang"]:
        print("Belum ada barang.")
        return

    print(
        f"{'ID':<9}{'NAMA BARANG':<20}{'KATEGORI':<13}{'STOK':>6}{'MIN':>6}"
        f"{'STATUS':>10}{'HARGA JUAL':>15}{'LABA':>15}"
    )
    print("-" * 96)

    for id_barang, barang in data_barang["barang"].items():
        pabrik = ambil_harga_pabrik(barang)
        jual = ambil_harga_jual(barang)
        laba = hitung_laba(pabrik, jual)
        st = status_stok_barang(barang)

        print(
            f"{id_barang:<9}"
            f"{barang['nama_barang'][:19]:<20}"
            f"{barang.get('kategori', 'Umum')[:12]:<13}"
            f"{barang['stok']:>6}"
            f"{barang.get('stok_min', 5):>6}"
            f"{st:>10}"
            f"{rupiah(jual):>15}"
            f"{rupiah(laba):>15}"
        )
    print("=" * 96)

def tambah_barang(id_login):
    print("\n=== TAMBAH BARANG ===")
    nomor_akhir = max([int(k[3:]) for k in data_barang["barang"] if k.startswith("BRG") and k[3:].isdigit()], default=0)
    id_barang = f"BRG{nomor_akhir + 1:03d}"
    print(f"❗[INFO] Kode Barang otomatis: {id_barang}")

    nama = input_wajib("Nama barang: ")
    kategori = input_wajib("Kategori barang: ")
    stok_min = input_angka("Stok minimum peringatan: ", 0)
    harga_pabrik = input_angka("Harga dari pabrik (Rp): ", 1)
    harga_jual = input_angka("Harga jual (Rp): ", 1)

    while True:
        tanggal_str = input_wajib("Tanggal expired (DD-MM-YYYY): ")
        try:
            datetime.strptime(tanggal_str, "%d-%m-%Y")
            break
        except ValueError:
            print("⚠️[ERROR] Format tanggal tidak valid.")

    laba = hitung_laba(harga_pabrik, harga_jual)

    # Sesuai aturan SAS: stok awal barang baru adalah 0 (bertambah lewat Barang Masuk)
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
        pelaku = data_pengguna["pengguna"][id_login]["username"]
        catat_log("admin", f"Menambah barang {id_barang} ({nama})", pelaku)
        print(f"\n✅[BERHASIL] Barang {id_barang} ditambahkan (Stok awal: 0).")
    else:
        del data_barang["barang"][id_barang]

def edit_barang(id_login):
    daftar_barang()
    id_barang = input_wajib("\nID barang yang diedit: ").upper()
    barang = data_barang["barang"].get(id_barang)
    if not barang:
        print("⚠️[ERROR] ID barang tidak ditemukan.")
        return

    print("\nKosongkan input jika tidak ingin mengubah data.")
    nama = input(f"Nama barang [{barang['nama_barang']}]: ").strip()
    kategori = input(f"Kategori [{barang.get('kategori', 'Umum')}]: ").strip()
    stok_min = input(f"Stok minimum [{barang.get('stok_min', 5)}]: ").strip()
    harga_pabrik = input(f"Harga pabrik [{ambil_harga_pabrik(barang)}]: ").strip()
    harga_jual = input(f"Harga jual [{ambil_harga_jual(barang)}]: ").strip()
    expired = input(f"Expired [{barang.get('expired', '')}]: ").strip()

    if "|" in nama or "|" in kategori:
        print("⚠️[ERROR] Input tidak boleh mengandung '|'.")
        return

    try:
        min_baru = int(stok_min) if stok_min else int(barang.get("stok_min", 5))
        pabrik_baru = int(harga_pabrik) if harga_pabrik else ambil_harga_pabrik(barang)
        jual_baru = int(harga_jual) if harga_jual else ambil_harga_jual(barang)
        if min_baru < 0 or pabrik_baru < 1 or jual_baru < 1:
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

    data_lama = copy.deepcopy(barang)
    barang.update({
        "nama_barang": nama or barang["nama_barang"],
        "kategori": kategori or barang.get("kategori", "Umum"),
        "stok_min": min_baru,
        "harga_pabrik": pabrik_baru,
        "harga_jual": jual_baru,
        "harga": jual_baru,
        "laba_per_barang": hitung_laba(pabrik_baru, jual_baru),
        "expired": expired or barang.get("expired", "31-12-2099")
    })

    if simpan_data():
        pelaku = data_pengguna["pengguna"][id_login]["username"]
        catat_log("admin", f"Mengedit barang {id_barang}", pelaku)
        print("\n✅[SUKSES] Data barang berhasil diperbarui.")
    else:
        barang.clear()
        barang.update(data_lama)

def hapus_barang(id_login):
    daftar_barang()
    id_barang = input_wajib("ID barang yang dihapus: ").upper()
    if id_barang not in data_barang["barang"]:
        print("⚠️[ERROR] ID barang tidak ditemukan.")
        return

    # Validasi SAS: barang yang pernah terjual / masuk / keluar tidak boleh dihapus
    pernah_transaksi = any(
        it["id_barang"] == id_barang
        for t in data_barang["transaksi"]
        for it in t.get("item", [])
    )
    pernah_masuk = FILE_MASUK.exists() and any(
        b.split("|")[2] == id_barang for b in FILE_MASUK.read_text(encoding="utf-8").splitlines() if len(b.split("|")) >= 3
    )
    pernah_keluar = FILE_KELUAR.exists() and any(
        b.split("|")[2] == id_barang for b in FILE_KELUAR.read_text(encoding="utf-8").splitlines() if len(b.split("|")) >= 3
    )

    if pernah_transaksi or pernah_masuk or pernah_keluar:
        print("⚠️[DITOLAK] Barang yang pernah terjual atau pernah dicatat masuk/keluar tidak boleh dihapus.")
        return

    if konfirmasi_default("Yakin hapus barang ini?"):
        barang_dihapus = data_barang["barang"].pop(id_barang)
        if simpan_data():
            pelaku = data_pengguna["pengguna"][id_login]["username"]
            catat_log("admin", f"Menghapus barang {barang_dihapus['nama_barang']} ({id_barang})", pelaku)
            print("✅[SUKSES] Barang berhasil dihapus.")

# ==========================================
# BARANG MASUK & BARANG KELUAR (GUDANG - SAS)
# ==========================================
def catat_barang_masuk(id_login):
    print("\n=== CATAT BARANG MASUK ===")
    if not data_barang["barang"]:
        print("⚠️[ERROR] Belum ada data barang. Minta Admin menambahkan barang terlebih dahulu.")
        return

    daftar_barang()
    id_barang = input_wajib("Masukkan kode barang (contoh BRG001): ").upper()
    if id_barang not in data_barang["barang"]:
        print("⚠️[ERROR] Kode barang tidak ditemukan.")
        return

    barang = data_barang["barang"][id_barang]
    stok_sebelum = int(barang["stok"])
    print(f"Barang dipilih : {barang['nama_barang']} (Stok saat ini: {stok_sebelum})")

    jumlah = input_angka("Jumlah barang masuk (> 0): ", minimum=1)
    pemasok = input_wajib("Nama pemasok: ")

    id_masuk = buat_id_otomatis(FILE_MASUK, "MSK")
    tgl_iso = datetime.now().strftime("%Y-%m-%d")
    petugas = data_pengguna["pengguna"][id_login]["username"]

    barang["stok"] = stok_sebelum + jumlah
    if not simpan_data():
        barang["stok"] = stok_sebelum
        print("⚠️[ERROR] Gagal menyimpan perubahan stok.")
        return

    baris_masuk = f"{id_masuk}|{tgl_iso}|{id_barang}|{jumlah}|{pemasok}|{petugas}\n"
    with FILE_MASUK.open("a", encoding="utf-8") as f:
        f.write(baris_masuk)

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

    daftar_barang()
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

    id_keluar = buat_id_otomatis(FILE_KELUAR, "KLR")
    tgl_iso = datetime.now().strftime("%Y-%m-%d")
    petugas = data_pengguna["pengguna"][id_login]["username"]

    barang["stok"] = stok_sebelum - jumlah
    if not simpan_data():
        barang["stok"] = stok_sebelum
        print("⚠️[ERROR] Gagal menyimpan perubahan stok.")
        return

    baris_keluar = f"{id_keluar}|{tgl_iso}|{id_barang}|{jumlah}|{alasan}|{keterangan}|{petugas}\n"
    with FILE_KELUAR.open("a", encoding="utf-8") as f:
        f.write(baris_keluar)

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
        for b in FILE_MASUK.read_text(encoding="utf-8").splitlines():
            p = b.split("|")
            if len(p) >= 6 and p[2] == id_barang:
                riwayat.append((p[1], "MASUK", f"+{p[3]}", f"{p[0]} ({p[4]})"))
    if FILE_KELUAR.exists():
        for b in FILE_KELUAR.read_text(encoding="utf-8").splitlines():
            p = b.split("|")
            if len(p) >= 7 and p[2] == id_barang:
                riwayat.append((p[1], "KELUAR", f"-{p[3]}", f"{p[0]} ({p[4]})"))
    for t in data_barang["transaksi"]:
        tgl_iso = t["tanggal"].split(" ")[0]
        try:
            tgl_iso = datetime.strptime(tgl_iso, "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
        for it in t.get("item", []):
            if it["id_barang"] == id_barang:
                riwayat.append((tgl_iso, "TERJUAL", f"-{it['jumlah']}", t["nomor"]))

    riwayat.sort(key=lambda x: x[0])
    print(f"\n=== KARTU STOK: {id_barang} - {barang['nama_barang']} ===")
    print(f"Stok Saat Ini: {barang['stok']} | Status: {status_stok_barang(barang)}")
    print("-" * 60)
    if not riwayat:
        print("Belum ada riwayat masuk, keluar, atau penjualan untuk barang ini.")
        return
    for tgl, jenis, jml, ket in riwayat:
        try:
            tgl_tampil = datetime.strptime(tgl, "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            tgl_tampil = tgl
        print(f"{tgl_tampil} | {jenis:<8} | {jml:>6} | {ket}")

# ==========================================
# FUNGSI SORTING, CARI, EXPIRED, LAPORAN & SPLDV ASLIMU
# ==========================================
def urut_barang_heap_sort():
    arr = list(data_barang["barang"].items())
    n = len(arr)
    if not arr:
        print("Belum ada barang.")
        return

    def heapify(arr, n, i):
        terbesar = i
        kiri, kanan = 2 * i + 1, 2 * i + 2
        if kiri < n and arr[kiri][1]["nama_barang"].casefold() > arr[terbesar][1]["nama_barang"].casefold():
            terbesar = kiri
        if kanan < n and arr[kanan][1]["nama_barang"].casefold() > arr[terbesar][1]["nama_barang"].casefold():
            terbesar = kanan
        if terbesar != i:
            arr[i], arr[terbesar] = arr[terbesar], arr[i]
            heapify(arr, n, terbesar)

    for i in range(n // 2 - 1, -1, -1):
        heapify(arr, n, i)
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        heapify(arr, i, 0)

    print("\n=== BARANG TERURUT A-Z (HEAP SORT) ===")
    for id_barang, barang in arr:
        print(
            f"{id_barang:<8} | "
            f"{barang['nama_barang'][:20]:<20} | "
            f"Stok: {barang['stok']:>4} | "
            f"{rupiah(barang['harga']):>12}"
        )

def cari_barang():
    print("\n" + "=" * 50)
    print("PENCARIAN DATA BARANG".center(50))
    print("=" * 50)
    keyword = input_wajib("Masukkan kode, nama, atau kategori barang: ")

    id_barang = keyword.upper()
    barang = data_barang["barang"].get(id_barang)
    if barang:
        print(f"\n[DITEMUKAN] {id_barang} | {barang['nama_barang']} | Kategori: {barang.get('kategori', '-')} | Stok: {barang['stok']} ({status_stok_barang(barang)}) | Harga: {rupiah(ambil_harga_jual(barang))}")
        return

    hasil = [
        (kunci, b) for kunci, b in data_barang["barang"].items()
        if keyword.casefold() in b["nama_barang"].casefold() or keyword.casefold() in b.get("kategori", "").casefold()
    ]
    if not hasil:
        print("\n⚠️[ERROR] Barang tidak ditemukan.")
        return

    for id_b, b in hasil:
        print(f"- {id_b:<8} | {b['nama_barang']:<22} | {b.get('kategori', '-'):<12} | Stok: {b['stok']:>4} ({status_stok_barang(b)}) | {rupiah(ambil_harga_jual(b))}")

def cek_expired():
    hari_ini = datetime.now().date()
    hasil_tabel = []
    if not data_barang["barang"]:
        print("Belum ada data barang.")
        return

    for id_barang, barang in data_barang["barang"].items():
        harga = barang["harga"]
        tanggal_str = barang.get("expired", "31-12-2099")
        try:
            tanggal_expired = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
        except ValueError:
            continue

        sisa_hari = (tanggal_expired - hari_ini).days
        if sisa_hari <= 0:
            status = "⚠️EXPIRED"
            diskon = 0
        elif sisa_hari <= 5:
            status = "⚠️BAHAYA"
            diskon = 0.04
        else:
            status = "NORMAL"
            diskon = 0

        harga_akhir = harga - (harga * diskon)
        hasil_tabel.append([id_barang, barang["nama_barang"], tanggal_str, status, f"{diskon * 100:.0f}%", rupiah(harga), rupiah(harga_akhir)])

    if hasil_tabel:
        print("\n=== LAPORAN CEK EXPIRED BARANG ===")
        for baris in hasil_tabel:
            print(" | ".join(str(x) for x in baris))

def riwayat_stok():
    print("\n--- RIWAYAT PERUBAHAN STOK SESI INI ---")
    if not list_riwayat_stok:
        print("Belum ada perubahan stok pada sesi ini.")
        return
    for nomor, r in enumerate(list_riwayat_stok, start=1):
        print(f"{nomor}. {r['id_barang']} ({r['nama_barang']}) | {r['jenis']} | Jumlah: {r['jumlah']} | {r['stok_sebelum']} -> {r['stok_sesudah']}")

def laporan_barang():
    print("\n--- LAPORAN KONDISI BARANG & GUDANG ---")
    if not data_barang["barang"]:
        print("Barang belum tersedia!")
        return

    aman = sum(1 for b in data_barang["barang"].values() if status_stok_barang(b) == "AMAN")
    minimum = sum(1 for b in data_barang["barang"].values() if status_stok_barang(b) == "MINIMUM")
    habis = sum(1 for b in data_barang["barang"].values() if status_stok_barang(b) == "HABIS")
    nilai_persediaan = sum(int(b["stok"]) * ambil_harga_jual(b) for b in data_barang["barang"].values())

    daftar_barang()
    print(f"Total Jenis Barang : {len(data_barang['barang'])}")
    print(f"Status AMAN        : {aman}")
    print(f"Status MINIMUM     : {minimum}")
    print(f"Status HABIS       : {habis}")
    print(f"Nilai Persediaan   : {rupiah(nilai_persediaan)}")

def tampilkan_barang():
    daftar_barang()

def analisis_spldv_harga_barang():
    print("\n=== ANALISIS HARGA BARANG (SPLDV) ===")
    a1 = float(input_angka("Jumlah Barang X di Paket 1: ", 0))
    b1 = float(input_angka("Jumlah Barang Y di Paket 1: ", 0))
    c1 = float(input_angka("Total Harga Paket 1 (Rp): ", 1))

    a2 = float(input_angka("Jumlah Barang X di Paket 2: ", 0))
    b2 = float(input_angka("Jumlah Barang Y di Paket 2: ", 0))
    c2 = float(input_angka("Total Harga Paket 2 (Rp): ", 1))

    determinan = (a1 * b2) - (a2 * b1)
    if determinan == 0:
        print("⚠️[ERROR] Sistem persamaan tidak memiliki solusi unik (determinan = 0).")
        return

    harga_x = ((c1 * b2) - (c2 * b1)) / determinan
    harga_y = ((a1 * c2) - (a2 * c1)) / determinan
    print(f"✅[SUKSES] Harga Barang X: {rupiah(int(harga_x))} | Harga Barang Y: {rupiah(int(harga_y))}")

def hitung_laba(harga_pabrik, harga_jual):
    return harga_jual - harga_pabrik

def hitung_laba_kotor_transaksi(transaksi):
    total_laba = 0
    for item in transaksi.get("item", []):
        if "harga_pabrik" not in item:
            return None
        total_laba += item["subtotal"] - (item["harga_pabrik"] * item["jumlah"])
    return total_laba

def ambil_harga_pabrik(barang):
    return barang.get("harga_pabrik", barang.get("harga", 0))

def ambil_harga_jual(barang):
    return barang.get("harga_jual", barang.get("harga", 0))

def hitung_diskon_expired(barang):
    hari_ini = datetime.now().date()
    tanggal_str = barang.get("expired", "")
    try:
        tanggal_expired = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
    except ValueError:
        return 0, 0, ambil_harga_jual(barang)

    sisa_hari = (tanggal_expired - hari_ini).days
    harga_normal = ambil_harga_jual(barang)
    diskon = 0.04 if 0 < sisa_hari <= 5 else 0
    potongan = round(harga_normal * diskon)
    return sisa_hari, potongan, harga_normal - potongan

def migrasi_harga_barang():
    for barang in data_barang["barang"].values():
        harga_lama = barang.get("harga", 0)
        barang.setdefault("harga_pabrik", harga_lama)
        barang.setdefault("harga_jual", harga_lama)
        barang.setdefault("status", "Aktif")
        barang["harga"] = barang["harga_jual"]
        barang["laba_per_barang"] = hitung_laba(barang["harga_pabrik"], barang["harga_jual"])

# ==========================================
# LAPORAN PENJUALAN & LOG AKTIVITAS (ADMIN)
# ==========================================
def laporan_penjualan_admin():
    print("\n" + "=" * 60)
    print("LAPORAN PENJUALAN".center(60))
    print("=" * 60)
    if not data_barang["transaksi"]:
        print("[INFO] Belum ada transaksi penjualan.")
        return

    tgl_awal_str = input_wajib("Tanggal awal (DD-MM-YYYY): ")
    tgl_akhir_str = input_wajib("Tanggal akhir (DD-MM-YYYY): ")
    try:
        tgl_awal = datetime.strptime(tgl_awal_str, "%d-%m-%Y").date()
        tgl_akhir = datetime.strptime(tgl_akhir_str, "%d-%m-%Y").date()
    except ValueError:
        print("⚠️[ERROR] Format tanggal tidak valid (gunakan DD-MM-YYYY).")
        return

    if tgl_awal > tgl_akhir:
        print("⚠️[ERROR] Tanggal awal tidak boleh lebih besar dari tanggal akhir.")
        return

    terfilter = []
    for t in data_barang["transaksi"]:
        try:
            tgl_t = datetime.strptime(t["tanggal"][:10], "%d-%m-%Y").date()
            if tgl_awal <= tgl_t <= tgl_akhir:
                terfilter.append(t)
        except ValueError:
            continue

    if not terfilter:
        print("Tidak ada data transaksi pada rentang tanggal tersebut.")
        return

    baris_laporan = [
        f"LAPORAN PENJUALAN ({tgl_awal_str} s/d {tgl_akhir_str})",
        "-" * 60
    ]
    total_omzet = 0
    per_kasir = {}
    for t in terfilter:
        baris_laporan.append(f"{t['nomor']} | {t['tanggal']} | {t['kasir_username']} | {rupiah(t['total'])}")
        total_omzet += t["total"]
        k = t["kasir_username"]
        per_kasir.setdefault(k, {"jml": 0, "total": 0})
        per_kasir[k]["jml"] += 1
        per_kasir[k]["total"] += t["total"]

    baris_laporan.append("-" * 60)
    baris_laporan.append(f"Jumlah Transaksi : {len(terfilter)}")
    baris_laporan.append(f"Total Penjualan  : {rupiah(total_omzet)}")
    baris_laporan.append("\nPenjualan per Kasir:")
    for k, info in per_kasir.items():
        baris_laporan.append(f"- {k}: {info['jml']} transaksi, {rupiah(info['total'])}")

    teks_laporan = "\n".join(baris_laporan)
    print("\n" + teks_laporan)

    if konfirmasi_default("Simpan laporan ke folder laporan?"):
        nama_file = FOLDER_LAPORAN / f"laporan_penjualan_{tgl_awal.strftime('%Y%m%d')}_{tgl_akhir.strftime('%Y%m%d')}.txt"
        nama_file.write_text(teks_laporan + "\n", encoding="utf-8")
        print(f"✅[SUKSES] Laporan disimpan ke: {nama_file}")

def rekomendasi_barang_terlaris():
    print("\n=== 5 BARANG TERLARIS ===")
    if not data_barang["transaksi"]:
        print("[INFO] Belum ada transaksi penjualan.")
        return

    rekap = {}
    for t in data_barang["transaksi"]:
        for it in t.get("item", []):
            kd = it["id_barang"]
            rekap.setdefault(kd, {"nama": it["nama_barang"], "terjual": 0, "pendapatan": 0})
            rekap[kd]["terjual"] += int(it["jumlah"])
            rekap[kd]["pendapatan"] += int(it["subtotal"])

    urut = sorted(rekap.items(), key=lambda x: (-x[1]["terjual"], x[0]))
    for rank, (kd, info) in enumerate(urut[:5], start=1):
        print(f"{rank}. {kd} - {info['nama']} | Terjual: {info['terjual']} unit | Omzet: {rupiah(info['pendapatan'])}")

def lihat_log_aktivitas():
    print("\n=== LOG AKTIVITAS (20 TERAKHIR) ===")
    print("1. Semua Aktivitas (log_aktivitas.txt)")
    print("2. Khusus Admin (log_admin.txt)")
    print("3. Khusus Gudang (log_gudang.txt)")
    print("4. Khusus Kasir (log_kasir.txt)")
    pilih = input("Pilih file log (1-4): ").strip()
    peta = {
        "1": FILE_LOG,
        "2": DATA_DIR / "log_admin.txt",
        "3": DATA_DIR / "log_gudang.txt",
        "4": DATA_DIR / "log_kasir.txt"
    }
    target = peta.get(pilih)
    if not target or not target.exists():
        print("[INFO] File log belum tersedia.")
        return
    baris = [b for b in target.read_text(encoding="utf-8").splitlines() if b.strip()]
    if not baris:
        print("[INFO] Log masih kosong.")
        return
    for b in baris[-20:]:
        print(b)

def ganti_password_sendiri(id_login):
    pengguna = data_pengguna["pengguna"][id_login]
    print("\n=== GANTI PASSWORD SENDIRI ===")
    lama = getpass.getpass("Masukkan password lama: ").strip()
    if not cek_password(lama, pengguna["password"]):
        print("⚠️[ERROR] Password lama salah.")
        return
    baru = input_password_simple("Masukkan password baru (min 6 karakter): ")
    if len(baru) < 6:
        print("⚠️[ERROR] Password baru minimal 6 karakter.")
        return
    pengguna["password"] = buat_hash_password(baru)
    pengguna["date_modified"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    if simpan_data():
        catat_log(pengguna["role"], "Mengganti password sendiri", pengguna["username"])
        print("✅[SUKSES] Password berhasil diubah.")

# ==========================================
# FITUR KASIR (TRANSAKSI PENJUALAN & STRUK)
# ==========================================
def tampil_keranjang(keranjang):
    print("\n=== KERANJANG BELANJA ===")
    if not keranjang:
        print("Keranjang masih kosong.")
        return 0
    total = 0
    for id_barang, jumlah in keranjang.items():
        barang = data_barang["barang"][id_barang]
        _, potongan, harga_akhir = hitung_diskon_expired(barang)
        subtotal = jumlah * harga_akhir
        total += subtotal
        print(f"- {id_barang} | {barang['nama_barang']} | {jumlah} x {rupiah(harga_akhir)} = {rupiah(subtotal)}")
    print(f"TOTAL BELANJA: {rupiah(total)}")
    return total

def format_struk(data_transaksi):
    garis = "=" * 46
    baris = [
        garis, "SMK MART".center(46), "STRUK PEMBELIAN".center(46), garis,
        f"No. Transaksi : {data_transaksi['nomor']}",
        f"Tanggal       : {data_transaksi['tanggal']}",
        f"Kasir         : {data_transaksi['kasir_nama']} (@{data_transaksi['kasir_username']})",
        "-" * 46
    ]
    for item in data_transaksi["item"]:
        baris.append(item["nama_barang"])
        kiri = f"  {item['jumlah']} x {rupiah(item['harga'])}"
        kanan = rupiah(item["subtotal"])
        baris.append(f"{kiri:<27}{kanan:>19}")

    baris += [
        "-" * 46,
        f"{'TOTAL':<25}{rupiah(data_transaksi['total']):>21}",
        f"{data_transaksi.get('metode', 'TUNAI'):<25}{rupiah(data_transaksi['bayar']):>21}",
        f"{'KEMBALIAN':<25}{rupiah(data_transaksi['kembalian']):>21}",
        garis, "Terima kasih telah berbelanja!".center(46), garis
    ]
    return "\n".join(baris)

def cetak_struk(data_transaksi):
    isi = format_struk(data_transaksi)
    print("\n" + isi)
    try:
        FOLDER_STRUK.mkdir(parents=True, exist_ok=True)
        lokasi_struk = FOLDER_STRUK / f"{data_transaksi['nomor']}.txt"
        lokasi_struk.write_text(isi + "\n", encoding="utf-8")
        print(f"✅[SUKSES] Struk tersimpan di: {lokasi_struk}")
    except OSError as error:
        print(f"⚠️[PERINGATAN] Gagal menyimpan file struk: {error}")

def transaksi_penjualan(kasir):
    if not data_barang["barang"]:
        print("⚠️[ERROR] Belum ada barang.")
        return
    keranjang = {}
    print("\n=== TRANSAKSI PENJUALAN ===")
    print("Masukkan ID/nama barang, ketik 'selesai' untuk bayar, 'batal' untuk membatalkan.")
    while True:
        daftar_barang()
        tampil_keranjang(keranjang)
        kata = input("ID / Nama barang / selesai / batal: ").strip()

        if kata.upper() == "BATAL":
            print("Transaksi dibatalkan.")
            return
        if kata.upper() == "SELESAI":
            if not keranjang:
                print("⚠️[ERROR] Keranjang kosong.")
                continue
            break

        id_barang = kata.upper()
        if id_barang not in data_barang["barang"]:
            cocok = [k for k, b in data_barang["barang"].items() if kata.casefold() in b["nama_barang"].casefold()]
            if len(cocok) == 1:
                id_barang = cocok[0]
            elif len(cocok) > 1:
                for k in cocok:
                    print(f"- {k}: {data_barang['barang'][k]['nama_barang']} (Stok: {data_barang['barang'][k]['stok']})")
                id_barang = input_wajib("Pilih kode barang: ").upper()
            else:
                print("⚠️[ERROR] Barang tidak ditemukan.")
                continue

        if id_barang not in data_barang["barang"]:
            print("⚠️[ERROR] Kode barang tidak ditemukan.")
            continue

        barang = data_barang["barang"][id_barang]
        tersedia = barang["stok"] - keranjang.get(id_barang, 0)
        if tersedia <= 0:
            print("⚠️[ERROR] Stok habis atau sudah maksimal di keranjang.")
            continue

        jumlah = input_angka(f"Jumlah beli (tersedia {tersedia}): ", 1)
        if jumlah > tersedia:
            print(f"⚠️[ERROR] Stok tidak cukup, tersedia {tersedia}.")
            continue
        keranjang[id_barang] = keranjang.get(id_barang, 0) + jumlah
        print("✅[SUKSES] Barang ditambahkan ke keranjang.")

    total = tampil_keranjang(keranjang)
    while True:
        pilih_metode = input("Metode bayar (1. Tunai | 2. Debit | 0. Batal): ").strip()
        if pilih_metode == "0":
            return
        elif pilih_metode == "1":
            metode = "TUNAI"
            bayar = input_angka("Uang dibayarkan (Rp): ", 1)
            if bayar < total:
                print(f"⚠️[ERROR] Uang kurang {rupiah(total - bayar)}.")
                continue
            kembalian = bayar - total
            break
        elif pilih_metode == "2":
            metode = "DEBIT"
            bayar = total
            kembalian = 0
            break
        else:
            print("⚠️[ERROR] Pilihan tidak valid.")

    baru = copy.deepcopy(data_barang)
    daftar_item = []
    for id_barang, jumlah in keranjang.items():
        barang = baru["barang"][id_barang]
        barang["stok"] -= jumlah
        _, potongan, harga_akhir = hitung_diskon_expired(barang)
        subtotal = jumlah * harga_akhir
        daftar_item.append({
            "id_barang": id_barang,
            "nama_barang": barang["nama_barang"],
            "jumlah": jumlah,
            "harga_pabrik": ambil_harga_pabrik(barang),
            "harga": harga_akhir,
            "subtotal": subtotal
        })
        if status_stok_barang(barang) in ("MINIMUM", "HABIS"):
            print(f"⚠️[PERINGATAN STOK] {barang['nama_barang']} kini berstatus {status_stok_barang(barang)} (sisa {barang['stok']}).")

    nomor_trx = f"TRX{baru['nomor_berikutnya']:03d}"
    data_transaksi = {
        "nomor": nomor_trx,
        "tanggal": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "kasir_id": kasir[0],
        "kasir_nama": kasir[1]["nama"],
        "kasir_username": kasir[1]["username"],
        "item": daftar_item,
        "total": total,
        "metode": metode,
        "bayar": bayar,
        "kembalian": kembalian
    }

    baru["transaksi"].append(data_transaksi)
    baru["nomor_berikutnya"] += 1
    if not simpan_data(baru):
        print("⚠️[ERROR] Transaksi gagal disimpan.")
        return

    data_barang.clear()
    data_barang.update(baru)
    catat_log("kasir", f"TRANSAKSI {nomor_trx} ({rupiah(total)})", kasir[1]["username"])
    cetak_struk(data_transaksi)

def cetak_ulang_struk():
    if not data_barang["transaksi"]:
        print("Belum ada transaksi.")
        return
    for t in data_barang["transaksi"]:
        print(f"{t['nomor']} | {t['tanggal']} | {rupiah(t['total'])}")
    nomor = input_wajib("Nomor transaksi untuk cetak ulang: ").upper()
    trx = next((t for t in data_barang["transaksi"] if t["nomor"] == nomor), None)
    if trx:
        cetak_struk(trx)
    else:
        print("⚠️[ERROR] Nomor transaksi tidak ditemukan.")

def riwayat_transaksi_tanggal():
    if not data_barang["transaksi"]:
        print("Belum ada transaksi.")
        return
    tanggal_cari = input_wajib("Tanggal (DD-MM-YYYY): ")
    hasil = [t for t in data_barang["transaksi"] if t["tanggal"][:10] == tanggal_cari]
    if not hasil:
        print(f"Tidak ada transaksi pada tanggal {tanggal_cari}.")
        return
    for t in hasil:
        print(f"{t['nomor']} | {t['tanggal']} | {t['kasir_username']} | {rupiah(t['total'])}")

# ==========================================
# SUBMENU GABUNGAN & PENGATURAN MENU PER ROLE
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
        print("0. Kembali")
        pilih = input("Pilih (0-6): ").strip()
        if pilih == "0": break
        elif pilih == "1": tampilkan_data_pengguna()
        elif pilih == "2": tambah_pengguna(id_login)
        elif pilih == "3": edit_pengguna(id_login)
        elif pilih == "4": hapus_pengguna(id_login)
        elif pilih == "5": aktifkan_pengguna(id_login)
        elif pilih == "6": cari_pengguna()
        else: print("Pilihan tidak valid.")

def submenu_kelola_barang_admin(id_login):
    while True:
        print("\n=== KELOLA DATA BARANG ===")
        print("1. Tampilkan & Urutkan Barang")
        print("2. Tambah Barang")
        print("3. Edit Barang")
        print("4. Hapus Barang")
        print("0. Kembali")
        pilih = input("Pilih (0-4): ").strip()
        if pilih == "0": break
        elif pilih == "1":
            daftar_barang()
            urut_barang_heap_sort()
        elif pilih == "2": tambah_barang(id_login)
        elif pilih == "3": edit_barang(id_login)
        elif pilih == "4": hapus_barang(id_login)
        else: print("Pilihan tidak valid.")

def submenu_lihat_cari_barang():
    while True:
        print("\n=== LIHAT & CARI BARANG ===")
        print("1. Daftar Semua Barang")
        print("2. Cari Barang (Kode / Nama / Kategori)")
        print("3. Urutkan Barang A-Z (Heap Sort)")
        print("0. Kembali")
        pilih = input("Pilih (0-3): ").strip()
        if pilih == "0": break
        elif pilih == "1": tampilkan_barang()
        elif pilih == "2": cari_barang()
        elif pilih == "3": urut_barang_heap_sort()
        else: print("Pilihan tidak valid.")

def menu_admin(id_login):
    peringatan_stok_otomatis()
    while True:
        print("\n=== MENU ADMIN ===")
        print("1. Kelola Pengguna")
        print("2. Kelola Data Barang")
        print("3. Lihat & Cari Barang")
        print("4. Daftar Stok & Kartu Stok")
        print("5. Laporan Penjualan & Gudang")
        print("6. Log Aktivitas")
        print("7. Ganti Password")
        print("0. Logout")
        pilih = input("Pilih fitur (0-7): ").strip()
        if pilih == "1": submenu_kelola_pengguna(id_login)
        elif pilih == "2": submenu_kelola_barang_admin(id_login)
        elif pilih == "3": submenu_lihat_cari_barang()
        elif pilih == "4":
            peringatan_stok_otomatis()
            kartu_stok_barang()
        elif pilih == "5":
            laporan_penjualan_admin()
            rekomendasi_barang_terlaris()
            laporan_barang()
        elif pilih == "6": lihat_log_aktivitas()
        elif pilih == "7": ganti_password_sendiri(id_login)
        elif pilih == "0":
            catat_log("admin", "LOGOUT", data_pengguna["pengguna"][id_login]["username"])
            break
        else:
            print("Pilihan tidak valid.")

def menu_gudang(id_login):
    peringatan_stok_otomatis()
    while True:
        print("\n=== MENU GUDANG ===")
        print("1. Lihat & Cari Barang")
        print("2. Catat Barang Masuk")
        print("3. Catat Barang Keluar")
        print("4. Daftar Stok, Kartu Stok & Cek Expired")
        print("5. Laporan Stok & Analisis Harga (SPLDV)")
        print("6. Ganti Password")
        print("0. Logout")
        pilih = input("Pilih fitur (0-6): ").strip()
        if pilih == "1": submenu_lihat_cari_barang()
        elif pilih == "2": catat_barang_masuk(id_login)
        elif pilih == "3": catat_barang_keluar(id_login)
        elif pilih == "4":
            peringatan_stok_otomatis()
            kartu_stok_barang()
            cek_expired()
        elif pilih == "5":
            laporan_barang()
            if konfirmasi_default("Jalankan analisis harga paket SPLDV?"):
                analisis_spldv_harga_barang()
        elif pilih == "6": ganti_password_sendiri(id_login)
        elif pilih == "0":
            catat_log("gudang", "LOGOUT", data_pengguna["pengguna"][id_login]["username"])
            break
        else:
            print("Pilihan tidak valid.")

def menu_kasir(id_login):
    while True:
        kasir = (id_login, data_pengguna["pengguna"][id_login])
        print(f"\n=== MENU KASIR | {kasir[1]['nama']} ===")
        print("1. Transaksi Penjualan dan Cetak Struk")
        print("2. Lihat & Cari Barang")
        print("3. Cetak Ulang Struk & Riwayat Tanggal")
        print("4. Ganti Password")
        print("0. Logout")
        pilih = input("Pilih fitur (0-4): ").strip()
        if pilih == "1": transaksi_penjualan(kasir)
        elif pilih == "2": submenu_lihat_cari_barang()
        elif pilih == "3":
            cetak_ulang_struk()
            riwayat_transaksi_tanggal()
        elif pilih == "4": ganti_password_sendiri(id_login)
        elif pilih == "0":
            catat_log("kasir", "LOGOUT", kasir[1]["username"])
            break
        else:
            print("Pilihan tidak valid.")

def main():
    print("\n=== SELAMAT DATANG DI SMK MART ===")
    global data_pengguna
    data_pengguna = muat_data()

    percobaan_gagal = 0
    while True:
        print("\n=== LOGIN SMK MART ===")
        username = input_wajib("Username (0 untuk keluar): ").lower()
        if username == "0":
            print("Terima kasih. Program selesai.")
            break

        password = getpass.getpass("Masukkan password anda: ").strip()

        akun_nonaktif = any(p["username"] == username for p in data_pengguna.get("arsip_pengguna", {}).values())
        if akun_nonaktif:
            print("⚠️[DITOLAK] Akun Anda berstatus NONAKTIF. Hubungi Admin.")
            continue

        login = next((
            (id_p, p) for id_p, p in data_pengguna["pengguna"].items()
            if p["username"] == username and cek_password(password, p["password"])
        ), None)

        if not login:
            percobaan_gagal += 1
            print(f"⚠️[ERROR] Username atau password salah ({percobaan_gagal}/3).")
            if percobaan_gagal >= 3:
                print("⚠️[DITOLAK] Salah 3 kali. Akses ditolak dan program berhenti.")
                break
            continue

        percobaan_gagal = 0
        id_login, pengguna = login
        catat_log(pengguna["role"], "LOGIN", pengguna["username"])
        print(f"✅[SUKSES] Halo, {pengguna['nama']}! Login sebagai {pengguna['role']}.")

        if pengguna["role"] == "admin": menu_admin(id_login)
        elif pengguna["role"] == "gudang": menu_gudang(id_login)
        elif pengguna["role"] == "kasir": menu_kasir(id_login)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram dihentikan.")