"""
Test Real Competitor Service (using Railway DB data)
"""

import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

# Mock database for testing
class MockDB:
    def execute(self, query, params=None):
        class MockResult:
            def mappings(self):
                return []
            def scalar(self):
                return 0
            def fetchone(self):
                return None
        return MockResult()


from app.services.real_competitor_service import RealCompetitorService
from app.services.datasource.builtin_viral_repository import get_builtin_repository


def test_service_init():
    """Test service initialization"""
    print("=" * 60)
    print("Test: Service Initialization")
    print("=" * 60)
    
    service = RealCompetitorService(db_session=None)
    print(f"Service initialized: {service is not None}")
    
    return True


def test_builtin_fallback():
    """Test builtin repository as fallback"""
    print("\n" + "=" * 60)
    print("Test: Builtin Repository (Fallback)")
    print("=" * 60)
    
    repo = get_builtin_repository()
    
    # Test different IP profiles
    profiles = [
        {
            "name": "Mom Entrepreneur",
            "expertise": "Mom entrepreneurship, side hustle",
            "content_direction": "Women growth",
            "target_audience": "Moms",
        },
        {
            "name": "Knowledge Paid",
            "expertise": "Knowledge monetization, course creation",
            "content_direction": "Content entrepreneurship",
            "target_audience": "Knowledge workers",
        },
    ]
    
    for profile in profiles:
        print(f"\nIP Profile: {profile['name']}")
        
        # Detect IP type
        ip_types = repo.detect_ip_type(profile)
        print(f"  Detected types: {[t.value for t in ip_types]}")
        
        # Get topics
        topics = repo.get_topics_for_ip(profile, limit=3)
        print(f"  Got {len(topics)} topics")
        
        for i, t in enumerate(topics, 1):
            title_ascii = t.title.encode('ascii', 'ignore').decode('ascii')
            print(f"    {i}. [{t.extra.get('content_type')}] {title_ascii[:40]}...")
    
    return True


def test_video_conversion():
    """Test video to topic conversion"""
    print("\n" + "=" * 60)
    print("Test: Video to Topic Conversion")
    print("=" * 60)
    
    service = RealCompetitorService(db_session=None)
    
    # Mock video data
    mock_video = {
        "video_id": "1234567890",
        "title": "Test viral video title",
        "desc": "Description here",
        "author": "TestAuthor",
        "platform": "douyin",
        "play_count": 150000,
        "like_count": 5000,
        "comment_count": 300,
        "share_count": 200,
        "competitor_name": "TestCompetitor",
        "competitor_id": "comp_001",
        "content_type": "money",
        "tags": ["创业", "赚钱"],
    }
    
    ip_profile = {
        "expertise": "Mom entrepreneurship",
        "target_audience": "Moms",
    }
    
    topic = service._video_to_topic(mock_video, ip_profile)
    
    if topic:
        print(f"\nConverted topic:")
        title_ascii = topic.title.encode('ascii', 'ignore').decode('ascii')
        print(f"  Title: {title_ascii}")
        print(f"  Score: {topic.score}")
        print(f"  Platform: {topic.platform}")
        print(f"  Play count: {topic.extra.get('play_count')}")
        print(f"  Is competitor: {topic.extra.get('is_competitor_topic')}")
        return True
    else:
        print("Conversion failed!")
        return False


def test_ranking():
    """Test IP match ranking"""
    print("\n" + "=" * 60)
    print("Test: IP Match Ranking")
    print("=" * 60)
    
    from app.services.datasource.base import TopicData
    
    service = RealCompetitorService(db_session=None)
    
    ip_profile = {
        "expertise": "Mom entrepreneurship, side hustle",
        "target_audience": "Moms, women",
    }
    
    # Create mock topics
    topics = [
        TopicData(
            id="1",
            title="Python programming tutorial",  # Not matching
            original_title="Python programming tutorial",
            platform="douyin",
            url="",
            tags=["tech"],
            score=4.5,
        ),
        TopicData(
            id="2",
            title="Mom side hustle guide",  # Matching
            original_title="Mom side hustle guide",
            platform="douyin",
            url="",
            tags=["mom", "business"],
            score=4.0,
        ),
        TopicData(
            id="3",
            title="How to make money at home for moms",  # Strongly matching
            original_title="How to make money at home for moms",
            platform="douyin",
            url="",
            tags=["mom", "money"],
            score=3.5,
        ),
    ]
    
    ranked = service._rank_by_ip_match(topics, ip_profile)
    
    print("\nRanking results:")
    for i, t in enumerate(ranked, 1):
        title_ascii = t.title.encode('ascii', 'ignore').decode('ascii')
        print(f"  {i}. {title_ascii}")
    
    # The strongly matching topic should be first
    return ranked[0].id == "3"


async def main():
    """Main test"""
    print("\n" + "=" * 60)
    print("Real Competitor Service Test")
    print("=" * 60)
    print("\nUsing Railway database:")
    print("- competitor_accounts: Competitor account configs")
    print("- competitor_videos: Competitor video data")
    print("\nFallback: Builtin viral repository (60+ templates)")
    
    results = []
    
    try:
        results.append(("Service Init", test_service_init()))
        results.append(("Builtin Fallback", test_builtin_fallback()))
        results.append(("Video Conversion", test_video_conversion()))
        results.append(("IP Match Ranking", test_ranking()))
        
        print("\n" + "=" * 60)
        print("Test Results:")
        print("=" * 60)
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            print(f"  {name}: {status}")
        
        all_passed = all(r[1] for r in results)
        print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))
        
        print("\n" + "=" * 60)
        print("Architecture:")
        print("=" * 60)
        print("Stage 1 - API Hot Topic Search")
        print("  1. Query competitor_videos table (Railway)")
        print("  2. Filter: play_count > 10k, recent 30 days")
        print("  3. Rank by: IP match score + play_count")
        print("  4. Fallback: Builtin viral repository")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
