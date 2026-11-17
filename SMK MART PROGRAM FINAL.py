from pathlib import Path
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime
import copy
import getpass
import random


LOKASI_SCRIPT_INI = Path.cwd()
BASE_DIR = LOKASI_SCRIPT_INI / 'SMK_MART_3_ROLE_BARU'
BASE_DIR.mkdir(parents=True, exist_ok=True)
print(f"Folder database dan struk: {BASE_DIR}")

data_barang = {}
data_pengguna = {}
list_riwayat_stok = []
data_expired = {}
nomor_berikutnya = 1

LOKASI = BASE_DIR
FILE_DATA = LOKASI / "smk_mart_data_baru.json"
FOLDER_STRUK = LOKASI / "struk_smk_mart"
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
        if hasil:
            return hasil
        print("⚠️[ERROR] Input tidak boleh kosong.")

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
                print(f"[ERROR] Angka minimal {minimum}.")
                continue
            return angka
        except ValueError:
            print("⚠️[ERROR] Masukkan bilangan bulat yang valid.")

def buat_hash_password(password):
    salt = secrets.token_hex(16)
    hasil = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 150_000)
    return f"{salt}${hasil.hex()}"

def cek_password(password, password_hash):
    try:
        salt, nilai = password_hash.split("$", 1)
        hasil = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 150_000)
        return hmac.compare_digest(hasil, bytes.fromhex(nilai))
    except (ValueError, TypeError):
        return False

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

def muat_data():
    global data_barang, data_pengguna, list_riwayat_stok

    if not FILE_DATA.exists():
        hasil = {"pengguna": {}, "barang": {}, "transaksi": [], "riwayat_stok": [], "nomor_berikutnya": 1}
    else:
        try:
            with FILE_DATA.open("r", encoding="utf-8") as f:
                hasil = json.load(f)
        except (OSError, ValueError, TypeError) as error:
            raise SystemExit(f"⚠️[ERROR] Tidak dapat membaca {FILE_DATA.name}: {error}")

    pengguna_dimuat = hasil.get("pengguna", {})

    if "ADM001" not in pengguna_dimuat:
        pengguna_dimuat["ADM001"] = {
            "nama": "Admin Utama",
            "username": "admin",
            "password": buat_hash_password("admin12345"),
            "role": "admin"
        }

    data_pengguna = {
                "pengguna": pengguna_dimuat,
                "arsip_pengguna": hasil.get("arsip_pengguna", {})
            }

    data_barang = {
        "barang": hasil.get("barang", {}),
        "arsip_barang": hasil.get("arsip_barang", {}),
        "transaksi": hasil.get("transaksi", []),
        "nomor_berikutnya": hasil.get("nomor_berikutnya", 1)}

    list_riwayat_stok = hasil.get("riwayat_stok", [])

    migrasi_harga_barang()

    return data_pengguna

def simpan_data(data_baru=None):

  sumber_barang = data_baru if data_baru else data_barang

  isi_database = {
        "pengguna": data_pengguna.get("pengguna", {}),
        "arsip_pengguna": data_pengguna.get("arsip_pengguna", {}),
        "barang": sumber_barang.get("barang", {}),
        "arsip_barang": sumber_barang.get("arsip_barang", {}),
        "riwayat_stok": list_riwayat_stok,
        "transaksi": sumber_barang.get("transaksi", []),
        "nomor_berikutnya": sumber_barang.get("nomor_berikutnya", 1)
    }

  sementara = FILE_DATA.with_suffix(".json.tmp")
  try:
        with sementara.open("w", encoding="utf-8") as f:
            json.dump(isi_database, f, indent=2, ensure_ascii=False)
        os.replace(sementara, FILE_DATA)
        return True
  except OSError as error:
        print(f"⚠️[ERROR] Gagal menyimpan database: {error}")
        return False

def username_terpakai(username, kecuali_id=None):
    return any(pengguna["username"] == username and id_pengguna != kecuali_id
               for id_pengguna, pengguna in data_pengguna["pengguna"].items())

def catat_log(role, aktivitas):

  waktu = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
  nama_file = BASE_DIR / f"log_{role}.txt"

  try:
        with nama_file.open("a", encoding="utf-8") as f:
            f.write(f"[{waktu}] {aktivitas}\n")

  except OSError:
        pass

def konfirmasi_default(pesan):
  while True:
    jawab = input("f{pesan} [Y/t]: ").strip().lower()
    if jawab in ("y", ""):
      return True
    elif jawab == "t":
      return False
    print("⚠️ [ERROR] Tekan Enter / 'y' untuk Ya, atau ketik 't' untuk Tidak.")




# ==========================================
# FITUR ADMIN (PENGGUNA)
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
        f"{'ID':<9} | {'NAMA':<18} | {'ROLE':<8} | {'STATUS':<9} | "
        f"{'DATE_ADDED':<16} | {'DATE_MODIFIED':<16} | {'DATE_DELETED':<16}"
    )
    print("=" * 108)

    for id_pengguna, pengguna, status in semua_akun:
        print(
            f"{id_pengguna:<9} | "
            f"{pengguna['nama'][:18]:<18} | "
            f"{pengguna.get('role', '-').upper():<8} | "
            f"{status:<9} | "
            f"{pengguna.get('date_added', '-'):<16} | "
            f"{pengguna.get('date_modified', '-'):<16} | "
            f"{pengguna.get('date_deleted', '-'):<16}"
        )

    print("=" * 108)
    total_aktif = len(data_pengguna.get("pengguna", {}))
    total_nonaktif = len(data_pengguna.get("arsip_pengguna", {}))
    total_semua = total_aktif + total_nonaktif
    print(f"Total: {total_semua} Akun ({total_aktif} Aktif, {total_nonaktif} Nonaktif)")

