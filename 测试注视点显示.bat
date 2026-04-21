@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   训练模块注视点显示功能测试
echo ========================================
echo.
echo 请选择测试方式:
echo.
echo [1] 使用鼠标模拟注视点（推荐 - 无需眼镜）
echo [2] 完整应用测试（需要连接眼镜）
echo [3] 简单按钮测试
echo.
set /p choice=请输入选项 (1/2/3): 

if "%choice%"=="1" (
    echo.
    echo 启动鼠标模拟测试...
    python test_mouse_gaze.py
) else if "%choice%"=="2" (
    echo.
    echo 启动完整应用...
    python main.py
) else if "%choice%"=="3" (
    echo.
    echo 启动简单按钮测试...
    python test_training_gaze.py
) else (
    echo.
    echo 无效的选项！
    pause
)
