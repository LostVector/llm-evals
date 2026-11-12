#!/usr/bin/env python3
"""Reproduce archived exact-window coding references; never execute their programs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from urllib.parse import quote
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.gpqa_diamond import private_path


def reference_score(rows, questions, start, end):
    expected={q['platform']+'/'+str(q['question_id']):q for q in questions}
    selected=[r for r in rows if start<=r['contest_date']<end]
    ids=[r['platform']+'/'+str(r['question_id']) for r in selected]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):
        raise ValueError('Submission does not cover exactly the frozen task set')
    scores,counts=[],set()
    for identifier,row in zip(ids,selected):
        if any(row[key]!=expected[identifier][key] for key in ('question_content','starter_code')):
            raise ValueError('Submission input text differs from the frozen task')
        grades=row['graded_list']
        if not grades or any(type(g) not in (bool,int) or g not in (0,1) for g in grades):
            raise ValueError('Invalid official grade array')
        score=sum(grades)/len(grades)
        if not math.isclose(row['pass@1'],score,abs_tol=1e-12):
            raise ValueError('Stored pass@1 disagrees with per-completion grades')
        scores.append(score);counts.add(len(grades))
    if len(counts)!=1:
        raise ValueError('Mixed completion counts require explicit review')
    return {'score':sum(scores)/len(scores),'samples_per_task':next(iter(counts))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-dir',type=private_path,required=True)
    parser.add_argument('--dataset-dir',type=private_path,required=True)
    parser.add_argument('--download',action='store_true',help='Cache missing immutable files from the official public repository')
    args=parser.parse_args()
    protocol=json.loads((ROOT/'protocols/livecodebench-v6-window.json').read_text())
    start,end=protocol['window_start_inclusive'],protocol['window_end_exclusive']
    with (args.dataset_dir/'test6.jsonl').open() as stream:
        questions=[r for line in stream if start<=(r:=json.loads(line))['contest_date']<end]
    questions.sort(key=lambda r:(r['contest_date'],r['platform'],r['question_id']))
    if hashlib.sha256(json.dumps(questions,sort_keys=True).encode()).hexdigest()!=protocol['selected_rows_sha256']:
        raise ValueError('Dataset does not match the pinned local coding window')
    records=json.loads((ROOT/'data/references/livecodebench-history-v6-2026-11-12.json').read_text())
    for record in records:
        config=record['protocol']['config']
        path=(args.archive_dir/record['model']['name']/config['source_filename']).resolve()
        if not path.is_relative_to(args.archive_dir):raise ValueError('Unsafe archive path')
        if not path.exists() and args.download:
            url='https://raw.githubusercontent.com/LiveCodeBench/submissions/'+config['source_commit']+'/'+quote(record['model']['name'],safe='')+'/'+quote(config['source_filename'],safe='')
            with urlopen(url,timeout=120) as response:data=response.read()
            if hashlib.sha256(data).hexdigest()!=config['source_file_sha256']:
                raise ValueError('Downloaded source file SHA-256 mismatch')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=config['source_file_sha256']:
            raise ValueError('Archived source file SHA-256 mismatch')
        if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=config['source_file_git_blob']:
            raise ValueError('Archived Git object hash mismatch')
        result=reference_score(json.loads(data),questions,start,end)
        if result['samples_per_task']!=config['samples_per_task'] or not math.isclose(round(result['score']*100,4),record['metric']['value'],abs_tol=1e-10):
            raise ValueError('Reference observation disagrees with official grades')
    print(f'Verified {len(records)} immutable official references on all {len(questions)} matching tasks')


if __name__=='__main__':main()
