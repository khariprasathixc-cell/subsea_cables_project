import re

with open('frontend/app.js', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print("=== Check for .addTo(map) calls ===\n")
for i, line in enumerate(lines, 1):
    if '.addTo(map)' in line:
        print(f"Line {i}: {line.strip()}")

print("\n=== Check for .addTo(markerLayerGroup) calls ===\n")
for i, line in enumerate(lines, 1):
    if '.addTo(markerLayerGroup)' in line:
        print(f"Line {i}: {line.strip()}")
