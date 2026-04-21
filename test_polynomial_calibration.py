"""
测试多项式校准算法
"""
import numpy as np

def test_polynomial_calibration():
    """测试二次多项式校准算法"""
    
    # 模拟25个校准点（5x5网格）
    positions = [0.1, 0.3, 0.5, 0.7, 0.9]
    calibration_points = []
    
    # 生成理想的校准数据（无噪声）
    for v in positions:
        for u in positions:
            # 添加一些非线性畸变来模拟真实情况
            distorted_u = u + 0.02 * (u - 0.5)**2 + 0.01 * (v - 0.5)
            distorted_v = v + 0.015 * (v - 0.5)**2 + 0.01 * (u - 0.5)
            
            calibration_points.append({
                'screen_u': u,
                'screen_v': v,
                'gaze_u': distorted_u,
                'gaze_v': distorted_v
            })
    
    print(f"生成了 {len(calibration_points)} 个校准点")
    
    # 构建特征矩阵
    n = len(calibration_points)
    X = np.zeros((n, 6))
    Y_u = np.zeros(n)
    Y_v = np.zeros(n)
    
    for i, point in enumerate(calibration_points):
        u = point['gaze_u']
        v = point['gaze_v']
        X[i, 0] = 1.0      # 常数项
        X[i, 1] = u        # u
        X[i, 2] = v        # v
        X[i, 3] = u * u    # u²
        X[i, 4] = u * v    # u*v
        X[i, 5] = v * v    # v²
        Y_u[i] = point['screen_u']
        Y_v[i] = point['screen_v']
    
    # 使用最小二乘法求解
    coeffs_u, residuals_u, rank_u, _ = np.linalg.lstsq(X, Y_u, rcond=None)
    coeffs_v, residuals_v, rank_v, _ = np.linalg.lstsq(X, Y_v, rcond=None)
    
    print(f"\nU方向系数: {coeffs_u}")
    print(f"V方向系数: {coeffs_v}")
    print(f"U方向残差: {residuals_u[0]:.8f}")
    print(f"V方向残差: {residuals_v[0]:.8f}")
    print(f"矩阵秩: U={rank_u}, V={rank_v}")
    
    # 验证拟合效果
    print("\n=== 验证拟合效果 ===")
    errors = []
    for i, point in enumerate(calibration_points):
        u = point['gaze_u']
        v = point['gaze_v']
        
        # 预测屏幕坐标
        pred_u = sum(coeffs_u[j] * X[i, j] for j in range(6))
        pred_v = sum(coeffs_v[j] * X[i, j] for j in range(6))
        
        # 计算误差
        error_u = abs(pred_u - point['screen_u'])
        error_v = abs(pred_v - point['screen_v'])
        error = np.sqrt(error_u**2 + error_v**2)
        errors.append(error)
        
        if i < 5:  # 只打印前5个点
            print(f"点{i+1}: 目标({point['screen_u']:.3f}, {point['screen_v']:.3f}), "
                  f"预测({pred_u:.4f}, {pred_v:.4f}), 误差={error:.6f}")
    
    errors = np.array(errors)
    print(f"\n平均误差: {np.mean(errors):.6f} ({np.mean(errors)*100:.4f}%)")
    print(f"最大误差: {np.max(errors):.6f} ({np.max(errors)*100:.4f}%)")
    print(f"标准差:   {np.std(errors):.6f} ({np.std(errors)*100:.4f}%)")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("测试多项式校准算法")
    print("=" * 60)
    test_polynomial_calibration()
    print("\n✅ 测试完成！")
