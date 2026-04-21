"""
测试代码是否能正常导入和初始化（不连接硬件）
"""
import sys
import os

# 添加本地 g3pylib 源码到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'g3pylib', 'src'))

# 设置 matplotlib 使用非交互式后端(避免GUI问题)
import matplotlib
matplotlib.use('Agg')

print("=" * 60)
print("测试代码导入和初始化")
print("=" * 60)

# 测试1: 导入所有模块
print("\n[测试1] 导入所有模块...")
try:
    from glasses_manager import GlassesManager
    print("  [OK] glasses_manager 导入成功")
except Exception as e:
    print(f"  [FAIL] glasses_manager 导入失败: {e}")
    sys.exit(1)

try:
    from coordinate_mapper import CoordinateMapper
    print("  [OK] coordinate_mapper 导入成功")
except Exception as e:
    print(f"  [FAIL] coordinate_mapper 导入失败: {e}")
    sys.exit(1)

try:
    from attention_model import AttentionEvaluator
    print("  [OK] attention_model 导入成功")
except Exception as e:
    print(f"  [FAIL] attention_model 导入失败: {e}")
    sys.exit(1)

try:
    from training_widget import TrainingWidget
    print("  [OK] training_widget 导入成功")
except Exception as e:
    print(f"  [FAIL] training_widget 导入失败: {e}")
    sys.exit(1)

try:
    from report_generator import ReportGenerator
    print("  [OK] report_generator 导入成功")
except Exception as e:
    print(f"  [FAIL] report_generator 导入失败: {e}")
    sys.exit(1)

# 测试2: 实例化类（不需要硬件）
print("\n[测试2] 实例化类...")
try:
    mapper = CoordinateMapper()
    print("  [OK] CoordinateMapper 实例化成功")
except Exception as e:
    print(f"  [FAIL] CoordinateMapper 实例化失败: {e}")
    sys.exit(1)

try:
    evaluator = AttentionEvaluator()
    print("  [OK] AttentionEvaluator 实例化成功")
except Exception as e:
    print(f"  [FAIL] AttentionEvaluator 实例化失败: {e}")
    sys.exit(1)

try:
    reporter = ReportGenerator()
    print("  [OK] ReportGenerator 实例化成功")
except Exception as e:
    print(f"  [FAIL] ReportGenerator 实例化失败: {e}")
    sys.exit(1)

# 测试3: 测试专注力评估模型
print("\n[测试3] 测试专注力评估模型...")
try:
    import time
    evaluator.add_gaze_point(100, 200, time.time())
    evaluator.add_gaze_point(105, 205, time.time() + 0.1)
    evaluator.add_gaze_point(110, 210, time.time() + 0.2)
    metrics = evaluator.get_metrics()
    if metrics:
        print(f"  [OK] 评估模型计算成功:")
        print(f"    - 有效注视率: {metrics['effective_fixation_rate']:.2%}")
        print(f"    - 回视次数: {metrics['regression_count']}")
        print(f"    - 视线熵: {metrics['saccade_entropy']:.3f}")
    else:
        print("  [WARN] 需要更多数据点来计算指标")
except Exception as e:
    print(f"  [FAIL] 评估模型测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试4: 测试报告生成
print("\n[测试4] 测试报告生成...")
try:
    import numpy as np
    for i in range(50):
        reporter.add_gaze_point(
            np.random.randint(0, 800),
            np.random.randint(0, 600)
        )
    reporter.generate_heatmap("test_heatmap.png")
    reporter.generate_trajectory("test_trajectory.png")
    
    if os.path.exists("test_heatmap.png") and os.path.exists("test_trajectory.png"):
        print("  [OK] 报告生成成功 (test_heatmap.png, test_trajectory.png)")
    else:
        print("  [FAIL] 报告文件未生成")
        sys.exit(1)
except Exception as e:
    print(f"  [FAIL] 报告生成失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("所有测试通过！代码可以正常运行。")
print("=" * 60)
print("\n注意：要运行完整的主程序 (main_window.py)，你需要：")
print("1. 连接 Tobii Pro Glasses 3 设备")
print("2. 在屏幕四角贴上 ArUco 标记")
print("3. 运行命令: venv\\Scripts\\python.exe main_window.py")
