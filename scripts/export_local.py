#!/usr/bin/env python3
"""Export a complete audited run with explicit, verified public model metadata."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evals import validate
from scripts.reasoning import reasoning_policy
from scripts.audit_reasoning_recovery import audit_recovery
from scripts.audit_local import audit_gpqa, audit_coding, audit_terminal
from scripts.build_site import public_check
from scripts.gpqa_diamond import private_path

PROTOCOLS = {'gpqa': 'gpqa-diamond.json', 'coding': 'livecodebench-v6-window.json',
             'terminal': 'terminal-bench-2.1.json'}


def observation(lane, summary, protocol, metadata, identifier, observed_at, audit_revision):
    if not summary.get('complete') or summary['completed'] != summary['total']:
        raise ValueError('Incomplete run: no public result may be written')
    if summary['total'] != protocol['expected_tasks']:
        raise ValueError('Audited task count does not match the frozen protocol')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,119}', identifier):
        raise ValueError('Result ID must be a public slug')
    if metadata.get('artifact_verified') is not True:
        raise ValueError('Actual loaded-artifact SHA-256 has not been verified')
    model = {key: metadata['model'][key] for key in (
        'name', 'revision', 'quantization', 'artifact', 'artifact_sha256')}
    labels = {label for family in json.loads((ROOT/'data/model_registry.json').read_text())
              for label in family['source_labels']}
    if model['name'] not in labels:
        raise ValueError('Model name must be a registered public label, not an endpoint alias')
    config = {'protocol_id': protocol['id'], 'protocol_file': 'protocols/'+PROTOCOLS[lane],
              'generation': protocol['generation'], 'attempts_per_task': 1,
              'audit_revision': audit_revision,
              'runtime_context': 'Shared inference service; suite lanes ran concurrently. Request times include queue/retry time.'}
    config['reasoning'] = reasoning_policy(metadata.get('reasoning'))
    telemetry = metadata.get('reasoning_closure_telemetry', 'backend_reported_markers_only')
    if telemetry not in ('backend_reported_markers_only', 'not_reported'):
        raise ValueError('Invalid reasoning closure telemetry description')
    config['reasoning_closure_telemetry'] = telemetry
    if metadata.get('response_recovery'):
        config['response_recovery'] = metadata['response_recovery']
        config['attempts_per_task'] = 'Variable; one retained or regenerated scored response per task; discarded originals preserved separately.'
    if metadata.get('infrastructure_recovery'):
        allowed_recovery = ('transport_failed_tasks', 'transport_failures_after_agent_actions', 'interrupted_pre_agent_tasks', 'user_interrupted_recovery_attempts', 'selected_replacements', 'additional_transport_failed_recoveries')
        recovery = metadata['infrastructure_recovery']
        if set(recovery) - set(allowed_recovery) or any(type(v) is not int or v < 0 for v in recovery.values()):
            raise ValueError('Invalid public infrastructure recovery summary')
        config['infrastructure_recovery'] = dict(recovery)
        config['attempts_per_task'] = 'Variable due to infrastructure failures and user interruption; one audited verifier outcome per task.'
    if metadata.get('observed_sampling_defaults'):
        config['observed_sampling_defaults'] = {key: value for key, value in metadata['observed_sampling_defaults'].items() if key in ('min_p', 'repeat_penalty', 'source', 'scope')}
    if metadata.get('kv_cache_precision'):
        config['kv_cache_precision'] = metadata['kv_cache_precision']
    if protocol.get('comparison_group'):
        config['comparison_group'] = protocol['comparison_group']
    if metadata.get('artifact_verification'):
        config['artifact_verification'] = {key: metadata['artifact_verification'][key]
            for key in ('source', 'verified_at', 'scope', 'evaluation_period_continuity',
                        'public_artifact_source_revision') if key in metadata['artifact_verification']}
    if lane != 'gpqa' and metadata.get('execution_environment'):
        config['execution_environment'] = metadata['execution_environment']
    if lane == 'gpqa':
        benchmark = {'name': 'GPQA Diamond', 'revision': protocol['dataset']['revision'],
                     'split': 'diamond', 'task_set': '198 questions; fixed shuffle seed 0'}
        harness = 'simple-evals GPQA prompt/regex plus audited local client'
        revision = 'prompt-source-sha256:'+protocol['prompt_source_sha256']
        config['client_phases'] = 'Scores are recomputed from final content using the frozen prompt, answer permutation, and extraction rule.'
        metric = 'accuracy'
    elif lane == 'coding':
        config['comparison_group'] = 'livecodebench-v6-feb-apr-2025-131'
        benchmark = {'name': 'LiveCodeBench', 'revision': protocol['release'],
                     'split': '2025-02-01 inclusive to 2025-05-01 exclusive',
                     'task_set': 'sha256:'+protocol['selected_rows_sha256']}
        harness = 'LiveCodeBench official prompt/scorer plus audited local client'
        revision = protocol['harness_revision']
        config['client_phases'] = 'Scores are checked against official per-test results using the frozen task set and grader.'
        metric = 'pass@1'
    else:
        benchmark = {'name': 'Terminal-Bench', 'revision': protocol['version'],
                     'split': 'full', 'task_set': 'sha256:'+protocol['snapshot_tree_sha256']}
        harness = protocol['harness']
        revision = protocol['harness_version']
        config['calibration'] = protocol['calibration']
        config['task_environment'] = protocol['environment']
        config['environment_config'] = protocol.get('environment_config', {})
        if protocol.get('environment_repairs'):
            config['environment_repairs'] = protocol['environment_repairs']
        metric = 'task_resolution'
    allowed = ('completed', 'total', 'correct', 'wilson_95', 'elapsed_request_seconds',
               'truncated', 'unparsed', 'forced_reasoning_closures', 'agent_timeouts',
               'elapsed_trial_seconds', 'elapsed_agent_seconds', 'elapsed_verifier_seconds',
               'artifact_fingerprints')
    record = {'schema_version': 1, 'id': identifier, 'kind': 'local', 'observed_at': observed_at,
              'model': model, 'benchmark': benchmark,
              'metric': {'name': metric, 'value': summary['accuracy'], 'unit': 'fraction',
                         'direction': 'higher', 'n': summary['total']},
              'protocol': {'harness': harness, 'harness_revision': revision, 'config': config,
                           'backend': metadata['backend'], 'backend_revision': metadata['backend_revision'],
                           'hardware': metadata['hardware']},
              'provenance': {'type': 'measured',
                             'location': 'https://github.com/LostVector/llm-evals/blob/main/data/results/'+identifier+'.json',
                             'retrieved_at': observed_at,
                             'notes': 'Sanitized complete-run audit. Raw task content and traces remain private; artifact fingerprints permit later integrity checks.'},
              'measurements': {key: summary[key] for key in allowed if key in summary},
              'notes': 'One attempt per task. Wilson intervals describe question-sampling uncertainty, not all model variability. Published references have different generation and harness profiles; they provide context rather than a controlled quant comparison.'}
    if telemetry == 'not_reported':
        if summary.get('forced_reasoning_closures', 0):
            raise ValueError('Closure markers present despite not-reported telemetry metadata')
        record['measurements'].pop('forced_reasoning_closures', None)
    if metadata.get('response_recovery'):
        record['notes'] = ('Partial regeneration: original responses below the reasoning threshold were retained; missing and preselected long/capped responses were generated under the recorded budget. Selection ignored correctness. This is not a fresh uniform full run. Discarded original request time is reported separately; interrupted and probe requests are excluded from timing totals. Exact Halogen closing-message equivalence and identical counterfactual outputs are unverified. Wilson intervals describe question-sampling uncertainty only; external references remain contextual.')
    if metadata.get('infrastructure_recovery'):
        record['notes'] = ('One audited verifier outcome per task. Predetermined infrastructure-failed or user-interrupted trials were replaced; some transport failures followed prior agent actions. Originals and interrupted recoveries are preserved, and model failures/timeouts were not retried to improve scores. Timings cover selected trials only and omit excluded attempts. This is a deployment comparison with different backend/runtime settings; external references provide context. Wilson intervals describe task-sampling uncertainty only.')
    if metadata.get('artifact_verification', {}).get('evaluation_period_continuity') == 'unverified':
        record['notes'] += ' Artifact SHA-256 was verified on the server after evaluation; continuity of this exact artifact/backend throughout the evaluation period is unverified. Public artifact source/revision is unknown.'
    errors = validate(record)
    if errors:
        raise ValueError('; '.join(errors))
    public_check(record)
    if re.search(r'\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b', json.dumps(record)):
        raise ValueError('Private network address in public metadata')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lane', choices=PROTOCOLS)
    parser.add_argument('--input', required=True, type=private_path)
    parser.add_argument('--dataset', type=private_path)
    parser.add_argument('--metadata', required=True, type=private_path)
    parser.add_argument('--id', required=True)
    parser.add_argument('--recovery-plan', type=private_path, help='Frozen partial-regeneration plan; requires original input for lineage audit')
    parser.add_argument('--original-input', type=private_path)
    parser.add_argument('--write', action='store_true', help='Write only a complete validated observation to data/results')
    args = parser.parse_args()
    protocol = json.loads((ROOT/'protocols'/PROTOCOLS[args.lane]).read_text())
    if args.lane == 'gpqa':
        if not args.dataset:
            parser.error('--dataset is required for GPQA')
        summary = audit_gpqa(args.input, args.dataset, protocol)
    else:
        summary = (audit_coding if args.lane == 'coding' else audit_terminal)(args.input, protocol)
    metadata = json.loads(args.metadata.read_text())
    manifest = args.input/'manifest.json'
    if manifest.exists() and 'reasoning' in json.loads(manifest.read_text()):
        recorded = reasoning_policy(json.loads(manifest.read_text())['reasoning'])
        if metadata.get('reasoning') and reasoning_policy(metadata['reasoning']) != recorded:
            raise ValueError('Export reasoning policy differs from run manifest')
        metadata['reasoning'] = recorded
    if args.recovery_plan:
        if args.lane == 'terminal' or not args.original_input:
            parser.error('--recovery-plan requires GPQA/coding and --original-input')
        metadata['response_recovery'] = audit_recovery(args.original_input, args.input, args.recovery_plan, args.lane)
    elif metadata.get('response_recovery'):
        parser.error('Partial-regeneration export requires --recovery-plan and --original-input; metadata alone is insufficient')
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    record = observation(args.lane, summary, protocol, metadata, args.id,
                         datetime.now(timezone.utc).date().isoformat(), revision)
    output = json.dumps(record, indent=2)+'\n'
    if args.write:
        destination = ROOT/'data/results'/f'{args.id}.json'
        with destination.open('x') as stream:
            stream.write(output)
        print(destination.relative_to(ROOT))
    else:
        print(output, end='')


if __name__ == '__main__':
    main()
