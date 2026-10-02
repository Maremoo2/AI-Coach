import copy
import json
import tempfile
import unittest
from pathlib import Path
from ai_coach.onboarding import build_snapshot, import_snapshot, source_overview
from ai_coach.journal import Journal
from ai_coach.service import CoachService
from ai_coach.coaching import compile_proposal
from tests.app_support import profile, NOW


def response(csv):
    return {'content':[{'type':'text','text':'Instructions mention ---- inline; quoted notes can span lines.\n----\n'+csv}]}


def snapshot():
    facts={'activities':response('id,date,sportType,subSportType,title,summary.duration,summary.durationTotal,summary.distance\na,2026-07-02T10:00:00Z,running,generic,Synthetic,1800,2100,5000\n'),
           'plans':response('id,date,updatedAt,sportType,title,notes,duration,executedTrainingId\np,2026-07-04T10:00:00Z,2026-07-01T10:00:00Z,running,Easy 45–55 min,"line one\nline two",3600,\n')}
    return build_snapshot(athlete_id=profile()['athlete_id'],source_facts=facts,
        context={'goals':[{'title':'Synthetic goal','description':'Conditional goal; no invented baseline','source_ref':'user:synthetic'}],
                 'rest_days':[{'date':'2026-07-03','source_ref':'hq:synthetic'}]},
        collected_at=NOW,window_start='2026-07-01T00:00:00Z',plan_start='2026-07-01T00:00:00Z',plan_end='2026-07-10T00:00:00Z',timezone='Europe/Oslo')


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.journal=Journal(Path(self.temp.name)/'coach.sqlite')
        self.service=CoachService(self.journal,lambda:NOW)
        self.service.save('profile',profile(),0)

    def test_ingestion_idempotency_and_no_plan_or_recommendation_write(self):
        value=snapshot();before=copy.deepcopy(value)
        result=import_snapshot(self.journal,value,1)
        self.assertEqual(result['activities'],1)
        self.assertEqual(value,before)
        self.assertIsNone(self.journal.state()['plan'])
        self.assertEqual(self.journal.state()['evaluations'],{})
        self.assertEqual(import_snapshot(self.journal,value,2)['status'],'ALREADY_IMPORTED')
        self.assertEqual(self.journal.state()['revision'],2)

    def test_metadata_dose_conflict_and_multiline_notes_preserved(self):
        value=snapshot()
        self.assertTrue(value['athlete_data']['planned'][0]['dose_conflict'])
        self.assertEqual(value['athlete_data']['planned'][0]['notes'],'line one\nline two')
        self.assertEqual(value['athlete_data']['activities'][0]['response_status'],'UNKNOWN')
        overview=source_overview(value,NOW,'Europe/Oslo')
        self.assertEqual(overview['recent_minutes'],30)
        self.assertEqual(overview['periods'][0]['elapsed_sec'],2100)
        self.assertTrue(overview['today_rest'])

    def test_projection_tampering_and_wrong_athlete_rejected(self):
        for field in ['tamper','identity']:
            value=snapshot()
            if field=='tamper':value['athlete_data']['activities'][0]['duration_sec']=999
            else:value['athlete_id']='other'
            with self.subTest(field=field),self.assertRaises(ValueError):import_snapshot(self.journal,value,1)
        self.assertEqual(self.journal.state()['revision'],1)

    def test_future_data_and_duplicate_activities_rejected(self):
        for edit in ['future','duplicate']:
            value=snapshot();facts=value['source_facts']
            if edit=='future':facts['activities']['content'][0]['text']=facts['activities']['content'][0]['text'].replace('2026-07-02','2027-07-02')
            else:facts['activities']={'pages':[facts['activities'],facts['activities']]}
            with self.subTest(edit=edit),self.assertRaises(ValueError):
                build_snapshot(athlete_id=value['athlete_id'],source_facts=facts,context=value['athlete_context'],collected_at=NOW,window_start=value['window_start'],plan_start=value['plan_start'],plan_end=value['plan_end'],timezone='Europe/Oslo')

    def test_missing_metric_is_unknown_not_zero_response(self):
        value=snapshot();facts=value['source_facts'];facts['activities']['content'][0]['text']=facts['activities']['content'][0]['text'].replace(',1800,2100,',',,2100,')
        result=build_snapshot(athlete_id=value['athlete_id'],source_facts=facts,context=value['athlete_context'],collected_at=NOW,window_start=value['window_start'],plan_start=value['plan_start'],plan_end=value['plan_end'],timezone='Europe/Oslo')
        self.assertIsNone(result['athlete_data']['activities'][0]['duration_sec'])
        self.assertEqual(source_overview(result,NOW,'Europe/Oslo')['missing_durations'],1)

    def test_flexible_time_does_not_create_dose(self):
        p=profile();p.update(weekly_minutes=None,max_session_minutes=None,available_days=[])
        self.service.save('profile',p,1)
        with self.assertRaises(ValueError):self.service.propose(2)
        self.assertIsNone(self.journal.state()['plan'])

    def test_source_import_cannot_trigger_a_new_starter_plan(self):
        import_snapshot(self.journal,snapshot(),1)
        with self.assertRaisesRegex(ValueError,'HQ'):self.service.propose(2)
        self.assertIsNone(self.journal.state()['plan'])

    def test_subjective_checkin_can_reference_imported_actual(self):
        import_snapshot(self.journal,snapshot(),1)
        self.service.save('checkin',{'id':'c','athlete_id':profile()['athlete_id'],'session_id':'actual-a','observed_at':NOW,'status':'DONE','duration_min':30,'rpe':None,'quality':None,'pain':None,'energy':None,'recovery':'UNKNOWN','notes':'Synthetic'},2)
        self.assertEqual(self.service.snapshot()['weekly_review']['incomplete_checkins'],1)
        self.assertIsNone(self.journal.state()['plan'])
        self.assertIn('HQ',self.service.chat('Neste økt')['message'])
