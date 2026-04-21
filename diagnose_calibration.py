"""
校准数据诊断脚本
分析校准采样数据，检查透视投影模型和多项式拟合的问题
"""
import numpy as np

# 从日志中提取的校准数据（前10个点）
calibration_data = [
    {'screen_u': 0.10, 'screen_v': 0.10, 'gaze_u': 0.2956, 'gaze_v': 0.3217},
    {'screen_u': 0.25, 'screen_v': 0.10, 'gaze_u': 0.3737, 'gaze_v': 0.3110},
    {'screen_u': 0.40, 'screen_v': 0.10, 'gaze_u': 0.4256, 'gaze_v': 0.3126},
    {'screen_u': 0.50, 'screen_v': 0.10, 'gaze_u': 0.4628, 'gaze_v': 0.3176},
    {'screen_u': 0.60, 'screen_v': 0.10, 'gaze_u': 0.4943, 'gaze_v': 0.3211},
    {'screen_u': 0.75, 'screen_v': 0.10, 'gaze_u': 0.5523, 'gaze_v': 0.3125},
    {'screen_u': 0.90, 'screen_v': 0.10, 'gaze_u': 0.6003, 'gaze_v': 0.3098},
]

print("=" * 80)
print("校准数据诊断分析")
print("=" * 80)

# 1. 分析gaze2d数据的范围
gaze_u_values = [p['gaze_u'] for p in calibration_data]
gaze_v_values = [p['gaze_v'] for p in calibration_data]
screen_u_values = [p['screen_u'] for p in calibration_data]
screen_v_values = [p['screen_v'] for p in calibration_data]

print("\n【1】数据范围统计")
print(f"gaze_u 范围: [{min(gaze_u_values):.4f}, {max(gaze_u_values):.4f}], 跨度={max(gaze_u_values)-min(gaze_u_values):.4f}")
print(f"gaze_v 范围: [{min(gaze_v_values):.4f}, {max(gaze_v_values):.4f}], 跨度={max(gaze_v_values)-min(gaze_v_values):.4f}")
print(f"screen_u 范围: [{min(screen_u_values):.4f}, {max(screen_u_values):.4f}], 跨度={max(screen_u_values)-min(screen_u_values):.4f}")
print(f"screen_v 范围: [{min(screen_v_values):.4f}, {max(screen_v_values):.4f}], 跨度={max(screen_v_values)-min(screen_v_values):.4f}")

# 2. 计算线性映射参数（最小二乘法）
print("\n【2】线性映射分析（screen = a * gaze + b）")

# U方向
A_u = np.vstack([gaze_u_values, np.ones(len(gaze_u_values))]).T
coeffs_u = np.linalg.lstsq(A_u, screen_u_values, rcond=None)[0]
a_u, b_u = coeffs_u
print(f"U方向: screen_u = {a_u:.4f} * gaze_u + ({b_u:.4f})")

# V方向
A_v = np.vstack([gaze_v_values, np.ones(len(gaze_v_values))]).T
coeffs_v = np.linalg.lstsq(A_v, screen_v_values, rcond=None)[0]
a_v, b_v = coeffs_v
print(f"V方向: screen_v = {a_v:.4f} * gaze_v + ({b_v:.4f})")

# 3. 验证透视投影模型参数
print("\n【3】当前透视投影模型参数验证")
center_u = 0.45
center_v = 0.42
scale_factor_u = 2.8
scale_factor_v = 3.5

print(f"中心点: (u={center_u}, v={center_v})")
print(f"缩放因子: U={scale_factor_u}, V={scale_factor_v}")

# 测试几个点
print("\n透视投影模型测试结果:")
for i, point in enumerate(calibration_data[:3]):
    u = point['gaze_u']
    v = point['gaze_v']
    
    offset_u = (u - center_u) * scale_factor_u
    offset_v = (v - center_v) * scale_factor_v
    
    pred_screen_u = 0.5 + offset_u
    pred_screen_v = 0.5 + offset_v
    
    actual_screen_u = point['screen_u']
    actual_screen_v = point['screen_v']
    
    error_u = abs(pred_screen_u - actual_screen_u)
    error_v = abs(pred_screen_v - actual_screen_v)
    
    print(f"  点{i+1}: gaze({u:.4f}, {v:.4f})")
    print(f"    预测屏幕: ({pred_screen_u:.4f}, {pred_screen_v:.4f})")
    print(f"    实际屏幕: ({actual_screen_u:.4f}, {actual_screen_v:.4f})")
    print(f"    误差: ({error_u:.4f}, {error_v:.4f})")

# 4. 建议的参数调整
print("\n【4】建议的透视投影参数调整")

# 根据线性映射结果反推透视投影参数
# screen = 0.5 + (gaze - center) * scale
# => scale = a (线性斜率)
# => center = 0.5 - b/scale

recommended_scale_u = a_u
recommended_center_u = 0.5 - b_u / a_u

recommended_scale_v = a_v
recommended_center_v = 0.5 - b_v / a_v

print(f"基于线性拟合的建议参数:")
print(f"  U方向: center={recommended_center_u:.4f}, scale={recommended_scale_u:.4f}")
print(f"  V方向: center={recommended_center_v:.4f}, scale={recommended_scale_v:.4f}")

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)
