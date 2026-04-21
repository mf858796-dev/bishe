@echo off
cd /d e:\毕设
set PYTHONPATH=e:\毕设\g3pylib\src;%PYTHONPATH%
venv\Scripts\python.exe test_imports.py
pause
