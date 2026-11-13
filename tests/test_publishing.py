import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_site import ROOT, build, collect, public_check
from scripts.sync_frontier import FEEDS, observations, parse_table, refresh

FIXTURES=ROOT/'tests/fixtures'


class PublishingTests(unittest.TestCase):
    def fetch(self,url):
        feed=next(k for k,v in FEEDS.items() if v[0]==url)
        return (FIXTURES/f'{feed}.md').read_text()

    def test_ingestion_keeps_aggregates_separate(self):
        rows=observations(self.fetch(FEEDS['bbeh'][0]),'bbeh','2026-11-11')
        self.assertEqual(len(rows),9)
        self.assertEqual({r['benchmark']['task_set'] for r in rows},{'full','mini'})
        self.assertEqual({r['metric']['name'] for r in rows},{'micro_accuracy','harmonic_accuracy'})
        self.assertEqual(rows[0]['metric']['value'],40)
        self.assertTrue(all(r['kind']=='external' for r in rows))

    def test_format_change_fails_without_overwriting_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            self.assertEqual(refresh(output,self.fetch,'2026-11-11'),2)
            before={p.name:p.read_bytes() for p in output.iterdir()}
            def broken(url):
                return 'Changed upstream layout' if url==FEEDS['supergpqa'][0] else self.fetch(url).replace('| 40 | 50 | 60 |','| 41 | 50 | 60 |')
            with self.assertRaises(ValueError): refresh(output,broken,'2026-11-12')
            self.assertEqual(before,{p.name:p.read_bytes() for p in output.iterdir()})
            self.assertEqual(refresh(output,self.fetch,'2026-11-12'),0)

    def test_same_day_changes_preserve_history_and_unique_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            refresh(output,self.fetch,'2026-11-11')
            changed=lambda url:self.fetch(url).replace('| 40 | 50 | 60 |','| 41 | 50 | 60 |')
            self.assertEqual(refresh(output,changed,'2026-11-11'),1)
            self.assertEqual(len(list(output.iterdir())),3)
            self.assertEqual(refresh(output,changed,'2026-11-11'),0)
            records=[r for p in output.iterdir() for r in json.loads(p.read_text())]
            self.assertEqual(len(records),len({r['id'] for r in records}))

    def test_out_of_range_score_is_rejected(self):
        text=self.fetch(FEEDS['bbeh'][0]).replace('| 40 | 50 | 60 |','| 140 | 50 | 60 |')
        with self.assertRaises(ValueError): parse_table(text,'bbeh')

    def test_public_data_checks(self):
        for value in ('/Users/example/private/log','/home/example/run','person@example.org','http://192.168.1.1/api',{'api_key':'placeholder'}):
            with self.assertRaises(ValueError): public_check(value)
        public_check({'hardware':'Generic workstation; 64 GiB RAM','source':'https://example.org/results'})

    def test_current_cohort_covers_required_providers_on_same_index_version(self):
        payload=collect(ROOT)
        featured=set(payload['reference_policy']['featured_observation_ids'])
        records=[r for r in payload['observations'] if r['id'] in featured and r['benchmark']['name']=='AA Intelligence Index' and r['benchmark']['revision']=='5.0.1']
        providers={m['provider'] for m in payload['model_registry'] if any(r['model']['name'] in m['source_labels'] for r in records)}
        self.assertTrue(set(payload['reference_policy']['required_providers']).issubset(providers))
        self.assertTrue(any('Fable 5.2' in r['model']['name'] for r in records))
        self.assertTrue(any('Sol' in r['model']['name'] for r in records))
        self.assertTrue(any('Opus 5.5' in r['model']['name'] for r in records))
        self.assertTrue(all(r['metric']['unit']=='index' for r in records))

    def test_primary_metric_is_public_diamond_not_private_composite(self):
        payload=collect(ROOT)
        primary=payload['reference_policy']['primary_metric']
        self.assertEqual(primary['benchmark'],'HLE-Diamond')
        self.assertEqual(primary['unit'],'percent')
        protocol=json.loads((ROOT/primary['protocol']).read_text())
        self.assertEqual(protocol['dataset'],'cais/hle-diamond')
        self.assertEqual(protocol['expected_tasks'],1000)
        self.assertFalse(protocol['tools'])

    def test_real_bundle_is_valid_and_complete(self):
        payload=collect(ROOT)
        self.assertGreaterEqual(len(payload['catalog']),6)
        self.assertGreater(len(payload['observations']),0)
        coding=[r for r in payload['observations'] if r['benchmark']['name']=='LiveCodeBench']
        self.assertGreaterEqual(len(coding),5)
        historical=[r for r in coding if r['id'].startswith('lcb-history-')]
        self.assertGreaterEqual(len(historical),5)
        vendor=[r for r in coding if r['provenance']['type']=='vendor_reported']
        self.assertTrue(vendor)
        self.assertTrue(all(r['metric']['n'] is None for r in vendor))
        self.assertTrue(all('comparison_group' not in r['protocol']['config'] for r in vendor))
        self.assertTrue(all(r['metric']['n']==131 for r in historical))
        self.assertTrue(all(r['id'] not in payload['reference_policy']['featured_observation_ids'] for r in historical))
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            build(ROOT,output)
            self.assertEqual(payload,json.loads((output/'data.json').read_text()))
            html=(output/'index.html').read_text()
            embedded=html.split('<script id="evaluation-data" type="application/json">')[1].split('</script>')[0]
            self.assertEqual(payload,json.loads(embedded))
            self.assertTrue((output/'app.js').exists())
            self.assertNotIn(str(ROOT),html)


if __name__=='__main__': unittest.main()