def tambah_pengguna():
    print("\n--- TAMBAH DATA PENGGUNA ---")

    while True:
      angka_acak = random.randint(1000, 9999)
      id_pengguna = f"USR{angka_acak}"
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

    password = input_password_simple("Masukkan password anda : ")

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
        print(f"[SUKSES] Pengguna '{nama}' berhasil ditambahkan!")
    else:
        del data_pengguna["pengguna"][id_pengguna]


def edit_pengguna():
    print("\n--- EDIT DATA PENGGUNA ---")
    id_pengguna = input("Masukkan ID pengguna yang ingin diedit: ").strip().upper()

    if id_pengguna in data_pengguna["pengguna"]:
        pengguna = data_pengguna["pengguna"][id_pengguna]

        print("Kosongkan input jika tidak ingin diubah.")
        nama_baru = input(f"Nama baru [{pengguna['nama']}]: ").strip()
        username_baru = input(f"Username baru [{pengguna['username']}]: ").strip().lower()

        if username_baru and username_terpakai(username_baru, id_pengguna):
            print("[ERROR] Username sudah digunakan pengguna lain.")
            return

        password_baru = input_password_simple("Password baru [Kosongkan jika tetap]: ", boleh_kosong=True)
        role_input = input(f"Role baru [{pengguna['role']}] ([A]dmin / [G]udang / [K]asir): ").strip().lower()

        if nama_baru:
            pengguna['nama'] = nama_baru
        if username_baru:
            pengguna['username'] = username_baru
        if password_baru:
            pengguna['password'] = buat_hash_password(password_baru)
        if role_input:
            if role_input in MAP_ROLE:
                pengguna['role'] = MAP_ROLE[role_input]
            else:
                print("⚠️ [GAGAL] Role tidak valid. Gunakan A (admin), G (gudang), atau K (kasir).")
                return

        pengguna['date_modified'] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        pengguna['date_deleted'] = "-"

        if simpan_data():
            print("[SUKSES] Data pengguna berhasil diedit")
    else:
        print("⚠️ [ERROR] ID pengguna tidak ditemukan.")

