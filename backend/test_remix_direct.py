"""
Direct test of enhanced remix (without API)
"""
import sys
import io
import json
sys.path.insert(0, "F:/AI-Native IP/backend")

# Set UTF-8 output
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Mock database, no real DB dependency
class MockIP:
    ip_id = "xiaomin1"
    nickname = "Xiaomin"
    name = "Xiaomin"
    style_features = "Friendly, professional, warm, approachable"
    vocabulary = "medical, health, wellness, care"
    tone = "friendly professional"
    catchphrases = "Girls, listen to me, really"

# Mock get_db
class MockDB:
    def query(self, *args):
        class Query:
            def filter(self, *args):
                return self
            def first(self):
                return MockIP()
        return Query()
    def close(self):
        pass

import app.services.enhanced_remix_pipeline as pipeline
pipeline.get_db = lambda: MockDB()

# Import core functions
from app.services.enhanced_remix_pipeline import create_enhanced_remix

# Test
ip_profile = {
    "name": "Xiaomin",
    "style_features": "Friendly, professional, warm, approachable",
    "vocabulary": "medical, health, wellness, care",
    "tone": "friendly professional",
    "catchphrases": "Girls, listen to me, really",
}

competitor_content = """Not that physical retail is hard to do, nor that there's no hope for physical stores. 
There are still many physical stores doing very well, even better than before. 
If you can read through these four points I summarize, I'm sure you'll be enlightened.

#physical economy #business tips #business model"""

print("Testing enhanced remix...")

result = create_enhanced_remix(
    ip_id="xiaomin1",
    ip_profile=ip_profile,
    competitor_content=competitor_content,
    topic="physical economy",
    viral_elements=["contrast", "crowd"],
    max_iterations=1
)

# Save result to file
output = {
    "content_length": len(result.get('content', '')),
    "content": result.get('content', ''),
    "quality": result.get('quality', {}),
    "structure": result.get('structure', {}),
    "viral_elements": result.get('viral_elements', []),
    "elevations": result.get('elevations', [])
}

with open("F:/AI-Native IP/backend/remix_output.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("Result saved to remix_output.json")
print(f"Content length: {output['content_length']}")
print(f"Quality score: {output['quality'].get('overall', 'N/A')}")
print(f"Structure: {output['structure'].get('hook', 'N/A')}")