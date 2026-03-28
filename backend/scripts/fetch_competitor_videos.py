#!/usr/bin/env python3
"""
抓取竞品账号视频数据

用法:
    python fetch_competitor_videos.py --ip-id xiaomin
    python fetch_competitor_videos.py --ip-id xiaomin --limit 20
    python fetch_competitor_videos.py --competitor-id comp_xiaomin_002

环境变量:
    TIKHUB_API_KEY: TIKHUB API密钥（用于实时抓取）
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 数据库配置（从环境变量或配置文件读取）
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/ip_factory"
)


class CompetitorVideoFetcher:
    """竞品视频抓取器"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.tikhub_key = os.environ.get("TIKHUB_API_KEY", "")
    
    async def fetch_for_ip(self, ip_id: str, limit_per_competitor: int = 10):
        """为指定IP抓取所有竞品账号的视频"""
        # 获取竞品账号列表
        competitors = self._get_competitors(ip_id)
        if not competitors:
            print(f"❌ 未找到IP '{ip_id}' 的竞品账号配置")
            return
        
        print(f"📋 找到 {len(competitors)} 个竞品账号")
        
        for comp in competitors:
            print(f"\n🎯 正在抓取: {comp['name']} ({comp['platform']})")
            videos = await self._fetch_videos(comp, limit_per_competitor)
            if videos:
                saved = self._save_videos(comp['competitor_id'], videos)
                print(f"   ✅ 保存 {saved} 条视频")
            else:
                print(f"   ⚠️ 未获取到视频")
    
    def _get_competitors(self, ip_id: str) -> List[Dict[str, Any]]:
        """从数据库获取竞品账号"""
        result = self.db.execute(
            text("""
                SELECT competitor_id, name, platform, external_id, notes
                FROM competitor_accounts
                WHERE ip_id = :ip_id
                ORDER BY competitor_id
            """),
            {"ip_id": ip_id}
        )
        return [dict(row._mapping) for row in result]
    
    async def _fetch_videos(self, competitor: Dict, limit: int) -> List[Dict]:
        """抓取单个竞品账号的视频"""
        platform = competitor.get("platform", "douyin")
        external_id = competitor.get("external_id", "")
        
        if platform == "douyin" and external_id:
            return await self._fetch_douyin_videos(external_id, limit)
        
        return []
    
    async def _fetch_douyin_videos(self, sec_uid: str, limit: int) -> List[Dict]:
        """使用TIKHUB API抓取抖音视频"""
        if not self.tikhub_key:
            print(f"   ⚠️ 未配置TIKHUB_API_KEY，跳过API抓取")
            return []
        
        try:
            import httpx
            
            url = "https://api.tikhub.io/api/v1/douyin/app/v3/fetch_user_post_videos"
            headers = {"Authorization": f"Bearer {self.tikhub_key}"}
            params = {
                "sec_user_id": sec_uid,
                "count": limit * 2,  # 多取一些用于筛选
                "max_cursor": 0
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=headers, params=params)
                
                if resp.status_code != 200:
                    print(f"   ❌ API请求失败: HTTP {resp.status_code}")
                    return []
                
                data = resp.json()
                if data.get("code") != 200:
                    print(f"   ❌ API错误: {data.get('message')}")
                    return []
                
                videos_data = data.get("data", {}).get("aweme_list", [])
                
                # 解析视频数据
                videos = []
                for v in videos_data[:limit]:
                    stats = v.get("statistics", {})
                    create_time = v.get("create_time", 0)
                    
                    video = {
                        "video_id": str(v.get("aweme_id", "")),
                        "title": v.get("desc", "")[:200],
                        "desc": v.get("desc", ""),
                        "author": v.get("author", {}).get("nickname", ""),
                        "platform": "douyin",
                        "play_count": stats.get("play_count", 0),
                        "like_count": stats.get("digg_count", 0),
                        "comment_count": stats.get("comment_count", 0),
                        "share_count": stats.get("share_count", 0),
                        "create_time": datetime.fromtimestamp(create_time) if create_time else None,
                        "tags": self._extract_tags(v.get("desc", "")),
                    }
                    videos.append(video)
                
                return videos
                
        except Exception as e:
            print(f"   ❌ 抓取失败: {e}")
            return []
    
    def _extract_tags(self, desc: str) -> List[str]:
        """从描述中提取标签"""
        import re
        tags = re.findall(r'#([^#\s]+)', desc)
        return tags[:10]
    
    def _save_videos(self, competitor_id: str, videos: List[Dict]) -> int:
        """保存视频到数据库"""
        saved_count = 0
        
        for video in videos:
            try:
                # 检查是否已存在
                result = self.db.execute(
                    text("""
                        SELECT 1 FROM competitor_videos 
                        WHERE video_id = :video_id AND competitor_id = :competitor_id
                    """),
                    {"video_id": video["video_id"], "competitor_id": competitor_id}
                )
                
                if result.fetchone():
                    # 更新数据
                    self.db.execute(
                        text("""
                            UPDATE competitor_videos SET
                                play_count = :play_count,
                                like_count = :like_count,
                                comment_count = :comment_count,
                                share_count = :share_count,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE video_id = :video_id AND competitor_id = :competitor_id
                        """),
                        {**video, "competitor_id": competitor_id}
                    )
                else:
                    # 插入新数据
                    self.db.execute(
                        text("""
                            INSERT INTO competitor_videos (
                                video_id, competitor_id, title, desc, author, platform,
                                play_count, like_count, comment_count, share_count, tags, create_time
                            ) VALUES (
                                :video_id, :competitor_id, :title, :desc, :author, :platform,
                                :play_count, :like_count, :comment_count, :share_count, :tags, :create_time
                            )
                        """),
                        {**video, "competitor_id": competitor_id, "tags": video["tags"]}
                    )
                
                saved_count += 1
                
            except Exception as e:
                print(f"   ⚠️ 保存视频失败 {video.get('video_id', '')}: {e}")
                continue
        
        self.db.commit()
        return saved_count


def main():
    parser = argparse.ArgumentParser(description='抓取竞品账号视频')
    parser.add_argument('--ip-id', required=True, help='IP ID (如: xiaomin)')
    parser.add_argument('--limit', type=int, default=10, help='每个竞品抓取视频数量')
    parser.add_argument('--competitor-id', help='指定单个竞品ID')
    
    args = parser.parse_args()
    
    # 创建数据库连接
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        fetcher = CompetitorVideoFetcher(db)
        
        if args.competitor_id:
            # 抓取单个竞品
            pass  # TODO: 实现单个竞品抓取
        else:
            # 抓取IP的所有竞品
            asyncio.run(fetcher.fetch_for_ip(args.ip_id, args.limit))
        
        print("\n✅ 抓取完成")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
