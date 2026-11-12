#!/usr/bin/env python3
"""Refresh two public upstream Markdown tables; fail closed on format changes."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals import validate

FEEDS = {
    'bbeh': ('https://raw.githubusercontent.com/google-deepmind/bbeh/main/leaderboard.md',
             'https://github.com/google-deepmind/bbeh/blob/main/leaderboard.md'),
    'supergpqa': ('https://raw.githubusercontent.com/SuperGPQA/SuperGPQA/main/README.md',
                  'https://github.com/SuperGPQA/SuperGPQA'),
}


def parse_table(text, feed):
    """Parse only recognized tables and exact expected columns, never infer a score."""
    rows = []
    header = None
    for line in text.splitlines():
        if '|' not in line:
            header = None
            continue
        cells = [re.sub(r'\*\*|`', '', c).strip() for c in line.strip().strip('|').split('|')]
        if feed == 'bbeh' and 'BBEH (Micro Avg)' in cells:
            if cells[-3:] != ['BBEH', 'BBEH (Micro Avg)', 'BBEH Mini (Micro Avg)']:
                raise ValueError('BBEH table columns changed')
            header = cells
            continue
        if feed == 'supergpqa' and 'Overall (sample)' in cells:
            if not all(c in cells for c in ('Model', 'Overall (sample)', 'Overall (discipline)')):
                raise ValueError('SuperGPQA table columns changed')
            header = cells
            continue
        if header is None or all(not c or re.fullmatch(r'[:\- ]+', c) for c in cells):
            continue
        if len(cells) != len(header):
            raise ValueError(f'{feed} row width changed')
        model = cells[0]
        if not model or model.lower() == 'random':
            continue
        if feed == 'bbeh':
            columns = [('BBEH', 'original-paper', 'full', 'harmonic_accuracy'),
                       ('BBEH (Micro Avg)', 'original-paper', 'full', 'micro_accuracy'),
                       ('BBEH Mini (Micro Avg)', 'original-paper', 'mini', 'micro_accuracy')]
        else:
            columns = [('Overall (sample)', 'original-paper', 'full', 'sample_accuracy'),
                       ('Overall (discipline)', 'original-paper', 'full', 'discipline_macro_accuracy')]
        for column, revision, task_set, metric in columns:
            raw = cells[header.index(column)].strip('% ')
            if not re.fullmatch(r'\d+(\.\d+)?', raw):
                raise ValueError(f'{feed}: unexpected score for {model}: {raw}')
            value = float(raw)
            if not 0 <= value <= 100:
                raise ValueError('score out of range')
            rows.append((model, revision, task_set, metric, value))
    if len(rows) < 6:
        raise ValueError(f'{feed}: expected at least three model rows; found {len(rows)} values')
    keys = [(r[0], r[2], r[3]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError(f'{feed}: duplicate model/metric rows')
    return rows


def observations(text, feed, retrieved):
    digest = hashlib.sha256(text.encode()).hexdigest()
    benchmark = 'BBEH' if feed == 'bbeh' else 'SuperGPQA'
    result = []
    for model, revision, task_set, metric, value in parse_table(text, feed):
        identity = hashlib.sha256(json.dumps([feed, model, task_set, metric, value]).encode()).hexdigest()[:20]
        record = dict(schema_version=1, id=f'{feed}-{retrieved}-{digest[:12]}-{identity}', kind='external', observed_at=retrieved,
            model=dict(name=model, revision='not_reported', quantization='not_reported', artifact='not_reported'),
            benchmark=dict(name=benchmark, revision=revision, split='test', task_set=task_set),
            metric=dict(name=metric, value=value, unit='percent', direction='higher', n=None),
            protocol=dict(harness='upstream published evaluation', harness_revision='not_reported', config='not_reported', backend='not_reported', backend_revision='not_reported', hardware='not_reported'),
            provenance=dict(type='benchmark_official', location=FEEDS[feed][1], retrieved_at=retrieved,
                notes=f'Upstream model row: {model}; fetched from {FEEDS[feed][0]}; response SHA-256 {digest}. Retrieval date is not evaluation date.'),
            notes='Historical reference table, not necessarily current frontier coverage. Original task/evaluator commit not established; original-paper is a source track label, not an immutable dataset pin. Do not assume equivalence with a new local run.')
        errors = validate(record)
        if errors:
            raise ValueError('; '.join(errors))
        result.append(record)
    return result


def signature(records):
    return sorted(json.dumps([r['model']['name'], r['benchmark'], r['metric']], sort_keys=True) for r in records)


def refresh(output, fetch, retrieved):
    """Fetch and validate every feed before writing anything; retain prior snapshots."""
    planned = []
    for feed, (url, _) in FEEDS.items():
        records = observations(fetch(url), feed, retrieved)
        previous = sorted(output.glob(f'{feed}-*.json')) if output.exists() else []
        if previous:
            old = json.loads(previous[-1].read_text())
            if signature(old) == signature(records):
                continue
        path = output / f'{feed}-{retrieved}.json'
        if path.exists():
            # Preserve more than one change on the same date without overwriting history.
            suffix = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()[:8]
            stamp = datetime.now(timezone.utc).strftime('%H%M%S%f')
            path = output / f'{feed}-{retrieved}_{stamp}-{suffix}.json'
        planned.append((path, records))
    output.mkdir(parents=True, exist_ok=True)
    for path, records in planned:
        path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + '\n')
    return len(planned)


def download(url):
    request = Request(url, headers={'User-Agent': 'llm-evals-public-table-sync/1.0'})
    with urlopen(request, timeout=30) as response:
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError('upstream response exceeds size limit')
    return data.decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'data/frontier')
    args = parser.parse_args()
    try:
        count = refresh(args.output, download, date.today().isoformat())
    except (ValueError, OSError) as exc:
        print(f'Sync failed; previous snapshots retained: {exc}', file=sys.stderr)
        return 1
    print(f'Wrote {count} changed source snapshots.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
