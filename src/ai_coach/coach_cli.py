"""CLI for a normalized v1 daily coach context."""

import argparse
import json
import sys

from .coach import build_daily_brief


def main():
    parser = argparse.ArgumentParser(description="Build an HQ-bounded AI Coach v1 daily brief")
    parser.add_argument("context", help="Path to normalized coach-context JSON")
    args = parser.parse_args()
    try:
        with open(args.context, encoding="utf-8") as source:
            context = json.load(source)
        print(json.dumps(build_daily_brief(context), indent=2, ensure_ascii=True))
    except Exception as exc:
        print(f"ai-coach-v1: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
