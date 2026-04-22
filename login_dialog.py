from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QTabWidget, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from database import DatabaseManager

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.user_id = None
        self.username = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("👁️ 眼动训练系统")
        self.setFixedSize(560, 540)
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f2f5;
            }
            QTabWidget::pane {
                border: none;
                background: white;
                border-radius: 12px;
            }
            QTabBar::tab {
                background: transparent;
                color: #6b7280;
                padding: 16px 36px;
                font-size: 17px;
                font-weight: bold;
                min-width: 130px;
            }
            QTabBar::tab:selected {
                color: #3b82f6;
                border-bottom: 3px solid #3b82f6;
            }
            QLineEdit {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 16px 18px;
                background: #f9fafb;
                font-size: 15px;
                min-height: 48px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background: white;
            }
            QPushButton {
                border-radius: 8px;
                color: white;
                font-weight: bold;
                padding: 14px;
                font-size: 16px;
            }
            QPushButton#LoginBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton#RegBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QLabel.title {
                color: #1f2937;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 24px;
            }
            QLabel.field {
                color: #374151;
                font-size: 14px;
                font-weight: bold;
                margin-top: 16px;
                margin-bottom: 6px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)
        
        # 标题区域
        title_label = QLabel("欢迎使用专注力训练系统")
        title_label.setProperty("class", "title")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 使用 Tab 切换登录和注册
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        
        # --- 登录标签页 ---
        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)
        login_layout.setContentsMargins(50, 40, 50, 40)
        login_layout.setSpacing(0)
        
        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText("请输入用户名")
        self.login_pass = QLineEdit()
        self.login_pass.setPlaceholderText("请输入密码")
        self.login_pass.setEchoMode(QLineEdit.Password)
        
        login_btn = QPushButton("登 录")
        login_btn.setObjectName("LoginBtn")
        login_btn.clicked.connect(self.handle_login)
        
        login_layout.addStretch()
        lbl_user = QLabel("用户名")
        lbl_user.setProperty("class", "field")
        login_layout.addWidget(lbl_user)
        login_layout.addWidget(self.login_user)
        lbl_pass = QLabel("密码")
        lbl_pass.setProperty("class", "field")
        login_layout.addWidget(lbl_pass)
        login_layout.addWidget(self.login_pass)
        login_layout.addSpacing(24)
        login_layout.addWidget(login_btn)
        login_layout.addStretch()
        
        # --- 注册标签页 ---
        register_tab = QWidget()
        register_layout = QVBoxLayout(register_tab)
        register_layout.setContentsMargins(50, 40, 50, 40)
        register_layout.setSpacing(0)
        
        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("设置用户名")
        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText("设置密码")
        self.reg_pass.setEchoMode(QLineEdit.Password)
        self.reg_sid = QLineEdit()
        self.reg_sid.setPlaceholderText("学号/工号")
        
        reg_btn = QPushButton("注 册")
        reg_btn.setObjectName("RegBtn")
        reg_btn.clicked.connect(self.handle_register)
        
        register_layout.addStretch()
        lbl_reg_user = QLabel("新用户名")
        lbl_reg_user.setProperty("class", "field")
        register_layout.addWidget(lbl_reg_user)
        register_layout.addWidget(self.reg_user)
        lbl_reg_pass = QLabel("设置密码")
        lbl_reg_pass.setProperty("class", "field")
        register_layout.addWidget(lbl_reg_pass)
        register_layout.addWidget(self.reg_pass)
        lbl_reg_sid = QLabel("学号/工号")
        lbl_reg_sid.setProperty("class", "field")
        register_layout.addWidget(lbl_reg_sid)
        register_layout.addWidget(self.reg_sid)
        register_layout.addSpacing(24)
        register_layout.addWidget(reg_btn)
        register_layout.addStretch()
        
        self.tabs.addTab(login_tab, "用户登录")
        self.tabs.addTab(register_tab, "新用户注册")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def handle_login(self):
        username = self.login_user.text().strip()
        password = self.login_pass.text().strip()
        
        if not username:
            QMessageBox.warning(self, "提示", "请输入用户名")
            return
        
        # 先检查用户是否存在
        basic_id = self.db.get_user_id(username)
        if not basic_id:
            QMessageBox.critical(self, "错误", "用户不存在，请先注册！")
            return
        
        # 验证密码
        user_id = self.db.verify_password(username, password)
        if user_id:
            self.user_id = user_id
            self.username = username
            self.accept()
        else:
            # 密码不匹配
            QMessageBox.critical(self, "错误", "用户名或密码错误！")

    def handle_register(self):
        username = self.reg_user.text().strip()
        password = self.reg_pass.text().strip()
        sid = self.reg_sid.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "提示", "用户名和密码不能为空")
            return
        
        # 先检查用户是否已存在
        if self.db.get_user_id(username):
            QMessageBox.warning(self, "注册失败", f"用户名 '{username}' 已被注册，请直接登录！")
            return
            
        try:
            user_id = self.db.add_user(username, password, sid)
            if user_id:
                QMessageBox.information(self, "成功", f"用户 {username} 注册成功！\n请登录。")
                self.tabs.setCurrentIndex(0) # 切换到登录页
                self.login_user.setText(username)
            else:
                QMessageBox.critical(self, "错误", "注册失败，请重试。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"注册失败: {str(e)}")
