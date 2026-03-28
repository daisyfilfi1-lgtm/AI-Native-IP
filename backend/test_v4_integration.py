#!/usr/bin/env python3
"""
V4选题推荐系统集成测试

测试内容：
1. 数据库中是否有竞品账号和视频数据
2. V4推荐服务是否正常工作
3. TopicStrategyAgent是否正确调用V4系统
"""

import os
import sys
import asyncio

# 添加backend到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 数据库配置
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/ip_factory"
)

def test_database_data():
    """测试数据库中是否有竞品数据"""
    print("=" * 60)
    print("1. 检查数据库中的竞品数据")
    print("=" * 60)
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # 检查竞品账号
        result = db.execute(text("SELECT COUNT(*) FROM competitor_accounts WHERE ip_id = 'xiaomin'"))
        comp_count = result.scalar()
        print(f"   竞品账号数量: {comp_count}")
        
        if comp_count > 0:
            result = db.execute(text("""
                SELECT competitor_id, name, platform, followers_display 
                FROM competitor_accounts 
                WHERE ip_id = 'xiaomin' 
                LIMIT 5
            """))
            print("   前5个竞品账号:")
            for row in result:
                print(f"     - {row.name} ({row.platform}) - {row.followers_display or 'N/A'}")
        
        # 检查竞品视频
        result = db.execute(text("""
            SELECT COUNT(*), AVG(play_count) 
            FROM competitor_videos cv
            JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
            WHERE ca.ip_id = 'xiaomin'
        """))
        row = result.fetchone()
        video_count = row[0] if row else 0
        avg_plays = row[1] if row and row[1] else 0
        
        print(f"   竞品视频数量: {video_count}")
        print(f"   平均播放量: {int(avg_plays):,}")
        
        if video_count > 0:
            result = db.execute(text("""
                SELECT cv.title, cv.play_count, cv.content_type, ca.name
                FROM competitor_videos cv
                JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
                WHERE ca.ip_id = 'xiaomin'
                ORDER BY cv.play_count DESC
                LIMIT 5
            """))
            print("   播放量TOP5视频:")
            for row in result:
                print(f"     - [{row.content_type}] {row.title[:40]}... ({row.play_count:,} plays) - {row.name}")
        
        return comp_count > 0 and video_count > 0
        
    except Exception as e:
        print(f"   ❌ 查询失败: {e}")
        return False
    finally:
        db.close()


async def test_v4_service():
    """测试V4推荐服务"""
    print("\n" + "=" * 60)
    print("2. 测试V4推荐服务")
    print("=" * 60)
    
    try:
        from app.services.topic_recommendation_v4 import get_recommendation_service_v4
        from app.db.session import SessionLocal
        
        service = get_recommendation_service_v4()
        db = SessionLocal()
        
        try:
            print("   调用 recommend_topics(ip_id='xiaomin', limit=6)...")
            topics = await service.recommend_topics(
                db=db,
                ip_id='xiaomin',
                limit=6,
                strategy='competitor_first'
            )
            
            print(f"   ✅ 返回 {len(topics)} 个选题")
            
            for i, topic in enumerate(topics[:3], 1):
                print(f"\n   [{i}] {topic.title}")
                print(f"       原始标题: {topic.original_title[:50]}...")
                print(f"       是否重构: {topic.is_remixed} (置信度: {topic.remix_confidence:.2f})")
                print(f"       内容类型: {topic.content_type} | 角度: {topic.content_angle}")
                if topic.competitor_author:
                    print(f"       竞品来源: {topic.competitor_author} ({topic.competitor_play_count:,} plays)")
            
            return len(topics) > 0
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"   ❌ V4服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_agent():
    """测试TopicStrategyAgent集成"""
    print("\n" + "=" * 60)
    print("3. 测试TopicStrategyAgent集成")
    print("=" * 60)
    
    try:
        from app.services.content_generation_pipeline import create_strategy_agent
        
        ip_profile = {
            "name": "小敏",
            "expertise": "宝妈创业、私房面食、副业变现",
            "content_direction": "分享在家创业的实战经验",
            "target_audience": "宝妈、想在家赚钱的女性",
            "unique_value_prop": "从0到1的副业启动指南",
        }
        
        print("   创建TopicStrategyAgent...")
        agent = create_strategy_agent("xiaomin", ip_profile)
        
        print("   调用 recommend_topics(count=6)...")
        result = agent.recommend_topics(count=6)
        
        topics = result.get("recommended_topics", [])
        analysis = result.get("analysis", "")
        
        print(f"   ✅ 返回 {len(topics)} 个选题")
        print(f"   分析: {analysis[:100]}...")
        
        for i, topic in enumerate(topics[:3], 1):
            print(f"\n   [{i}] {topic['title']}")
            print(f"       评分: {topic['score']} | 趋势: {topic['trend']}")
            print(f"       爆款元素: {', '.join(topic['viral_elements'])}")
            print(f"       理由: {topic['reason'][:60]}...")
            
            # 检查是否有V4数据
            if '_v4_data' in topic:
                v4 = topic['_v4_data']
                print(f"       [V4] is_remixed={v4.get('is_remixed')}, confidence={v4.get('remix_confidence', 0):.2f}")
        
        return len(topics) > 0
        
    except Exception as e:
        print(f"   ❌ Agent测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "🧪 V4选题推荐系统集成测试".center(60, "="))
    
    # 测试1: 数据库数据
    has_data = test_database_data()
    
    # 测试2: V4服务
    v4_ok = asyncio.run(test_v4_service())
    
    # 测试3: Agent集成
    agent_ok = test_strategy_agent()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"   数据库数据: {'✅ 通过' if has_data else '❌ 失败'}")
    print(f"   V4服务: {'✅ 通过' if v4_ok else '❌ 失败'}")
    print(f"   Agent集成: {'✅ 通过' if agent_ok else '❌ 失败'}")
    
    if has_data and v4_ok and agent_ok:
        print("\n   🎉 所有测试通过！系统工作正常。")
        return 0
    else:
        print("\n   ⚠️ 部分测试失败，请检查配置。")
        if not has_data:
            print("   💡 提示: 运行以下命令初始化竞品数据:")
            print("      psql -d ip_factory -f backend/scripts/setup_competitors_from_analysis.sql")
            print("      psql -d ip_factory -f backend/scripts/seed_competitor_videos.sql")
        return 1


if __name__ == "__main__":
    sys.exit(main())
