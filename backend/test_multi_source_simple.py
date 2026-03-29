"""
Multi-source Hotlist Demo (ASCII version for Windows)
"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.services.datasource.multi_source_hotlist import (
    get_multi_source_aggregator,
    fetch_hotlist_fallback,
)
from app.services.datasource.builtin_viral_repository import get_builtin_repository
from app.services.smart_ip_matcher import get_smart_matcher


async def demo_builtin_repository():
    """Demo builtin viral repository"""
    print("\n" + "=" * 60)
    print("Demo: Builtin Viral Repository")
    print("=" * 60)
    
    repo = get_builtin_repository()
    
    # Test different IP profiles
    test_profiles = [
        {
            "name": "Mom Entrepreneur IP",
            "expertise": "Mom entrepreneurship, side hustle, make money at home",
            "content_direction": "Women growth, financial independence",
            "target_audience": "Moms, women who want to make money",
        },
        {
            "name": "Knowledge Paid IP",
            "expertise": "Knowledge monetization, course creation, personal brand",
            "content_direction": "Knowledge paid, content entrepreneurship",
            "target_audience": "Knowledge workers, professionals",
        },
    ]
    
    for profile in test_profiles:
        print(f"\nIP Profile: {profile['name']}")
        
        # Detect IP type
        ip_types = repo.detect_ip_type(profile)
        print(f"  Detected types: {[t.value for t in ip_types]}")
        
        # Get recommended topics
        topics = repo.get_topics_for_ip(profile, limit=3)
        print(f"  Recommended topics:")
        for i, topic in enumerate(topics, 1):
            print(f"    {i}. {topic.title[:50]}...")
            print(f"       Type: {topic.extra.get('content_type')} | Tags: {topic.tags[:3]}")


async def demo_smart_matcher():
    """Demo smart IP matcher"""
    print("\n" + "=" * 60)
    print("Demo: Smart IP Matcher")
    print("=" * 60)
    
    matcher = get_smart_matcher()
    
    ip_profile = {
        "name": "Mom Entrepreneur Mentor",
        "expertise": "Mom entrepreneurship, side hustle, make money at home",
        "content_direction": "Women growth, financial independence",
        "target_audience": "Moms, women who want to make money",
        "unique_value_prop": "Help moms earn 10k+ monthly at home",
        "style_features": "Friendly, down-to-earth, inspirational",
    }
    
    test_titles = [
        "From 0 to 30k monthly: This mom's side hustle method is amazing",
        "After being laid off at 35, I earn 50k monthly with this",
        "Python programming tutorial",
        "Latest phone review 2024",
    ]
    
    print(f"\nIP Profile: {ip_profile['name']}")
    print(f"  Expertise: {ip_profile['expertise']}")
    print(f"  Audience: {ip_profile['target_audience']}")
    
    print(f"\n  Title Matching Analysis:")
    for title in test_titles:
        match_result = matcher.analyze_match(title, ip_profile)
        content_type, confidence = matcher.detect_content_type(title)
        viral_elements = matcher.extract_viral_elements(title)
        
        print(f"\n    Title: {title[:45]}...")
        print(f"    - Match Score: {match_result.overall:.2f}")
        print(f"    - Content Type: {content_type} (confidence: {confidence:.2f})")
        print(f"    - Viral Elements: {viral_elements}")


async def demo_integrated_flow():
    """Demo complete flow"""
    print("\n" + "=" * 60)
    print("Demo: Complete Flow (Multi-source + Builtin + IP Match)")
    print("=" * 60)
    
    ip_profile = {
        "name": "Mom Entrepreneur Mentor",
        "expertise": "Mom entrepreneurship, side hustle, make money at home",
        "content_direction": "Women growth, financial independence",
        "target_audience": "Moms, women who want to make money",
    }
    
    print(f"\nGetting recommendations for IP: {ip_profile['name']}")
    
    # Use new fetch_hotlist_fallback function
    topics = await fetch_hotlist_fallback(ip_profile, limit=8)
    
    print(f"  Got {len(topics)} topics")
    print(f"\n  Recommendations:")
    
    # Analyze match score for each topic
    matcher = get_smart_matcher()
    for i, topic in enumerate(topics[:5], 1):
        match_score = matcher.calculate_match_score(topic.title, ip_profile)
        source = "Builtin" if topic.extra.get("is_builtin") else "Multi-source"
        
        print(f"\n  {i}. [{source}] Match: {match_score:.2f}")
        print(f"      {topic.title}")


async def main():
    """Main function"""
    print("=" * 60)
    print("Stage 1 Enhancement Demo: API Hot Topic Search")
    print("=" * 60)
    print("\nNew Features:")
    print("1. Multi-source hotlist aggregation (Douyin+XHS+Kuaishou+Bilibili)")
    print("2. Builtin viral repository fallback (60+ high-quality templates)")
    print("3. Smart IP matching (semantic analysis)")
    
    try:
        await demo_builtin_repository()
        await demo_smart_matcher()
        await demo_integrated_flow()
        
        print("\n" + "=" * 60)
        print("Demo completed!")
        print("=" * 60)
        print("\nEnhancement Highlights:")
        print("- Multi-platform hotlist aggregation for richer data sources")
        print("- Automatic builtin fallback when APIs fail")
        print("- Smart filtering and sorting based on IP profile")
        print("- Semantic-level matching, not just keywords")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
