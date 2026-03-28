import sys
import io
import json
import os

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, "F:/AI-Native IP/backend")

# Test step by step
from app.services.competitor_analyzer import analyze_competitor_structure

test_content = "Not that physical retail is hard to do. There are still many stores doing very well."

print("Step 1: Competitor structure...")
structure = analyze_competitor_structure(test_content)

print("Step 2: Viewpoint elevation...")
from app.services.viewpoint_elevation import elevate_viewpoint
ip_style = {"name": "Xiaomin", "style_features": "friendly", "catchphrases": "Girls, listen"}
elevation = elevate_viewpoint(
    original_viewpoint="Physical retail is hard",
    ip_style=ip_style,
    ip_assets="No assets",
    structure_info="hook: empathy"
)

print("Step 3: LLM generation...")
from app.services.ai_client import chat
result = chat([{"role": "user", "content": "Generate a short message: say hello"}])

# Save results
output = {
    "step1_structure": structure,
    "step2_elevation": str(elevation)[:200] if elevation else "N/A",
    "step3_chat": result
}

with open("F:/AI-Native IP/backend/test_output.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("Done - saved to test_output.json")