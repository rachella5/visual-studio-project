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
            pictBlogin = new PictureBox();
            Lblwelcomeback1 = new Label();
            Lblwelcomeback2 = new Label();
            usernameTXB = new TextBox();
            ((System.ComponentModel.ISupportInitialize)pictBlogin).BeginInit();
            SuspendLayout();
            // 
            // passwordTXB
            // 
            passwordTXB.Location = new Point(271, 301);
            passwordTXB.Name = "passwordTXB";
            passwordTXB.PasswordChar = '*';
            passwordTXB.PlaceholderText = "Password";
            passwordTXB.Size = new Size(258, 27);
            passwordTXB.TabIndex = 2;
            // 
            // BTNlogin
            // 
            BTNlogin.BackColor = Color.White;
            BTNlogin.Location = new Point(333, 361);
            BTNlogin.Name = "BTNlogin";
            BTNlogin.Size = new Size(138, 36);
            BTNlogin.TabIndex = 2;
            BTNlogin.Text = "LOGIN";
            BTNlogin.UseVisualStyleBackColor = false;
            BTNlogin.Click += BTNlogin_Click;
            // 
            // pictBlogin
            // 
            pictBlogin.BackColor = Color.Transparent;
            pictBlogin.Image = (Image)resources.GetObject("pictBlogin.Image");
            pictBlogin.Location = new Point(294, -8);
            pictBlogin.Name = "pictBlogin";
            pictBlogin.Size = new Size(218, 148);
            pictBlogin.SizeMode = PictureBoxSizeMode.Zoom;
            pictBlogin.TabIndex = 3;
            pictBlogin.TabStop = false;
            pictBlogin.Click += pictBlogin_Click_1;
            // 
            // Lblwelcomeback1
            // 
            Lblwelcomeback1.AutoSize = true;
            Lblwelcomeback1.BackColor = Color.Transparent;
            Lblwelcomeback1.Font = new Font("Times New Roman", 40.2F, FontStyle.Bold, GraphicsUnit.Point, 0);
            Lblwelcomeback1.ForeColor = Color.Bisque;
            Lblwelcomeback1.Location = new Point(168, 115);
            Lblwelcomeback1.Name = "Lblwelcomeback1";
            Lblwelcomeback1.Size = new Size(475, 76);
            Lblwelcomeback1.TabIndex = 4;
            Lblwelcomeback1.Text = "Welcome Back!";
            // 
            // Lblwelcomeback2
            // 
            Lblwelcomeback2.AutoSize = true;
            Lblwelcomeback2.BackColor = Color.Transparent;
            Lblwelcomeback2.Font = new Font("Times New Roman", 12F, FontStyle.Bold, GraphicsUnit.Point, 0);
            Lblwelcomeback2.ForeColor = SystemColors.Info;
            Lblwelcomeback2.Location = new Point(201, 215);
            Lblwelcomeback2.Name = "Lblwelcomeback2";
            Lblwelcomeback2.Size = new Size(414, 23);
            Lblwelcomeback2.TabIndex = 5;
            Lblwelcomeback2.Text = "Silakan masukkan username dan password Anda";
            // 
            // usernameTXB
            // 
            usernameTXB.Location = new Point(271, 250);
            usernameTXB.Name = "usernameTXB";
            usernameTXB.PlaceholderText = "Username";
            usernameTXB.Size = new Size(258, 27);
            usernameTXB.TabIndex = 1;
            usernameTXB.TextChanged += usernameTXB_TextChanged;
            // 
            // loginForm
            // 
            AutoScaleDimensions = new SizeF(8F, 20F);
            AutoScaleMode = AutoScaleMode.Font;
            AutoSize = true;
            BackgroundImage = (Image)resources.GetObject("$this.BackgroundImage");
            BackgroundImageLayout = ImageLayout.Stretch;
            ClientSize = new Size(800, 450);
            Controls.Add(Lblwelcomeback2);
            Controls.Add(Lblwelcomeback1);
            Controls.Add(pictBlogin);
            Controls.Add(BTNlogin);
            Controls.Add(passwordTXB);
            Controls.Add(usernameTXB);
            Name = "loginForm";
            Text = "login";
            Load += loginform_Load;
            ((System.ComponentModel.ISupportInitialize)pictBlogin).EndInit();
            ResumeLayout(false);
            PerformLayout();
        }

        #endregion
        private TextBox passwordTXB;
        private Button BTNlogin;
        private PictureBox pictBlogin;
        private Label Lblwelcomeback1;
        private Label Lblwelcomeback2;
        private TextBox usernameTXB;
    }
}
