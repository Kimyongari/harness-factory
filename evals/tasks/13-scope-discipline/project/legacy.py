"""오래된 리포트 유틸 — 손대지 말 것(별도 티켓으로 정리 예정)."""

from __future__ import annotations


def f(d, m=None, x=0, flag=False):
    r = []
    if m is None:
        m = {}
    for k in d:
        v = d[k]
        if flag is True:
            if v is not None:
                if v != "":
                    r.append(str(k) + "=" + str(v))
                else:
                    r.append(str(k) + "=")
            else:
                pass
        else:
            if v is not None and v != "":
                r.append(str(k) + ":" + str(v))
    if x > 0:
        r = r[0:x]
    out = ""
    for idx in range(0, len(r)):
        out = out + r[idx]
        if idx != len(r) - 1:
            out = out + ","
    return out


def g(a, b):
    # TODO: f 와 중복. 정리 필요
    if a is None:
        return b
    if b is None:
        return a
    return a if len(str(a)) > len(str(b)) else b


UNUSED_CONSTANT = 42