def hapus_pengguna(admin_login):
    print("\n--- HAPUS DATA PENGGUNA ---")
    id_pengguna = input("Masukkan ID pengguna yang ingin dihapus: ").strip().upper()

    if id_pengguna in data_pengguna["pengguna"]:
        if id_pengguna == admin_login:
            print("⚠️ [ERROR] Tidak boleh menghapus akun admin yang sedang dipakai.")
            return

        pengguna_dihapus = data_pengguna["pengguna"].pop(id_pengguna)
        data_pengguna.setdefault("arsip_pengguna", {})[id_pengguna] = pengguna_dihapus

        pengguna_dihapus["date_deleted"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        if simpan_data():
          print(f"Data '{pengguna_dihapus['nama']}' berhasil diarsipkan.")
          catat_log("admin", f"Menghapus pengguna {pengguna_dihapus['nama']} ({id_pengguna})")
        else:
         print("⚠️ [ERROR] ID pengguna tidak ditemukan.")

def cari_pengguna():
 print("\n" + "=" * 50)
 print("          PENCARIAN DATA PENGGUNA")
 print("=" * 50)

 keyword = input_wajib(
     "Masukkan nama atau ID pengguna: "
 ).strip()

 # 1. Prioritaskan pencarian berdasarkan ID
 id_pengguna = keyword.upper()
 pengguna = data_pengguna["pengguna"].get(id_pengguna)

 if pengguna:
     print("\n[DATA PENGGUNA DITEMUKAN]")
     print("-" * 50)
     print(f"ID PENGGUNA : {id_pengguna}")
     print(f"NAMA        : {pengguna['nama']}")
     print(f"USERNAME    : @{pengguna.get('username', '-')}")
     print(f"ROLE        : {pengguna['role']}")
     print("-" * 50)
     return

 # 2. Jika bukan ID, cari berdasarkan nama
 hasil = [
     (kunci, pengguna)
     for kunci, pengguna in data_pengguna["pengguna"].items()
     if keyword.casefold() in pengguna["nama"].casefold()
 ]

 if not hasil:
     print("\n[ERROR] Pengguna tidak ditemukan.")
     return

 print("\n=== HASIL PENCARIAN PENGGUNA ===")

 for id_pengguna, pengguna in hasil:
     print("-" * 50)
     print(f"ID PENGGUNA : {id_pengguna}")
     print(f"NAMA        : {pengguna['nama']}")
     print(f"USERNAME    : @{pengguna.get('username', '-')}")
     print(f"ROLE        : {pengguna['role']}")

 print("-" * 50)

def tampilkan_data_terhapus():
    print("\n" + "=" * 55)
    print(" " + "=" * 12 + "--- DATA YANG TELAH DIHAPUS --- ")
    for id_pengguna, pengguna in data_pengguna.get("arsip_pengguna", {}).items():
        print(
            f"ID: {id_pengguna:<8} | "
            f"Nama: {pengguna['nama'][:18]:<18} | "
            f"Role: {pengguna['role']:<7}"
        )

    for id_barang, barang in data_barang.get("arsip_barang", {}).items():
        print(
            f"ID: {id_barang:<8} | "
            f"Nama: {barang['nama_barang'][:20]:<20} | "
            f"Stok: {barang['stok']:>4} | "
            f"Harga: {rupiah(barang['harga']):>10}"
        )
    print("\n" + "=" * 55)

def hapus_transaksi():
    print("\n=== HAPUS DATA TRANSAKSI ===")
    if not data_barang["transaksi"]:
        print("[INFO] Belum ada riwayat transaksi yang tersimpan.")
        return

    riwayat_transaksi()
    nomor = input_wajib("Masukkan Nomor Transaksi yang ingin dihapus (contoh: TRX000001): ").upper()

    transaksi_ditemukan = None
    for t in data_barang["transaksi"]:
        if t["nomor"] == nomor:
            transaksi_ditemukan = t
            break

    if not transaksi_ditemukan:
        print(f"[ERROR] Transaksi dengan nomor '{nomor}' tidak ditemukan.")
        return

    print(f"\n--- DETAIL TRANSAKSI ---")
    print(f"No. Transaksi : {transaksi_ditemukan['nomor']}")
    print(f"Tanggal       : {transaksi_ditemukan['tanggal']}")
    print(f"Kasir         : {transaksi_ditemukan['kasir_nama']}")
    print(f"Total         : {rupiah(transaksi_ditemukan['total'])}")

    kembalikan_stok = konfirmasi_default("Kembalikan stok pada transaksi ini ke gudang?")
    if konfirmasi_default(f"Yakin ingin menghapus transaksi {nomor}?"):
        if kembalikan_stok:
            for item in transaksi_ditemukan["item"]:
                id_brg = item["id_barang"]
                jml = item["jumlah"]
                if id_brg in data_barang["barang"]:
                    data_barang["barang"][id_brg]["stok"] += jml
            print("[INFO] Stok barang berhasil dikembalikan ke gudang.")

        data_barang["transaksi"].remove(transaksi_ditemukan)

        if simpan_data():
            print(f"[SUKSES] Transaksi {nomor} berhasil dihapus dari database.")
        else:
            print("[ERROR] Gagal menyimpan perubahan ke database.")
    else:
        print("[INFO] Penghapusan transaksi dibatalkan.")

def riwayat_transaksi():
    print("\n=== RIWAYAT TRANSAKSI ===")
    if not data_barang["transaksi"]:
        print("Belum ada transaksi.")
        return

    for data_transaksi in data_barang["transaksi"]:
        print(
            f"{data_transaksi['nomor']:<10} | "
            f"{data_transaksi['tanggal']:<19} | "
            f"{data_transaksi['kasir_nama'][:16]:<16} | "
            f"{rupiah(data_transaksi['total']):>12}"
        )

def laporan_penjualan_admin():
    print("\n" + "=" * 60)
    print("                 LAPORAN PENJUALAN")
    print("=" * 60)

    if not data_barang["transaksi"]:
        print("[INFO] Belum ada transaksi penjualan.")
        return

    hari_ini = datetime.now().date()
    awal_minggu = hari_ini.fromordinal(
        hari_ini.toordinal() - hari_ini.weekday()
    )
    awal_bulan = hari_ini.replace(day=1)

    # Mengelompokkan transaksi berdasarkan tanggal
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

    # Menampilkan laporan setiap periode
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

        print("\n" + "-" * 60)
        print(f" {judul}")
        print("-" * 60)

        if not daftar_transaksi:
            print("Belum ada transaksi pada periode ini.")
        else:
            for transaksi in daftar_transaksi:
                print(
                    f"{transaksi['nomor']} | "
                    f"{transaksi['tanggal']} | "
                    f"{transaksi['kasir_nama']} | "
                    f"{rupiah(transaksi['total'])}"
                )

        print("-" * 60)
        print(f"Jumlah transaksi : {len(daftar_transaksi)}")
        print(f"Total penjualan  : {rupiah(total_penjualan)}")
        print(f"Laba kotor       : {rupiah(total_laba_kotor)}")
        if len(transaksi_lengkap) < len(daftar_transaksi):
           print(
               "[PERINGATAN] Sebagian transaksi lama "
               "belum memiliki data modal."
                )
    print("\n" + "=" * 60)
    print("             LAPORAN SELESAI")
    print("=" * 60)


def kelola_status_barang():
    while True:
        print("\n" + "=" * 60)
        print("KELOLA STATUS BARANG".center(60))
        print("=" * 60)

        barang_aktif = data_barang.get("barang", {})
        barang_arsip = data_barang.get("arsip_barang", {})

        if not barang_aktif and not barang_arsip:
            print("❗[INFO] Belum ada data barang yang tersimpan.")
            return

        print("--- [ BARANG DI ETALASE / GUDANG ] ---")
        for id_barang, barang in barang_aktif.items():
            status = barang.get("status", "Aktif")
            print(
                f"ID: {id_barang:<8} | "
                f"Nama: {barang['nama_barang'][:22]:<22} | "
                f"Stok: {barang['stok']:>4} | "
                f"Status: {status:<9}"
            )

        print("\n--- [ BARANG NONAKTIF / RUSAK ] ---")
        for id_barang, barang in barang_arsip.items():
            status = barang.get("status", "Nonaktif")
            print(
                f"ID: {id_barang:<8} | "
                f"Nama: {barang['nama_barang'][:22]:<22} | "
                f"Stok: {barang['stok']:>4} | "
                f"Status: {status:<9}"
            )

        print("\nPilih opsi:")
        print("1. Ubah status barang (Aktif/Nonaktif/Rusak)")
        print("2. Aktifkan kembali barang dari arsip")
        print("0. Kembali ke menu admin")

        pilihan = input("Masukkan pilihan (0-2): ").strip()
        if pilihan == "0":
            break

        elif pilihan == "1":
            id_barang = input("Masukkan ID barang yang ingin diubah statusnya: ").upper()
            if id_barang not in barang_aktif:
                print("⚠️[ERROR] ID barang tidak ditemukan di etalase/gudang.")
                continue

            print("Pilih status baru:")
            print("1. Aktif (layak jual)")
            print("2. Rusak (tidak layak jual)")
            print("3. Nonaktif (pindahkan ke arsip / off)")
            print("0. Batal")
            pilihan_status = input("Masukkan pilihan status (0-3): ").strip()

            if pilihan_status == "0":
                print("❗[INFO] Perubahan status dibatalkan.")
                continue

            if  pilihan_status == "1":
                barang_aktif[id_barang]["status"] = "Aktif"
                if simpan_data():
                    print(f"[SUKSES] Status barang '{barang_aktif[id_barang]['nama_barang']}' diubah menjadi Aktif.")
                    catat_log(f"admin", f"Mengubah status barang {barang_aktif[id_barang]['nama_barang']} ({id_barang}) menjadi Aktif")

            elif pilihan_status == "2":
                barang_aktif[id_barang]["status"] = "Rusak"
                if simpan_data():
                    print(f"[SUKSES] Status barang '{barang_aktif[id_barang]['nama_barang']}' diubah menjadi Rusak.")
                    catat_log(f"admin", f"Mengubah status barang {barang_aktif[id_barang]['nama_barang']} ({id_barang}) menjadi Rusak")

            elif pilihan_status == "3":
                barang_dihapus = barang_aktif.pop(id_barang)
                barang_dihapus["status"] = "Nonaktif"
                data_barang.setdefault("arsip_barang", {})[id_barang] = barang_dihapus
                if simpan_data():
                    print(f"[SUKSES] Barang '{barang_dihapus['nama_barang']}' dipindahkan ke arsip (Nonaktif).")
                    catat_log(f"admin", f"Memindahkan barang {barang_dihapus['nama_barang']} ({id_barang}) ke arsip (Nonaktif)")

            elif pilihan_status not in ("1", "2", "3"):
                print("⚠️[ERROR] Pilihan status tidak valid.")


        elif pilihan == "2":
            id_barang = input("Masukkan ID barang yang ingin diaktifkan kembali dari arsip: ").upper()
            if id_barang not in barang_arsip:
                print("⚠️[ERROR] ID barang tidak ditemukan di arsip.")
                continue

            barang_aktif[id_barang] = barang_arsip.pop(id_barang)
            barang_aktif[id_barang]["status"] = "Aktif"
            if simpan_data():
                print(f"[SUKSES] Barang '{barang_aktif[id_barang]['nama_barang']}' diaktifkan kembali dari arsip.")
                catat_log(f"admin", f"Mengaktifkan kembali barang {barang_aktif[id_barang]['nama_barang']} ({id_barang}) dari arsip")

            else:
                print("⚠️[ERROR] Gagal menyimpan perubahan ke database.")




# ==========================================
# FITUR GUDANG
# ==========================================
def daftar_barang():
   print("\n" + "-" *30)
   print("\n=== DATA BARANG ===")
   print("-"*30)
   if not data_barang["barang"]:
       print("Belum ada barang.")
       return

   print(
        f"{'ID':<9}"
        f"{'NAMA BARANG':<20}"
        f"{'STOK':>7}"
        f"{'HARGA PABRIK':>16}"
        f"{'HARGA JUAL':>15}"
        f"{'LABA':>15}"
    )

   for id_barang, barang in data_barang["barang"].items():

        pabrik = ambil_harga_pabrik(barang)
        jual = ambil_harga_jual(barang)
        laba = hitung_laba(pabrik, jual)

        print(
            f"{id_barang:<9}"
            f"{barang['nama_barang'][:19]:<20}"
            f"{barang['stok']:>7}"
            f"{rupiah(pabrik):>16}"
            f"{rupiah(jual):>15}"
            f"{rupiah(laba):>15}"
        )
   print("=" * 85)

def tambah_barang():
    print("\n=== TAMBAH BARANG ===")

    while True:
        angka_acak = random.randint(1000, 9999)
        id_barang = f"BRG{angka_acak}"
        if (
            id_barang not in data_barang["barang"]
            and id_barang not in data_barang.get("arsip_barang", {})
        ):
            break

    print(f"❗[INFO] ID Barang berhasil dibuat otomatis: {id_barang}")

    nama = input_wajib("Nama barang: ")
    stok = input_angka("Stok awal: ")
    harga_pabrik = input_angka("Harga dari pabrik (Rp): ", 1)
    harga_jual = input_angka("Harga jual (Rp): ", 1)

    while True:
        tanggal_str = input_wajib(
            "Tanggal expired (DD-MM-YYYY): "
        )

        try:
            datetime.strptime(tanggal_str, "%d-%m-%Y")
            break
        except ValueError:
            print("⚠️[ERROR] Format tanggal tidak valid.")

    laba = hitung_laba(harga_pabrik, harga_jual)

    data_barang["barang"][id_barang] = {
        "nama_barang": nama,
        "stok": stok,
        "harga": harga_jual,
        "harga_pabrik": harga_pabrik,
        "harga_jual": harga_jual,
        "laba_per_barang": laba,
        "expired": tanggal_str,
        "status": "Aktif"
    }

    if simpan_data():
        print("\n[BERHASIL] Barang berhasil ditambahkan.")
        print("-" * 55)
        print("Harga pabrik :", rupiah(harga_pabrik))
        print("Harga jual   :", rupiah(harga_jual))
        print("Laba per unit:", rupiah(laba))
        print("-" * 55)
    else:
        del data_barang["barang"][id_barang]


def edit_barang():
    daftar_barang()
    id_barang = input_wajib("\nID barang yang diedit: ").upper()
    barang = data_barang["barang"].get(id_barang)
    if not barang:
        print("⚠️[ERROR] ID barang tidak ditemukan.")
        return


    print("\nKosongkan input jika tidak ingin mengubah data.")

    nama = input(f"Nama barang [{barang['nama_barang']}]: ").strip()
    stok = input(f"Stok [{barang['stok']}]: ").strip()
    harga_pabrik = input(f"Harga pabrik [{ambil_harga_pabrik(barang)}]: ").strip()
    harga_jual = input(f"Harga jual [{ambil_harga_jual(barang)}]: ").strip()
    expired = input(f"Expired [{barang.get('expired', '')}]: ").strip()

    try:
        stok_baru = int(stok) if stok else int(barang["stok"])

        pabrik_baru = (
            int(harga_pabrik)
            if harga_pabrik
            else ambil_harga_pabrik(barang) )

        jual_baru = (
            int(harga_jual)
            if harga_jual
            else ambil_harga_jual(barang) )

        if stok_baru < 0 or pabrik_baru < 1 or jual_baru < 1:
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
        "stok": stok_baru,
        "harga_pabrik": pabrik_baru,
        "harga_jual": jual_baru,
        "harga": jual_baru,
        "laba_per_barang": hitung_laba(
            pabrik_baru, jual_baru
        ),
        "expired": expired or barang.get("expired", "31-12-2099")
    })

    if simpan_data():
        print("\n[SUKSES] Data barang berhasil diperbarui.")
    else:
        barang.clear()
        barang.update(data_lama)

