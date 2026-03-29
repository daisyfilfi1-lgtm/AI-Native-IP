"""
测试环节2：爆款链接 → 提取内容

测试场景：
1. 单条链接提取
2. 批量链接提取  
3. 完整流程（环节1+2组合）
"""

import asyncio
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

# 设置API Key
os.environ["TIKHUB_API_KEY"] = "k6ANCMEu1nWQhW2vRIel/y3ucxi0XoQyzwuJhE/ZBvWr1W+4FmaNU2KDKw=="

from app.services.smart_content_extractor import extract_content, extract_content_for_remix


async def test_single_extraction():
    """测试单条链接提取"""
    print("=" * 70)
    print("Test 1: Single URL Extraction")
    print("=" * 70)
    
    # 使用已知的抖音链接（来自之前的测试）
    test_url = "https://www.douyin.com/video/7428114719"  # 顶妈的一个视频
    
    print(f"\nExtracting: {test_url}")
    
    result = await extract_content(test_url, use_cache=False)
    
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Platform: {result.platform}")
    print(f"  Method: {result.extract_method}")
    
    if result.success:
        print(f"\n  Title: {result.title[:60]}..." if len(result.title) > 60 else f"\n  Title: {result.title}")
        print(f"  Hook: {result.hook[:50]}..." if result.hook else "  Hook: [empty]")
        print(f"  Body: {result.body[:50]}..." if result.body else "  Body: [empty]")
        print(f"  CTA: {result.cta[:50]}..." if result.cta else "  CTA: [empty]")
        print(f"\n  Tags: {result.tags}")
        print(f"  Keywords: {result.keywords[:5]}")
        print(f"  Viral Elements: {result.viral_elements}")
        print(f"\n  Content Structure:")
        for k, v in result.content_structure.items():
            print(f"    {k}: {v}")
        
        return True
    else:
        print(f"  Error: {result.error}")
        return False


async def test_extract_for_remix():
    """测试为仿写优化的提取"""
    print("\n" + "=" * 70)
    print("Test 2: Extract for Remix (Structured)")
    print("=" * 70)
    
    test_url = "https://www.douyin.com/video/7428114719"
    
    print(f"\nExtracting: {test_url}")
    
    result = await extract_content_for_remix(test_url)
    
    print(f"\nResult:")
    print(f"  Success: {result['success']}")
    
    if result['success']:
        structure = result.get('structure', {})
        print(f"\n  Structured Content:")
        print(f"    Title: {structure.get('title', '')[:60]}")
        print(f"    Hook: {structure.get('hook', '')[:50]}")
        print(f"    Body: {structure.get('body', '')[:50]}")
        print(f"    CTA: {structure.get('cta', '')[:50]}")
        print(f"\n    Tags: {structure.get('tags', [])}")
        print(f"    Viral Elements: {structure.get('viral_elements', [])}")
        
        metadata = result.get('metadata', {})
        print(f"\n  Metadata:")
        print(f"    Platform: {metadata.get('platform')}")
        print(f"    Author: {metadata.get('author')}")
        print(f"    Likes: {metadata.get('like_count')}")
        print(f"    Method: {metadata.get('extract_method')}")
        
        print(f"\n  Full Text (for remix):\n{result.get('original_text', '')[:200]}...")
        
        return True
    else:
        print(f"  Error: {result.get('error')}")
        return False


async def test_batch_extraction():
    """测试批量提取"""
    print("\n" + "=" * 70)
    print("Test 3: Batch URL Extraction")
    print("=" * 70)
    
    # 多个测试链接
    test_urls = [
        "https://www.douyin.com/video/7428114719",  # 顶妈
        "https://www.douyin.com/video/7539467800",  # 淘淘子
    ]
    
    print(f"\nExtracting {len(test_urls)} URLs...")
    
    from app.services.smart_content_extractor import extract_content_for_remix
    
    results = []
    for url in test_urls:
        result = await extract_content_for_remix(url)
        results.append((url, result))
    
    print(f"\nResults:")
    for url, result in results:
        status = "✓" if result.get("success") else "✗"
        title = result.get("structure", {}).get("title", "")[:30]
        print(f"  {status} {url[:50]}... -> {title}...")
    
    successful = sum(1 for _, r in results if r.get("success"))
    print(f"\nSuccessful: {successful}/{len(test_urls)}")
    
    return successful > 0


async def main():
    """主测试"""
    print("\n" + "=" * 70)
    print("Stage 2 Pipeline Test: URL → Extracted Content")
    print("=" * 70)
    print("\nStage 2 Flow:")
    print("  Input: Video URL (from Stage 1)")
    print("  Output: Structured Content (Title/Hook/Body/CTA/Tags)")
    
    results = []
    
    try:
        results.append(("Single Extraction", await test_single_extraction()))
        results.append(("Extract for Remix", await test_extract_for_remix()))
        results.append(("Batch Extraction", await test_batch_extraction()))
        
        print("\n" + "=" * 70)
        print("Test Summary")
        print("=" * 70)
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            print(f"  {name}: {status}")
        
        all_passed = all(r[1] for r in results)
        
        print("\n" + "=" * 70)
        if all_passed:
            print("ALL TESTS PASSED!")
            print("=" * 70)
            print("\nStage 2 is ready:")
            print("  ✓ Single URL extraction")
            print("  ✓ Structured content output")
            print("  ✓ Batch processing")
            print("\nAPI Endpoints:")
            print("  POST /strategy/v4/extract-content")
            print("  POST /strategy/v4/extract-content/batch")
            print("  POST /strategy/v4/competitor-full-pipeline (Stage 1+2)")
        else:
            print("SOME TESTS FAILED")
            print("=" * 70)
            
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
