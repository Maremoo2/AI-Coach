"""CLI for materializing a Personal Response Profile from the local Experience Store."""
import argparse
import json
import sys
from datetime import datetime, timezone

from .experience_store import ExperienceStore
from .profile import build_personal_response_profile, render_profile_summary


def main():
    parser = argparse.ArgumentParser(description="Materialize AI Coach personal response profile")
    parser.add_argument("--db", required=True, help="SQLite experience-store path")
    parser.add_argument("--athlete-id", default=None)
    parser.add_argument("--as-of", default=None, help="ISO-8601 timestamp; defaults to current UTC")
    parser.add_argument("--language", choices=("no", "en"), default="no")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    try:
        as_of = args.as_of or datetime.now(timezone.utc).isoformat()
        rows = ExperienceStore(args.db).export_learning_rows(args.athlete_id)
        profile = build_personal_response_profile(rows, as_of, args.athlete_id)
        if args.summary_only:
            print(json.dumps(render_profile_summary(profile, args.language), indent=2, ensure_ascii=True))
        else:
            profile["summary"] = render_profile_summary(profile, args.language)
            print(json.dumps(profile, indent=2, ensure_ascii=True))
    except Exception as exc:
        print(f"ai-coach-profile: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
