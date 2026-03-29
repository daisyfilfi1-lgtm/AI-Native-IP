"""
Test TIKHub with sec_uid - Check if we can get real data
"""

import asyncio
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

from app.services.tikhub_client import is_configured
from app.services.competitor_client import CompetitorClient


async def test_tikhub_config():
    """Test TIKHub configuration"""
    print("=" * 60)
    print("1. TIKHub Configuration Check")
    print("=" * 60)
    
    # Check environment variables
    api_key = os.environ.get("TIKHUB_API_KEY", "").strip()
    competitor_uids = os.environ.get("TIKHUB_COMPETITOR_SEC_UIDS", "").strip()
    
    print(f"\nTIKHUB_API_KEY: {'Configured (' + api_key[:10] + '...)' if api_key else 'NOT SET'}")
    print(f"TIKHUB_COMPETITOR_SEC_UIDS: {competitor_uids if competitor_uids else 'NOT SET'}")
    
    # Check if TIKHub is configured
    configured = is_configured()
    print(f"\nTIKHub is_configured(): {configured}")
    
    if not api_key:
        print("\n[ERROR] TIKHUB_API_KEY is not set!")
        print("Please set it in your .env file or environment variables")
        return False
    
    return True


async def test_competitor_client():
    """Test CompetitorClient with configured sec_uids"""
    print("\n" + "=" * 60)
    print("2. CompetitorClient Check")
    print("=" * 60)
    
    client = CompetitorClient()
    
    print(f"\nIs configured: {client.is_configured()}")
    print(f"Number of competitor sec_uids: {len(client.competitor_sec_uids)}")
    
    if client.competitor_sec_uids:
        print(f"\nConfigured sec_uids:")
        for i, uid in enumerate(client.competitor_sec_uids, 1):
            print(f"  {i}. {uid[:40]}...")
    else:
        print("\n[WARNING] No competitor sec_uids configured!")
        print("Set TIKHUB_COMPETITOR_SEC_UIDS env variable")
        print("Format: sec_uid1,sec_uid2,sec_uid3")
    
    return len(client.competitor_sec_uids) > 0


async def test_fetch_real_data():
    """Test fetching real data from TIKHub"""
    print("\n" + "=" * 60)
    print("3. Fetch Real Data from TIKHub")
    print("=" * 60)
    
    client = CompetitorClient()
    
    if not client.is_configured():
        print("[SKIP] TIKHub not configured, skipping real data test")
        return False
    
    # Try to fetch from first competitor
    if not client.competitor_sec_uids:
        print("[SKIP] No sec_uids configured, skipping real data test")
        return False
    
    sec_uid = client.competitor_sec_uids[0]
    print(f"\nTrying to fetch videos for sec_uid: {sec_uid[:40]}...")
    
    try:
        videos = await client.fetch_user_videos(sec_uid, count=5)
        
        print(f"\n[RESULT] Fetched {len(videos)} videos")
        
        if videos:
            for i, v in enumerate(videos[:3], 1):
                title_ascii = v.get("title", "").encode('ascii', 'ignore').decode('ascii')
                print(f"\n  {i}. {title_ascii[:50]}...")
                print(f"      Author: {v.get('competitor_author', 'N/A')}")
                print(f"      Plays: {v.get('estimatedViews', 'N/A')}")
                print(f"      Video ID: {v.get('video_id', 'N/A')[:20]}...")
            return True
        else:
            print("\n[WARNING] No videos returned - possible reasons:")
            print("  - sec_uid is invalid or expired")
            print("  - Account is private")
            print("  - TIKHub API quota exceeded")
            print("  - Network error")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Failed to fetch: {e}")
        return False


async def test_with_sample_secuid():
    """Test with a sample public sec_uid if no config"""
    print("\n" + "=" * 60)
    print("4. Test with Sample sec_uid (if needed)")
    print("=" * 60)
    
    # A sample public sec_uid for testing (this is a random example format)
    # You should replace this with a real public account sec_uid
    sample_sec_uid = "MS4wLjABAAAAVVe4hJr2jqhWcB0vIB2Fw5QLUNNHfPbzJV2Q1HBzGwE6tdyX"
    
    print(f"\nSample sec_uid: {sample_sec_uid[:40]}...")
    print("[NOTE] This is just a format example, may not be valid")
    
    return True


async def main():
    """Main test"""
    print("\n" + "=" * 60)
    print("TIKHub + sec_uid Test")
    print("=" * 60)
    print("\nPurpose: Verify we can get real competitor data from TIKHub")
    
    results = []
    
    try:
        results.append(("TIKHub Config", await test_tikhub_config()))
        results.append(("CompetitorClient", await test_competitor_client()))
        results.append(("Fetch Real Data", await test_fetch_real_data()))
        await test_with_sample_secuid()
        
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            print(f"  {name}: {status}")
        
        all_passed = all(r[1] for r in results)
        
        print("\n" + "=" * 60)
        if all_passed:
            print("All tests PASSED - TIKHub is ready!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Ensure competitor sec_uids are configured")
            print("2. The system will fetch real data from these accounts")
            print("3. Data will be stored in competitor_videos table")
        else:
            print("Some tests FAILED - Action needed")
            print("=" * 60)
            print("\nTo fix:")
            print("1. Set TIKHUB_API_KEY in your .env file")
            print("2. Set TIKHUB_COMPETITOR_SEC_UIDS with comma-separated sec_uids")
            print("3. Or configure competitor_accounts table in database")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
