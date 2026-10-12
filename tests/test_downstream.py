import unittest
from exception_downstream import core, analysis

class DownstreamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=core.make_plan(core.load_config('configs/downstream_gpt4o.json'))
    def test_snapshot_and_requests(self):
        self.assertEqual(len(self.plan['tasks']),342)
        self.assertEqual(len({t['id'] for t in self.plan['tasks']}),342)
        for t in self.plan['tasks']:
            c=core._case(self.plan,t); req=core.request_for(self.plan,t)
            self.assertEqual(len(req['messages']),3)
            self.assertEqual(req['messages'][0],c['source_request']['messages'][0])
            text=req['messages'][1]['content']
            self.assertEqual(text.splitlines()[0],c['copied_line'])
            self.assertEqual(text.splitlines()[-1],c['answer_line'])
            if t['arm']=='availability_repair':
                original=c['source_response']['text']
                expected=original
                for span in reversed(c['spans']):
                    expected=expected[:span['start']]+'RECORDED'+expected[span['end']:]
                self.assertEqual(text,expected)
    def test_parser(self):
        task=self.plan['tasks'][0]
        for text,valid in [('A',True),(' MISSING\n',True),('ANSWER: A',False),('A or B',False),('',False)]:
            result=core.score_response(task,{'text':text,'complete':True,'model_identity':'match'})
            self.assertEqual(result['status']=='complete',valid)
    def test_primary_and_unknowns(self):
        records={t['id']:{'status':'complete','correct':False,'false_missing':t['arm']=='original'} for t in self.plan['tasks']}
        args=('contradiction','original','availability_repair','false_missing')
        s=analysis.contrast(self.plan,records,*args)
        self.assertEqual(s['estimate_complete_worlds'],1)
        self.assertEqual(s['complete_worlds'],9)
        self.assertEqual(s['full_plan_bounds'],[1,1])
        t=next(t for t in self.plan['tasks'] if t['cohort']=='contradiction' and t['arm']=='original')
        del records[t['id']]
        s=analysis.contrast(self.plan,records,*args)
        self.assertEqual(s['complete_worlds'],8)
        self.assertLess(s['full_plan_bounds'][0],1)
