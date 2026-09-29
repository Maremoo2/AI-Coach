"""CLI for the append-only athlete experience store."""
import argparse
import json
import sys

from .experience_store import ExperienceStore


def main():
    parser = argparse.ArgumentParser(description="AI Coach athlete experience store")
    parser.add_argument("--db", required=True, help="SQLite experience-store path")
    sub = parser.add_subparsers(dest="command", required=True)

    append_cmd = sub.add_parser("append")
    append_cmd.add_argument("event", help="JSON experience-event file")

    show_cmd = sub.add_parser("show")
    show_cmd.add_argument("experience_id")

    export_cmd = sub.add_parser("export")
    export_cmd.add_argument("--athlete-id", default=None)

    args = parser.parse_args()
    try:
        store = ExperienceStore(args.db)
        if args.command == "append":
            with open(args.event, encoding="utf-8") as source:
                event = json.load(source)
            print(store.append(event))
        elif args.command == "show":
            print(json.dumps(store.materialize(args.experience_id), indent=2, ensure_ascii=True))
        elif args.command == "export":
            print(json.dumps(store.export_learning_rows(args.athlete_id), indent=2, ensure_ascii=True))
    except Exception as exc:
        print(f"ai-coach-experience: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
