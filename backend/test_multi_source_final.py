"""
Multi-source Hotlist Demo
Test Stage 1 Enhancement
"""

import asyncio
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

from app.services.datasource.multi_source_hotlist import (
    get_multi_source_aggregator,
    fetch_hotlist_fallback,
)
from app.services.datasource.builtin_viral_repository import get_builtin_repository
from app.services.smart_ip_matcher import get_smart_matcher


async def test_builtin_repository():
    """Test builtin viral repository"""
    print("\n" + "=" * 60)
    print("Test: Builtin Viral Repository")
    print("=" * 60)
    
    repo = get_builtin_repository()
    
    # Test IP profile
    profile = {
        "name": "Test IP",
        "expertise": "Mom entrepreneurship, side hustle",
        "content_direction": "Women growth",
        "target_audience": "Moms",
    }
    
    print(f"\nIP Profile: {profile['name']}")
    
    # Detect IP type
    ip_types = repo.detect_ip_type(profile)
    print(f"Detected types: {[t.value for t in ip_types]}")
    
    # Get topics
    topics = repo.get_topics_for_ip(profile, limit=3)
    print(f"Got {len(topics)} topics")
    
    for i, topic in enumerate(topics, 1):
        # Only print ASCII-safe characters
        title_ascii = topic.title.encode('ascii', 'ignore').decode('ascii')
        print(f"  {i}. {title_ascii[:40]}...")
        print(f"     Type: {topic.extra.get('content_type')}")
    
    return len(topics) > 0


async def test_smart_matcher():
    """Test smart IP matcher"""
    print("\n" + "=" * 60)
    print("Test: Smart IP Matcher")
    print("=" * 60)
    
    matcher = get_smart_matcher()
    
    ip_profile = {
        "name": "Mom Entrepreneur",
        "expertise": "Mom entrepreneurship, side hustle",
        "target_audience": "Moms, women",
    }
    
    test_titles = [
        "From 0 to 30k monthly: Mom side hustle",
        "Python programming tutorial",
    ]
    
    print(f"\nIP: {ip_profile['name']}")
    
    for title in test_titles:
        match_result = matcher.analyze_match(title, ip_profile)
        content_type, confidence = matcher.detect_content_type(title)
        
        title_ascii = title.encode('ascii', 'ignore').decode('ascii')
        print(f"\n  Title: {title_ascii}")
        print(f"  - Match Score: {match_result.overall:.2f}")
        print(f"  - Content Type: {content_type}")
        print(f"  - Dimensions: {match_result.dimensions}")
    
    return True


async def test_integrated_flow():
    """Test complete flow"""
    print("\n" + "=" * 60)
    print("Test: Integrated Flow")
    print("=" * 60)
    
    ip_profile = {
        "name": "Test IP",
        "expertise": "Mom entrepreneurship, side hustle",
        "content_direction": "Women growth",
        "target_audience": "Moms",
    }
    
    print(f"\nFetching recommendations...")
    
    topics = await fetch_hotlist_fallback(ip_profile, limit=5)
    
    print(f"Got {len(topics)} topics")
    
    matcher = get_smart_matcher()
    for i, topic in enumerate(topics[:3], 1):
        match_score = matcher.calculate_match_score(topic.title, ip_profile)
        source = "Builtin" if topic.extra.get("is_builtin") else "Multi-source"
        
        title_ascii = topic.title.encode('ascii', 'ignore').decode('ascii')
        print(f"\n  {i}. [{source}] Match: {match_score:.2f}")
        print(f"      {title_ascii[:50]}...")
    
    return len(topics) > 0


async def main():
    """Main test function"""
    print("=" * 60)
    print("Stage 1 Enhancement Test")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("Builtin Repository", await test_builtin_repository()))
        results.append(("Smart Matcher", await test_smart_matcher()))
        results.append(("Integrated Flow", await test_integrated_flow()))
        
        print("\n" + "=" * 60)
        print("Test Results:")
        print("=" * 60)
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            print(f"  {name}: {status}")
        
        all_passed = all(r[1] for r in results)
        print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
