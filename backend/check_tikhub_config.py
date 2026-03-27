#!/usr/bin/env python3
"""
检查 TIKHUB_API_KEY 配置状态
在 Railway 的 shell 中运行：python check_tikhub_config.py
"""

import os
import sys

print("=" * 60)
print("TIKHUB 配置检查")
print("=" * 60)

# 检查环境变量
api_key = os.environ.get("TIKHUB_API_KEY", "")
base_url = os.environ.get("TIKHUB_BASE_URL", "")

print(f"\n1. TIKHUB_API_KEY:")
print(f"   是否存在: {'✅ 是' if api_key else '❌ 否'}")
print(f"   长度: {len(api_key)} 字符")
print(f"   前10字符: {api_key[:10]}..." if len(api_key) > 10 else f"   值: {api_key}")

print(f"\n2. TIKHUB_BASE_URL:")
print(f"   是否存在: {'✅ 是' if base_url else '❌ 否 (使用默认值)'}")
if base_url:
    print(f"   值: {base_url}")
else:
    print(f"   默认值: https://api.tikhub.io")

# 检查 tikhub_client 是否能正确读取
print(f"\n3. tikhub_client 检查:")
try:
    from app.services import tikhub_client
    is_configured = tikhub_client.is_configured()
    print(f"   is_configured(): {'✅ True' if is_configured else '❌ False'}")
    
    if is_configured:
        print(f"\n4. 测试连接:")
        import asyncio
        async def test_connection():
            try:
                # 尝试获取推荐选题
                cards = await tikhub_client.get_recommended_topic_cards(limit=3)
                print(f"   ✅ 连接成功")
                print(f"   获取到 {len(cards)} 条数据")
                if cards:
                    print(f"   示例: {cards[0].get('title', 'N/A')[:30]}...")
                return True
            except Exception as e:
                print(f"   ❌ 连接失败: {e}")
                return False
        
        result = asyncio.run(test_connection())
    else:
        print(f"\n   跳过连接测试 (未配置)")
        
except Exception as e:
    print(f"   ❌ 导入失败: {e}")

print("\n" + "=" * 60)

# 给出建议
if not api_key:
    print("❌ TIKHUB_API_KEY 未设置")
    print("   请在 Railway Dashboard → Variables 中添加:")
    print('   Name: TIKHUB_API_KEY')
    print('   Value: qJkdBOoQ3w6H3SvWWN+e4QXUJhHSX4Z97SLWqEDbWce+jHeTeFDSbCigDQ==')
elif not is_configured:
    print("⚠️  环境变量存在但 tikhub_client 返回未配置")
    print("   可能原因:")
    print("   1. 服务需要重启才能读取新环境变量")
    print("   2. 环境变量名称大小写不匹配")
    print("   3. 环境变量值包含隐藏字符")
    print("\n   建议操作:")
    print("   → 在 Railway Dashboard 中点击 'Redeploy' 重启服务")
else:
    print("✅ TIKHUB 配置正常")
    if result:
        print("✅ 连接测试通过")
    else:
        print("❌ 连接测试失败，请检查 API Key 是否有效")
