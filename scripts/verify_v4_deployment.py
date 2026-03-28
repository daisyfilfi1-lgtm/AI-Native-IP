#!/usr/bin/env python3
"""
V4部署验证脚本
在Railway容器或本地运行，验证V4系统是否正常工作
"""

import os
import sys
import json
import requests

# 颜色输出
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def check_env():
    """检查环境变量"""
    print("=" * 60)
    print("1. 检查环境变量")
    print("=" * 60)
    
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url:
        # 隐藏密码
        masked = db_url.replace(db_url.split(':')[2].split('@')[0], '****') if '@' in db_url else db_url
        print(f"   DATABASE_URL: {masked}")
    else:
        print(f"   {RED}❌ DATABASE_URL 未设置{RESET}")
        return False
    
    api_key = os.environ.get('TIKHUB_API_KEY', '')
    if api_key:
        print(f"   TIKHUB_API_KEY: {'*' * len(api_key)}")
    else:
        print(f"   {YELLOW}⚠️ TIKHUB_API_KEY 未设置（可选，用于实时抓取）{RESET}")
    
    return True

def check_database():
    """检查数据库数据"""
    print("\n" + "=" * 60)
    print("2. 检查数据库数据")
    print("=" * 60)
    
    try:
        from sqlalchemy import create_engine, text
        
        db_url = os.environ.get('DATABASE_URL')
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # 检查竞品账号
            result = conn.execute(text("SELECT COUNT(*) FROM competitor_accounts WHERE ip_id = 'xiaomin'"))
            comp_count = result.scalar()
            print(f"   竞品账号数量: {comp_count}")
            
            if comp_count == 0:
                print(f"   {RED}❌ 没有竞品账号数据{RESET}")
                return False
            
            # 检查视频
            result = conn.execute(text("""
                SELECT COUNT(*), AVG(play_count) 
                FROM competitor_videos cv
                JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
                WHERE ca.ip_id = 'xiaomin'
            """))
            row = result.fetchone()
            video_count = row[0] if row else 0
            avg_plays = int(row[1]) if row and row[1] else 0
            
            print(f"   竞品视频数量: {video_count}")
            print(f"   平均播放量: {avg_plays:,}")
            
            if video_count == 0:
                print(f"   {RED}❌ 没有竞品视频数据{RESET}")
                return False
            
            # 显示TOP 3
            result = conn.execute(text("""
                SELECT ca.name, cv.title, cv.play_count, cv.content_type
                FROM competitor_videos cv
                JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
                WHERE ca.ip_id = 'xiaomin'
                ORDER BY cv.play_count DESC
                LIMIT 3
            """))
            
            print("\n   TOP 3 爆款视频:")
            for i, row in enumerate(result, 1):
                print(f"   {i}. [{row.content_type}] {row.title[:40]}... ({row.play_count:,} plays) - {row.name}")
        
        return True
        
    except Exception as e:
        print(f"   {RED}❌ 数据库检查失败: {e}{RESET}")
        return False

def check_api():
    """测试API"""
    print("\n" + "=" * 60)
    print("3. 测试API")
    print("=" * 60)
    
    # 确定API地址
    api_base = os.environ.get('API_BASE_URL', 'http://localhost:8000')
    api_url = f"{api_base}/api/v1/content/topics/recommend"
    
    print(f"   API地址: {api_url}")
    
    try:
        response = requests.post(
            api_url,
            json={"ip_id": "xiaomin", "count": 3},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"   {RED}❌ API返回错误: HTTP {response.status_code}{RESET}")
            print(f"   响应: {response.text[:200]}")
            return False
        
        data = response.json()
        recommendations = data.get('recommendations', [])
        
        print(f"   返回选题数量: {len(recommendations)}")
        
        if not recommendations:
            print(f"   {RED}❌ 没有返回选题{RESET}")
            return False
        
        # 检查V4数据
        v4_count = sum(1 for r in recommendations if r.get('_v4_data'))
        print(f"   包含V4数据的选题: {v4_count}/{len(recommendations)}")
        
        # 显示第一个选题详情
        if recommendations:
            first = recommendations[0]
            print("\n   第一个选题详情:")
            print(f"   - 标题: {first.get('title', 'N/A')}")
            print(f"   - 评分: {first.get('score', 'N/A')}")
            print(f"   - 理由: {first.get('reason', 'N/A')[:80]}...")
            
            v4_data = first.get('_v4_data')
            if v4_data:
                print(f"   {GREEN}   ✅ 是V4选题{RESET}")
                print(f"   - 原始标题: {v4_data.get('original_title', 'N/A')[:50]}...")
                print(f"   - 是否重构: {v4_data.get('is_remixed', False)}")
                print(f"   - 重构置信度: {v4_data.get('remix_confidence', 0):.2f}")
                print(f"   - 竞品来源: {v4_data.get('competitor_author', 'N/A')}")
                print(f"   - 竞品播放: {v4_data.get('competitor_play_count', 0):,}")
            else:
                print(f"   {YELLOW}   ⚠️ 不是V4选题（LLM生成）{RESET}")
        
        return v4_count > 0
        
    except Exception as e:
        print(f"   {RED}❌ API测试失败: {e}{RESET}")
        return False

def main():
    print("\n" + "=" * 60)
    print("V4选题推荐系统部署验证")
    print("=" * 60)
    
    results = []
    
    # 检查环境
    results.append(("环境变量", check_env()))
    
    # 检查数据库
    results.append(("数据库数据", check_database()))
    
    # 检查API
    results.append(("API测试", check_api()))
    
    # 汇总
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = f"{GREEN}✅ 通过{RESET}" if result else f"{RED}❌ 失败{RESET}"
        print(f"   {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print(f"\n{GREEN}🎉 所有验证通过！V4系统工作正常。{RESET}")
        return 0
    else:
        print(f"\n{YELLOW}⚠️ 部分验证失败，请检查上述错误。{RESET}")
        print("\n修复建议:")
        print("   1. 如果数据库检查失败，请运行: bash scripts/deploy_v4_to_railway.sh")
        print("   2. 如果API测试失败，请检查后端日志")
        return 1

if __name__ == "__main__":
    sys.exit(main())
