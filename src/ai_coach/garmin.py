"""Optional, read-only Garmin Connect adapter. Credentials never enter the journal."""
import argparse
import getpass
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .contracts import digest, instant, require
from .journal import Journal, utc_now, ConflictError
from .onboarding import number

LOCK = threading.Lock()

def token_directory(journal):
    return journal.path.parent / ('garmin-' + journal.path.stem)

def client_factory():
    if sys.version_info < (3, 12):
        raise ValueError('Garmin krever Python 3.12. Start med Start-Garmin-Coach.ps1.')
    try:
        from garminconnect import Garmin
    except ImportError:
        raise ValueError('Garmin-delen er ikke installert. Installer pakken med [garmin].') from None
    logging.getLogger('garminconnect').setLevel(logging.CRITICAL)
    return Garmin

def normalize(raw, collected_at, timezone_name):
    require(isinstance(raw, list), 'Ugyldig aktivitetsliste fra Garmin')
    result, seen = [], set()
    for row in raw:
        require(isinstance(row, dict), 'Ugyldig Garmin-aktivitet')
        identity = row.get('activityId')
        require(type(identity) is int and identity > 0, 'Garmin activityId mangler')
        key = 'garmin-' + str(identity)
        require(key not in seen, 'Duplikat fra Garmin; prøv ny synk')
        seen.add(key)
        stamp = row.get('startTimeGMT')
        require(isinstance(stamp, str), 'Garmin UTC-starttid mangler')
        when = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        require(when <= instant(collected_at), 'Aktivitet i fremtiden')
        subtype = (row.get('activityType') or {}).get('typeKey') or 'unknown'
        sport = 'running' if 'running' in subtype else 'cycling' if 'cycling' in subtype else 'swimming' if 'swimming' in subtype else 'misc'
        result.append({'id': key, 'date': when.isoformat(), 'local_date': when.astimezone(ZoneInfo(timezone_name)).date().isoformat(),
            'sport': sport, 'subsport': subtype, 'title': row.get('activityName') or subtype,
            'duration_sec': number(row.get('duration')), 'elapsed_sec': number(row.get('elapsedDuration')),
            'distance_m': number(row.get('distance')), 'source_ref': 'garmin:activity:' + str(identity), 'response_status': 'UNKNOWN'})
    return sorted(result, key=lambda a: (a['date'], a['id']))

def status(journal):
    state = journal.state()
    value = state.get('garmin_sync') or {}
    return {'connected': (token_directory(journal) / 'garmin_tokens.json').is_file(),
            'last_success': value.get('collected_at'), 'activities': len(value.get('activities', [])),
            'last_error': (state.get('garmin_status') or {}).get('error'), 'scheduled_sync': False}

def sync(journal, revision, factory=None, clock=utc_now):
    require(LOCK.acquire(blocking=False), 'Garmin-synk pågår allerede')
    try:
        state = journal.state()
        if state['revision'] != revision:
            raise ConflictError('Data endret; oppdater siden før synk')
        require(state['profile'], 'Lagre profil før Garmin-synk')
        if factory is None:
            require((token_directory(journal) / "garmin_tokens.json").is_file(), "Logg inn lokalt med Start-Garmin-Coach.ps1 -Login først")
        factory = factory or client_factory()
        client = factory()
        try:
            client.login(str(token_directory(journal)))
            account = getattr(client, "display_name", None)
            require(isinstance(account, str) and account, "Garmin-konto kunne ikke identifiseres")
            previous = state.get("garmin_sync")
            require(not previous or previous["account_hash"] == digest(account), "Garmin-konto endret; bruk separat database")
            raw = []
            # Bounded full pagination: never silently accept a truncated history.
            for offset in range(0, 10000, 100):
                page = client.get_activities(offset, 100)
                require(isinstance(page, list), 'Ugyldig Garmin-svar')
                raw.extend(page)
                if len(page) < 100:
                    break
            else:
                raise ValueError('Historikken overstiger importgrensen; ingen data erstattet')
        except Exception:
            error = 'Garmin kunne ikke hentes. Kontroller lokal innlogging, nettverk eller vent ved ratebegrensning. Tidligere data er bevart.'
            with journal.transaction(revision) as (db, current):
                journal.append(db, 'GARMIN_STATUS', 'garmin', {'error': error, 'attempted_at': clock()})
            raise ValueError(error) from None
        collected = clock()
        activities = normalize(raw, collected, state['profile']['timezone'])
        previous = state.get('garmin_sync')
        require(not previous or instant(collected) >= instant(previous['collected_at']), 'Eldre synk avvist')
        payload = {'athlete_id': state['profile']['athlete_id'], 'collected_at': collected,
                   'account_hash': digest(account), 'source_facts': raw, 'activities': activities, 'auto_plan_write': False}
        with journal.transaction(revision) as (db, current):
            journal.append(db, 'GARMIN_SYNC', 'garmin', payload)
            journal.append(db, 'GARMIN_STATUS', 'garmin', {'error': None, 'attempted_at': collected})
        return {'activities': len(activities), 'collected_at': collected}
    finally:
        LOCK.release()

def merged_snapshot(state):
    from copy import deepcopy
    value = deepcopy(state.get('source_snapshot'))
    garmin = state.get('garmin_sync')
    if not garmin:
        return value
    if value is None:
        value = {'athlete_context': {'goals': []}, 'athlete_data': {'planned': []}, 'plan_end': 'Ikke importert'}
    value['athlete_data']['activities'] = garmin['activities']
    # Garmin cannot refresh the HQ plan or confirm Tredict execution links.
    for planned in value['athlete_data']['planned']:
        planned['match_status'] = 'UNCONFIRMED'
    value['plan_collected_at'] = (state.get('source_snapshot') or {}).get('collected_at')
    value['collected_at'] = garmin['collected_at']
    value['window_start'] = garmin['activities'][0]['date'] if garmin['activities'] else garmin['collected_at']
    value['activity_provider'] = 'Garmin'
    return value

def login_password():
    return os.environ.get('GARMINPASSWORD') or getpass.getpass('Garmin passord: ')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=Path.home()/'.ai-coach'/'coach.sqlite')
    parser.add_argument('--login', action='store_true')
    args = parser.parse_args()
    journal = Journal(args.db)
    if args.login:
        factory = client_factory()
        folder = token_directory(journal)
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        client = factory(input('Garmin e-post: ').strip(), login_password(),
                         prompt_mfa=lambda: getpass.getpass('Garmin engangskode: '))
        try:
            client.login(str(folder))
        except Exception:
            raise SystemExit('Innlogging feilet. Ingen passord er lagret av coachen.') from None
        print('Garmin er tilkoblet. Tilgangstoken lagres privat ved databasen.')
    else:
        try:
            result = sync(journal, journal.state()['revision'])
            print('Synkronisert:', result['activities'], 'aktiviteter.')
        except ValueError as error:
            raise SystemExit(str(error)) from None

if __name__ == '__main__':
    main()