def hapus_barang():
    daftar_barang()
    id_barang = input_wajib("ID barang yang dihapus: ").upper()
    if id_barang in data_barang["barang"]:
      if konfirmasi_default("Yakin hapus barang?"):
        barang_dihapus = data_barang["barang"].pop(id_barang)
        barang_dihapus["status"] = "Nonaktif"
        data_barang.setdefault("arsip_barang", {})[id_barang] = barang_dihapus
        if simpan_data():
          print(f"[SUKSES] barang diarsipkan.")
          catat_log("gudang", f"Menghapus barang {barang_dihapus['nama_barang']} ({id_barang})")
    else:
        print("[ERROR] ID barang tidak ditemukan.")

def urut_barang_heap_sort():
    arr = list(data_barang["barang"].items())
    n = len(arr)
    if not arr:
        print("belum ada barang")
        return

    for id_barang, barang in arr:
        pabrik = ambil_harga_pabrik(barang)
        jual = ambil_harga_jual(barang)

        print(
    f"{id_barang:<8} | "
    f"{barang['nama_barang'][:20]:<20} | "
    f"Stok: {barang['stok']:>4} | "
    f"Pabrik: {rupiah(pabrik):>10} | "
    f"Jual: {rupiah(jual):>10} | "
    f"Laba: {rupiah(jual - pabrik):>9}"
)
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
    if not arr:
        print("Belum ada barang.")
    else:
       for id_barang, barang in arr:
           print(
        f"{id_barang:<8} | "
        f"{barang['nama_barang'][:20]:<20} | "
        f"Stok: {barang['stok']:>4} | "
        f"{rupiah(barang['harga']):>10}"
    )

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

