"""Read a snapshot, emit advice to stdout, optionally append local audit history."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

from jsonschema.exceptions import ValidationError

from .audit import AuditLog
from .engine import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    try:
        if args.audit and args.input.resolve() == args.audit.resolve():
            raise ValueError("Input and audit paths must differ")
        request = json.loads(args.input.read_text(encoding="utf-8"))
        recommendation = evaluate(request)
        if args.audit:
            AuditLog(args.audit).append(request, recommendation)
        print(json.dumps(recommendation, indent=2, allow_nan=False))
    except (ValueError, ValidationError, OSError, sqlite3.Error) as error:
        print(f"Evaluation rejected: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
