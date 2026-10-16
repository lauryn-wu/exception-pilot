import json
import os
import socket
import sys
import time
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,os.getcwd())

def forbidden(*a,**kw):
    raise AssertionError('Network forbidden during offline acceptance suite')

def flatten(suite):
    for t in suite:
        if isinstance(t,unittest.TestSuite):yield from flatten(t)
        else:yield t.id()

with patch.object(socket.socket,'connect',forbidden),patch('socket.create_connection',forbidden):
    suite=unittest.defaultTestLoader.discover('tests')
    ids=list(flatten(suite))
    started=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    elapsed=time.monotonic()-started
report=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
            successful=result.wasSuccessful(),elapsed_seconds=round(elapsed,3),network_blocked=True,
            paid_judge_calls=0,pretrained_qwen_inference_calls=0,gpu_inference_calls=0,
            v22_tests=sum(t.startswith('test_study2_v5_review_v22.') for t in ids),
            followup_tests=sum(t.startswith('test_study2_v5_review_v2_followup.') for t in ids),
            prior_review_v2_tests=sum(t.startswith('test_study2_v5_review_v2.') for t in ids),
            existing_v5_tests=sum(t.startswith(('test_study2_v5.','test_study2_v5_staged.')) for t in ids),
            test_ids=ids)
Path('/tmp/study2-v22-full-offline-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='test_ids'},indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
