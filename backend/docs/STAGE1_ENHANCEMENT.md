# Stage 1 Enhancement: API Hot Topic Search

## Overview

This document describes the enhancements made to Stage 1 (API Hot Topic Search) of the content creation pipeline.

## Problem Statement

The original implementation had several issues:

1. **Single Source Dependency**: Relied solely on TikHub API, which was unstable
2. **No Fallback**: When APIs failed, returned empty results
3. **Weak IP Matching**: Simple keyword matching instead of semantic understanding
4. **Platform Limitation**: Only supported Douyin, missing XHS/Kuaishou/Bilibili

## Solution

### 1. Multi-Source Hotlist Aggregation

**File**: `app/services/datasource/multi_source_hotlist.py`

Aggregates hot topics from multiple platforms:
- Douyin (via TikHub API)
- Xiaohongshu (with fallback)
- Kuaishou
- Bilibili

**Key Features**:
- Parallel fetching from all platforms
- Timeout handling per source
- Automatic deduplication
- Platform diversity enforcement

**Usage**:

```python
from app.services.datasource.multi_source_hotlist import fetch_multi_source_hotlist

# Fetch hot topics from all platforms
result = await fetch_multi_source_hotlist(ip_profile, limit=20)

# result.items contains HotListItem objects from all platforms
# result.source_stats shows count per platform
```

### 2. Builtin Viral Repository

**File**: `app/services/datasource/builtin_viral_repository.py`

Provides 60+ high-quality viral title templates as ultimate fallback.

**Categories**:
- Mom Entrepreneur (宝妈创业)
- Side Hustle (副业赚钱)
- Knowledge Paid (知识付费)
- Lifestyle (生活方式)
- Emotional Growth (情感成长)
- Skill Teaching (技能教学)
- General (通用)

**Key Features**:
- Automatic IP type detection from profile
- Content type distribution (4-3-2-1 matrix)
- Randomization to avoid repetition

**Usage**:

```python
from app.services.datasource.builtin_viral_repository import get_builtin_repository

repo = get_builtin_repository()
topics = repo.get_topics_for_ip(ip_profile, limit=12)
```

### 3. Smart IP Matcher

**File**: `app/services/smart_ip_matcher.py`

Performs semantic-level matching between titles and IP profiles.

**Dimensions**:
- Domain Match (25%): Professional field alignment
- Audience Match (25%): Target audience fit
- Style Match (20%): Writing style consistency
- Value Match (15%): Value proposition alignment
- Feasibility Match (15%): Content producibility

**Features**:
- Content type detection (money/emotion/skill/life)
- Viral element extraction
- Improvement suggestions

**Usage**:

```python
from app.services.smart_ip_matcher import get_smart_matcher

matcher = get_smart_matcher()

# Get match score
score = matcher.calculate_match_score(title, ip_profile)

# Detailed analysis
result = matcher.analyze_match(title, ip_profile)
# result.overall: 0-1 score
# result.dimensions: per-dimension scores
# result.reasons: why it matches/doesn't match
# result.suggestions: improvement tips
```

### 4. Integrated Fallback Flow

**File**: `app/services/datasource/multi_source_hotlist.py::fetch_hotlist_fallback`

Complete fallback chain:

1. Try multi-source hotlist aggregation
2. If insufficient results, supplement with builtin repository
3. Return combined, deduplicated results

**Guarantee**: Always returns requested number of topics (unless builtin also fails).

## Integration with V4 Recommendation

The V4 recommendation service now uses the enhanced Stage 1:

```python
# In topic_recommendation_v4.py

async def _fetch_other_sources(self, ip_profile, limit):
    # Uses new multi-source + builtin fallback
    return await fetch_hotlist_fallback(ip_profile, limit)

def _calculate_ip_fit(self, topic, ip_profile):
    # Uses smart matcher
    matcher = get_smart_matcher()
    return matcher.calculate_match_score(topic.title, ip_profile)
```

## API Endpoints

### Test Multi-Source Aggregation

```
GET /strategy/v4/multi-source-test?ip_id={ip_id}&limit=12
```

Returns:
- Multi-source fetch statistics
- Per-topic match analysis
- Content type detection
- Viral element extraction

### Get Builtin Topics

```
GET /strategy/v4/builtin-topics?ip_id={ip_id}&limit=12
```

Returns:
- Detected IP types
- Recommended topics from builtin repository
- Match scores

## Configuration

No additional configuration required. The system will:
- Use TikHub API if available
- Fall back to other platforms
- Use builtin repository as ultimate fallback

## Testing

Run the test script:

```bash
cd backend
python test_multi_source_final.py
```

## Benefits

1. **Reliability**: No more empty results when APIs fail
2. **Diversity**: Topics from multiple platforms
3. **Relevance**: Semantic IP matching improves quality
4. **Speed**: Parallel fetching + intelligent fallback

## Next Steps

Stage 2: Enhanced Title Extraction from URLs
- Improve text extraction from competitor links
- Structured title element extraction
