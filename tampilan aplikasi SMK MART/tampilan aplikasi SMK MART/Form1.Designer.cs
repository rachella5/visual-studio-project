namespace tampilan_aplikasi_SMK_MART
{
    partial class loginForm
    {
        /// <summary>
        ///  Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        ///  Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        ///  Required method for Designer support - do not modify
        ///  the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(loginForm));
            passwordTXB = new TextBox();
            BTNlogin = new Button();
            usernameTXB = new TextBox();
            panel1 = new Panel();
            panel1.SuspendLayout();
            SuspendLayout();
            // 
            // passwordTXB
            // 
            passwordTXB.Anchor = AnchorStyles.Left | AnchorStyles.Right;
            passwordTXB.BackColor = Color.White;
            passwordTXB.Font = new Font("Segoe UI", 13.8F, FontStyle.Regular, GraphicsUnit.Point, 0);
            passwordTXB.Location = new Point(45, 298);
            passwordTXB.Multiline = true;
            passwordTXB.Name = "passwordTXB";
            passwordTXB.PasswordChar = '*';
            passwordTXB.PlaceholderText = "Password";
            passwordTXB.Size = new Size(434, 50);
            passwordTXB.TabIndex = 2;
            passwordTXB.TextChanged += passwordTXB_TextChanged;
            // 
            // BTNlogin
            // 
            BTNlogin.Anchor = AnchorStyles.Left | AnchorStyles.Right;
            BTNlogin.BackColor = Color.AliceBlue;
            BTNlogin.Font = new Font("Segoe UI", 13.8F, FontStyle.Bold, GraphicsUnit.Point, 0);
            BTNlogin.Location = new Point(45, 427);
            BTNlogin.Name = "BTNlogin";
            BTNlogin.Size = new Size(434, 50);
            BTNlogin.TabIndex = 2;
            BTNlogin.Text = "LOGIN";
            BTNlogin.UseVisualStyleBackColor = false;
            BTNlogin.Click += BTNlogin_Click;
            // 
            // usernameTXB
            // 
            usernameTXB.Anchor = AnchorStyles.Left | AnchorStyles.Right;
            usernameTXB.BackColor = Color.White;
            usernameTXB.Font = new Font("Segoe UI", 13.8F, FontStyle.Regular, GraphicsUnit.Point, 0);
            usernameTXB.Location = new Point(45, 227);
            usernameTXB.Multiline = true;
            usernameTXB.Name = "usernameTXB";
            usernameTXB.PlaceholderText = "Username";
            usernameTXB.Size = new Size(434, 50);
            usernameTXB.TabIndex = 1;
            usernameTXB.TextChanged += usernameTXB_TextChanged;
            // 
            // panel1
            // 
            panel1.Anchor = AnchorStyles.Right;
            panel1.BackColor = Color.Transparent;
            panel1.Controls.Add(BTNlogin);
            panel1.Controls.Add(usernameTXB);
            panel1.Controls.Add(passwordTXB);
            panel1.Location = new Point(815, 159);
            panel1.Name = "panel1";
            panel1.Size = new Size(521, 516);
            panel1.TabIndex = 3;
            panel1.Paint += panel1_Paint;
            // 
            // loginForm
            // 
            AutoScaleMode = AutoScaleMode.None;
            BackgroundImage = (Image)resources.GetObject("$this.BackgroundImage");
            BackgroundImageLayout = ImageLayout.Stretch;
            ClientSize = new Size(1348, 721);
            Controls.Add(panel1);
            DoubleBuffered = true;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            Name = "loginForm";
            Text = "login";
            WindowState = FormWindowState.Maximized;
            Load += loginform_Load;
            panel1.ResumeLayout(false);
            panel1.PerformLayout();
            ResumeLayout(false);
        }

        #endregion
        private TextBox passwordTXB;
        private Button BTNlogin;
        private TextBox usernameTXB;
        private Panel panel1;
    }
}
