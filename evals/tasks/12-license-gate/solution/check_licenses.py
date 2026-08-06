"""SPDX 라이선스 식 평가기 — POLICY.md 의 골든 구현.

사용법: python check_licenses.py <deps.json>
출력: 패키지당 `이름<TAB>allow|deny<TAB>사유` (이름 오름차순), deny 가 하나라도 있으면 exit 1.
"""

import json
import sys
from pathlib import Path

ALLOWED = {"mit", "bsd-2-clause", "bsd-3-clause", "apache-2.0", "isc"}
FORBIDDEN = {
    "gpl-2.0-only",
    "gpl-2.0-or-later",
    "gpl-3.0-only",
    "gpl-3.0-or-later",
    "agpl-3.0-only",
    "agpl-3.0-or-later",
    "gpl-2.0",
    "gpl-2.0+",
    "gpl-3.0",
    "gpl-3.0+",
    "agpl-3.0",
}
CONDITIONAL = {
    "lgpl-2.1-only",
    "lgpl-2.1-or-later",
    "lgpl-3.0-only",
    "lgpl-3.0-or-later",
    "lgpl-2.1",
    "lgpl-2.1+",
    "lgpl-3.0",
    "lgpl-3.0+",
}

OK, FORB, COND, UNK = "ok", "forbidden", "conditional", "unknown"
_DENY_ORDER = [FORB, COND, UNK]  # 정책 §7: deny 사유 우선순위
_OPERATORS = {"and", "or", "with"}


class ParseError(ValueError):
    pass


def _classify(identifier: str) -> str:
    lowered = identifier.lower()
    if lowered in ALLOWED:
        return OK
    if lowered in FORBIDDEN:
        return FORB
    if lowered in CONDITIONAL:
        return COND
    return UNK


def _pick_deny(verdicts: list[str]) -> str:
    denies = [v for v in verdicts if v != OK]
    return min(denies, key=_DENY_ORDER.index)


def _combine_or(verdicts: list[str]) -> str:
    return OK if OK in verdicts else _pick_deny(verdicts)


def _combine_and(verdicts: list[str]) -> str:
    return OK if all(v == OK for v in verdicts) else _pick_deny(verdicts)


class _Parser:
    """재귀 하강 파서. 결합 우선순위: WITH > AND > OR (정책 §6)."""

    def __init__(self, expression: str):
        self.tokens = expression.replace("(", " ( ").replace(")", " ) ").split()
        self.pos = 0

    def _peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _peek_op(self) -> str | None:
        token = self._peek()
        return token.lower() if token and token.lower() in _OPERATORS else None

    def _next(self) -> str:
        token = self._peek()
        if token is None:
            raise ParseError("식이 도중에 끝남")
        self.pos += 1
        return token

    def parse(self) -> str:
        if not self.tokens:
            raise ParseError("빈 식")
        verdict = self._parse_or()
        if self._peek() is not None:
            raise ParseError(f"남은 토큰: {self._peek()}")
        return verdict

    def _parse_or(self) -> str:
        verdicts = [self._parse_and()]
        while self._peek_op() == "or":
            self._next()
            verdicts.append(self._parse_and())
        return _combine_or(verdicts)

    def _parse_and(self) -> str:
        verdicts = [self._parse_with()]
        while self._peek_op() == "and":
            self._next()
            verdicts.append(self._parse_with())
        return _combine_and(verdicts)

    def _parse_with(self) -> str:
        verdict = self._parse_atom()
        while self._peek_op() == "with":
            self._next()
            exception = self._peek()
            if exception is None or exception in "()" or exception.lower() in _OPERATORS:
                raise ParseError("WITH 뒤에 예외 식별자가 없음")
            self._next()  # 예외 조항은 판정에 영향 없음(정책 §5: 기반 라이선스 기준)
        return verdict

    def _parse_atom(self) -> str:
        token = self._next()
        if token == "(":
            verdict = self._parse_or()
            if self._next() != ")":
                raise ParseError("닫는 괄호 없음")
            return verdict
        if token == ")" or token.lower() in _OPERATORS:
            raise ParseError(f"식별자 자리에 {token!r}")
        return _classify(token)


def evaluate(expression) -> str:
    """식 하나를 판정 사유(ok/forbidden/conditional/unknown)로 평가한다."""
    if not isinstance(expression, str) or not expression.strip():
        return UNK
    try:
        return _Parser(expression).parse()
    except ParseError:
        return UNK


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python check_licenses.py <deps.json>", file=sys.stderr)
        return 2
    packages = json.loads(Path(argv[1]).read_text(encoding="utf-8"))

    rows = []
    for package in packages:
        name = str(package.get("name", ""))
        rows.append((name, evaluate(package.get("license"))))
    rows.sort(key=lambda row: row[0])

    any_deny = False
    for name, verdict in rows:
        decision = "allow" if verdict == OK else "deny"
        any_deny = any_deny or decision == "deny"
        print(f"{name}\t{decision}\t{verdict}")
    return 1 if any_deny else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
