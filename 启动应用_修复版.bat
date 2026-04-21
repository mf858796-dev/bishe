@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   专注力训练系统启动中...
echo ========================================
echo.

REM 设置 OpenBLAS 单线程模式，避免内存分配错误
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
set OMP_NUM_THREADS=1

echo 正在启动应用...
echo.

venv\Scripts\python.exe main.py

pause
