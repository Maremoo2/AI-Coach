"""Read-only Tredict snapshot ingestion. Never creates HQ_PLAN or recommendations."""
import argparse
import csv
import io
import json
import math
import re
from collections import Counter
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .contracts import canonical, digest, instant, require
from .journal import Journal, utc_now


def csv_rows(result):
    if 'pages' in result:
        return [row for page in result['pages'] for row in csv_rows(page)]
    require(not result.get('isError'), 'Connector reported an error')
    text = '\n'.join(c.get('text', '') for c in result.get('content', []) if c.get('type') == 'text')
    parts = re.split(r'(?m)^\s*----\s*$', text, maxsplit=1)
    require(len(parts) == 2, 'Missing CSV payload; do not treat an unreadable response as empty history')
    reader = csv.DictReader(io.StringIO(parts[1].strip()))
    rows = list(reader)
    require(reader.fieldnames is not None and all(None not in row for row in rows), 'Malformed CSV')
    return rows


def number(value):
    if value in (None, ''):
        return None
    result = float(value)
    require(math.isfinite(result) and result >= 0, 'Invalid nonnegative metric')
    return result


def normalize_activities(result, collected_at, window_start, timezone):
    rows, seen = [], set()
    for raw in csv_rows(result):
        key = raw['id']
        require(key and key not in seen, 'Duplicate activity ID')
        seen.add(key)
        when = instant(raw['date'])
        require(instant(window_start) <= when <= instant(collected_at), 'Activity outside import window')
        rows.append({'id': key, 'date': raw['date'], 'local_date': when.astimezone(ZoneInfo(timezone)).date().isoformat(),
                     'sport': raw['sportType'], 'subsport': raw.get('subSportType'),
                     'title': raw.get('title') or raw.get('subSportType') or raw['sportType'],
                     'duration_sec': number(raw.get('summary.duration')),
                     'elapsed_sec': number(raw.get('summary.durationTotal')),
                     'distance_m': number(raw.get('summary.distance')),
                     'source_ref': 'tredict:activity:' + key,
                     'response_status': 'UNKNOWN'})
    return sorted(rows, key=lambda r: (r['date'], r['id']))


def normalize_plans(result, timezone, start, end):
    rows, seen = [], set()
    for raw in csv_rows(result):
        key = raw['id']
        require(key and key not in seen, 'Duplicate planned workout ID')
        seen.add(key)
        when = instant(raw['date'])
        require(instant(start) <= when <= instant(end), 'Plan outside import window')
        title = raw.get('title') or raw['sportType']
        seconds = number(raw.get('duration'))
        match = re.search(r'(\d+)\s*[–-]\s*(\d+)\s*min', title)
        bounds = [int(match[1]), int(match[2])] if match else None
        conflict = bool(bounds and seconds is not None and not bounds[0] <= seconds / 60 <= bounds[1])
        note = 'Varighet mangler i struktur; se HQ-tittel og protokoll.' if seconds is None else f'Struktur: {seconds / 60:g} min.'
        if conflict:
            note += ' Avvik mellom tittel og struktur: må avklares av HQ, ikke automatisk korrigert.'
        rows.append({'id': key, 'date': raw['date'], 'local_date': when.astimezone(ZoneInfo(timezone)).date().isoformat(),
                     'title': title, 'sport': raw['sportType'], 'notes': raw.get('notes') or '',
                     'duration_sec': seconds, 'title_range_min': bounds, 'dose_conflict': conflict, 'dose_note': note,
                     'executed_activity_id': raw.get('executedTrainingId') or None,
                     'source_ref': 'tredict:planned:' + key, 'source_updated_at': raw.get('updatedAt')})
    return sorted(rows, key=lambda r: (r['date'], r['id']))


def build_snapshot(*, athlete_id, source_facts, context, collected_at, window_start, plan_start, plan_end, timezone):
    canonical(context)
    require(isinstance(context.get('goals'), list) and context['goals'], 'Goals with provenance required')
    require(all(isinstance(g.get('description'), str) and g.get('source_ref') for g in context['goals']), 'Goal provenance missing')
    activities = normalize_activities(source_facts['activities'], collected_at, window_start, timezone)
    plans = normalize_plans(source_facts['plans'], timezone, plan_start, plan_end)
    # Exact provider links only. Date/sport similarities are not proof of a match.
    ids = {a['id'] for a in activities}
    for p in plans:
        p['match_status'] = 'SOURCE_LINK' if p['executed_activity_id'] in ids else 'UNCONFIRMED'
    return {'schema_version': 'onboarding-1.0', 'athlete_id': athlete_id, 'collected_at': collected_at,
            'window_start': window_start, 'plan_start': plan_start, 'plan_end': plan_end,
            'source_facts': source_facts, 'athlete_context': context,
            'athlete_data': {'activities': activities, 'planned': plans},
            'recommendations': [], 'auto_plan_write': False}


