import unittest
from collections import Counter
from exception_features import core, analysis

class FeaturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=core.make_plan(core.load_config('configs/features_gpt4o.json'))
    def test_schedule_and_balance(self):
        p=self.plan
        self.assertEqual(len(p['tasks']),648)
        self.assertEqual(len({t['id'] for t in p['tasks']}),648)
        self.assertEqual(Counter(w['target_position'] for w in p['worlds']),dict.fromkeys(range(1,13),3))
        self.assertEqual(Counter(w['target_climate'] for w in p['worlds']),{'warm':18,'cold':18})
        self.assertEqual(set(Counter(tuple(w['roles'].values()) for w in p['worlds']).values()),{6})
    def test_intervention_invariants(self):
        for w in self.plan['worlds']:
            base=w['cue_rows']['favor_1']
            self.assertEqual(len(base),12)
            self.assertEqual(len({r['id'] for r in base}),12)
            for cue,rows in w['cue_rows'].items():
                self.assertEqual(rows[0],base[0])
                self.assertEqual(Counter(tuple(r[k] for k in core.FEATURES) for r in rows),Counter(tuple(r[k] for k in core.FEATURES) for r in base))
                for left,right in zip(base,rows):
                    self.assertEqual({k:v for k,v in left.items() if k not in core.FEATURES},{k:v for k,v in right.items() if k not in core.FEATURES})
            for i,r in enumerate(base[1:],1):
                if r['class']==w['roles']['pattern']:
                    self.assertEqual(r,w['cue_rows']['favor_2'][i])
            for record in core.RECORDS:
                task={'world_id':w['id'],'record':record,'cue':'favor_1','arm':'direct'}
                rows=core.table_rows(self.plan,task)
                self.assertEqual(rows[w['target_position']-1]['id'],w['target_id'])
                counts=Counter(r['class'] for r in rows)
                self.assertEqual(counts[w['roles']['pattern']],5)
                self.assertEqual(counts[w['roles'][record]],4)
    def test_known_estimands(self):
        records={}
        for t in self.plan['tasks']:
            w=core.world_for(self.plan,t)
            answer=w['roles'][t['record']]
            if t['arm']=='cot' and t['cue'] in ('favor_1','favor_2'):
                answer=w['roles']['record_1' if t['cue']=='favor_1' else 'record_2']
            records[t['id']]={'status':'complete','answer':answer}
        stat=analysis.paired_statistics(self.plan,records)['cot_minus_direct_cue_sensitivity']
        self.assertEqual(stat['estimate'],1)
        self.assertEqual(stat['full_plan_bounds'],[1,1])
        first=next(t for t in self.plan['tasks'] if t['arm']=='cot' and t['cue']=='favor_1')
        del records[first['id']]
        stat=analysis.paired_statistics(self.plan,records)['cot_minus_direct_cue_sensitivity']
        self.assertEqual(stat['complete_worlds'],35)
        self.assertLess(stat['full_plan_bounds'][0],1)
