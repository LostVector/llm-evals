#!/usr/bin/env python3
"""Build a private, auditable terminal cohort without changing original trials."""
import argparse
import json
from pathlib import Path

from scripts.audit_local import fingerprint, read, ROOT
from scripts.gpqa_diamond import private_path


def select_trials(original, recovery, protocol):
    repairs = protocol.get('environment_repairs', {})
    selected, excluded, replacements = {}, set(), set()
    for source, recovered in ((original, False), (recovery, True)):
        for path in sorted(source.glob('*/result.json')):
            record = read(path)
            if not record.get('finished_at'):
                continue
            name = record['task_name'].rsplit('/', 1)[-1]
            if name not in protocol['task_names'] or name in ('.', '..'):
                raise ValueError('Unexpected task in terminal cohort')
            repair = repairs.get(name)
            if not recovered and repair and fingerprint(path) == repair['excluded_setup_result_sha256']:
                if (record.get('agent_execution') or record.get('agent_setup')
                        or record['task_checksum'] != repair['original_task_checksum']
                        or not record.get('exception_info')):
                    raise ValueError('Excluded setup trial has unexpected execution evidence')
                excluded.add(name)
                continue
            if recovered:
                if (not repair or fingerprint(path) != repair['recovery_result_sha256']
                        or record['task_checksum'] != repair['recovered_task_checksum']):
                    raise ValueError('Recovery trial is not the explicitly pinned replacement')
                replacements.add(name)
            if name in selected:
                raise ValueError('Repeated task; refuse outcome selection')
            selected[name] = path.parent.resolve()
    if excluded != replacements:
        raise ValueError('Every excluded setup must have exactly one pinned replacement')
    return selected, sorted(excluded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=private_path)
    parser.add_argument('--recovery', required=True, type=private_path)
    parser.add_argument('--output', required=True, type=private_path)
    args = parser.parse_args()
    protocol = read(ROOT/'protocols/terminal-bench-2.1.json')
    selected, excluded = select_trials(args.input, args.recovery, protocol)
    if args.output.exists():
        raise ValueError('Use a fresh private output directory; existing cohorts are never overwritten')
    args.output.mkdir(parents=True)
    for name, path in selected.items():
        (args.output/name).symlink_to(path, target_is_directory=True)
    (args.output/'selection.json').write_text(json.dumps({
        'protocol_id': protocol['id'], 'excluded_pre_agent_setups': excluded,
        'trials': {name: str(path) for name, path in selected.items()},
    }, indent=2)+'\n')
    print(f'Assembled {len(selected)} completed trials; run audit_local before accepting scores.')


if __name__ == '__main__':
    main()
