using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

namespace tampilan_aplikasi_SMK_MART
{
    public partial class loginForm : Form
    {
        private int percobaanGagal = 0;
        private readonly string folderData = @"C:\Users\rache\OneDrive\Dokumen\visual studio project\SMK_MART_Python\data";

        private string FilePengguna => Path.Combine(folderData, "pengguna.txt");
        private string FileLog => Path.Combine(folderData, "log_aktivitas.txt");

        public loginForm()
        {
            InitializeComponent();
            this.Load += (s, e) => PosisikanPanelLogin();
            this.Resize += (s, e) => PosisikanPanelLogin();
        }

        private void SiapkanFileDataAwal()
        {
            if (!Directory.Exists(folderData))
            {
                Directory.CreateDirectory(folderData);
            }

            if (!File.Exists(FilePengguna))
            {
                string isiAwal =
                    "admin|admin123|Administrator SMK MART|admin|aktif\n" +
                    "kasir1|kasir123|Dewi Lestari|kasir|aktif\n" +
                    "kasir2|kasir123|Rian Saputra|kasir|aktif\n" +
                    "kasir3|kasir123|Sari Wulandari|kasir|nonaktif\n" +
                    "gudang1|gudang123|Budi Santoso|gudang|aktif\n";
                File.WriteAllText(FilePengguna, isiAwal, Encoding.UTF8);
            }
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
            File.AppendAllText(FileLog, $"{tanggal}|{waktu}|{username}|{aksi}\n", Encoding.UTF8);
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
            bool akunDitemukan = false;

            foreach (string baris in semuaBaris)
            {
                if (string.IsNullOrWhiteSpace(baris)) continue;

                string[] kolom = baris.Split('|');
                if (kolom.Length < 5) continue;

                string uname = kolom[0].Trim().ToLower();
                string pwTersimpan = kolom[1].Trim();
                string namaLengkap = kolom[2].Trim();
                string peran = kolom[3].Trim().ToLower();
                string status = kolom[4].Trim().ToLower();

                if (uname == inputUsername && CekPassword(inputPassword, pwTersimpan))
                {
                    akunDitemukan = true;

                    if (status != "aktif")
                    {
                        MessageBox.Show("Akun Anda berstatus NONAKTIF. Hubungi Admin.", "Akses Ditolak", MessageBoxButtons.OK, MessageBoxIcon.Stop);
                        return;
                    }

                    percobaanGagal = 0;
                    CatatLog(uname, "LOGIN");
                    MessageBox.Show($"Halo, {namaLengkap}! Login berhasil sebagai {peran.ToUpper()}.", "Sukses", MessageBoxButtons.OK, MessageBoxIcon.Information);

                    // Nanti arahkan ke Form tujuan sesuai peran di sini:
                    if (peran == "admin")
                    {
                        // Contoh jika form admin sudah dibuat:
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
                    return;
                }
            }

            if (!akunDitemukan)
            {
                percobaanGagal++;
                if (percobaanGagal >= 3)
                {
                    MessageBox.Show("Salah password 3 kali. Akses ditolak dan aplikasi berhenti.", "Login Gagal!", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    Application.Exit();
                }
                else
                {
                    MessageBox.Show($"Username atau password salah ({percobaanGagal}/3).", "Login Gagal!", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    passwordTXB.Clear();
                    passwordTXB.Focus();
                }
            }
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
