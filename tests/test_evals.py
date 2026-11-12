import json
from pathlib import Path
import tempfile
import unittest

from evals import ROOT, load_results, report, validate


def fixture(kind='local'):
    return dict(schema_version=1, id='run-1', kind=kind, observed_at='2026-11-11',
        model=dict(name='test/model', revision='abc123', quantization='Q4_K_M', artifact='weights.gguf', artifact_sha256='a'*64),
        benchmark=dict(name='test-suite', revision='abc123', split='test', task_set='sha256:123'),
        metric=dict(name='success', value=0.5, unit='fraction', direction='higher', n=10),
        protocol=dict(harness='agent', harness_revision='abc123', config={'seed': 42}, backend='runtime', backend_revision='abc123', hardware='test-host'),
        provenance=dict(type='measured' if kind == 'local' else 'independent', location='artifacts/result.json' if kind == 'local' else 'https://example.org/results', retrieved_at='2026-11-11', notes='test fixture only'),
        notes='Synthetic fixture; not a real score.')


class ValidationTests(unittest.TestCase):
    def test_valid_records(self):
        for kind in ('local', 'external'):
            self.assertEqual(validate(fixture(kind)), [])

    def test_invalid_scores_and_counts(self):
        for value in (None, True, float('nan'), float('inf'), -0.1, 1.1):
            r = fixture()
            r['metric']['value'] = value
            self.assertTrue(validate(r), value)
        for count in (None, True, 0, -1, 1.5):
            r = fixture()
            r['metric']['n'] = count
            self.assertTrue(validate(r), count)
        r = fixture('external')
        r['metric']['n'] = None
        self.assertEqual(validate(r), [])

    def test_provenance_and_artifact_requirements(self):
        for section, key, value in [('model', 'artifact_sha256', 'bad'), ('model', 'revision', 'not_reported'), ('protocol', 'config', {}), ('provenance', 'type', 'vendor_reported'), ('provenance', 'retrieved_at', '2026-02-30')]:
            r = fixture()
            r[section][key] = value
            self.assertTrue(validate(r))
        r = fixture('external')
        r['provenance']['location'] = '/local/file'
        self.assertTrue(validate(r))

    def test_invalid_unit_type(self):
        r = fixture()
        r['metric']['unit'] = []
        self.assertTrue(validate(r))

    def test_templates_require_completion(self):
        for kind in ('local', 'external'):
            self.assertTrue(validate(json.loads((ROOT/'templates'/f'{kind}.json').read_text())))

    def test_malformed_and_unknown_fields(self):
        for record in (None, [], {}, {'schema_version': True}):
            self.assertTrue(validate(record))
        for key in ('metric', 'model', 'protocol', 'provenance'):
            r = fixture()
            r[key] = []
            self.assertTrue(validate(r))
        r = fixture()
        r['metirc'] = {}
        self.assertTrue(validate(r))

    def test_duplicate_ids_and_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for name in ('one', 'two'):
                (path/f'{name}.json').write_text(json.dumps(fixture()))
            self.assertTrue(any('duplicate id' in e for e in load_results(path)[1]))
            (path/'bad.json').write_text('{')
            self.assertTrue(load_results(path)[1])
        self.assertTrue(load_results(Path('/nonexistent/evals'))[1])

    def test_report_does_not_expose_absolute_record_paths(self):
        result = report([(Path('/private/example/results/run.json'), fixture())])
        self.assertNotIn('/private/example', result)
        self.assertIn('[record](run.json)', result)

    def test_report_preserves_scale_and_separates_sources(self):
        local, external = fixture(), fixture('external')
        local['model']['name'] = '<tag>|name\nrow'
        external['metric'].update(value=50, unit='percent')
        result = report([(Path('local.json'), local), (Path('external.json'), external)])
        self.assertIn('fraction / higher', result)
        self.assertIn('percent / higher', result)
        self.assertIn('## External references', result)
        self.assertIn('&lt;tag&gt;&#124;name row', result)
        self.assertNotIn('<tag>', result)
        self.assertIn('No observations recorded.', report([]))


if __name__ == '__main__':
    unittest.main()
