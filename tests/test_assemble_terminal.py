import json
from pathlib import Path
import tempfile
import unittest

from scripts.assemble_terminal import select_trials
from scripts.audit_local import fingerprint


class AssemblyTests(unittest.TestCase):
    def test_only_pinned_pre_agent_failure_can_be_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, recovery = root/'original', root/'recovery'
            bad, good = original/'failed', recovery/'replacement'
            bad.mkdir(parents=True); good.mkdir(parents=True)
            failed = {'task_name': 'dataset/task', 'finished_at': 'finished',
                      'task_checksum': 'original', 'agent_setup': None,
                      'agent_execution': None, 'exception_info': {'exception_type': 'RuntimeError'}}
            passed = {'task_name': 'dataset/task', 'finished_at': 'finished',
                      'task_checksum': 'recovered'}
            def save(path, record):
                path.write_text(json.dumps(record))
                return fingerprint(path)
            repair = {'original_task_checksum': 'original', 'recovered_task_checksum': 'recovered',
                      'excluded_setup_result_sha256': save(bad/'result.json', failed),
                      'recovery_result_sha256': save(good/'result.json', passed)}
            protocol = {'task_names': ['task'], 'environment_repairs': {'task': repair}}
            selected, excluded = select_trials(original, recovery, protocol)
            self.assertEqual(selected, {'task': good.resolve()})
            self.assertEqual(excluded, ['task'])
            failed['agent_execution'] = {'started_at': 'started'}
            repair['excluded_setup_result_sha256'] = save(bad/'result.json', failed)
            with self.assertRaisesRegex(ValueError, 'execution evidence'):
                select_trials(original, recovery, protocol)
            failed['agent_execution'] = None
            repair['excluded_setup_result_sha256'] = save(bad/'result.json', failed)
            passed['task_checksum'] = 'different'
            save(good/'result.json', passed)
            with self.assertRaisesRegex(ValueError, 'pinned replacement'):
                select_trials(original, recovery, protocol)
            (good/'result.json').unlink()
            with self.assertRaisesRegex(ValueError, 'exactly one'):
                select_trials(original, recovery, protocol)
