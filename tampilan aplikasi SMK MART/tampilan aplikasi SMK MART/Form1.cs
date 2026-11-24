using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

namespace tampilan_aplikasi_SMK_MART
{
    public partial class loginForm : Form
    {
        // [DIRUBAH] Gunakan Dictionary agar hitungan gagal dilacak per username (sama seperti Python)
        private readonly Dictionary<string, int> percobaanGagal = new Dictionary<string, int>();
        private readonly string folderData = @"C:\Users\rache\OneDrive\Dokumen\visual studio project\SMK_MART_Python\data";

        private string FilePengguna => Path.Combine(folderData, "pengguna.txt");
        private string FileLog => Path.Combine(folderData, "log_aktivitas.txt");
        private string FileLogSistem => Path.Combine(folderData, "log_sistem.txt");

        public loginForm()
        {
            InitializeComponent();
            SiapkanFileDataAwal();
            this.Load += (s, e) => PosisikanPanelLogin();
            this.Resize += (s, e) => PosisikanPanelLogin();
        }

        private void SiapkanFileDataAwal()
        {
            if (!Directory.Exists(folderData))
            {
                Directory.CreateDirectory(folderData);
            }

            string tgl = DateTime.Now.ToString("dd-MM-yyyy HH:mm:ss");
            string barisAdminDefault = $"admin utama|admin123|Administrator SMK MART|admin|aktif|{tgl}|-|-";

            if (!File.Exists(FilePengguna))
            {
                File.WriteAllText(FilePengguna, barisAdminDefault + "\n", new UTF8Encoding(false));
                return;
            }

            
            List<string> barisList = new List<string>(File.ReadAllLines(FilePengguna, new UTF8Encoding(false)));
            bool adminDitemukan = false;

            for (int i = 0; i < barisList.Count; i++)
            {
                if (string.IsNullOrWhiteSpace(barisList[i])) continue;

                string[] kolom = barisList[i].Split('|');
                string uname = kolom[0].Trim().ToLower();

                if (uname == "admin utama" || uname == "admin_utama")
                {
                    if (!adminDitemukan)
                    {
                        string pwLama = (kolom.Length > 1 && !string.IsNullOrWhiteSpace(kolom[1])) ? kolom[1].Trim() : "admin123";
                        string tglAdd = (kolom.Length > 5 && !string.IsNullOrWhiteSpace(kolom[5])) ? kolom[5].Trim() : tgl;
                        barisList[i] = $"admin utama|{pwLama}|Administrator SMK MART|admin|aktif|{tglAdd}|-|-";
                        adminDitemukan = true;
                    }
                    else
                    {
                        // Hapus baris duplikat jika ada lebih dari 1 admin utama
                        barisList.RemoveAt(i);
                        i--;
                    }
                }
            }

            if (!adminDitemukan)
            {
                barisList.Insert(0, barisAdminDefault);
            }

            File.WriteAllLines(FilePengguna, barisList, new UTF8Encoding(false));
        }

        private bool CekPassword(string inputPassword, string passwordTersimpan)
        {
            if (!passwordTersimpan.Contains("$"))
            {
                return inputPassword == passwordTersimpan;
            }

            try
            {
                string[] bagian = passwordTersimpan.Split('$');
                byte[] salt = HexKeBytes(bagian[0]);
                byte[] hashAsli = HexKeBytes(bagian[1]);

                using (var pbkdf2 = new Rfc2898DeriveBytes(inputPassword, salt, 150000, HashAlgorithmName.SHA256))
                {
                    byte[] hashInput = pbkdf2.GetBytes(hashAsli.Length);
                    if (hashInput.Length != hashAsli.Length) return false;

                    int selisih = 0;
                    for (int i = 0; i < hashInput.Length; i++)
                    {
                        selisih |= hashInput[i] ^ hashAsli[i];
                    }
                    return selisih == 0;
                }
            }
            catch
            {
                return false;
            }
        }

        private byte[] HexKeBytes(string hex)
        {
            int panjang = hex.Length;
            byte[] hasil = new byte[panjang / 2];
            for (int i = 0; i < panjang; i += 2)
            {
                hasil[i / 2] = Convert.ToByte(hex.Substring(i, 2), 16);
            }
            return hasil;
        }

        private void CatatLog(string username, string aksi)
        {
            string tanggal = DateTime.Now.ToString("yyyy-MM-dd");
            string waktu = DateTime.Now.ToString("HH:mm:ss");
            File.AppendAllText(FileLog, $"{tanggal}|{waktu}|{username}|{aksi}\n", new UTF8Encoding(false));
        }

        private void CatatLogSistem(string username, string pesan)
        {
            string waktuLengkap = DateTime.Now.ToString("dd-MM-yyyy HH:mm:ss");
            File.AppendAllText(FileLogSistem, $"[{waktuLengkap}] [{username}] {pesan}\n", new UTF8Encoding(false));
        }

        private void loginform_Load(object sender, EventArgs e)
        {

        }

        private void usernameTXB_TextChanged(object sender, EventArgs e)
        {

        }

