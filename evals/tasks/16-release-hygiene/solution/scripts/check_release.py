"""릴리스 전 버전 일치 검사 — exit 0 이면 통과.

버전 문자열은 세 곳에 있다: pyproject.toml, src/cli.py, README.md 배지.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)


def cli_version() -> str:
    text = (ROOT / "src" / "cli.py").read_text(encoding="utf-8")
    return re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)


def readme_version() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return re.search(r"badge/version-([0-9][^-]*)-", text).group(1)


def main() -> int:
    versions = {
        "pyproject.toml": pyproject_version(),
        "src/cli.py": cli_version(),
        "README.md": readme_version(),
    }
    if len(set(versions.values())) != 1:
        for name, found in versions.items():
            print(f"  {name}: {found}", file=sys.stderr)
        print("버전 불일치 — 위 파일들을 맞춘 뒤 다시 실행하세요", file=sys.stderr)
        return 1
    print(f"버전 일치: {versions['pyproject.toml']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
