#!/bin/bash
echo "=== [1/4] Researching Topic & Generating 5-Min Video ==="
python3 scripts/researcher.py
python3 scripts/day2_long.py

echo "=== [2/4] Adding Highlighted Captions ==="
python3 scripts/add_captions_highlight.py

echo "=== [3/4] Uploading to YouTube as PUBLIC ==="
python3 scripts/upload_youtube_long.py

echo "=== LONG PIPELINE COMPLETE ==="
