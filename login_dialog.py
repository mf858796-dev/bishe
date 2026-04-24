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
        self.setFixedSize(680, 620)
        
        # 高级现代 UI 样式 - 完全独立，不受全局 QSS 影响
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2563eb, stop:0.45 #6366f1, stop:1 #a855f7
                );
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.14);
                background: rgba(255, 255, 255, 0.96);
                border-radius: 22px;
                margin-top: 0px;
            }
            QTabBar {
                qproperty-drawBase: 0;
                background: transparent;
            }
            QTabBar::tab {
                background: transparent;
                color: rgba(255, 255, 255, 0.72);
                padding: 16px 42px;
                font-size: 16px;
                font-weight: 600;
                min-width: 180px;
                border: none;
                border-bottom: 3px solid transparent;
                margin-right: 0px;
            }
            QTabBar::tab:selected {
                color: white;
                font-weight: 700;
                border-bottom: 3px solid white;
                background: rgba(255, 255, 255, 0.12);
            }
            QTabBar::tab:hover:!selected {
                color: rgba(255, 255, 255, 0.92);
            }
            QLineEdit {
                border: 1px solid #dbe4f0;
                border-radius: 14px;
                padding: 13px 16px;
                background: #f8fafc;
                font-size: 14px;
                min-height: 48px;
                color: #1e293b;
            }
            QLineEdit:focus {
                border: 1px solid #6366f1;
                background: white;
            }
            QLineEdit:hover {
                border: 1px solid #b8c4d4;
            }
            QPushButton {
                border-radius: 14px;
                color: white;
                font-weight: 700;
                padding: 14px;
                font-size: 16px;
                border: none;
                min-height: 50px;
            }
            QPushButton#LoginBtn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #8b5cf6
                );
            }
            QPushButton#LoginBtn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1d4ed8, stop:1 #7c3aed
                );
            }
            QPushButton#LoginBtn:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e40af, stop:1 #6d28d9
                );
            }
            QPushButton#RegBtn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #06b6d4
                );
            }
            QPushButton#RegBtn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #059669, stop:1 #0891b2
                );
            }
            QPushButton#RegBtn:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #047857, stop:1 #0e7490
                );
            }
            QLabel.title {
                color: white;
                font-size: 34px;
                font-weight: 800;
                qproperty-alignment: AlignCenter;
            }
            QLabel.subtitle {
                color: rgba(255, 255, 255, 0.92);
                font-size: 15px;
                qproperty-alignment: AlignCenter;
            }
            QLabel.field {
                color: #475569;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 8px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题区域 - 透明背景
        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(48, 42, 48, 26)
        header_layout.setSpacing(10)
        
        title_label = QLabel("👁️ 眼动训练系统")
        title_label.setProperty("class", "title")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("代码阅读训练 · 实时反馈 · 数据记录")
        subtitle_label.setProperty("class", "subtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_widget)
        
        # 使用 Tab 切换登录和注册
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        
        # --- 登录标签页 ---
        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)
        login_layout.setContentsMargins(44, 34, 44, 34)
        login_layout.setSpacing(10)
        
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
        lbl_user.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 4px;")
        login_layout.addWidget(lbl_user)
        login_layout.addWidget(self.login_user)
        lbl_pass = QLabel("密码")
        lbl_pass.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 4px;")
        login_layout.addWidget(lbl_pass)
        login_layout.addWidget(self.login_pass)
        login_layout.addSpacing(18)
        login_layout.addWidget(login_btn)
        login_layout.addStretch()
        
        # --- 注册标签页 ---
        register_tab = QWidget()
        register_tab.setStyleSheet("background: transparent;")
        register_layout = QVBoxLayout(register_tab)
        register_layout.setContentsMargins(44, 28, 44, 36)
        register_layout.setSpacing(10)
        
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
        register_layout.addSpacing(18)
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
