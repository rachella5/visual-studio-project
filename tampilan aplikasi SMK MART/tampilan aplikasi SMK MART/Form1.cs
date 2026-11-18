namespace tampilan_aplikasi_SMK_MART
{
    public partial class loginForm : Form
    {
        public loginForm()
        {
            InitializeComponent();
            this.Load += (s, e) => PosisikanPanelLogin();
            this.Resize += (s, e) => PosisikanPanelLogin();
        }

        private void loginform_Load(object sender, EventArgs e)
        {

        }

        private void usernameTXB_TextChanged(object sender, EventArgs e)
        {

        }

        private void BTNlogin_Click(object sender, EventArgs e)
        {
            string inputUsername = usernameTXB.Text.ToLower();
            string inputPassword = passwordTXB.Text;

            if (inputUsername == "admin" && inputPassword == "admin12345")
            {
                MessageBox.Show("Halo, Admin Utama! Login berhasil.", "Sukses", MessageBoxButtons.OK, MessageBoxIcon.Information);

            }
            else
            {
                MessageBox.Show("Username atau password salah.", "Login Gagal!", MessageBoxButtons.OK, MessageBoxIcon.Error);
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
