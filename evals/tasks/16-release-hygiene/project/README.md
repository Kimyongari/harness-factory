# shipit

![version](https://img.shields.io/badge/version-0.2.9-blue)

소형 배포 CLI.

## 사용법

    shipit --version
    shipit deploy
    shipit rollback

## 릴리스 절차

1. 버전 문자열을 갱신한다 (pyproject.toml · src/cli.py · 이 README 의 배지).
2. `python scripts/check_release.py` 로 버전 일치를 확인한다.
3. CHANGELOG.md 를 갱신하고 릴리스 커밋과 태그를 만든다.
