import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.audit_reasoning_recovery import audit_recovery
from scripts.reasoning import reasoning_policy


class RecoveryAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root/'original'; self.original.mkdir()
        self.corrected = self.root/'corrected'; self.corrected.mkdir()
        self.plan_file = self.root/'plan.json'
        policy = reasoning_policy({'budget_tokens': 100})
        evidence = []
        for i in range(198):
            record = {'seconds': 1, 'response': {'usage': {'completion_tokens': 100 if i == 1 else 50},
                       'choices': [{'finish_reason': 'length' if i == 2 else 'stop'}]}}
            raw = json.dumps(record).encode()
            (self.corrected/f'{i:03}.json').write_bytes(raw)
            if i != 197:
                p = self.original/f'{i:03}.json'; p.write_bytes(raw)
                evidence.append({'index': i, 'sha256': hashlib.sha256(raw).hexdigest()})
        (self.corrected/'manifest.json').write_text(json.dumps({
            'reasoning': policy, 'reasoning_request': {'reasoning_budget_tokens': 100}}))
        self.plan = {'policy': policy, 'lanes': {'gpqa': {
            'retained': [i for i in range(197) if i not in (1,2)],
            'regenerate': [1,2], 'missing': [197], 'source_evidence': evidence}}}
        self.save_plan()

    def save_plan(self):
        self.plan_file.write_text(json.dumps(self.plan))

    def audit(self):
        return audit_recovery(self.original, self.corrected, self.plan_file, 'gpqa')

    def test_lineage_counts_and_discarded_cost_are_preserved(self):
        result = self.audit()
        self.assertEqual((result['retained_responses'], result['regenerated_responses'],
                          result['previously_missing_responses']), (195,2,1))
        self.assertEqual(result['discarded_original_request_seconds'], 2)
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_mutated_original_or_reused_response_is_rejected(self):
        p = self.original/'000.json'; raw = p.read_bytes(); p.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Original response changed'): self.audit()
        p.write_bytes(raw); (self.corrected/'000.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Retained response changed'): self.audit()

    def test_missing_result_is_rejected(self):
        (self.corrected/'197.json').unlink()
        with self.assertRaisesRegex(ValueError, 'incomplete'): self.audit()

    def test_selectively_retaining_a_long_answer_is_rejected(self):
        lane = self.plan['lanes']['gpqa']
        lane['regenerate'].remove(1); lane['retained'].append(1); self.save_plan()
        with self.assertRaisesRegex(ValueError, 'independent of score'): self.audit()

    def test_mismatched_request_budget_is_rejected(self):
        p = self.corrected/'manifest.json'; manifest = json.loads(p.read_text())
        manifest['reasoning_request']['reasoning_budget_tokens'] = 99
        p.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'request override'): self.audit()
