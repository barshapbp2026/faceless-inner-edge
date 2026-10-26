#!/bin/bash
cd ~/faceless-factory
source venv/bin/activate

echo "=== [1/6] Researching fresh topic ==="
python3 scripts/researcher.py

echo "=== [2/6] Generating script, voice, and clips ==="
python3 scripts/day2_fix.py

echo "=== [3/6] Adding highlighted captions ==="
python3 scripts/add_captions_highlight.py

echo "=== [4/6] Uploading to YouTube ==="
python3 scripts/upload_youtube.py

echo "=== [5/6] Uploading to Instagram ==="
python3 scripts/upload_instagram_cloudinary.py

echo "=== [6/6] Sending X notification ==="
python3 scripts/notify.py

echo ""
echo "PIPELINE COMPLETE"
