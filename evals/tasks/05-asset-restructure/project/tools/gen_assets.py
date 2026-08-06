#!/usr/bin/env python3
"""assets_manifest.json 대로 assets/ 파일을 생성한다 (파일명 → 내용)."""

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "assets_manifest.json").read_text(encoding="utf-8"))
assets = root / "assets"
assets.mkdir(exist_ok=True)
for name, content in manifest.items():
    (assets / name).write_text(content + "\n", encoding="utf-8")
print(f"generated {len(manifest)} files in {assets}")
