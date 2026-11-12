#!/usr/bin/env python3
"""Offline observation validation and reporting. Python 3.11+, standard library only."""
import argparse
from datetime import date
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent
FIELDS = {
    'model': ('name', 'revision', 'quantization', 'artifact'),
    'benchmark': ('name', 'revision', 'split', 'task_set'),
    'protocol': ('harness', 'harness_revision', 'config', 'backend', 'backend_revision', 'hardware'),
    'provenance': ('type', 'location', 'retrieved_at', 'notes'),
}
REQUIRED = {'schema_version', 'id', 'kind', 'observed_at', 'metric', 'notes', *FIELDS}
UNITS = {'fraction', 'percent', 'seconds', 'tokens_per_second', 'index', 'usd'}


def validate(record):
    """Return all validation errors; never infer or repair missing metadata."""
    errors = []
    if not isinstance(record, dict):
        return ['record must be an object']
    for key in sorted(REQUIRED - record.keys()):
        errors.append(f'missing {key}')
    for key in sorted(record.keys() - REQUIRED - {'measurements'}):
        errors.append(f'unknown field {key}')

    def text_field(value, path):
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{path} must be a nonempty string')

    def iso_date(value, path):
        try:
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            errors.append(f'{path} must be YYYY-MM-DD')

    def walk(value, path='record'):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f'{path}.{key}')
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, f'{path}[{i}]')
        elif isinstance(value, str) and 'TODO' in value.upper():
            errors.append(f'{path} contains a TODO placeholder')
        elif isinstance(value, float) and not math.isfinite(value):
            errors.append(f'{path} must be finite')

    walk(record)
    if type(record.get('schema_version')) is not int or record['schema_version'] != 1:
        errors.append('schema_version must be 1')
    kind = record.get('kind')
    if kind not in ('local', 'external'):
        errors.append('kind must be local or external')
    text_field(record.get('id'), 'id')
    text_field(record.get('notes'), 'notes')
    iso_date(record.get('observed_at'), 'observed_at')
    for section, fields in FIELDS.items():
        obj = record.get(section)
        if not isinstance(obj, dict):
            errors.append(f'{section} must be an object')
            continue
        for field in fields:
            if section == 'protocol' and field == 'config' and isinstance(obj.get(field), dict):
                if not obj[field]:
                    errors.append('protocol.config must not be empty')
            else:
                text_field(obj.get(field), f'{section}.{field}')
            if kind == 'local' and obj.get(field) == 'not_reported':
                errors.append(f'local {section}.{field} must be reported')
    model = record.get('model', {})
    if kind == 'local' and isinstance(model, dict):
        if not re.fullmatch('[0-9a-fA-F]{64}', str(model.get('artifact_sha256', ''))):
            errors.append('local model.artifact_sha256 must be 64 hex characters')
    provenance = record.get('provenance', {})
    if isinstance(provenance, dict):
        iso_date(provenance.get('retrieved_at'), 'provenance.retrieved_at')
        allowed = ('measured',) if kind == 'local' else ('benchmark_official', 'independent', 'vendor_reported')
        if provenance.get('type') not in allowed:
            errors.append(f'provenance.type must be one of {allowed}')
        if kind == 'external':
            location = provenance.get('location')
            url = urlparse(location) if isinstance(location, str) else urlparse('')
            if url.scheme not in ('http', 'https') or not url.netloc:
                errors.append('external provenance.location must be an HTTP(S) URL')
    metric = record.get('metric')
    if not isinstance(metric, dict):
        errors.append('metric must be an object')
    else:
        text_field(metric.get('name'), 'metric.name')
        value = metric.get('value')
        numeric = type(value) in (int, float) and math.isfinite(value)
        if not numeric:
            errors.append('metric.value must be a finite number')
        unit = metric.get('unit')
        if not isinstance(unit, str) or unit not in UNITS:
            errors.append(f'metric.unit must be one of {sorted(UNITS)}')
        if numeric and (value < 0 or (unit == 'fraction' and value > 1) or (unit == 'percent' and value > 100)):
            errors.append('metric.value outside unit range')
        if metric.get('direction') not in ('higher', 'lower'):
            errors.append('metric.direction must be higher or lower')
        n = metric.get('n')
        if not (kind == 'external' and 'n' in metric and n is None):
            if type(n) is not int or n <= 0:
                errors.append('metric.n must be a positive integer (external may use null)')
    if 'measurements' in record and not isinstance(record['measurements'], dict):
        errors.append('measurements must be an object')
    return errors


def load_results(directory):
    records, errors, ids = [], [], set()
    if not directory.is_dir():
        return [], [f'{directory}: directory does not exist']
    for path in sorted(directory.rglob('*.json')):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            errors.append(f'{path}: {exc}')
            continue
        problems = validate(record)
        if not problems:
            if record['id'] in ids:
                problems.append(f'duplicate id {record["id"]}')
            ids.add(record['id'])
        errors.extend(f'{path}: {problem}' for problem in problems)
        if not problems:
            records.append((path, record))
    return records, errors


def cell(value):
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')


def report(records):
    lines = ['# Evaluation observations', '', 'Inventory only: review each record’s protocol before comparing scores. No pooled ranking.', '']
    for kind, title in [('local', 'Local measurements'), ('external', 'External references')]:
        lines += [f'## {title}', '']
        rows = [(p, r) for p, r in records if r['kind'] == kind]
        if not rows:
            lines += ['No observations recorded.', '']
            continue
        lines += ['| Model / quant | Benchmark / revision / split / task set | Metric | Value | Unit / direction | Tasks | Date | Provenance | Record |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        for path, r in sorted(rows, key=lambda item: (item[1]['benchmark']['name'], item[1]['model']['name'], item[1]['id'])):
            m, b, metric, source = r['model'], r['benchmark'], r['metric'], r['provenance']
            columns = [f'{m["name"]} / {m["quantization"]}', ' / '.join(b[k] for k in ('name', 'revision', 'split', 'task_set')), metric['name'], metric['value'], f'{metric["unit"]} / {metric["direction"]}', metric['n'] if metric['n'] is not None else 'not reported', r['observed_at'], f'{source["type"]}: {source["location"]}', path.as_posix()]
            rendered = [cell(c) for c in columns]
            try:
                public_path = path.resolve().relative_to(ROOT).as_posix()
            except ValueError:
                public_path = path.name
            rendered[-1] = f'[record]({quote(public_path, safe="/")})'
            lines.append('| ' + ' | '.join(rendered) + ' |')
        lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=ROOT / 'data/results')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('validate')
    commands.add_parser('report')
    template = commands.add_parser('template')
    template.add_argument('kind', choices=['local', 'external'])
    args = parser.parse_args()
    if args.command == 'template':
        print((ROOT / 'templates' / f'{args.kind}.json').read_text(), end='')
        return 0
    records, errors = load_results(args.results)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(report(records) if args.command == 'report' else f'Validated {len(records)} observations.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
