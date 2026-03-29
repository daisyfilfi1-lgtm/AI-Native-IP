"""
竞品数据同步服务

将TIKHub抓取的竞品视频数据存入数据库
并按四维权重排序供前端展示
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from psycopg2.extras import Json
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.competitor_client import CompetitorClient
from app.services.smart_ip_matcher import get_smart_matcher

logger = logging.getLogger(__name__)

# 与 db/migrations/014_competitor_system.sql 中 competitor_id 一致（17 个竞品账号）
COMPETITORS_DEFAULT: List[Dict[str, str]] = [
    {"competitor_id": "comp_xiaomin_001", "sec_uid": "MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA", "name": "淘淘子"},
    {"competitor_id": "comp_xiaomin_002", "sec_uid": "MS4wLjABAAAATeQUszhzY6JjMfJy1Gya6ao5gGD66Gg1I_9vcJC-y9dfNHKtcXaQ-Mu0K1SPy8EK", "name": "顶妈私房早餐"},
    {"competitor_id": "comp_xiaomin_003", "sec_uid": "MS4wLjABAAAA3XsMOiah1EsT6TSzoqMjlgH4GdMhoBCLwunPVyUP34y-EbUgIV04OU2dnpImMfHq", "name": "深圳蓝蒂蔻Gina"},
    {"competitor_id": "comp_xiaomin_004", "sec_uid": "MS4wLjABAAAAErFzzalv2271brW_cK7vbdLX67B8zOw2ReVYJ72GyoPu2AbZnT3QYNpq4uyxePWr", "name": "梁宸瑜·无价之姐"},
    {"competitor_id": "comp_xiaomin_005", "sec_uid": "MS4wLjABAAAAWwcXLQaOlIV4k04tSI4xYaYmCzRZt1a9_IDDutj7Wzra_yNzBUDrPQgV8UVJ_dsH", "name": "Olga姐姐"},
    {"competitor_id": "comp_xiaomin_006", "sec_uid": "MS4wLjABAAAAfmygSsGTU3RIctsoi4vcbWkAQaMRi_KwtQh1bP7WCzf1k0yydcLtKQj7kE-FSwsJ", "name": "张琦老师-商业连锁"},
    {"competitor_id": "comp_xiaomin_007", "sec_uid": "MS4wLjABAAAAHu4SbvaUZQ1GN2WgySRB6G4nmvUvWxD2fNLzvDKOkOAmqxZkQ5fJtx0ZhANSST7V", "name": "崔璀优势星球"},
    {"competitor_id": "comp_xiaomin_008", "sec_uid": "MS4wLjABAAAAbDuwvhxdzfp009rDpY1mj4NmPu_A_Txsi9SP6Ybz3Bk", "name": "王潇_潇洒姐"},
    {"competitor_id": "comp_xiaomin_009", "sec_uid": "MS4wLjABAAAAvrhmrhhYvc4eJvqu_0MStkyBihmGdJZCBl_JVZ0AulE", "name": "张萌萌姐"},
    {"competitor_id": "comp_xiaomin_010", "sec_uid": "MS4wLjABAAAAV5oVsV-RjxHKrcCuqQotWtHvT8_Y7z_aQnTvT61slic", "name": "清华陈晶聊商业"},
    {"competitor_id": "comp_xiaomin_011", "sec_uid": "MS4wLjABAAAAnTsmfVQNtopff5MrXYMf9y2oVrZ9usIHaCOb_6T1mVo", "name": "Dada人物圈"},
    {"competitor_id": "comp_xiaomin_012", "sec_uid": "MS4wLjABAAAA7hiENPfyARPotUS0FootY0s1Qg51l4X3gvkXEKYUHas", "name": "赵三观"},
    {"competitor_id": "comp_xiaomin_013", "sec_uid": "MS4wLjABAAAAoGgpFqfuSXAjeMy21Qk8Pn1NvaSukBN7vCipz3xsPOU", "name": "程前Jason"},
    {"competitor_id": "comp_xiaomin_014", "sec_uid": "MS4wLjABAAAAO_KKPhlqsPDzmTIxBFSFUX5Hjuj8Y94gHQpJgqHlub0", "name": "群响刘思毅"},
    {"competitor_id": "comp_xiaomin_015", "sec_uid": "MS4wLjABAAAAZXgVjvDmWo_ipGRJnXwFREdhkG29krGiVSwIQhzIrDA", "name": "透透糖"},
    {"competitor_id": "comp_xiaomin_016", "sec_uid": "MS4wLjABAAAAHAlF09yQrLMxW8wyJUO0NGlrsE7O0_9yTki_BkZM16g", "name": "房琪kiki"},
    {"competitor_id": "comp_xiaomin_017", "sec_uid": "MS4wLjABAAAAB1lxLcDT1n51dY3jyB-VQACgN0gbYWGxvSdiE0DWYLY", "name": "杨天真"},
]


@dataclass
class FourDimScore:
    """四维评分"""
    relevance: float  # 相关度 0-1
    hotness: float    # 热度 0-1
    competition: float  # 竞争度 0-1（越低越好）
    conversion: float   # 转化率 0-1
    
    def weighted_total(self, weights: Dict[str, float]) -> float:
        """计算加权总分"""
        return (
            self.relevance * weights.get("relevance", 0.3) +
            self.hotness * weights.get("hotness", 0.3) +
            (1 - self.competition) * weights.get("competition", 0.2) +  # 竞争度越低越好
            self.conversion * weights.get("conversion", 0.2)
        )


class CompetitorSyncService:
    """
    竞品数据同步服务
    
    1. 从TIKHub抓取竞品视频
    2. 计算四维得分
    3. 存入competitor_videos表
    4. 提供按四维排序的查询接口
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.client = CompetitorClient()
        self.matcher = get_smart_matcher()
    
    async def sync_competitor(
        self,
        competitor_id: str,
        sec_uid: str,
        competitor_name: str,
        ip_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        同步单个竞品的视频数据
        
        Args:
            competitor_id: 竞品账号ID
            sec_uid: 抖音sec_uid
            competitor_name: 竞品名称
            ip_id: 关联的IP ID
            limit: 抓取视频数量
        """
        logger.info(f"[CompetitorSync] Syncing {competitor_name} ({sec_uid[:20]}...)")
        
        # 1. 从TIKHub抓取视频
        videos = await self.client.fetch_user_videos(sec_uid, count=limit)
        
        if not videos:
            logger.warning(f"[CompetitorSync] No videos fetched for {competitor_name}")
            return {"synced": 0, "errors": 0}
        
        logger.info(f"[CompetitorSync] Fetched {len(videos)} videos from {competitor_name}")
        
        # 2. 获取IP画像用于计算相关度
        ip_profile = await self._get_ip_profile(ip_id)
        
        # 3. 处理每个视频
        synced = 0
        errors = 0
        
        for video_data in videos:
            try:
                await self._save_video(video_data, competitor_id, competitor_name, ip_id, ip_profile)
                synced += 1
            except Exception as e:
                logger.error(f"[CompetitorSync] Failed to save video: {e}")
                errors += 1
        
        logger.info(f"[CompetitorSync] Synced {synced}/{len(videos)} videos for {competitor_name}")
        
        return {
            "competitor_name": competitor_name,
            "synced": synced,
            "errors": errors,
            "total_fetched": len(videos)
        }
    
    async def _get_ip_profile(self, ip_id: str) -> Dict[str, Any]:
        """获取IP画像"""
        try:
            result = self.db.execute(
                text("""
                    SELECT expertise, target_audience, content_direction, 
                           unique_value_prop, strategy_config
                    FROM ip WHERE ip_id = :ip_id
                """),
                {"ip_id": ip_id}
            )
            row = result.fetchone()
            if row:
                return {
                    "expertise": row.expertise or "",
                    "target_audience": row.target_audience or "",
                    "content_direction": row.content_direction or "",
                    "unique_value_prop": row.unique_value_prop or "",
                    "strategy_config": row.strategy_config or {}
                }
        except Exception as e:
            logger.error(f"[CompetitorSync] Failed to get IP profile: {e}")
        
        return {}
    
    async def _save_video(
        self,
        video_data: Dict[str, Any],
        competitor_id: str,
        competitor_name: str,
        ip_id: str,
        ip_profile: Dict[str, Any]
    ):
        """保存单个视频到数据库"""
        
        video_id = video_data.get("video_id", "")
        if not video_id:
            return
        
        # 计算四维得分
        four_dim = self._calculate_four_dim(video_data, ip_profile)
        
        # 检测内容类型（4-3-2-1矩阵）
        content_type, _ = self.matcher.detect_content_type(video_data.get("title", ""))
        
        # 提取标签
        tags = video_data.get("tags", [])
        if isinstance(tags, str):
            tags = tags.split(",")
        
        # 构建视频URL
        platform = video_data.get("platform", "douyin")
        url = ""
        if "douyin" in platform:
            url = f"https://www.douyin.com/video/{video_id}"
        
        # 构建数据结构
        video_record = {
            "video_id": video_id,
            "competitor_id": competitor_id,
            "title": video_data.get("title", ""),
            "desc": video_data.get("title", ""),  # 抖音desc就是标题
            "author": competitor_name,
            "platform": platform,
            "url": url,
            "play_count": self._parse_int(video_data.get("estimatedViews", 0)),
            "like_count": video_data.get("digg_count", 0),
            "comment_count": 0,  # API可能不提供
            "share_count": video_data.get("share_count", 0),
            "content_type": content_type,
            "tags": Json(tags if isinstance(tags, list) else list(tags or [])),
            "four_dim_relevance": four_dim.relevance,
            "four_dim_hotness": four_dim.hotness,
            "four_dim_competition": four_dim.competition,
            "four_dim_conversion": four_dim.conversion,
            "four_dim_total": four_dim.weighted_total({
                "relevance": 0.3, "hotness": 0.3, 
                "competition": 0.2, "conversion": 0.2
            }),
            "fetched_at": datetime.utcnow(),
            "create_time": None,  # API可能不提供
            "content_structure": Json({}),
            "raw_data": Json(video_data),
        }
        
        # 插入或更新数据库
        self._upsert_video(video_record)
    
    def _calculate_four_dim(
        self,
        video_data: Dict[str, Any],
        ip_profile: Dict[str, Any]
    ) -> FourDimScore:
        """计算四维得分"""
        
        # 1. 相关度：基于IP匹配
        title = video_data.get("title", "")
        relevance = self.matcher.calculate_match_score(title, ip_profile)
        
        # 2. 热度：基于点赞数（播放量可能为0）
        like_count = video_data.get("digg_count", 0)
        # 归一化：0-10000点赞=0-1分，超过10000算满分
        hotness = min(1.0, like_count / 10000)
        
        # 3. 竞争度：基于内容类型竞争激烈程度
        content_type, _ = self.matcher.detect_content_type(title)
        # 简单规则：搞钱类竞争最激烈，生活类竞争最小
        competition_map = {
            "money": 0.8,    # 搞钱类竞争大
            "emotion": 0.6,  # 情感类中等
            "skill": 0.5,    # 技能类中等
            "life": 0.3,     # 生活类竞争小
        }
        competition = competition_map.get(content_type, 0.5)
        
        # 4. 转化率：基于内容类型和互动率
        # 搞钱类 + 高互动 = 高转化
        conversion_base = {"money": 0.8, "skill": 0.7, "emotion": 0.5, "life": 0.3}
        conversion = conversion_base.get(content_type, 0.5)
        
        # 互动率加成
        if like_count > 1000:
            conversion = min(1.0, conversion + 0.1)
        
        return FourDimScore(
            relevance=round(relevance, 2),
            hotness=round(hotness, 2),
            competition=round(competition, 2),
            conversion=round(conversion, 2)
        )
    
    def _upsert_video(self, video: Dict[str, Any]):
        """插入或更新视频记录"""
        try:
            # 检查是否已存在
            result = self.db.execute(
                text(
                    "SELECT 1 FROM competitor_videos "
                    "WHERE video_id = :video_id AND competitor_id = :competitor_id"
                ),
                {"video_id": video["video_id"], "competitor_id": video["competitor_id"]},
            )
            exists = result.fetchone() is not None
            
            if exists:
                # 更新
                self.db.execute(
                    text("""
                        UPDATE competitor_videos SET
                            title = :title,
                            desc = :desc,
                            play_count = :play_count,
                            like_count = :like_count,
                            share_count = :share_count,
                            content_type = :content_type,
                            tags = :tags,
                            four_dim_relevance = :four_dim_relevance,
                            four_dim_hotness = :four_dim_hotness,
                            four_dim_competition = :four_dim_competition,
                            four_dim_conversion = :four_dim_conversion,
                            four_dim_total = :four_dim_total,
                            fetched_at = :fetched_at,
                            raw_data = :raw_data
                        WHERE video_id = :video_id
                    """),
                    video
                )
            else:
                # 插入
                self.db.execute(
                    text("""
                        INSERT INTO competitor_videos (
                            video_id, competitor_id, title, "desc", author, platform,
                            url, play_count, like_count, comment_count, share_count,
                            content_type, tags,
                            four_dim_relevance, four_dim_hotness, 
                            four_dim_competition, four_dim_conversion, four_dim_total,
                            fetched_at, create_time, content_structure, raw_data
                        ) VALUES (
                            :video_id, :competitor_id, :title, :desc, :author, :platform,
                            :url, :play_count, :like_count, :comment_count, :share_count,
                            :content_type, :tags,
                            :four_dim_relevance, :four_dim_hotness,
                            :four_dim_competition, :four_dim_conversion, :four_dim_total,
                            :fetched_at, :create_time, :content_structure, :raw_data
                        )
                    """),
                    video
                )
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def _parse_int(self, value) -> int:
        """安全解析整数"""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                # 处理 "1.5万" 格式
                if "万" in value:
                    return int(float(value.replace("万", "").replace("+", "")) * 10000)
                return int(value.replace(",", ""))
            except:
                return 0
        return 0
    
    async def sync_all_competitors(
        self,
        ip_id: str,
        competitors: List[Dict[str, Any]],
        videos_per_competitor: int = 10
    ) -> List[Dict[str, Any]]:
        """
        批量同步所有竞品
        
        Args:
            ip_id: IP ID
            competitors: 竞品列表 [{"competitor_id", "sec_uid", "name"}, ...]
            videos_per_competitor: 每个竞品抓取视频数
        """
        results = []
        
        for comp in competitors:
            result = await self.sync_competitor(
                competitor_id=comp["competitor_id"],
                sec_uid=comp["sec_uid"],
                competitor_name=comp["name"],
                ip_id=ip_id,
                limit=videos_per_competitor
            )
            results.append(result)
            
            # 速率限制
            await asyncio.sleep(1)
        
        return results


class CompetitorQueryService:
    """
    竞品查询服务
    
    提供按四维权重排序的查询接口
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def query_by_four_dim(
        self,
        ip_id: str,
        limit: int = 12,
        weights: Optional[Dict[str, float]] = None,
        content_type_filter: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        按四维权重查询竞品视频
        
        Args:
            ip_id: IP ID
            limit: 返回数量
            weights: 自定义四维权重，默认均等
            content_type_filter: 按内容类型筛选
            min_score: 最低总分筛选
        """
        weights = weights or {
            "relevance": 0.3,
            "hotness": 0.3,
            "competition": 0.2,
            "conversion": 0.2
        }
        
        # 构建查询
        where_clauses = ["c.ip_id = :ip_id"]
        params = {"ip_id": ip_id, "limit": limit, "min_score": min_score}
        
        if content_type_filter:
            where_clauses.append("v.content_type = :content_type")
            params["content_type"] = content_type_filter
        
        where_sql = " AND ".join(where_clauses)
        
        # 计算加权总分
        score_sql = """
            (v.four_dim_relevance * :w_relevance +
             v.four_dim_hotness * :w_hotness +
             (1 - v.four_dim_competition) * :w_competition +
             v.four_dim_conversion * :w_conversion) as weighted_score
        """
        
        params.update({
            "w_relevance": weights["relevance"],
            "w_hotness": weights["hotness"],
            "w_competition": weights["competition"],
            "w_conversion": weights["conversion"]
        })
        
        query = text(f"""
            SELECT 
                v.video_id,
                v.title,
                v.author as competitor_name,
                v.platform,
                v.url,
                v.play_count,
                v.like_count,
                v.comment_count,
                v.share_count,
                v.content_type,
                v.tags,
                v.four_dim_relevance,
                v.four_dim_hotness,
                v.four_dim_competition,
                v.four_dim_conversion,
                v.four_dim_total,
                {score_sql},
                v.fetched_at
            FROM competitor_videos v
            JOIN competitor_accounts c ON v.competitor_id = c.competitor_id
            WHERE {where_sql}
            AND v.four_dim_total >= :min_score
            ORDER BY weighted_score DESC, v.like_count DESC
            LIMIT :limit
        """)
        
        result = self.db.execute(query, params)
        
        videos = []
        for row in result.mappings():
            video = dict(row)
            # 添加前端展示用的字段
            video["score_display"] = f"{video['weighted_score']:.2f}"
            video["hot_display"] = self._format_number(video["like_count"])
            videos.append(video)
        
        return videos
    
    def query_by_content_matrix(
        self,
        ip_id: str,
        total_limit: int = 12
    ) -> List[Dict[str, Any]]:
        """
        按4-3-2-1内容矩阵查询
        
        40% 搞钱 (money)
        30% 情感 (emotion)  
        20% 技能 (skill)
        10% 生活 (life)
        """
        distribution = {
            "money": int(total_limit * 0.4),
            "emotion": int(total_limit * 0.3),
            "skill": int(total_limit * 0.2),
            "life": total_limit - int(total_limit * 0.9)  # 剩余
        }
        
        all_videos = []
        for content_type, count in distribution.items():
            if count > 0:
                videos = self.query_by_four_dim(
                    ip_id=ip_id,
                    limit=count,
                    content_type_filter=content_type
                )
                all_videos.extend(videos)
        
        # 按加权得分重新排序
        all_videos.sort(key=lambda x: x.get("weighted_score", 0), reverse=True)
        
        return all_videos[:total_limit]
    
    def _format_number(self, num: int) -> str:
        """格式化数字显示"""
        if num >= 10000:
            return f"{num / 10000:.1f}万"
        if num >= 1000:
            return f"{num / 1000:.1f}千"
        return str(num)


# ============== 便捷函数 ==============

async def sync_competitors_from_csv(
    db_session: Session,
    ip_id: str,
    competitors: List[Dict[str, str]],
    videos_per_competitor: int = 10
) -> List[Dict[str, Any]]:
    """
    从CSV配置的竞品列表同步数据
    
    competitors: [{"competitor_id", "sec_uid", "name"}, ...]
    """
    service = CompetitorSyncService(db_session)
    return await service.sync_all_competitors(
        ip_id=ip_id,
        competitors=competitors,
        videos_per_competitor=videos_per_competitor
    )


def get_competitor_videos_by_four_dim(
    db_session: Session,
    ip_id: str,
    limit: int = 12,
    use_content_matrix: bool = True
) -> List[Dict[str, Any]]:
    """
    获取按四维排序的竞品视频
    
    前端调用此接口获取排序后的选题
    """
    service = CompetitorQueryService(db_session)
    
    if use_content_matrix:
        # 按4-3-2-1矩阵返回
        return service.query_by_content_matrix(ip_id, limit)
    else:
        # 纯按四维得分返回
        return service.query_by_four_dim(ip_id, limit)
