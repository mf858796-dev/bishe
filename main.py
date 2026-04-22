import sys
import os

# 设置 Qt 平台插件路径
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'base_prefix', sys.prefix) != sys.prefix:
    venv_path = sys.prefix
    plugin_path = os.path.join(venv_path, 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

from PyQt5.QtWidgets import QApplication, QDialog
from main_window import MainWindow
from login_dialog import LoginDialog

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用 Fusion 风格,跨平台一致
    
    # 1. 显示登录对话框
    login_dialog = LoginDialog()
    if login_dialog.exec_() != QDialog.Accepted:
        sys.exit(0) # 如果用户关闭登录框，则退出程序
    
    # 2. 启动主窗口并传入用户信息
    window = MainWindow()
    window.set_current_user(login_dialog.user_id, login_dialog.username)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
