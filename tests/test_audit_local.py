import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_local import audit_gpqa, audit_coding, audit_terminal
from scripts.gpqa_diamond import tasks


def write(path, value):
    path.write_text(json.dumps(value))


class LocalAuditTests(unittest.TestCase):
    def test_gpqa_recomputes_scores_and_retains_incomplete_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            rows=[{'Record ID':str(i),'High-level domain':'synthetic','Question':'Synthetic',
                   'Correct Answer':'correct','Incorrect Answer 1':'one','Incorrect Answer 2':'two',
                   'Incorrect Answer 3':'three'} for i in range(2)]
            dataset=folder/'dataset.csv'
            with dataset.open('w') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            protocol={'expected_tasks':2,'generation':{'temperature':1},'answer_shuffle_seed':0,
                      'prompt':'{Question}\n{A}\n{B}\n{C}\n{D}', 'answer_pattern':r'Answer: ([A-D])',
                      'dataset':{'sha256':hashlib.sha256(dataset.read_bytes()).hexdigest()}}
            selected=tasks(rows,protocol)
            write(folder/'manifest.json',{'protocol':protocol,'tasks_sha256':hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest()})
            task=selected[0]
            record={k:v for k,v in task.items() if k!='prompt'}
            record.update(answer=task['expected'],correct=True,seconds=1,finish_reason='stop',
                          response={'choices':[{'finish_reason':'stop','message':{'content':'Answer: '+task['expected']}}]})
            write(folder/'000.json',record)
            result=audit_gpqa(folder,dataset,protocol)
            self.assertEqual((result['completed'],result['total'],result['correct']),(1,2,1))
            self.assertFalse(result['complete'])
            self.assertNotIn('Synthetic',json.dumps(result))
            record['correct']=False;write(folder/'000.json',record)
            with self.assertRaises(ValueError):audit_gpqa(folder,dataset,protocol)

    def test_coding_runner_errors_cannot_become_wrong_answers(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            protocol={'generation':{'temperature':1},'harness_revision':'pinned',
                      'selected_rows_sha256':'dataset-hash','task_ids':['public-task','second-task']}
            write(folder/'manifest.json',{'protocol':protocol,'rows_sha256':'dataset-hash'})
            record={'index':0,'task':'public-task','result':[{'pass@1':1.0},{'0':[[True]]},[['{}']]]}
            write(folder/'000-score.json',record)
            write(folder/'000-response.json',{'seconds':1,'response':{'choices':[{'finish_reason':'stop','message':{'content':'```python\nprint(2)\n```'}}]}})
            result=audit_coding(folder,protocol)
            self.assertEqual(result['correct'],1)
            self.assertFalse(result['complete'])
            record['result'][2]=[['{"error_code":-5,"error_message":"TestRunnerError"}']]
            write(folder/'000-score.json',record)
            with self.assertRaises(ValueError):audit_coding(folder,protocol)

    def test_terminal_timeout_is_failure_but_wrong_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);trial=folder/'trial';trial.mkdir()
            protocol={'task_names':['task'],'task_checksums':{'task':'correct-version'},
                      'generation':{'reasoning_effort':'medium','max_tokens':8192}}
            record={'finished_at':'2026-11-12T00:00:00Z','task_name':'dataset/task',
                    'task_checksum':'correct-version','config':{'timeout_multiplier':1,
                    'agent':{'kwargs':{'reasoning_effort':'medium','llm_call_kwargs':{'max_tokens':8192}}}},
                    'exception_info':{'exception_type':'AgentTimeoutError'},'verifier_result':{'rewards':{'reward':0.0}}}
            write(trial/'result.json',record)
            verifier=trial/'verifier';verifier.mkdir()
            (verifier/'test-stdout.txt').write_text('1 failed\n')
            report={'results':{'tool':{'name':'pytest'},
                    'summary':{'tests':1,'passed':0,'failed':1,'skipped':0},
                    'tests':[{'status':'failed'}]}}
            write(verifier/'ctrf.json',report)
            result=audit_terminal(folder,protocol)
            self.assertTrue(result['complete']);self.assertEqual(result['correct'],0)
            self.assertEqual(result['agent_timeouts'],1)
            (verifier/'test-stdout.txt').write_text('qemu: uncaught target signal 11 (Segmentation fault)\n')
            with self.assertRaisesRegex(ValueError,'emulation crash'):audit_terminal(folder,protocol)
            (verifier/'test-stdout.txt').write_text('uvx failed before tests\n')
            (verifier/'ctrf.json').unlink()
            with self.assertRaisesRegex(ValueError,'Missing terminal verifier test report'):audit_terminal(folder,protocol)
            write(verifier/'ctrf.json',report)
            report['results']['summary'].update(passed=1,failed=0)
            report['results']['tests']=[{'status':'passed'}]
            write(verifier/'ctrf.json',report)
            with self.assertRaisesRegex(ValueError,'reward disagrees'):audit_terminal(folder,protocol)
            report['results']['summary'].update(passed=0,failed=1)
            report['results']['tests']=[{'status':'failed'}]
            write(verifier/'ctrf.json',report)
            protocol['environment_config']={'force_build':True}
            with self.assertRaisesRegex(ValueError,'environment mismatch'):audit_terminal(folder,protocol)
            record['config']['environment']={'force_build':True};write(trial/'result.json',record)
            record['task_checksum']='older-version';write(trial/'result.json',record)
            with self.assertRaises(ValueError):audit_terminal(folder,protocol)
            record['task_checksum']='correct-version';record['exception_info']['exception_type']='EnvironmentStartError'
            write(trial/'result.json',record)
            with self.assertRaises(ValueError):audit_terminal(folder,protocol)
