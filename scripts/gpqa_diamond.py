#!/usr/bin/env python3
"""Run the frozen one-pass GPQA Diamond protocol; keep configuration/output private."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import time
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]


def read_completion(response, progress=None):
    """Collect streaming final content and reasoning without grading partial text."""
    if 'text/event-stream' not in response.headers.get('Content-Type', ''):
        return json.load(response)
    content, reasoning, usage, finish = [], [], {}, None
    for line in response:
        if not line.startswith(b'data:'):
            continue
        data = line[5:].strip()
        if data == b'[DONE]':
            break
        event = json.loads(data)
        if event.get('error'):
            raise ValueError('Streaming API returned an error; no score recorded')
        if event.get('usage'):
            usage = event['usage']
        for choice in event.get('choices', []):
            delta = choice.get('delta', {})
            if delta.get('content'):
                content.append(delta['content'])
            if delta.get('reasoning_content'):
                reasoning.append(delta['reasoning_content'])
            if choice.get('finish_reason'):
                finish = choice['finish_reason']
        if progress:
            progress(sum(map(len, content)), sum(map(len, reasoning)))
    if finish is None:
        raise ValueError('Incomplete stream; no score recorded')
    return {'choices': [{'finish_reason': finish, 'message': {'role': 'assistant',
            'content': ''.join(content), 'reasoning_content': ''.join(reasoning)}}], 'usage': usage}


def private_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to((ROOT / '.local').resolve()):
        raise ValueError('Configuration, dataset and output must be under ignored .local/')
    return path


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def tasks(rows, protocol):
    if len(rows) != protocol['expected_tasks']:
        raise ValueError('Unexpected GPQA Diamond task count')
    rng = random.Random(protocol['answer_shuffle_seed'])
    result = []
    for index, row in enumerate(rows):
        permutation = rng.sample(range(4), 4)
        options = [row['Correct Answer']] + [row[f'Incorrect Answer {i}'] for i in (1, 2, 3)]
        prompt = protocol['prompt'].format(Question=row['Question'], **dict(zip('ABCD', [options[i] for i in permutation])))
        result.append({'index': index, 'id': row['Record ID'], 'domain': row['High-level domain'],
                       'permutation': permutation, 'expected': 'ABCD'[permutation.index(0)], 'prompt': prompt})
    if len({task['id'] for task in result}) != len(result):
        raise ValueError('Duplicate task IDs')
    return result


def summarize(records, total):
    n = len(records)
    correct = sum(r['correct'] for r in records)
    # Wilson interval describes question-sampling uncertainty, not all model variability.
    z = 1.959963984540054
    p = correct / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    radius = z * ((p*(1-p)/n + z*z/(4*n*n))**0.5) / (1 + z*z/n)
    return {'completed': n, 'total': total, 'correct': correct, 'accuracy': p,
            'wilson_95': [max(0, center-radius), min(1, center+radius)],
            'elapsed_request_seconds': sum(r['seconds'] for r in records),
            'unparsed': sum(r['answer'] is None for r in records),
            'truncated': sum(r['finish_reason'] == 'length' for r in records),
            'forced_reasoning_closures': sum(bool(r['response'].get('usage', {}).get('completion_tokens_details', {}).get('reasoning_closed_by')) for r in records)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=private_path)
    parser.add_argument('--dataset', required=True, type=private_path)
    parser.add_argument('--output', required=True, type=private_path)
    parser.add_argument('--limit', type=int, help='Pilot prefix only; never label as the full score')
    args = parser.parse_args()
    protocol = json.loads((ROOT / 'protocols/gpqa-diamond.json').read_text())
    config = json.loads(args.config.read_text())
    dataset_sha256 = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    if dataset_sha256 != protocol['dataset']['sha256']:
        raise ValueError('Dataset bytes do not match the frozen Diamond revision')
    rows = list(csv.DictReader(args.dataset.open()))
    all_tasks = tasks(rows, protocol)
    if args.limit is not None and not 1 <= args.limit <= len(all_tasks):
        raise ValueError('Pilot limit must be between 1 and 198')
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {'protocol': protocol, 'dataset_sha256': dataset_sha256,
                'model': config['model'], 'deployment': config['deployment'],
                'tasks_sha256': hashlib.sha256(json.dumps(all_tasks, sort_keys=True).encode()).hexdigest()}
    manifest_path = args.output / 'manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise ValueError('Existing output belongs to a different configuration; choose another directory')
    save(manifest_path, manifest)
    opener = build_opener(ProxyHandler({})) if config.get('bypass_proxy') else build_opener()
    for task in all_tasks[:args.limit]:
        path = args.output / f"{task['index']:03}.json"
        if path.exists():
            continue
        request = {'model': config['model'], 'messages': [{'role': 'user', 'content': task['prompt']}],
                   'stream': True, 'stream_options': {'include_usage': True}, **protocol['generation']}
        headers = {'Content-Type': 'application/json'}
        if config.get('api_key'):
            headers['Authorization'] = 'Bearer ' + config['api_key']
        start = time.monotonic()
        req = Request(config['base_url'].rstrip('/') + '/chat/completions', data=json.dumps(request).encode(), headers=headers)
        with opener.open(req, timeout=1500) as response:
            body = read_completion(response)
        choice = body['choices'][0]
        match = re.search(protocol['answer_pattern'], choice['message'].get('content') or '')
        answer = match.group(1) if match else None
        record = {k: v for k, v in task.items() if k != 'prompt'}
        record.update(answer=answer, correct=answer == task['expected'], seconds=time.monotonic()-start,
                      finish_reason=choice['finish_reason'], response=body)
        save(path, record)
        records = [json.loads(p.read_text()) for p in sorted(args.output.glob('[0-9][0-9][0-9].json'))]
        summary = summarize(records, len(all_tasks))
        save(args.output / 'summary.json', summary)
        print(json.dumps({k: summary[k] for k in ('completed', 'total', 'correct')}), flush=True)


if __name__ == '__main__':
    main()
