"""heldout 픽스처와 기대 출력(.expected.tsv) 생성기 — 골든 CLI 로 산출해 하드코딩한다.

재생성: `python gen_expected.py` (이 디렉터리에서). 결정론적(입력 고정)이다.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
GOLDEN = HERE.parent / "check_licenses.py"

FIXTURES: dict[str, list[dict]] = {
    # 게이트: 보이는 테스트 수준의 단일 식별자 4종.
    "basic": [
        {"name": "alpha", "license": "MIT"},
        {"name": "beta", "license": "GPL-3.0-only"},
        {"name": "gamma", "license": "LGPL-2.1-only"},
        {"name": "delta", "license": "WTFPL"},
    ],
    # 그룹 ①: 중첩 괄호 × OR/AND 혼합.
    "nested": [
        {"name": "n01", "license": "(MIT OR GPL-3.0-only) AND BSD-3-Clause"},
        {"name": "n02", "license": "GPL-2.0-only OR (Apache-2.0 AND UNKNOWN-1.0)"},
        {"name": "n03", "license": "(MIT AND ISC) OR GPL-2.0-only"},
        {"name": "n04", "license": "MIT AND (ISC OR AGPL-3.0-only)"},
        {"name": "n05", "license": "MIT AND (AGPL-3.0-only OR UNKNOWN-2.0)"},
        {
            "name": "n06",
            "license": "((MIT OR (GPL-2.0-only AND UNKNOWN-1.0)) AND (BSD-2-Clause OR AGPL-3.0-only))",
        },
        {"name": "n07", "license": "(GPL-2.0-only OR GPL-3.0-only) OR LGPL-2.1-only"},
        {"name": "n08", "license": "(MIT OR ISC) AND (BSD-2-Clause OR BSD-3-Clause)"},
    ],
    # 그룹 ②: WITH 의미론 · 괄호 없는 결합 우선순위(WITH > AND > OR).
    "withprec": [
        {"name": "w01", "license": "Apache-2.0 WITH LLVM-exception"},
        {"name": "w02", "license": "GPL-2.0-only WITH Classpath-exception-2.0"},
        {"name": "w03", "license": "(Apache-2.0 WITH LLVM-exception) AND MIT"},
        {"name": "w04", "license": "MIT OR GPL-3.0-only AND UNKNOWN-1.0"},
        {"name": "w05", "license": "GPL-2.0-only WITH Classpath-exception-2.0 OR MIT"},
        {"name": "w06", "license": "LGPL-2.1-only WITH Some-exception AND MIT"},
    ],
    # 그룹 ③: 대소문자·공백 관용, 파싱 불가, deny 사유 우선순위, 필드 결손.
    "lexical": [
        {"name": "l01", "license": "mit"},
        {"name": "l02", "license": "APACHE-2.0   and   isc"},
        {"name": "l03", "license": "bsd-3-clause or gpl-3.0-only"},
        {"name": "l04", "license": "MIT AND"},
        {"name": "l05", "license": "(MIT OR ISC"},
        {"name": "l06", "license": ""},
        {"name": "l07", "license": "UNKNOWN-1.0 OR LGPL-3.0-only"},
        {"name": "l08"},
        {"name": "l09", "license": 42},
    ],
    # exit code 계약 검사용.
    "allow_all": [
        {"name": "one", "license": "MIT"},
        {"name": "two", "license": "ISC OR MIT"},
        {"name": "three", "license": "Apache-2.0 WITH LLVM-exception"},
    ],
    "one_deny": [
        {"name": "safe-a", "license": "MIT"},
        {"name": "safe-b", "license": "BSD-2-Clause"},
        {"name": "bad-c", "license": "AGPL-3.0-only"},
    ],
    # 출력 형식·정렬 검사용(입력 순서는 비정렬, 이름에 대소문자 혼재).
    "format": [
        {"name": "mango", "license": "MIT"},
        {"name": "Zebra", "license": "GPL-2.0-only"},
        {"name": "apple", "license": "ISC"},
        {"name": "berry-2", "license": "LGPL-3.0-only"},
        {"name": "berry", "license": "Apache-2.0"},
    ],
}


def main() -> None:
    for stem, packages in FIXTURES.items():
        fixture = HERE / f"{stem}.json"
        fixture.write_text(json.dumps(packages, ensure_ascii=False, indent=1) + "\n", "utf-8")
        proc = subprocess.run(
            [sys.executable, str(GOLDEN), str(fixture)], capture_output=True, text=True, timeout=30
        )
        expected = HERE / f"{stem}.expected.tsv"
        expected.write_text(f"exit={proc.returncode}\n{proc.stdout}", encoding="utf-8")
        print(f"{stem}: exit={proc.returncode}, {len(proc.stdout.splitlines())} lines")


if __name__ == "__main__":
    main()
