import copy
import tempfile
import unittest
from pathlib import Path
from ai_coach.garmin import normalize, sync, merged_snapshot, status
from ai_coach.journal import Journal
from ai_coach.service import CoachService
from tests.app_support import profile, NOW
from tests.integration.test_onboarding import snapshot
from ai_coach.onboarding import import_snapshot

RAW={'activityId': 123, 'startTimeGMT':'2026-07-02 10:00:00','activityName':'Synthetic run','activityType':{'typeKey':'running'},'duration':1800,'elapsedDuration':2000,'distance':5000}
class Fake:
    display_name='synthetic-account'
    def login(self, path): pass
    def get_activities(self, start, limit): return [copy.deepcopy(RAW)] if start==0 else []

class GarminTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.j=Journal(Path(self.temp.name)/'coach.sqlite')
        CoachService(self.j,lambda:NOW).save('profile',profile(),0)
    def run_sync(self, factory=Fake):
        return sync(self.j,self.j.state()['revision'],factory,lambda:NOW)
    def test_sync_repeated_raw_and_hq_boundary(self):
        self.run_sync();self.run_sync()
        s=self.j.state();self.assertEqual(len(s['garmin_sync']['activities']),1)
        self.assertEqual(s['garmin_sync']['source_facts'],[RAW]);self.assertIsNone(s['plan'])
        self.assertFalse(s['garmin_sync']['auto_plan_write']);self.assertEqual(s['evaluations'],{})
        self.assertEqual(status(self.j)['last_success'],NOW)
    def test_failure_preserves_data_and_redacts_credentials(self):
        self.run_sync();before=self.j.state()['garmin_sync']
        class Bad(Fake):
            def login(self,path): raise RuntimeError('secret-password-secret')
        with self.assertRaisesRegex(ValueError,'Garmin kunne ikke hentes'): self.run_sync(Bad)
        self.assertEqual(self.j.state()['garmin_sync'],before)
        self.assertNotIn('secret-password-secret',str(self.j.read()))
        self.assertTrue(status(self.j)['last_error'])
    def test_account_change_refused(self):
        self.run_sync()
        class Other(Fake): display_name='other'
        with self.assertRaises(ValueError):self.run_sync(Other)
        self.assertEqual(len(self.j.state()['garmin_sync']['activities']),1)
    def test_unknown_duration_utc_and_duplicates(self):
        raw=copy.deepcopy(RAW);raw.pop('duration')
        result=normalize([raw],NOW,'Europe/Oslo')[0]
        self.assertIsNone(result['duration_sec']);self.assertEqual(result['date'],'2026-07-02T10:00:00+00:00')
        for rows in ([RAW,RAW],[dict(RAW,startTimeGMT='2030-01-01 12:00:00')],[dict(RAW,duration=-1)]):
            with self.assertRaises(ValueError): normalize(rows,NOW,'Europe/Oslo')
    def test_pagination_full_then_short(self):
        class Pages(Fake):
            def get_activities(self,start,limit):
                return [dict(RAW,activityId=start+i+1) for i in range(100 if start==0 else 2)]
        self.run_sync(Pages);self.assertEqual(len(self.j.state()['garmin_sync']['activities']),102)
    def test_source_switch_preserves_context_and_plan_date(self):
        import_snapshot(self.j,snapshot(),1);old=self.j.state()['source_snapshot']
        self.run_sync();s=self.j.state();merged=merged_snapshot(s)
        self.assertEqual(merged['athlete_context'],old['athlete_context'])
        self.assertEqual(len(merged['athlete_data']['activities']),1)
        self.assertEqual(merged['activity_provider'],'Garmin')
        self.assertEqual(merged['plan_collected_at'],old['collected_at'])
        self.assertEqual(s['source_snapshot'],old)
        self.assertEqual(CoachService(self.j,lambda:NOW).snapshot()['source_context']['total_activities'],1)
    def test_invalid_page_no_partial_import(self):
        class Pages(Fake):
            def get_activities(self,start,limit):return {'error':'unexpected'}
        with self.assertRaises(ValueError):self.run_sync(Pages)
        self.assertIsNone(self.j.state()['garmin_sync'])
    def test_checkin_from_garmin(self):
        from tests.app_support import checkin
        self.run_sync()
        c=checkin();c['session_id']='actual-garmin-123'
        CoachService(self.j,lambda:NOW).save('checkin',c,self.j.state()['revision'])
        self.assertIn('actual-garmin-123',self.j.state()['checkins'])
