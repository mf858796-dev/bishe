"""
全局主题管理器 - Material Design 风格
支持：浅色主题、深色主题、护眼模式
使用 QSS + QPalette 实现全局样式统一
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

class ThemeManager:
    """全局主题管理器"""
    
    THEMES = {
        'light': {
            'name': '浅色主题',
            'primary': '#6366f1',
            'primary_hover': '#4f46e5',
            'secondary': '#8b5cf6',
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444',
            'background': '#f8fafc',
            'surface': '#ffffff',
            'surface_alt': '#f1f5f9',
            'text_primary': '#0f172a',
            'text_secondary': '#64748b',
            'border': '#e2e8f0',
            'border_strong': '#cbd5e1',
            'hover': '#f1f5f9',
            'pressed': '#e2e8f0',
        },
        'dark': {
            'name': '深色主题',
            'primary': '#4f8cff',
            'primary_hover': '#3d7cf0',
            'secondary': '#4f8cff',
            'success': '#22c55e',
            'warning': '#f59e0b',
            'danger': '#ef4444',
            'background': '#1e1e1e',
            'surface': '#252526',
            'surface_alt': '#2d2d30',
            'text_primary': '#f3f4f6',
            'text_secondary': '#d1d5db',
            'border': '#3f3f46',
            'border_strong': '#52525b',
            'hover': '#323236',
            'pressed': '#3a3a3f',
        },
        'eye': {
            'name': '护眼模式',
            'primary': '#059669',
            'primary_hover': '#047857',
            'secondary': '#10b981',
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444',
            'background': '#f0fdf4',
            'surface': '#ffffff',
            'surface_alt': '#ecfdf5',
            'text_primary': '#1f2937',
            'text_secondary': '#6b7280',
            'border': '#a7f3d0',
            'border_strong': '#6ee7b7',
            'hover': '#ecfdf5',
            'pressed': '#d1fae5',
        }
    }
    
    @staticmethod
    def apply_theme(app, theme_name='light'):
        if theme_name not in ThemeManager.THEMES:
            theme_name = 'light'
        
        theme = ThemeManager.THEMES[theme_name]
        ThemeManager._apply_palette(app, theme)
        qss = ThemeManager._generate_qss(theme_name, theme)
        app.setStyleSheet(qss)
        
        font = app.font()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(10)
        app.setFont(font)
        
        return theme
    
    @staticmethod
    def _apply_palette(app, theme):
        palette = QPalette()
        
        bg_color = QColor(theme['background'])
        surface_color = QColor(theme['surface'])
        text_primary = QColor(theme['text_primary'])
        text_secondary = QColor(theme['text_secondary'])
        primary_color = QColor(theme['primary'])
        
        palette.setColor(QPalette.Window, bg_color)
        palette.setColor(QPalette.WindowText, text_primary)
        palette.setColor(QPalette.Base, surface_color)
        palette.setColor(QPalette.AlternateBase, QColor(theme['surface_alt']))
        palette.setColor(QPalette.Text, text_primary)
        palette.setColor(QPalette.Button, surface_color)
        palette.setColor(QPalette.ButtonText, text_primary)
        palette.setColor(QPalette.ToolTipBase, surface_color)
        palette.setColor(QPalette.ToolTipText, text_primary)
        palette.setColor(QPalette.Highlight, primary_color)
        palette.setColor(QPalette.HighlightedText, QColor('#ffffff'))
        palette.setColor(QPalette.Link, primary_color)
        palette.setColor(QPalette.PlaceholderText, text_secondary)
        
        app.setPalette(palette)

    @staticmethod
    def _generate_qss(theme_name, theme):
        button_background = theme['primary'] if theme_name == 'dark' else f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary']}, stop:1 {theme['secondary']})"
        button_hover = theme['primary_hover'] if theme_name == 'dark' else f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme['primary_hover']}, stop:1 {theme['primary']})"

        return f"""
        * {{
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            selection-background-color: {theme['primary']};
            selection-color: white;
            outline: none;
        }}
        
        QMainWindow, QDialog {{
            background-color: {theme['background']};
        }}
        
        QWidget {{
            background-color: {theme['surface']};
            color: {theme['text_primary']};
        }}
        
        QLabel {{
            color: {theme['text_primary']};
            background: transparent;
        }}
        
        QPushButton {{
            background: {button_background};
            color: #ffffff;
            border: 1px solid {theme['primary']};
            border-radius: 10px;
            padding: 8px 18px;
            font-size: 14px;
            font-weight: 600;
            min-height: 34px;
        }}
        
        QPushButton:hover {{
            background: {button_hover};
            border: 1px solid {theme['primary_hover']};
        }}
        
        QPushButton:pressed {{
            background: {theme['pressed']};
            border: 1px solid {theme['primary_hover']};
        }}
        
        QPushButton:disabled {{
            background: {theme['surface_alt']};
            color: {theme['text_secondary']};
            border: 1px solid {theme['border']};
        }}
        
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {theme['surface_alt']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border_strong']};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {theme['primary']};
            background-color: {theme['surface_alt']};
        }}
        
        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
            border: 1px solid {theme['text_secondary']};
        }}
        
        QComboBox, QSpinBox {{
            background-color: {theme['surface_alt']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border_strong']};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
            min-height: 34px;
        }}
        
        QComboBox:focus, QSpinBox:focus {{
            border: 1px solid {theme['primary']};
        }}
        
        QComboBox:hover, QSpinBox:hover {{
            border: 1px solid {theme['text_secondary']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 28px;
            background: transparent;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border: 2px solid {theme['text_secondary']};
            border-top: none;
            border-left: none;
            width: 7px;
            height: 7px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme['surface']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border_strong']};
            selection-background-color: {theme['primary']};
            selection-color: white;
        }}
        
        QGroupBox {{
            font-weight: 700;
            font-size: 15px;
            color: {theme['text_primary']};
            border: 1px solid {theme['border_strong']};
            border-radius: 12px;
            margin-top: 14px;
            padding: 18px 14px 14px 14px;
            background-color: {theme['surface']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            color: {theme['text_primary']};
            background-color: {theme['surface']};
        }}
        
        QTabWidget::pane {{
            border: none;
            background-color: {theme['surface']};
        }}
        
        QTabBar::tab {{
            background-color: {theme['surface_alt']};
            color: {theme['text_primary']};
            padding: 10px 20px;
            margin-right: 4px;
            border-radius: 8px;
            border: 1px solid {theme['border']};
            min-width: 108px;
            font-weight: 600;
        }}
        
        QTabBar::tab:selected {{
            background-color: {theme['primary']};
            color: #ffffff;
            border: 1px solid {theme['primary']};
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {theme['hover']};
            color: {theme['text_primary']};
        }}
        
        QScrollArea {{
            border: none;
            background-color: {theme['surface']};
        }}
        
        QScrollBar:vertical {{
            background-color: {theme['surface']};
            width: 12px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {theme['border_strong']};
            border-radius: 6px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {theme['text_secondary']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            height: 0;
            background: none;
        }}
        
        QTableWidget {{
            background-color: {theme['surface']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border_strong']};
            border-radius: 10px;
            gridline-color: {theme['border']};
            alternate-background-color: {theme['surface_alt']};
        }}
        
        QTableWidget::item {{
            padding: 8px;
            border: none;
        }}
        
        QTableWidget::item:selected {{
            background-color: {theme['primary']};
            color: white;
        }}
        
        QHeaderView::section {{
            background-color: {theme['surface_alt']};
            color: {theme['text_primary']};
            padding: 10px;
            border: none;
            border-bottom: 1px solid {theme['border_strong']};
            font-weight: 700;
        }}
        
        QCheckBox, QRadioButton {{
            color: {theme['text_primary']};
            spacing: 8px;
            background: transparent;
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
        }}
        
        QStatusBar {{
            background-color: {theme['surface']};
            color: {theme['text_primary']};
            border-top: 1px solid {theme['border']};
        }}
        
        QMenuBar {{
            background-color: {theme['surface']};
            color: {theme['text_primary']};
            border-bottom: 1px solid {theme['border']};
        }}
        
        QMenuBar::item {{
            background: transparent;
            padding: 8px 12px;
            border-radius: 6px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme['hover']};
        }}
        
        QMenu {{
            background-color: {theme['surface']};
            color: {theme['text_primary']};
            border: 1px solid {theme['border_strong']};
            padding: 6px;
        }}
        
        QMenu::item {{
            padding: 8px 14px;
            border-radius: 6px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme['hover']};
        }}
        """
