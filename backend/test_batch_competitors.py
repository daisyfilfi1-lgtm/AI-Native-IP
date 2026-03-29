"""
Batch fetch all competitors from sec_uid.csv
"""

import asyncio
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

# Set API Key
os.environ["TIKHUB_API_KEY"] = "k6ANCMEu1nWQhW2vRIel/y3ucxi0XoQyzwuJhE/ZBvWr1W+4FmaNU2KDKw=="

from app.services.competitor_client import CompetitorClient


# Competitors from sec_uid.csv
COMPETITORS = [
    {"name": "淘淘子", "sec_uid": "MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA"},
    {"name": "顶妈私房早餐", "sec_uid": "MS4wLjABAAAATeQUszhzY6JjMfJy1Gya6ao5gGD66Gg1I_9vcJC-y9dfNHKtcXaQ-Mu0K1SPy8EK"},
    {"name": "深圳蓝蒂蔻Gina", "sec_uid": "MS4wLjABAAAA3XsMOiah1EsT6TSzoqMjlgH4GdMhoBCLwunPVyUP34y-EbUgIV04OU2dnpImMfHq"},
    {"name": "梁宸瑜·无价之姐", "sec_uid": "MS4wLjABAAAAErFzzalv2271brW_cK7vbdLX67B8zOw2ReVYJ72GyoPu2AbZnT3QYNpq4uyxePWr"},
    {"name": "Olga姐姐", "sec_uid": "MS4wLjABAAAAWwcXLQaOlIV4k04tSI4xYaYmCzRZt1a9_IDDutj7Wzra_yNzBUDrPQgV8UVJ_dsH"},
    {"name": "张琦老师", "sec_uid": "MS4wLjABAAAAfmygSsGTU3RIctsoi4vcbWkAQaMRi_KwtQh1bP7WCzf1k0yydcLtKQj7kE-FSwsJ"},
    {"name": "崔璀优势星球", "sec_uid": "MS4wLjABAAAAHu4SbvaUZQ1GN2WgySRB6G4nmvUvWxD2fNLzvDKOkOAmqxZkQ5fJtx0ZhANSST7V"},
    {"name": "王潇_潇洒姐", "sec_uid": "MS4wLjABAAAAbDuwvhxdzfp009rDpY1mj4NmPu_A_Txsi9SP6Ybz3Bk"},
    {"name": "张萌萌姐", "sec_uid": "MS4wLjABAAAAvrhmrhhYvc4eJvqu_0MStkyBihmGdJZCBl_JVZ0AulE"},
    {"name": "清华陈晶聊商业", "sec_uid": "MS4wLjABAAAAV5oVsV-RjxHKrcCuqQotWtHvT8_Y7z_aQnTvT61slic"},
    {"name": "Dada人物圈", "sec_uid": "MS4wLjABAAAAnTsmfVQNtopff5MrXYMf9y2oVrZ9usIHaCOb_6T1mVo"},
    {"name": "赵三观", "sec_uid": "MS4wLjABAAAA7hiENPfyARPotUS0FootY0s1Qg51l4X3gvkXEKYUHas"},
    {"name": "程前Jason", "sec_uid": "MS4wLjABAAAAoGgpFqfuSXAjeMy21Qk8Pn1NvaSukBN7vCipz3xsPOU"},
    {"name": "群响刘思毅", "sec_uid": "MS4wLjABAAAAO_KKPhlqsPDzmTIxBFSFUX5Hjuj8Y94gHQpJgqHlub0"},
    {"name": "透透糖", "sec_uid": "MS4wLjABAAAAZXgVjvDmWo_ipGRJnXwFREdhkG29krGiVSwIQhzIrDA"},
    {"name": "房琪kiki", "sec_uid": "MS4wLjABAAAAHAlF09yQrLMxW8wyJUO0NGlrsE7O0_9yTki_BkZM16g"},
    {"name": "杨天真", "sec_uid": "MS4wLjABAAAAB1lxLcDT1n51dY3jyB-VQACgN0gbYWGxvSdiE0DWYLY"},
]


