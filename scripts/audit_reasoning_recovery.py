"""Audit outcome-independent partial regeneration without exposing task content."""
import hashlib
import json
from pathlib import Path
from scripts.reasoning import reasoning_policy


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_recovery(original, corrected, plan_file, lane):
    plan = read(plan_file)
    policy = reasoning_policy(plan['policy'])
    budget = policy['budget_tokens']
    if type(budget) is not int or budget <= 0:
        raise ValueError('Recovery needs an explicit positive reasoning budget')
    selection = plan['lanes'][lane]
    manifest = read(corrected/'manifest.json')
    if reasoning_policy(manifest.get('reasoning')) != policy:
        raise ValueError('Recovery manifest policy differs from selection plan')
    if manifest.get('reasoning_request') != {'reasoning_budget_tokens': budget}:
        raise ValueError('Recovery request override differs from selection policy')
    retained, regenerate, missing = [set(selection[k]) for k in ('retained', 'regenerate', 'missing')]
    expected_count = 198 if lane == 'gpqa' else 131
    if (retained & regenerate or retained & missing or regenerate & missing
            or retained | regenerate | missing != set(range(expected_count))):
        raise ValueError('Recovery selections must partition the entire task set')
    pattern = '[0-9][0-9][0-9].json' if lane == 'gpqa' else '[0-9][0-9][0-9]-response.json'
    originals = {int(p.name[:3]): p for p in original.glob(pattern)}
    outputs = {int(p.name[:3]): p for p in corrected.glob(pattern)}
    evidence = {item['index']: item for item in selection['source_evidence']}
    if set(originals) != retained | regenerate or set(evidence) != set(originals):
        raise ValueError('Original response inventory differs from frozen evidence')
    if set(outputs) != set(range(expected_count)):
        raise ValueError('Corrected response inventory is incomplete or unexpected')
    discarded_seconds = reused_seconds = generated_seconds = 0
    for index, source in originals.items():
        if sha(source) != evidence[index]['sha256']:
            raise ValueError('Original response changed after selection')
        response = read(source)
        tokens = response['response'].get('usage', {}).get('completion_tokens')
        affected = (response['response']['choices'][0]['finish_reason'] == 'length'
                    or tokens is None or tokens >= budget)
        if affected != (index in regenerate):
            raise ValueError('Recovery selection is not independent of score')
        if index in retained:
            if sha(outputs[index]) != sha(source):
                raise ValueError('Retained response changed')
            if lane == 'coding' and sha(corrected/f'{index:03}-score.json') != sha(original/f'{index:03}-score.json'):
                raise ValueError('Retained coding score changed')
            reused_seconds += response['seconds']
        else:
            discarded_seconds += response['seconds']
    for index in regenerate | missing:
        generated_seconds += read(outputs[index])['seconds']
    return {
        'policy': 'partial_regeneration',
        'selection': 'Regenerate missing responses and every original response with length finish reason, unknown token usage, or total output tokens >= the reasoning threshold; selection ignores correctness.',
        'reasoning_budget_tokens': budget,
        'retained_responses': len(retained),
        'regenerated_responses': len(regenerate),
        'previously_missing_responses': len(missing),
        'selection_plan_sha256': sha(plan_file),
        'original_evidence_sha256': hashlib.sha256(json.dumps(selection['source_evidence'], sort_keys=True).encode()).hexdigest(),
        'discarded_original_request_seconds': discarded_seconds,
        'retained_request_seconds': reused_seconds,
        'new_request_seconds': generated_seconds,
        'limitations': 'Not a fresh uniform full run. Reused responses came from the earlier server policy; identical counterfactual outputs and exact Halogen closing-message equivalence are unverified. Times omit incomplete/interrupted requests and probe requests.',
    }
