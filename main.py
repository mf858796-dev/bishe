import sys
import os

if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'base_prefix', sys.prefix) != sys.prefix:
    venv_path = sys.prefix
    plugin_path = os.path.join(venv_path, 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from main_window import MainWindow
from login_dialog import LoginDialog
from theme_manager import ThemeManager


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    ThemeManager.apply_theme(app, 'light')

    login_dialog = LoginDialog()
    if login_dialog.exec_() != QDialog.Accepted:
        sys.exit(0)

    window = MainWindow()
    window.set_current_user(login_dialog.user_id, login_dialog.username)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
