"""
Live Test TIKHub API with real credentials
"""

import asyncio
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

# Set the provided credentials
os.environ["TIKHUB_API_KEY"] = "k6ANCMEu1nWQhW2vRIel/y3ucxi0XoQyzwuJhE/ZBvWr1W+4FmaNU2KDKw=="
os.environ["TIKHUB_COMPETITOR_SEC_UIDS"] = "MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA"

import httpx
from app.services.tikhub_client import is_configured
from app.services.competitor_client import CompetitorClient, get_competitor_client


async def test_tikhub_connection():
    """Test basic TIKHub connection"""
    print("=" * 60)
    print("1. TIKHub Connection Test")
    print("=" * 60)
    
    api_key = os.environ.get("TIKHUB_API_KEY", "").strip()
    print(f"\nAPI Key: {api_key[:20]}...")
    print(f"Is configured: {is_configured()}")
    
    # Test direct API call
    base_url = "https://api.tikhub.io"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to fetch user info first
            url = f"{base_url}/api/v1/douyin/app/v3/fetch_user_post_videos"
            params = {
                "sec_user_id": "MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA",
                "max_cursor": 0,
                "count": 5
            }
            
            print(f"\nRequesting: {url}")
            print(f"Params: {params}")
            
            r = await client.get(url, headers=headers, params=params)
            
            print(f"Status: {r.status_code}")
            
            if r.status_code == 200:
                data = r.json()
                print(f"Response code: {data.get('code')}")
                print(f"Message: {data.get('message', 'N/A')}")
                
                if data.get("code") == 200:
                    aweme_list = data.get("data", {}).get("aweme_list", [])
                    print(f"\n[SUCCESS] Got {len(aweme_list)} videos!")
                    return True, data
                else:
                    print(f"\n[API ERROR] {data.get('message')}")
                    return False, data
            else:
                print(f"\n[HTTP ERROR] {r.status_code}")
                print(f"Response: {r.text[:500]}")
                return False, None
                
    except Exception as e:
        print(f"\n[EXCEPTION] {e}")
        return False, None


async def test_competitor_client():
    """Test CompetitorClient with real data"""
    print("\n" + "=" * 60)
    print("2. CompetitorClient Test")
    print("=" * 60)
    
    client = get_competitor_client()
    
    print(f"Is configured: {client.is_configured()}")
    print(f"Number of sec_uids: {len(client.competitor_sec_uids)}")
    
    if client.is_configured():
        print("\nFetching videos...")
        videos = await client.fetch_user_videos(
            sec_uid="MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA",
            count=5
        )
        
        print(f"\nGot {len(videos)} videos")
        
        if videos:
            print("\n--- Video Details ---")
            for i, v in enumerate(videos[:3], 1):
                title = v.get("title", "")
                author = v.get("competitor_author", "")
                plays = v.get("estimatedViews", "N/A")
                
                # Try to encode safely
                try:
                    print(f"\n{i}. {title[:60]}")
                except:
                    print(f"\n{i}. [Title contains non-ASCII characters]")
                
                print(f"   Author: {author}")
                print(f"   Plays: {plays}")
                print(f"   ID: {v.get('video_id', 'N/A')[:20]}...")
            
            return True
        else:
            print("\n[WARNING] No videos returned")
            return False
    else:
        print("[SKIP] Client not configured")
        return False


async def test_data_structure():
    """Verify data structure matches what we need"""
    print("\n" + "=" * 60)
    print("3. Data Structure Verification")
    print("=" * 60)
    
    success, data = await test_tikhub_connection()
    
    if not success or not data:
        print("\n[SKIP] No data to analyze")
        return False
    
    aweme_list = data.get("data", {}).get("aweme_list", [])
    
    if not aweme_list:
        print("\n[SKIP] Empty video list")
        return False
    
    # Analyze first video structure
    video = aweme_list[0]
    
    print("\n--- Required Fields Check ---")
    
    required_fields = {
        "aweme_id": "Video ID",
        "desc": "Title/Description",
        "create_time": "Publish Time",
        "author": "Author Info",
        "statistics": "Stats (plays, likes, etc.)",
    }
    
    all_good = True
    for field, desc in required_fields.items():
        has_field = field in video
        status = "✓" if has_field else "✗"
        print(f"  {status} {desc} ({field}): {'Present' if has_field else 'MISSING'}")
        if not has_field:
            all_good = False
    
    # Check statistics
    if "statistics" in video:
        stats = video["statistics"]
        print("\n--- Statistics Check ---")
        stat_fields = {
            "play_count": "Play count",
            "digg_count": "Like count",
            "comment_count": "Comment count",
            "share_count": "Share count",
        }
        for field, desc in stat_fields.items():
            has_field = field in stats
            value = stats.get(field, "N/A")
            status = "✓" if has_field else "✗"
            print(f"  {status} {desc} ({field}): {value}")
    
    # Check author info
    if "author" in video:
        author = video["author"]
        print("\n--- Author Info Check ---")
        author_fields = {
            "nickname": "Nickname",
            "sec_uid": "sec_uid",
        }
        for field, desc in author_fields.items():
            has_field = field in author
            value = author.get(field, "N/A")
            if field == "sec_uid" and has_field:
                value = value[:30] + "..."
            status = "✓" if has_field else "✗"
            print(f"  {status} {desc} ({field}): {value}")
    
    return all_good


async def main():
    """Main test"""
    print("\n" + "=" * 60)
    print("TIKHub Live Test with Real Credentials")
    print("=" * 60)
    
    results = []
    
    try:
        # Test 1: Connection
        success, data = await test_tikhub_connection()
        results.append(("API Connection", success))
        
        # Test 2: CompetitorClient
        if success:
            client_success = await test_competitor_client()
            results.append(("CompetitorClient", client_success))
        else:
            results.append(("CompetitorClient", False))
        
        # Test 3: Data Structure
        struct_success = await test_data_structure()
        results.append(("Data Structure", struct_success))
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            print(f"  {name}: {status}")
        
        all_passed = all(r[1] for r in results)
        
        print("\n" + "=" * 60)
        if all_passed:
            print("ALL TESTS PASSED!")
            print("=" * 60)
            print("\nTIKHub is working with the provided credentials!")
            print("The sec_uid returns real video data.")
            print("\nYou can now:")
            print("1. Use this sec_uid for competitor monitoring")
            print("2. Add more sec_uids to TIKHUB_COMPETITOR_SEC_UIDS")
            print("3. The system will fetch real competitor data")
        else:
            print("SOME TESTS FAILED")
            print("=" * 60)
            print("\nPossible issues:")
            print("- API Key may be invalid or expired")
            print("- sec_uid may be invalid or account private")
            print("- TIKHub API may have rate limits")
            
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