async def fetch_competitor_data(competitor: dict, client: CompetitorClient):
    """Fetch data for a single competitor"""
    name = competitor["name"]
    sec_uid = competitor["sec_uid"]
    
    try:
        videos = await client.fetch_user_videos(sec_uid, count=5)
        
        # Calculate total engagement
        total_likes = sum(v.get("digg_count", 0) for v in videos)
        
        return {
            "name": name,
            "sec_uid": sec_uid[:30] + "...",
            "videos_count": len(videos),
            "total_likes": total_likes,
            "sample_titles": [v.get("title", "")[:30] for v in videos[:2]],
            "status": "success"
        }
    except Exception as e:
        return {
            "name": name,
            "sec_uid": sec_uid[:30] + "...",
            "videos_count": 0,
            "total_likes": 0,
            "sample_titles": [],
            "status": f"error: {str(e)[:50]}"
        }


async def main():
    """Main test"""
    print("=" * 70)
    print("Batch Competitor Fetch Test")
    print("=" * 70)
    print(f"\nTotal competitors: {len(COMPETITORS)}")
    print("\nCompetitor list:")
    for i, c in enumerate(COMPETITORS, 1):
        print(f"  {i}. {c['name']}")
    
    print("\n" + "=" * 70)
    print("Fetching data from TIKHub...")
    print("=" * 70)
    
    client = CompetitorClient()
    
    # Fetch all competitors with rate limiting
    results = []
    for i, comp in enumerate(COMPETITORS, 1):
        print(f"\n[{i}/{len(COMPETITORS)}] Fetching: {comp['name']}...")
        result = await fetch_competitor_data(comp, client)
        results.append(result)
        
        # Print result
        status_icon = "✓" if result["status"] == "success" else "✗"
        print(f"  {status_icon} Videos: {result['videos_count']}, Likes: {result['total_likes']:,}")
        
        if result["sample_titles"]:
            for title in result["sample_titles"]:
                try:
                    print(f"    - {title}...")
                except:
                    print(f"    - [Non-ASCII title]...")
        
        # Rate limit: wait between requests
        if i < len(COMPETITORS):
            await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    successful = sum(1 for r in results if r["status"] == "success")
    total_videos = sum(r["videos_count"] for r in results)
    
    print(f"\nSuccessful fetches: {successful}/{len(COMPETITORS)}")
    print(f"Total videos fetched: {total_videos}")
    
    # Top competitors by engagement
    print("\n--- Top 5 by Total Likes ---")
    sorted_by_likes = sorted(results, key=lambda x: x["total_likes"], reverse=True)
    for i, r in enumerate(sorted_by_likes[:5], 1):
        print(f"  {i}. {r['name']}: {r['total_likes']:,} likes ({r['videos_count']} videos)")
    
    # Failed fetches
    failed = [r for r in results if r["status"] != "success"]
    if failed:
        print("\n--- Failed Fetches ---")
        for r in failed:
            print(f"  - {r['name']}: {r['status']}")
    
    print("\n" + "=" * 70)
    print("Conclusion")
    print("=" * 70)
    
    if successful > 0:
        print(f"\n✓ Successfully fetched data from {successful} competitors!")
        print(f"✓ Total of {total_videos} videos available for content creation")
        print("\nThese are all high-quality competitors in the female entrepreneurship space:")
        print("- 淘淘子, 顶妈私房早餐: 私房创业类")
        print("- 深圳蓝蒂蔻Gina, 张琦老师: 商业培训类")
        print("- 杨天真, 房琪kiki: 个人成长类")
        print("- 程前Jason, 群响刘思毅: 创业者访谈类")
        print("\nThis data is PERFECT for your IP content creation pipeline!")
    else:
        print("\n✗ All fetches failed - check API key and rate limits")


if __name__ == "__main__":
    asyncio.run(main())