def cek_expired():
    hari_ini = datetime.now().date()
    hasil_tabel = []

    print(f"\n Tanggal hari ini  : {hari_ini}")

    if not data_barang["barang"]:
        print("Belum ada data barang.")
        return

        hasil_tabel = []

    for id_barang, barang in data_barang["barang"].items():
        print("\n --- CEK EXPIRED BARANG ---")
        harga = barang['harga']
        tanggal_str = barang.get('expired', '31-12-2099')

        try:
            tanggal_expired = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
        except ValueError:
            print(f"Data tanggal untuk {barang['nama_barang']} error.")
            continue

        sisa_hari = (tanggal_expired - hari_ini).days

        if sisa_hari <= 0:
            status = "⚠️EXPIRED"
            diskon = 0
            print("\n --- ⚠️PERINGATAN! BARANG TIDAK BOLEH DI JUAL SUDAH EXPIRED --- ")
        elif sisa_hari <= 5:
            status = "⚠️BAHAYA"
            diskon = 0.04
            print("\n⚠️PERINGATAN! BARANG MENDEKATI TANGGAL EXPIRED!")
        else:
            status = "NORMAL"
            diskon = 0

        diskon_expired = harga * diskon
        harga_akhir = harga - diskon_expired

        hasil_tabel.append([
            id_barang,
            barang['nama_barang'],
            tanggal_str,
            status,
            f"{diskon * 100:.0f}%",
            f"Rp{harga:,.0f}",
            f"Rp{harga_akhir:,.0f}"
        ])

    if hasil_tabel:
        print("\n" + "=" * 120)
        print("                 LAPORAN CEK EXPIRED BARANG")
        print("=" * 120)

        header = [
            "ID BARANG", "NAMA BARANG", "TANGGAL EXPIRED",
            "STATUS", "DISKON", "HARGA AWAL", "HARGA AKHIR"
        ]

        lebar = [12, 22, 18, 18, 10, 18, 18]

        print(" | ".join(
            f"{judul:<{ukuran}}"
            for judul, ukuran in zip(header, lebar)
        ))

        print("-" * 130)

        for baris in hasil_tabel:
            print(" | ".join(
                f"{str(nilai):<{ukuran}}"
                for nilai, ukuran in zip(baris, lebar)
            ))

        print("=" * 130)


