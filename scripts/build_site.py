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
    policy=json.loads((root/'data/reference_policy.json').read_text())
    date.fromisoformat(policy['reviewed_at'])
    featured=policy['featured_observation_ids']
    if not isinstance(featured,list) or not featured or any(not isinstance(i,str) for i in featured):
        raise ValueError('Reference policy needs an explicit nonempty observation ID list')
    if len(featured)!=len(set(featured)) or set(featured)-ids:
        raise ValueError('Reference policy has duplicate or missing observation IDs')
    if type(policy.get('review_interval_days')) is not int or policy['review_interval_days']<=0:
        raise ValueError('Reference review interval must be positive')
    public_check(policy)
    registry=json.loads((root/'data/model_registry.json').read_text())
    if not isinstance(registry,list) or not registry:
        raise ValueError('Model registry must be a nonempty list')
    family_ids=set(); labels=set()
    for model in registry:
        if not all(isinstance(model.get(k),str) and model[k] for k in ('id','name','provider')):
            raise ValueError('Invalid model registry identity')
        aliases=model.get('source_labels')
        if not isinstance(aliases,list) or any(not isinstance(a,str) or not a for a in aliases):
            raise ValueError('Invalid model registry source labels')
        if model['id'] in family_ids or labels.intersection(aliases):
            raise ValueError('Duplicate model family or ambiguous source label')
        family_ids.add(model['id']); labels.update(aliases)
    featured_rows=[r for r in records if r['id'] in featured]
    for provider in policy['required_providers']:
        aliases={a for m in registry if m['provider']==provider for a in m['source_labels']}
        if not any(r['model']['name'] in aliases for r in featured_rows):
            raise ValueError(f'Required provider has no featured observations: {provider}')
    public_check(registry)
    return dict(schema_version=1,built_at=date.today().isoformat(),catalog=catalog,reference_policy=policy,model_registry=registry,observations=records)


def build(root, output):
    data=collect(root)  # Fail before touching an existing successful build.
    output.mkdir(parents=True,exist_ok=True)
    for name in ('styles.css','compare.js','app.js'):
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
