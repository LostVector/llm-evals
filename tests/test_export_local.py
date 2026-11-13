import json
import unittest
from pathlib import Path

from scripts.export_local import observation


class LocalExportTests(unittest.TestCase):
    def setUp(self):
        self.protocol=json.loads(Path('protocols/gpqa-diamond.json').read_text())
        self.summary={'complete':True,'completed':198,'total':198,'correct':100,
                      'accuracy':100/198,'wilson_95':[0.4,0.6],'artifact_fingerprints':['a'*64]}
        self.metadata={'artifact_verified':True,'model':{'name':'Qwen3.8-Flash-Next',
                       'revision':'sha256:'+'a'*64,'artifact_sha256':'a'*64,
                       'quantization':'Synthetic test format','artifact':'synthetic-test.hgn'},
                       'hardware':'Synthetic CPU and RAM','backend':'Synthetic backend','backend_revision':'test'}

    def export(self):
        return observation('gpqa',self.summary,self.protocol,self.metadata,
                           'synthetic-export-test','2026-11-12','test-audit-revision')

    def test_incomplete_or_unverified_result_is_rejected(self):
        self.summary['complete']=False
        with self.assertRaises(ValueError):self.export()
        self.summary['complete']=True;self.metadata['artifact_verified']=False
        with self.assertRaises(ValueError):self.export()

    def test_private_config_fields_are_never_copied(self):
        self.metadata.update(api_key='synthetic-private-value',base_url='http://example.invalid/private')
        self.metadata['model']['private_note']='not-public'
        result=self.export();serialized=json.dumps(result)
        self.assertNotIn('synthetic-private-value',serialized)
        self.assertNotIn('example.invalid',serialized)
        self.assertNotIn('not-public',serialized)
        self.assertEqual(result['metric']['n'],198)
        self.assertEqual(result['protocol']['config']['comparison_group'],'gpqa-diamond-198')

    def test_private_addresses_and_endpoint_aliases_are_rejected(self):
        self.metadata['hardware']='Synthetic server at 10.0.0.1'
        with self.assertRaises(ValueError):self.export()
        self.metadata['hardware']='Synthetic CPU'
        self.metadata['model']['name']='private-endpoint-alias'
        with self.assertRaises(ValueError):self.export()

    def test_post_run_hash_discloses_unverified_continuity(self):
        self.metadata['artifact_verification']={'evaluation_period_continuity':'unverified',
            'source':'https://github.com/example/evals/pull/1', 'api_key':'synthetic-secret'}
        result=self.export()
        self.assertIn('continuity',result['notes'])
        self.assertIn('unverified',result['notes'])
        self.assertNotIn('synthetic-secret',json.dumps(result))

    def test_wrong_task_count_or_path_like_identifier_is_rejected(self):
        self.summary['total']=self.summary['completed']=2
        with self.assertRaises(ValueError):self.export()
        self.summary['total']=self.summary['completed']=198
        with self.assertRaises(ValueError):
            observation('gpqa',self.summary,self.protocol,self.metadata,'../escape','2026-11-12','test')
