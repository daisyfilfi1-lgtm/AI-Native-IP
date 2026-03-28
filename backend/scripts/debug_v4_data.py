"""
调试 V4 推荐数据问题
"""
import asyncio
import asyncpg
import os

async def debug():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return
    
    conn = await asyncpg.connect(database_url)
    try:
        print("=== 调试 V4 数据 ===\n")
        
        # 1. 检查 xiaomin1 的竞品账号
        print("1. xiaomin1 的竞品账号:")
        accounts = await conn.fetch(
            "SELECT competitor_id, name, platform FROM competitor_accounts WHERE ip_id = 'xiaomin1'"
        )
        print(f"   找到 {len(accounts)} 个账号")
        for acc in accounts[:3]:
            print(f"   - {acc['name']} ({acc['competitor_id']})")
        
        # 2. 检查所有竞品视频（不限制时间）
        print("\n2. 所有竞品视频（按播放量排序）:")
        videos = await conn.fetch("""
            SELECT cv.video_id, cv.title, cv.author, cv.play_count, 
                   cv.fetched_at, cv.create_time, ca.name as competitor_name
            FROM competitor_videos cv
            JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
            ORDER BY cv.play_count DESC
            LIMIT 5
        """)
        print(f"   找到 {len(videos)} 个视频")
        for v in videos:
            print(f"   - {v['competitor_name']}: {v['play_count']} plays, fetched_at={v['fetched_at']}, create_time={v['create_time']}")
        
        # 3. 检查时间限制条件
        print("\n3. 检查时间限制（最近7天）:")
        recent_videos = await conn.fetch("""
            SELECT COUNT(*) as count 
            FROM competitor_videos 
            WHERE fetched_at > NOW() - INTERVAL '7 days'
        """)
        print(f"   最近7天的视频: {recent_videos[0]['count']} 个")
        
        # 4. 检查 xiaomin1 的视频（不限制时间）
        print("\n4. xiaomin1 的视频（不限制时间）:")
        xiaomin1_videos = await conn.fetch("""
            SELECT cv.video_id, cv.title, cv.author, cv.play_count, cv.fetched_at
            FROM competitor_videos cv
            JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
            WHERE ca.ip_id = 'xiaomin1'
            ORDER BY cv.play_count DESC
            LIMIT 5
        """)
        print(f"   找到 {len(xiaomin1_videos)} 个视频")
        for v in xiaomin1_videos:
            print(f"   - {v['author']}: {v['play_count']} plays, fetched_at={v['fetched_at']}")
        
        # 5. 检查 xiaomin1 的视频（带时间限制）
        print("\n5. xiaomin1 的视频（最近7天）:")
        xiaomin1_recent = await conn.fetch("""
            SELECT cv.video_id, cv.title, cv.author, cv.play_count
            FROM competitor_videos cv
            JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
            WHERE ca.ip_id = 'xiaomin1'
            AND cv.fetched_at > NOW() - INTERVAL '7 days'
            ORDER BY cv.play_count DESC
            LIMIT 5
        """)
        print(f"   找到 {len(xiaomin1_recent)} 个视频")
        
        if not xiaomin1_recent and xiaomin1_videos:
            print("\n   ⚠️  问题找到：有过期视频但无近期视频！")
            print("   建议：更新视频的 fetched_at 字段")
            print("   SQL: UPDATE competitor_videos SET fetched_at = NOW() WHERE fetched_at < NOW() - INTERVAL '7 days'")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(debug())
