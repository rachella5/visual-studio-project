namespace tampilan_aplikasi_SMK_MART
{
    public partial class loginForm : Form
    {
        public loginForm()
        {
            InitializeComponent();
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
    }
}