def import_snapshot(journal, snapshot, expected_revision):
    canonical(snapshot)
    # Rebuild derived normalization from the originals instead of trusting a supplied projection.
    state = journal.state()
    require(state['profile'] and state['profile']['athlete_id'] == snapshot['athlete_id'], 'Snapshot athlete mismatch')
    rebuilt = build_snapshot(athlete_id=snapshot['athlete_id'], source_facts=snapshot['source_facts'],
        context=snapshot['athlete_context'], collected_at=snapshot['collected_at'], window_start=snapshot['window_start'],
        plan_start=snapshot['plan_start'], plan_end=snapshot['plan_end'], timezone=state['profile']['timezone'])
    require(rebuilt == snapshot, 'Snapshot projection does not match raw sources')
    require(instant(snapshot['collected_at']) <= instant(utc_now()), 'Future collection timestamp')
    key = digest(snapshot)
    with journal.transaction(expected_revision) as (db, state):
        if key in state['source_snapshots']:
            return {'status': 'ALREADY_IMPORTED', 'snapshot_hash': key}
        require(not state['source_snapshot'] or instant(snapshot['collected_at']) >= instant(state['source_snapshot']['collected_at']), 'Older snapshot cannot replace a newer one')
        journal.append(db, 'SOURCE_SNAPSHOT', key, snapshot)
    return {'status': 'IMPORTED', 'snapshot_hash': key, 'activities': len(snapshot['athlete_data']['activities']), 'plans': len(snapshot['athlete_data']['planned'])}


def source_overview(snapshot, as_of, timezone):
    if snapshot is None:
        return None
    now = instant(as_of)
    today = now.astimezone(ZoneInfo(timezone)).date().isoformat()
    activities = [a for a in snapshot['athlete_data']['activities'] if instant(a['date']) <= now]
    recent = [a for a in activities if now - timedelta(days=7) <= instant(a['date'])]
    plans = snapshot['athlete_data']['planned']
    upcoming = [p for p in plans if p['local_date'] >= today and p['match_status'] != 'SOURCE_LINK']
    missing = sum(a['duration_sec'] is None for a in activities)
    counts = dict(Counter(a['sport'] for a in activities))
    periods = {}
    for a in activities:
        day = instant(a['date']).astimezone(ZoneInfo(timezone)).date()
        for key in (day.strftime('%Y-%m'), 'Uke ' + (day - timedelta(days=day.weekday())).isoformat()):
            row = periods.setdefault(key, {'period': key, 'count': 0, 'active_sec': 0, 'elapsed_sec': 0, 'missing_active': 0, 'sports': {}, 'subsports': {}})
            row['count'] += 1
            row['active_sec'] += a['duration_sec'] or 0
            row['elapsed_sec'] += a['elapsed_sec'] or 0
            row['missing_active'] += a['duration_sec'] is None
            row['sports'][a['sport']] = row['sports'].get(a['sport'], 0) + (a['duration_sec'] or 0)
            subtype = a['subsport'] or a['sport']
            row['subsports'][subtype] = row['subsports'].get(subtype, 0) + (a['duration_sec'] or 0)
    rest_days = snapshot['athlete_context'].get('rest_days', [])
    return {'collected_at': snapshot['collected_at'], 'window_start': snapshot['window_start'],
            'plan_end': snapshot['plan_end'], 'stale': (now - instant(snapshot['collected_at'])).total_seconds() > 86400,
            'total_activities': len(activities), 'sport_counts': counts,
            'recent_count': len(recent), 'recent_minutes': round(sum(a['duration_sec'] or 0 for a in recent) / 60, 1),
            'latest_activity_date': activities[-1]['local_date'] if activities else None,
            'goals': snapshot['athlete_context']['goals'], 'availability': snapshot['athlete_context'].get('availability', {}),
            'periods': [periods[key] for key in sorted(periods)],
            'progression': snapshot['athlete_context'].get('progression', []),
            'rest_days': rest_days, 'today_rest': any(d['date'] == today for d in rest_days),
            'open_questions': snapshot['athlete_context'].get('open_questions', []),
            'assessment': 'Historikken viser faktisk aktivitet, men mangler systematisk subjektiv respons og 24–72-timers oppfølging. Ingen automatisk progresjon er utledet.',
            'missing_durations': missing, 'plan_conflicts': [p for p in plans if p['dose_conflict']],
            'upcoming': upcoming, 'activities': activities, 'plans': plans,
            'linked_plans': sum(p['match_status'] == 'SOURCE_LINK' for p in plans)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    journal = Journal(args.db)
    result = import_snapshot(journal, json.loads(args.snapshot.read_text(encoding='utf-8')), journal.state()['revision'])
    print(json.dumps(result))


if __name__ == '__main__':
    main()
