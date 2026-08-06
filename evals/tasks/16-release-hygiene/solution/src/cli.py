"""shipit — 소형 배포 CLI."""

import sys

__version__ = "0.4.0"


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--version"]:
        print(__version__)
        return 0
    if args[:1] == ["deploy"]:
        print("deploy: 대상 없음 (드라이런)")
        return 0
    if args[:1] == ["rollback"]:
        print("rollback: 이전 배포 없음")
        return 1
    print("usage: shipit [--version] <deploy|rollback>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
