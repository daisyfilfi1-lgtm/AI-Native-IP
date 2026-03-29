"""
Direct fetch test - Bypass CompetitorClient to verify data flow
"""

import asyncio
import os
import httpx

os.environ["TIKHUB_API_KEY"] = "k6ANCMEu1nWQhW2vRIel/y3ucxi0XoQyzwuJhE/ZBvWr1W+4FmaNU2KDKw=="

API_KEY = os.environ["TIKHUB_API_KEY"]
BASE_URL = "https://api.tikhub.io"
SEC_UID = "MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA"


async def direct_fetch():
    """Direct API call"""
    print("Direct API Call:")
    print("-" * 40)
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    url = f"{BASE_URL}/api/v1/douyin/app/v3/fetch_user_post_videos"
    params = {
        "sec_user_id": SEC_UID,
        "max_cursor": 0,
        "count": 5
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=headers, params=params)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 200:
                aweme_list = data.get("data", {}).get("aweme_list", [])
                print(f"Videos: {len(aweme_list)}")
                return aweme_list
    
    return []


async def competitor_client_fetch():
    """Using CompetitorClient"""
    print("\nUsing CompetitorClient:")
    print("-" * 40)
    
    from app.services.competitor_client import CompetitorClient
    
    client = CompetitorClient()
    print(f"API Key: {client.api_key[:20]}...")
    print(f"Base URL: {client.base_url}")
    print(f"Is configured: {client.is_configured()}")
    
    videos = await client.fetch_user_videos(SEC_UID, count=5)
    print(f"Videos returned: {len(videos)}")
    
    return videos


async def fixed_fetch():
    """Fixed version - check what's happening"""
    print("\nDebug Fixed Version:")
    print("-" * 40)
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    url = f"{BASE_URL}/api/v1/douyin/app/v3/fetch_user_post_videos"
    params = {
        "sec_user_id": SEC_UID,
        "max_cursor": 0,
        "count": 5
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=headers, params=params)
        print(f"Status: {r.status_code}")
        
        data = r.json()
        print(f"Response code: {data.get('code')}")
        print(f"Response message: {data.get('message')}")
        
        if data.get("code") == 200:
            aweme_list = data.get("data", {}).get("aweme_list", [])
            print(f"Raw videos: {len(aweme_list)}")
            
            # Process like CompetitorClient does
            results = []
            for video in aweme_list[:5]:
                if not isinstance(video, dict):
                    print(f"  Skip: not a dict")
                    continue
                
                desc = video.get("desc", "")
                aweme_id = video.get("aweme_id", "")
                
                print(f"  Video: id={aweme_id[:10] if aweme_id else 'N/A'}..., desc={'Yes' if desc else 'No'}")
                
                if not desc:
                    print(f"    -> Skipped (no desc)")
                    continue
                
                stats = video.get("statistics", {})
                results.append({
                    "id": f"comp_{aweme_id}",
                    "title": desc[:100],
                    "play_count": stats.get("play_count", 0),
                    "like_count": stats.get("digg_count", 0),
                })
            
            print(f"Processed videos: {len(results)}")
            return results
        else:
            print(f"API Error: {data.get('message')}")
            return []


async def main():
    print("=" * 60)
    print("Direct Fetch Test")
    print("=" * 60)
    
    # Test 1: Direct API
    direct_videos = await direct_fetch()
    
    # Test 2: CompetitorClient
    client_videos = await competitor_client_fetch()
    
    # Test 3: Fixed version
    fixed_videos = await fixed_fetch()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"Direct API: {len(direct_videos)} videos")
    print(f"CompetitorClient: {len(client_videos)} videos")
    print(f"Fixed version: {len(fixed_videos)} videos")


if __name__ == "__main__":
    asyncio.run(main())
