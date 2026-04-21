"""
依赖检查脚本 - 检查所有必需的库是否已安装
"""
import sys

print(f"Python 版本: {sys.version}")
print(f"Python 路径: {sys.executable}")
print("\n正在检查依赖库...")

required_packages = {
    'PyQt5': 'pyqt5',
    'cv2': 'opencv-python',
    'numpy': 'numpy',
    'g3pylib': 'g3pylib',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
}

missing = []
installed = []

for module_name, package_name in required_packages.items():
    try:
        __import__(module_name)
        installed.append(package_name)
        print(f"[OK] {package_name} 已安装")
    except ImportError:
        missing.append(package_name)
        print(f"[MISSING] {package_name} 未安装")

print("\n" + "="*50)
if missing:
    print(f"缺少的依赖库: {', '.join(missing)}")
    print("\n请运行以下命令安装:")
    print(f"pip install {' '.join(missing)}")
else:
    print("所有依赖库已安装！")
