#!/usr/bin/env python3
"""Audit private run artifacts and emit only sanitized aggregate statistics."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

try:
    from scripts.gpqa_diamond import private_path, summarize, tasks
    from scripts.livecodebench import scorer_infrastructure_error
except ModuleNotFoundError:
    from gpqa_diamond import private_path, summarize, tasks
    from livecodebench import scorer_infrastructure_error

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binary_summary(values, total):
    n = len(values)
    if not n:
        return {'completed': 0, 'total': total, 'complete': False}
    correct = sum(values)
    p = correct/n
    z = 1.959963984540054
    center = (p+z*z/(2*n))/(1+z*z/n)
    radius = z*((p*(1-p)/n+z*z/(4*n*n))**0.5)/(1+z*z/n)
    return {'completed': n, 'total': total, 'complete': n == total,
            'correct': correct, 'accuracy': p,
            'wilson_95': [max(0, center-radius), min(1, center+radius)]}


def audit_gpqa(folder, dataset, protocol):
    manifest = read(folder/'manifest.json')
    if manifest['protocol']['generation'] != protocol['generation']:
        raise ValueError('GPQA generation profile mismatch')
    if fingerprint(dataset) != protocol['dataset']['sha256']:
        raise ValueError('GPQA dataset hash mismatch')
    with dataset.open() as stream:
        selected = tasks(list(csv.DictReader(stream)), protocol)
    if manifest['tasks_sha256'] != hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest():
        raise ValueError('GPQA task manifest mismatch')
    records, ids, hashes = [], set(), []
    for path in sorted(folder.glob('[0-9][0-9][0-9].json')):
        r = read(path)
        index = r['index']
        if type(index) is not int or not 0 <= index < len(selected) or index in ids:
            raise ValueError('Unexpected or duplicate GPQA task index')
        ids.add(index)
        expected = selected[index]
        if any(r[key] != expected[key] for key in ('id', 'permutation', 'expected')):
            raise ValueError('GPQA task identity or answer permutation mismatch')
        choice = r['response']['choices'][0]
        match = re.search(protocol['answer_pattern'], choice['message'].get('content') or '')
        answer = match.group(1) if match else None
        if r['answer'] != answer or r['correct'] != (answer == expected['expected']):
            raise ValueError('GPQA stored score disagrees with frozen extraction')
        if r['finish_reason'] != choice['finish_reason']:
            raise ValueError('GPQA finish reason mismatch')
        records.append(r)
        hashes.append(fingerprint(path))
    result = summarize(records, len(selected)) if records else binary_summary([], len(selected))
    result['complete'] = len(ids) == len(selected)
    result['artifact_fingerprints'] = hashes
    return result


def audit_coding(folder, protocol):
    manifest = read(folder/'manifest.json')
    if manifest['protocol']['generation'] != protocol['generation'] or manifest['protocol']['harness_revision'] != protocol['harness_revision']:
        raise ValueError('Coding generation or harness profile mismatch')
    if manifest['rows_sha256'] != protocol['selected_rows_sha256']:
        raise ValueError('Coding dataset hash mismatch')
    values, ids, hashes, seconds = [], set(), [], 0.0
    truncated = forced = unparsed = 0
    for path in sorted(folder.glob('*-score.json')):
        r = read(path)
        index = r['index']
        if type(index) is not int or not 0 <= index < len(protocol['task_ids']) or index in ids:
            raise ValueError('Unexpected or duplicate coding task index')
        ids.add(index)
        if r['task'] != protocol['task_ids'][index]:
            raise ValueError('Coding task identity mismatch')
        result = r['result']
        if scorer_infrastructure_error(result[2]):
            raise ValueError(f'Unresolved coding TestRunnerError at task {index}')
        cases = result[1]['0']
        if len(cases) != 1 or not cases[0]:
            raise ValueError('Expected exactly one completion with nonempty test results')
        passed = all(type(v) in (bool, int, float) and v > 0 for v in cases[0])
        if result[0]['pass@1'] != float(passed):
            raise ValueError('Coding score disagrees with per-test results')
        response_path = folder/f'{index:03}-response.json'
        response = read(response_path)
        if not math.isfinite(response['seconds']) or response['seconds'] < 0:
            raise ValueError('Invalid coding request time')
        seconds += response['seconds']
        body = response['response']
        truncated += body['choices'][0]['finish_reason'] == 'length'
        content = body['choices'][0]['message'].get('content') or ''
        unparsed += sum('```' in line for line in content.splitlines()) < 2
        forced += bool(body.get('usage', {}).get('completion_tokens_details', {}).get('reasoning_closed_by'))
        values.append(int(passed))
        hashes.append({'score': fingerprint(path), 'response': fingerprint(response_path)})
    result = binary_summary(values, len(protocol['task_ids']))
    result.update(elapsed_request_seconds=seconds, truncated=truncated,
                  unparsed=unparsed, forced_reasoning_closures=forced, artifact_fingerprints=hashes)
    return result


def audit_terminal(folder, protocol):
    values, names, hashes, timeouts = [], set(), [], 0
    trial_seconds = agent_seconds = verifier_seconds = 0.0

    def elapsed(phase):
        start = datetime.fromisoformat(phase['started_at'])
        finish = datetime.fromisoformat(phase['finished_at'])
        if start.tzinfo is None or finish.tzinfo is None or finish < start:
            raise ValueError('Invalid terminal execution timestamps')
        return (finish-start).total_seconds()

    for path in sorted(folder.glob('*/result.json')):
        r = read(path)
        if not r.get('finished_at'):
            continue
        name = r['task_name'].rsplit('/', 1)[-1]
        if name not in protocol['task_names'] or name in names:
            raise ValueError('Unexpected or repeated terminal task')
        if r['task_checksum'] != protocol['task_checksums'][name]:
            raise ValueError('Terminal task content/version mismatch')
        config = r['config']
        if any(config.get('environment', {}).get(key) != value
               for key, value in protocol.get('environment_config', {}).items()):
            raise ValueError('Terminal execution environment mismatch')
        options = config['agent']['kwargs']
        requested = {'temperature': options.get('temperature'), 'reasoning_effort': options.get('reasoning_effort'),
                     'max_tokens': options['llm_call_kwargs'].get('max_tokens'),
                     **options['llm_call_kwargs'].get('extra_body', {})}
        if any(requested.get(key) != value for key, value in protocol['generation'].items()):
            raise ValueError('Terminal generation profile mismatch')
        if config['timeout_multiplier'] != 1 or config.get('agent_timeout_multiplier') not in (None, 1) or config['agent'].get('override_timeout_sec') is not None:
            raise ValueError('Terminal task timeout was overridden')
        error = (r.get('exception_info') or {}).get('exception_type')
        if error not in (None, 'AgentTimeoutError'):
            raise ValueError(f'Unresolved terminal exception: {error}')
        reward = ((r.get('verifier_result') or {}).get('rewards') or {}).get('reward')
        if type(reward) not in (int, float) or reward not in (0, 1):
            raise ValueError('Missing or nonbinary terminal verifier outcome')
        verifier = path.parent/'verifier'
        output = verifier/'test-stdout.txt'
        if not output.is_file():
            raise ValueError('Missing terminal verifier execution log')
        log = output.read_text(errors='replace')
        if re.search(r'qemu: uncaught target signal|Segmentation fault.*uvx|uvx.*Segmentation fault', log):
            raise ValueError('Terminal verifier emulation crash; reward is invalid')
        # Every task in the frozen 2.1 snapshot requests a pytest CTRF report.
        # test.sh may write reward=0 even when uvx crashes before pytest starts.
        report = verifier/'ctrf.json'
        if not report.is_file():
            raise ValueError('Missing terminal verifier test report; manual infrastructure review required')
        results = read(report)['results']
        tests_run = results.get('tests', [])
        summary = results.get('summary', {})
        if results.get('tool', {}).get('name') != 'pytest' or not tests_run:
            raise ValueError('Terminal verifier did not record executed tests')
        counts = {status: sum(t.get('status') == status for t in tests_run)
                  for status in ('passed', 'failed', 'skipped')}
        if (sum(counts.values()) != len(tests_run)
                or summary.get('tests') != len(tests_run)
                or any(summary.get(k) != v for k, v in counts.items())
                or not counts['passed'] + counts['failed']):
            raise ValueError('Incomplete or inconsistent terminal verifier test report')
        if reward != int(counts['failed'] == 0):
            raise ValueError('Terminal reward disagrees with executed tests')
        trial_seconds += elapsed(r)
        agent_seconds += elapsed(r['agent_execution'])
        verifier_seconds += elapsed(r['verifier'])
        names.add(name)
        values.append(int(reward))
        hashes.append({'result': fingerprint(path), 'verifier_report': fingerprint(report),
                       'verifier_log': fingerprint(output)})
        timeouts += error == 'AgentTimeoutError'
    result = binary_summary(values, len(protocol['task_names']))
    result.update(agent_timeouts=timeouts, elapsed_trial_seconds=trial_seconds,
                  elapsed_agent_seconds=agent_seconds, elapsed_verifier_seconds=verifier_seconds,
                  artifact_fingerprints=hashes)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lane', choices=['gpqa', 'coding', 'terminal'])
    parser.add_argument('--input', required=True, type=private_path)
    parser.add_argument('--dataset', type=private_path)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    filenames = {'gpqa': 'gpqa-diamond.json', 'coding': 'livecodebench-v6-window.json', 'terminal': 'terminal-bench-2.1.json'}
    protocol = read(ROOT/'protocols'/filenames[args.lane])
    if args.lane == 'gpqa':
        if not args.dataset:
            parser.error('--dataset is required for GPQA audit')
        result = audit_gpqa(args.input, args.dataset, protocol)
    else:
        result = (audit_coding if args.lane == 'coding' else audit_terminal)(args.input, protocol)
    if args.require_complete and not result['complete']:
        raise ValueError('Run is incomplete; refuse final-score export')
    print(json.dumps({'protocol_id': protocol['id'], **result}, indent=2))


if __name__ == '__main__':
    main()
