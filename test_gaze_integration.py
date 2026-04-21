"""
测试眼动仪坐标转换功能
模拟眼动仪数据，验证屏幕坐标到 viewport 坐标的转换
"""
import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.setWindowTitle("眼动仪坐标转换测试")
    window.resize(1400, 900)
    window.show()
    
    print("=" * 70)
    print("🎯 眼动仪坐标转换测试程序")
    print("=" * 70)
    print("\n使用说明:")
    print("  1. 连接到 Tobii 眼动仪（或等待连接）")
    print("  2. 切换到'训练'标签页")
    print("  3. 选择一个训练任务")
    print("  4. 点击'▶️ 开始训练'按钮")
    print("  5. 注视代码区域，观察控制台输出")
    print("\n预期效果:")
    print("  ✓ 控制台会显示屏幕坐标和 viewport 坐标")
    print("  ✓ 红色注视点会在代码区域显示")
    print("  ✓ 有效注视时间会增长")
    print("  ✓ 完成率会提升")
    print("=" * 70)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
