"""
测试训练模块的注视点显示功能
"""
import sys
from PyQt5.QtWidgets import QApplication
from training_widget import TrainingWidget

def test_training_widget():
    app = QApplication(sys.argv)
    
    # 创建训练组件
    widget = TrainingWidget()
    widget.setWindowTitle("训练模块测试 - 注视点显示")
    widget.resize(1200, 800)
    widget.show()
    
    print("=" * 60)
    print("训练模块测试程序已启动")
    print("=" * 60)
    print("\n测试步骤:")
    print("1. 点击'开始训练'按钮")
    print("2. 在代码区域移动鼠标（模拟注视点）")
    print("3. 观察是否显示红色注视点")
    print("4. 查看控制台输出的调试信息")
    print("=" * 60)
    
    # 模拟鼠标移动事件来测试注视点显示
    def simulate_gaze(x, y):
        """模拟注视点数据"""
        if widget.is_training:
            import time
            dt = 0.016  # 约60fps
            widget.check_gaze(x, y, dt)
    
    # 添加一个测试按钮
    from PyQt5.QtWidgets import QPushButton
    test_btn = QPushButton("测试注视点 (500, 300)")
    test_btn.clicked.connect(lambda: simulate_gaze(500, 300))
    widget.layout().addWidget(test_btn)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    test_training_widget()
