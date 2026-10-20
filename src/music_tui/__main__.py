import sys


def main() -> int:
    if "--version" in sys.argv:
        print("music-tui 0.1.0")
        return 0
    print("not implemented yet")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())