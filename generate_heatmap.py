"""
Reads sector_heatmap_data.json and injects it into the HTML template.
Run after scanner.py to produce sector_heatmap.html
"""
import json, re, os

with open("sector_heatmap_data.json") as f:
    data = json.load(f)

# Read base template
with open("sector_heatmap_template.html") as f:
    html = f.read()

# Inject live data
html = re.sub(
    r"const SCAN_DATA = \{.*?\};",
    f"const SCAN_DATA = {json.dumps(data)};",
    html,
    flags=re.DOTALL
)

with open("sector_heatmap.html", "w") as f:
    f.write(html)

print("✅ sector_heatmap.html generated")
