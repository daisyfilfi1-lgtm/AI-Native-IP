"""
同步竞品数据到数据库

Usage:
    cd backend
    python scripts/sync_competitors_to_db.py --ip_id xiaomin
"""

import asyncio
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.services.competitor_sync_service import sync_competitors_from_csv


# 从 sec_uid.csv 导入的竞品列表
COMPETITORS = [
    {"competitor_id": "comp_001", "sec_uid": "MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA", "name": "淘淘子"},
    {"competitor_id": "comp_002", "sec_uid": "MS4wLjABAAAATeQUszhzY6JjMfJy1Gya6ao5gGD66Gg1I_9vcJC-y9dfNHKtcXaQ-Mu0K1SPy8EK", "name": "顶妈私房早餐"},
    {"competitor_id": "comp_003", "sec_uid": "MS4wLjABAAAA3XsMOiah1EsT6TSzoqMjlgH4GdMhoBCLwunPVyUP34y-EbUgIV04OU2dnpImMfHq", "name": "深圳蓝蒂蔻Gina"},
    {"competitor_id": "comp_004", "sec_uid": "MS4wLjABAAAAErFzzalv2271brW_cK7vbdLX67B8zOw2ReVYJ72GyoPu2AbZnT3QYNpq4uyxePWr", "name": "梁宸瑜·无价之姐"},
    {"competitor_id": "comp_005", "sec_uid": "MS4wLjABAAAAWwcXLQaOlIV4k04tSI4xYaYmCzRZt1a9_IDDutj7Wzra_yNzBUDrPQgV8UVJ_dsH", "name": "Olga姐姐"},
    {"competitor_id": "comp_006", "sec_uid": "MS4wLjABAAAAfmygSsGTU3RIctsoi4vcbWkAQaMRi_KwtQh1bP7WCzf1k0yydcLtKQj7kE-FSwsJ", "name": "张琦老师"},
    {"competitor_id": "comp_007", "sec_uid": "MS4wLjABAAAAHu4SbvaUZQ1GN2WgySRB6G4nmvUvWxD2fNLzvDKOkOAmqxZkQ5fJtx0ZhANSST7V", "name": "崔璀优势星球"},
    {"competitor_id": "comp_008", "sec_uid": "MS4wLjABAAAAbDuwvhxdzfp009rDpY1mj4NmPu_A_Txsi9SP6Ybz3Bk", "name": "王潇_潇洒姐"},
    {"competitor_id": "comp_009", "sec_uid": "MS4wLjABAAAAvrhmrhhYvc4eJvqu_0MStkyBihmGdJZCBl_JVZ0AulE", "name": "张萌萌姐"},
    {"competitor_id": "comp_010", "sec_uid": "MS4wLjABAAAAV5oVsV-RjxHKrcCuqQotWtHvT8_Y7z_aQnTvT61slic", "name": "清华陈晶聊商业"},
    {"competitor_id": "comp_011", "sec_uid": "MS4wLjABAAAAnTsmfVQNtopff5MrXYMf9y2oVrZ9usIHaCOb_6T1mVo", "name": "Dada人物圈"},
    {"competitor_id": "comp_012", "sec_uid": "MS4wLjABAAAA7hiENPfyARPotUS0FootY0s1Qg51l4X3gvkXEKYUHas", "name": "赵三观"},
    {"competitor_id": "comp_013", "sec_uid": "MS4wLjABAAAAoGgpFqfuSXAjeMy21Qk8Pn1NvaSukBN7vCipz3xsPOU", "name": "程前Jason"},
    {"competitor_id": "comp_014", "sec_uid": "MS4wLjABAAAAO_KKPhlqsPDzmTIxBFSFUX5Hjuj8Y94gHQpJgqHlub0", "name": "群响刘思毅"},
    {"competitor_id": "comp_015", "sec_uid": "MS4wLjABAAAAZXgVjvDmWo_ipGRJnXwFREdhkG29krGiVSwIQhzIrDA", "name": "透透糖"},
    {"competitor_id": "comp_016", "sec_uid": "MS4wLjABAAAAHAlF09yQrLMxW8wyJUO0NGlrsE7O0_9yTki_BkZM16g", "name": "房琪kiki"},
    {"competitor_id": "comp_017", "sec_uid": "MS4wLjABAAAAB1lxLcDT1n51dY3jyB-VQACgN0gbYWGxvSdiE0DWYLY", "name": "杨天真"},
]


async def main():
    parser = argparse.ArgumentParser(description="Sync competitor data to database")
    parser.add_argument("--ip_id", required=True, help="IP ID to associate with competitors")
    parser.add_argument("--limit", type=int, default=10, help="Videos per competitor")
    parser.add_argument("--check", action="store_true", help="Only check existing data")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        if args.check:
            # 检查现有数据
            from sqlalchemy import text
            result = db.execute(
                text("""
                    SELECT 
                        v.competitor_id,
                        c.name as competitor_name,
                        COUNT(*) as video_count,
                        AVG(v.four_dim_total) as avg_score,
                        MAX(v.like_count) as max_likes
                    FROM competitor_videos v
                    JOIN competitor_accounts c ON v.competitor_id = c.competitor_id
                    WHERE c.ip_id = :ip_id
                    GROUP BY v.competitor_id, c.name
                    ORDER BY video_count DESC
                """),
                {"ip_id": args.ip_id}
            )
            
            print(f"\nExisting data for IP: {args.ip_id}")
            print("-" * 80)
            print(f"{'Competitor':<20} {'Videos':<10} {'Avg Score':<12} {'Max Likes':<10}")
            print("-" * 80)
            
            total_videos = 0
            for row in result.mappings():
                print(f"{row['competitor_name']:<20} {row['video_count']:<10} "
                      f"{row['avg_score']:.2f}       {row['max_likes']:<10,}")
                total_videos += row['video_count']
            
            print("-" * 80)
            print(f"Total: {total_videos} videos from {result.rowcount} competitors\n")
            
        else:
            # 同步数据
            print(f"\nSyncing {len(COMPETITORS)} competitors for IP: {args.ip_id}")
            print(f"Videos per competitor: {args.limit}")
            print("=" * 80)
            
            results = await sync_competitors_from_csv(
                db_session=db,
                ip_id=args.ip_id,
                competitors=COMPETITORS,
                videos_per_competitor=args.limit
            )
            
            print("\n" + "=" * 80)
            print("Sync Results:")
            print("=" * 80)
            
            total_synced = 0
            for r in results:
                status = "✓" if r["errors"] == 0 else "⚠"
                print(f"{status} {r['competitor_name']}: "
                      f"{r['synced']}/{r['total_fetched']} synced "
                      f"({r['errors']} errors)")
                total_synced += r["synced"]
            
            print("=" * 80)
            print(f"Total synced: {total_synced} videos\n")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
