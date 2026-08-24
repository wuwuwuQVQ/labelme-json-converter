@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m labelme_json_converter
  exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
  python -m labelme_json_converter
  exit /b %errorlevel%
)

echo 未找到 Python 3，请安装 Python 3.9 或更高版本。
pause
exit /b 1

