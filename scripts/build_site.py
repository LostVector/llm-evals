#!/usr/bin/env python3
"""Build a self-contained public static bundle from validated repo data."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals import load_results, validate


def public_check(record):
    """Catch common accidental leaks; human review remains necessary."""
    raw = json.dumps(record)
    for pattern in (r'/Users/', r'/home/', r'(?i)[A-Z]:\\\\Users\\\\',
                    r'(?i)(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_\-]{12,}',
                    r'(?i)[\w.+-]+@[\w.-]+\.[a-z]{2,}',
                    r'(?i)https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(?:[:/]|\b)'):
        if re.search(pattern, raw):
            raise ValueError('Possible private information in public data; review/redact before building')
    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if re.search(r'(?i)^(api[_-]?key|access[_-]?token|password|authorization|secret)$',key):
                    raise ValueError('Credential field in public data; remove before building')
                walk(item)
        elif isinstance(value,list):
            for item in value: walk(item)
    walk(record)


def collect(root):
    local, errors = load_results(root/'data/results')
    if errors: raise ValueError('\n'.join(errors))
    records = [r for _,r in local]
    for directory in ('references','frontier'):
        for path in sorted((root/'data'/directory).glob('*.json')):
            batch = json.loads(path.read_text())
            if not isinstance(batch,list): raise ValueError(f'{path.name}: expected observation array')
            for record in batch:
                errors = validate(record)
                if errors: raise ValueError(f'{path.name}: {errors}')
                if record['kind'] != 'external': raise ValueError('Reference snapshots must be external')
                records.append(record)
    ids=set()
    for record in records:
        if record['id'] in ids: raise ValueError('Duplicate observation ID')
        ids.add(record['id'])
        public_check(record)
    catalog=json.loads((root/'data/frontier_catalog.json').read_text())
    public_check(catalog)
    return dict(schema_version=1,built_at=date.today().isoformat(),catalog=catalog,observations=records)


def build(root, output):
    data=collect(root)  # Fail before touching an existing successful build.
    output.mkdir(parents=True,exist_ok=True)
    for name in ('styles.css','app.js'):
        shutil.copyfile(root/'site'/name,output/name)
    payload=json.dumps(data,ensure_ascii=False,indent=2)
    (output/'data.json').write_text(payload+'\n')
    html=(root/'site/index.html').read_text()
    embedded='<script id="evaluation-data" type="application/json">'+payload.replace('<',r'\u003c')+'</script>'
    (output/'index.html').write_text(html.replace('</body>',embedded+'\n</body>'))
    (output/'.nojekyll').touch()
    return len(data['observations'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    try: print(f'Built site with {build(ROOT,args.output)} observations.')
    except (OSError,ValueError) as exc:
        print(f'Build failed: {exc}',file=sys.stderr)
        sys.exit(1)
