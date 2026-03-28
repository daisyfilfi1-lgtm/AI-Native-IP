"""
检查竞品数据是否正确配置
"""
import asyncio
import asyncpg
import os

async def check():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return
    
    conn = await asyncpg.connect(database_url)
    try:
        # 检查竞品账号
        print("=== 竞品账号 ===")
        accounts = await conn.fetch("SELECT ip_id, competitor_id, name, platform FROM competitor_accounts ORDER BY ip_id")
        for acc in accounts:
            print(f"  IP: {acc['ip_id']} | {acc['name']} ({acc['platform']})")
        
        print(f"\n总计: {len(accounts)} 个竞品账号")
        
        # 检查竞品视频
        print("\n=== 竞品视频 ===")
        videos = await conn.fetch("""
            SELECT cv.video_id, cv.title, cv.author, cv.play_count, cv.platform, ca.ip_id
            FROM competitor_videos cv
            JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
            ORDER BY cv.play_count DESC
            LIMIT 10
        """)
        
        for v in videos:
            print(f"  [{v['ip_id']}] {v['author']}: {v['title'][:30]}... ({v['play_count']} plays)")
        
        print(f"\n总计: {len(videos)} 个视频")
        
        # 检查 xiaomin1 的竞品
        print("\n=== xiaomin1 的竞品 ===")
        xiaomin1_accounts = await conn.fetch(
            "SELECT * FROM competitor_accounts WHERE ip_id = 'xiaomin1'"
        )
        print(f"xiaomin1 有 {len(xiaomin1_accounts)} 个竞品账号")
        
        if xiaomin1_accounts:
            competitor_ids = [a['competitor_id'] for a in xiaomin1_accounts]
            xiaomin1_videos = await conn.fetch(
                "SELECT * FROM competitor_videos WHERE competitor_id = ANY($1) LIMIT 5",
                competitor_ids
            )
            print(f"xiaomin1 有 {len(xiaomin1_videos)} 个视频")
        else:
            print("xiaomin1 没有配置竞品账号！")
            print("\n建议执行: UPDATE competitor_accounts SET ip_id = 'xiaomin1' WHERE ip_id = 'xiaomin'")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
