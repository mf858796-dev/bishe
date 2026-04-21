"""
最简单的注视点绘制测试
"""
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor

class SimpleGazeWidget(QWidget):
    """简单的注视点显示组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #1e293b;")
        self.test_point = (200, 150)  # 测试点位置
        
    def paintEvent(self, event):
        """绘制测试点"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        x, y = self.test_point
        
        # 绘制外圈（红色）
        pen = QPen(QColor(255, 50, 50))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 50, 50, 100)))
        painter.drawEllipse(QPointF(x, y), 20, 20)
        
        # 绘制内圈（白色）
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(QPointF(x, y), 8, 8)
        
        painter.end()
        print(f"[绘制] 已在 ({x}, {y}) 绘制红色圆点")

def main():
    app = QApplication(sys.argv)
    
    window = QWidget()
    window.setWindowTitle("简单绘制测试")
    window.resize(600, 400)
    
    layout = QVBoxLayout(window)
    
    # 创建测试组件
    gaze_widget = SimpleGazeWidget()
    layout.addWidget(gaze_widget)
    
    # 添加按钮刷新
    btn = QPushButton("刷新绘制")
    btn.clicked.connect(lambda: gaze_widget.update())
    layout.addWidget(btn)
    
    window.show()
    
    print("=" * 60)
    print("简单绘制测试程序")
    print("=" * 60)
    print("如果能看到红色圆点，说明绘制功能正常")
    print("如果看不到，说明是Qt绘制系统的问题")
    print("=" * 60)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