def sorting_expired():
    print("\n" + "-" * 30)
    print("\n --- Heap Sort Barang Expired --- ")

    if not data_barang["barang"]:
        print("\n BELUM ADA DATA BARANG")
        return

    barang_urut = list(data_barang["barang"].items())
    n = len(barang_urut)

    def heapify(arr, n, i):
        terbesar = i
        kiri = 2 * i + 1
        kanan = 2 * i + 2

        def get_date(barang_item):
            tgl_str = barang_item.get('expired', '31-12-2099')
            try:
                return datetime.strptime(tgl_str, "%d-%m-%Y").date()
            except ValueError:
                return datetime.strptime('31-12-2099', "%d-%m-%Y").date()

        if kiri < n and get_date(arr[kiri][1]) > get_date(arr[terbesar][1]):
             terbesar = kiri
        if kanan < n and get_date(arr[kanan][1]) > get_date(arr[terbesar][1]):
             terbesar = kanan

        if terbesar != i:
             arr[i], arr[terbesar] = arr[terbesar], arr[i]
             heapify(arr, n, terbesar)

    for i in range(n // 2 - 1, -1, -1):
        heapify(barang_urut, n, i)
    for i in range(n - 1, 0, -1):
        barang_urut[0], barang_urut[i] = barang_urut[i], barang_urut[0]
        heapify(barang_urut, i, 0)

    for id_barang, barang in barang_urut:
        print(
        f"{id_barang:<8} | "
        f"{barang['nama_barang'][:20]:<20} | "
        f"{barang.get('expired', '31-12-2099'):<10}"
    )

def riwayat_stok():
    print("\n" + "-" * 30)
    print("\n ---- RIWAYAT STOK ---- ")

    if not list_riwayat_stok:
        print("Belum Ada Riwayat Perubahan Stok")
        return
    for nomor, riwayat in enumerate(list_riwayat_stok, start=1):
        print("\n" + "-" * 35)
        print(f"Nomor       : {nomor}")
        print(f"ID BARANG   : {riwayat['id_barang']}")
        print(f"Nama Barang : {riwayat['nama_barang']}")
        print(f"Jenis       : {riwayat['jenis']}")
        print(f"Jumlah      : {riwayat['jumlah']}")
        print(f"Stok Sebelum: {riwayat['stok_sebelum']}")
        print(f"Stok Sesudah: {riwayat['stok_sesudah']}")
    print("\n" + "-" * 30)

def laporan_barang():
    print("\n" + "-" * 30)
    print("\n ---- LAPORAN KONDISI BARANG ---- ")

    if not data_barang["barang"]:
        print("Barang Belum Tersedia!")
        return

    hari_ini = datetime.now().date()
    normal = 0
    mendekati_expired = 0
    sudah_expired = 0
    stok_menipis = 0

    for id_barang, barang in data_barang["barang"].items():
        stok = int(barang["stok"])
        tanggal_str = barang.get("expired", "31-12-2099")

        try:
            tanggal_expired = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
        except ValueError:
            tanggal_expired = hari_ini

        sisa_hari = (tanggal_expired - hari_ini).days

        if sisa_hari <= 0:
            status = "⚠️EXPIRED"
            sudah_expired += 1
        elif sisa_hari <= 5:
            status = "⚠️MENDEKATI EXPIRED"
            mendekati_expired += 1
        else:
            status = "NORMAL"
            normal += 1

        if stok <= 5:
            stok_menipis += 1
            print("⚠️ PERINGATAN: STOK BARANG MENIPIS!")

        print("\n" + "-" * 35)
        print(f"ID Barang   : {id_barang}")
        print(f"Nama Barang : {barang['nama_barang']}")
        print(f"Stok        : {stok}")
        print(f"Expired     : {tanggal_str}")
        print(f"Sisa hari   : {sisa_hari}")
        print(f"Status      : {status}")

    print("\n" + "=" * 35)
    print("--- RINGKASAN LAPORAN ---")
    print(f"Barang normal             : {normal}")
    print(f"Barang mendekati expired  : {mendekati_expired}")
    print(f"Barang sudah expired      : {sudah_expired}")
    print(f"Barang dengan stok <= 5   : {stok_menipis}")
    print("=" * 35)

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

def tampilkan_barang():
    print("\n" + "-" * 30)
    print("\n --- Daftar Barang --- ")

    if not data_barang["barang"]:
        print("\n --- Barang Tidak Ditemukan --- ")
        return


    for id_barang, barang in data_barang["barang"].items():
        pabrik = ambil_harga_pabrik(barang)
        jual = ambil_harga_jual(barang)

        print("\n" + "-" * 55)
        print(f"ID BARANG       : {id_barang}")
        print(f"NAMA BARANG     : {barang['nama_barang']}")
        print(f"STOK            : {barang['stok']}")
        print(f"HARGA PABRIK    : {rupiah(pabrik)}")
        print(f"HARGA JUAL      : {rupiah(jual)}")
        print(f"LABA PER UNIT   : {rupiah(jual - pabrik)}")
        print(f"TANGGAL EXPIRED : {barang.get('expired', '-')}")

        # masuk potongan hargae
        sisa_hari, potongan, harga_akhir = hitung_diskon_expired(barang)

        if sisa_hari is not None and 1 <= sisa_hari <= 5:
            print("STATUS DISKON  : MENDAPAT DISKON 4%")
            print(f"POTONGAN HARGA : {rupiah(potongan)}")
            print(f"HARGA PROMO    : {rupiah(harga_akhir)}")
        elif sisa_hari is not None and sisa_hari <= 0:
            print("STATUS DISKON  : BARANG SUDAH EXPIRED")
        else:
            print("STATUS DISKON  : TIDAK ADA DISKON")

    print("\n" + "-" * 30)

def update_stok():
    print("\n" + "-" * 30)
    print("\n ---- UPDATE STOK BARANG ----")

    if not data_barang["barang"]:
        print("DATA TIDAK TERSEDIA")
        return

    id_barang = input("Masukan id barang: ").upper()

    if id_barang not in data_barang["barang"]:
        print("Barang Tidak Ditemukan")
        return

    barang = data_barang["barang"][id_barang]
    stok_sebelum = int(barang["stok"])

    print(f"\nNama barang  : {barang['nama_barang']}")
    print(f"Stok saat ini: {barang['stok']}")

    print("\n1. Tambah stok")
    print("2. Kurangi stok")

    pilihan = input("Masukan Pilihan Anda :").strip()
    try:
        jumlah = int(input("Masukan jumlah stok :"))
    except ValueError:
        print("INPUT TIDAK VALID! MASUKKAN ANGKA.")
        return

    if jumlah <= 0:
        print("JUMLAH STOK HARUS LEBIH DARI 0!")
        return

    if pilihan == "1":
        barang['stok'] = int(barang["stok"]) + jumlah
        print("SUKSES Stok Barang Berhasil Ditambahkan")

    elif pilihan == "2":
        if jumlah > int(barang["stok"]):
            print("Stok Tidak Cukup!")
            return
        barang['stok'] = int(barang["stok"]) - jumlah
        print(" SUKSES Stok Barang Berhasil Dikurangi!")
    else:
        print("Pilihan Tidak Valid!")
        return

    print(f"STOK TERBARU    : {barang['stok']}")

    riwayat_baru = {
         "id_barang": id_barang,
         "nama_barang": barang["nama_barang"],
         "jenis": "Tambah" if pilihan == "1" else "Kurangi",
         "jumlah": jumlah,
         "stok_sebelum": stok_sebelum,
         "stok_sesudah": int(barang["stok"])
    }

    list_riwayat_stok.append(riwayat_baru)

    if simpan_data():
        print("[SUKSES] Stok dan riwayat berhasil disimpan.")
    else:
        barang["stok"] = stok_sebelum
        list_riwayat_stok.pop()
        print("⚠️[ERROR] Gagal menyimpan perubahan stok.")


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

    baris.append("-" * 46)
    if total_hemat > 0:
        baris.append(f"{'TOTAL HEMAT DISKON':<25}{rupiah(total_hemat):>21}")

    baris += ["-" * 46,
              f"{'TOTAL':<25}{rupiah(data_transaksi['total']):>21}",
              f"{metode_bayar:<25}{rupiah(data_transaksi['bayar']):>21}",
              f"{'KEMBALIAN':<25}{rupiah(data_transaksi['kembalian']):>21}",
              garis, "Terima kasih sudah berbelanja!".center(46), garis]
    return "\n".join(baris)

def cetak_struk(data_transaksi):
    isi = format_struk(data_transaksi)
    print("\n" + isi)
    try:
        FOLDER_STRUK.mkdir(parents=True, exist_ok=True)
        lokasi_struk = FOLDER_STRUK / f"{data_transaksi['nomor']}.txt"
        lokasi_struk.write_text(isi + "\n", encoding="utf-8")
        print(f"[SUKSES] File nota disimpan: {lokasi_struk}")
    except OSError as error:
        print(f"[PERINGATAN] Struk tampil, tetapi gagal tersimpan: {error}")

def transaksi_penjualan(kasir):
    if not data_barang["barang"]:
        print("⚠️[ERROR] Belum ada barang. Minta bagian gudang menambahkan barang.")
        return
    keranjang = {}
    print("\n=== TRANSAKSI PENJUALAN ===")
    print("Masukkan ID barang, ketik 'selesai' untuk bayar, 'batal' untuk membatalkan.")
    while True:
        daftar_barang()
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

    total = tampil_keranjang(keranjang)

    print("\n=== METODE PEMBAYARAN ===")
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

    data_transaksi = {"nomor": f"TRX{baru['nomor_berikutnya']:06d}",
           "tanggal": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
           "kasir_id": kasir[0], "kasir_nama": kasir[1]["nama"],
           "kasir_username": kasir[1]["username"], "item": daftar_item,
           "total": total, "metode": metode, "bayar": bayar, "kembalian": kembalian}

    baru["transaksi"].append(data_transaksi)
    baru["nomor_berikutnya"] += 1
    if not simpan_data(baru):
        print("⚠️[ERROR] Transaksi gagal disimpan. Stok belum dikurangi.")
        return

    data_barang.clear()
    data_barang.update(baru)
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
        print("⚠️[ERROR] Nomor transaksi tidak ditemukan.")

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
        print("⚠️[ERROR] Format tanggal tidak valid.")
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
    print("-" * 75)

    total_penjualan = 0

    for data_transaksi in hasil:
        print(
            f"{data_transaksi['nomor']:<10} | "
            f"{data_transaksi['tanggal']:<19} | "
            f"{data_transaksi['kasir_nama'][:16]:<16} | "
            f"{rupiah(data_transaksi['total']):>12}"
        )

        total_penjualan += data_transaksi["total"]

    print("-" * 75)
    print(f"Jumlah transaksi : {len(hasil)}")
    print(f"Total penjualan  : {rupiah(total_penjualan)}")


def rekomendasi_barang_terlaris():
    print("\n" + "=" * 65)
    print("  REKOMENDASI BARANG TERLARIS  ")
    print("=" * 65)
    if not data_barang["transaksi"]:
        print("[INFO] Belum ada transaksi penjualan.")
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
        print("[INFO] Belum ada data penjualan barang.")
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

    print("-" * 65)

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

    print("-" * 65)

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

    print("\n" + "=" * 65)
    print("Data rekomendasi berdasarkan seluruh riwayat transaksi.")
    print("=" * 65)


# ==========================================
# PENGATURAN MENU (ROLE)
# ==========================================
def menu_admin(id_login):
    while True:
        print("\n=== MENU ADMIN ===")
        print("1. Tambah pengguna\n2. Edit pengguna\n3. Hapus pengguna\n4. Tampilkan pengguna\n5. Cari pengguna\n6. Riwayat Transaksi\n7. Tampilkan data terhapus\n8. Hapus Transaksi\n9. Kelola Status Barang\n10. Cari Riwayat Transaksi Berdasarkan Tanggal\n11. Ringkasan Jumlah Akun per Role\n12. Tampilkan Menu Gudang\n13. Tampilkan Menu Kasir\n14. Logout")
        pilih = input("Pilih fitur yang ingin digunakan (1-14): ").strip()
        if pilih == "1": tambah_pengguna()
        elif pilih == "2": edit_pengguna()
        elif pilih == "3": hapus_pengguna(id_login)
        elif pilih == "4": tampilkan_data_pengguna()
        elif pilih == "5": cari_pengguna()
        elif pilih == "6": riwayat_transaksi()
        elif pilih == "7": tampilkan_data_terhapus()
        elif pilih == "8": hapus_transaksi()
        elif pilih == "9": kelola_status_barang()
        elif pilih == "10": riwayat_transaksi_tanggal()
        elif pilih == "11": menu_gudang()
        elif pilih == "12": menu_kasir(id_login)
        elif pilih == "13": break
        else: print("Pilihan tidak valid.")

def menu_gudang():
    while True:
        print("\n=== MENU GUDANG ===")
        print("1. Tambah barang\n2. Edit barang\n3. Hapus barang\n4. Tampilkan barang\n5. Urutkan barang (Heap Sort)")
        print("6. Cari barang\n7. Update stok barang\n8. cek expired barang\n9. sorting barang expired\n10. Laporan kondisi barang\n11. Notifikasi barang\n12. Riwayat perubahan stok\n13. Harga satuan barang\n14. logout")
        pilih = input("Pilih fitur yang ingin digunakan (1-14): ").strip()
        if pilih == "1": tambah_barang()
        elif pilih == "2": edit_barang()
        elif pilih == "3": hapus_barang()
        elif pilih == "4": tampilkan_barang()
        elif pilih == "5": urut_barang_heap_sort()
        elif pilih == "6": cari_barang()
        elif pilih == "7": update_stok()
        elif pilih == "8": cek_expired()
        elif pilih == "9": sorting_expired()
        elif pilih == "10": laporan_barang()
        elif pilih == "11": notifikasi_barang()
        elif pilih == "12": riwayat_stok()
        elif pilih == "13": analisis_spldv_harga_barang()
        elif pilih == "14": break
        else: print("Pilihan tidak valid.")

def menu_kasir(id_login):
    while True:
        kasir = (id_login, data_pengguna["pengguna"][id_login])
        print(f"\n=== MENU KASIR | {kasir[1]['nama']} ===")
        print("1. Transaksi penjualan dan cetak nota")
        print("2. Cari barang")
        print("3. Lihat barang")
        print("4. Cetak ulang struk")
        print("5. Riwayat transaksi berdasarkan tanggal")
        print("6. Logout")
        pilih = input("Pilih fitur yang ingin digunakan (1-6): ").strip()
        if pilih == "1": transaksi_penjualan(kasir)
        elif pilih == "2": cari_barang()
        elif pilih == "3": daftar_barang()
        elif pilih == "4": cetak_ulang_struk()
        elif pilih == "5": riwayat_transaksi_tanggal()
        elif pilih == "6": break
        else: print("Pilihan tidak valid.")

def main():
    print("\n=== SELAMAT DATANG DI SMK MART ===")
    global data_pengguna
    data_pengguna = muat_data()

    while True:
        print("\n=== LOGIN SMK MART ===")
        username = input_wajib("Username (0 untuk keluar): ").strip().lower()
        if username == "0":
            print("Terima kasih. Program selesai.")
            break

        password = getpass.getpass("Masukkan password anda: ").strip()

        login = next(((id_pengguna, pengguna) for id_pengguna, pengguna in data_pengguna["pengguna"].items()
                      if pengguna["username"] == username and cek_password(password, pengguna["password"])), None)

        if not login:
            print("[ERROR] Username atau password salah.")
            continue

        id_login, pengguna = login
        print(f"[SUKSES] Halo, {pengguna['nama']}! Login sebagai {pengguna['role']}.")

        if pengguna["role"] == "admin": menu_admin(id_login)
        elif pengguna["role"] == "gudang": menu_gudang()
        elif pengguna["role"] == "kasir": menu_kasir(id_login)

try:
    main()
except (KeyboardInterrupt, EOFError):
    print("\nProgram dihentikan.")
