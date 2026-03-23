@echo off
chcp 65001 >nul
REM 文件上传测试脚本 (Windows)
REM 使用方法: test_upload.bat [文件路径] [IP_ID]

set FILE_PATH=%1
if "%FILE_PATH%"=="" set FILE_PATH=test.txt

set IP_ID=%2
if "%IP_ID%"=="" set IP_ID=test_ip_001

REM 创建测试文件（如果不存在）
if not exist "%FILE_PATH%" (
    echo 创建测试文件: %FILE_PATH%
    echo This is a test file for upload testing. > "%FILE_PATH%"
)

echo ================================
echo 测试文件上传
echo 文件: %FILE_PATH%
for %%I in ("%FILE_PATH%") do echo 大小: %%~zI bytes
echo IP ID: %IP_ID%
echo ================================

echo.
echo 1. 测试文件上传...
curl -X POST ^
  http://localhost:8000/api/v1/memory/upload ^
  -H "Origin: http://localhost:3000" ^
  -F "ip_id=%IP_ID%" ^
  -F "file=@%FILE_PATH%"

echo.
echo ================================
echo 测试完成
echo ================================
pause
