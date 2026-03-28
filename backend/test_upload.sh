#!/bin/bash
# 文件上传测试脚本
# 使用方法: ./test_upload.sh <file_path>

FILE_PATH=${1:-"test.txt"}
IP_ID=${2:-"test_ip_001"}

# 创建测试文件（如果不存在）
if [ ! -f "$FILE_PATH" ]; then
    echo "创建测试文件: $FILE_PATH"
    echo "This is a test file for upload testing." > "$FILE_PATH"
fi

echo "================================"
echo "测试文件上传"
echo "文件: $FILE_PATH"
echo "大小: $(ls -lh $FILE_PATH | awk '{print $5}')"
echo "IP ID: $IP_ID"
echo "================================"

# 测试上传
echo ""
echo "1. 测试文件上传..."
curl -X POST \
  http://localhost:8000/api/v1/memory/upload \
  -H "Origin: http://localhost:3000" \
  -F "ip_id=$IP_ID" \
  -F "file=@$FILE_PATH" \
  -v 2>&1 | grep -E "(>|HTTP|upload_memory_file|file_id|error)"

echo ""
echo "================================"
echo "测试完成"
echo "================================"