        private void BTNlogin_Click(object sender, EventArgs e)
        {
            string inputUsername = usernameTXB.Text.Trim().ToLower();
            string inputPassword = passwordTXB.Text.Trim();

            if (string.IsNullOrEmpty(inputUsername) || string.IsNullOrEmpty(inputPassword))
            {
                MessageBox.Show("Username dan password tidak boleh kosong!", "Peringatan", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            string[] semuaBaris = File.ReadAllLines(FilePengguna, Encoding.UTF8);
            int indexAkun = -1;
            string[] kolomAkun = Array.Empty<string>();

            // 1. Cari akun berdasarkan username terlebih dahulu
            for (int i = 0; i < semuaBaris.Length; i++)
            {
                if (string.IsNullOrWhiteSpace(semuaBaris[i])) continue;

                string[] kolom = semuaBaris[i].Split('|');
                if (kolom.Length < 5) continue;

                if (kolom[0].Trim().ToLower() == inputUsername)
                {
                    indexAkun = i;
                    kolomAkun = kolom;
                    break;
                }
            }

            // === KODE 1: GANTI BAGIAN INI (saat username tidak ditemukan) ===
            if (indexAkun == -1)
            {
                MessageBox.Show("Username tidak ditemukan!", "Login Gagal", MessageBoxButtons.OK, MessageBoxIcon.Error);
                usernameTXB.Clear();
                passwordTXB.Clear();
                usernameTXB.Focus();
                return;
            }

            string unameAsli = kolomAkun[0].Trim();
            string pwTersimpan = kolomAkun[1].Trim();
            string namaLengkap = kolomAkun[2].Trim();
            string peran = kolomAkun[3].Trim().ToLower();
            string status = kolomAkun[4].Trim().ToLower();

            // === KODE 2: GANTI BAGIAN INI (saat status akun nonaktif) ===
            if (status != "aktif")
            {
                MessageBox.Show("Akun Anda berstatus NONAKTIF. Hubungi Admin.", "Akses Ditolak", MessageBoxButtons.OK, MessageBoxIcon.Stop);
                usernameTXB.Clear();
                passwordTXB.Clear();
                usernameTXB.Focus();
                return;
            }

                // 3. Verifikasi password
                if (CekPassword(inputPassword, pwTersimpan))
            {
                percobaanGagal[inputUsername] = 0;
                CatatLog(unameAsli, "LOGIN");
                MessageBox.Show($"Halo, {namaLengkap}! Login berhasil sebagai {peran.ToUpper()}.", "Sukses", MessageBoxButtons.OK, MessageBoxIcon.Information);

                if (peran == "admin")
                {
                    // new AdminForm().Show();
                    // this.Hide();
                }
                else if (peran == "gudang")
                {
                    // new GudangForm().Show();
                    // this.Hide();
                }
                else if (peran == "kasir")
                {
                    // new KasirForm().Show();
                    // this.Hide();
                }
            }
            else
            {
                if (!percobaanGagal.ContainsKey(inputUsername))
                    percobaanGagal[inputUsername] = 0;

                percobaanGagal[inputUsername]++;
                int jumlahGagal = percobaanGagal[inputUsername];

                // POTONGAN 1: Saat salah ke-3x dan akun dinonaktifkan
                if (jumlahGagal >= 3 && inputUsername != "admin utama")
                {
                    string waktuHapus = DateTime.Now.ToString("dd-MM-yyyy HH:mm:ss");

                    string[] kolomBaru = new string[8];
                    for (int k = 0; k < 8; k++)
                    {
                        kolomBaru[k] = (k < kolomAkun.Length && !string.IsNullOrWhiteSpace(kolomAkun[k])) ? kolomAkun[k].Trim() : "-";
                    }
                    kolomBaru[4] = "nonaktif";
                    kolomBaru[7] = waktuHapus;

                    semuaBaris[indexAkun] = string.Join("|", kolomBaru);
                    File.WriteAllLines(FilePengguna, semuaBaris, new UTF8Encoding(false));

                    CatatLog(unameAsli, "NONAKTIF_OTOMATIS");
                    CatatLogSistem(unameAsli, $"Akun {unameAsli} dinonaktifkan otomatis (3x gagal login)");

                    MessageBox.Show($"Password salah 3 kali!\nAkun '{unameAsli}' otomatis DINONAKTIFKAN.", "Akun Dinonaktifkan", MessageBoxButtons.OK, MessageBoxIcon.Stop);
                    usernameTXB.Clear();
                    passwordTXB.Clear();
                    usernameTXB.Focus();
                }
                // POTONGAN 2: Saat salah ke-1x atau ke-2x (atau admin utama salah)
                else
                {
                    string infoSisa = (inputUsername == "admin utama")
                        ? "Password admin utama salah!"
                        : $"Password salah ({jumlahGagal}/3). Setelah 3x salah, akun akan dinonaktifkan.";
                    MessageBox.Show(infoSisa, "Login Gagal!", MessageBoxButtons.OK, MessageBoxIcon.Error);

                    usernameTXB.Clear();
                    passwordTXB.Clear();
                    usernameTXB.Focus();
                }
            }
            // === BATAS AKHIR METHOD BTNlogin_Click ===
        }

        private void pictBlogin_Click_1(object sender, EventArgs e)
        {

        }

        private void passwordTXB_TextChanged(object sender, EventArgs e)
        {

        }

        private void panel1_Paint(object sender, PaintEventArgs e)
        {

        }

        private void PosisikanPanelLogin()
        {
            int tengahKartuPutihX = (int)(this.ClientSize.Width * 0.779);
            int posisiY = (int)(this.ClientSize.Height * 0.47);

            panel1.Left = tengahKartuPutihX - (panel1.Width / 2);
            panel1.Top = posisiY - (panel1.Height / 2);
        }
    }
}