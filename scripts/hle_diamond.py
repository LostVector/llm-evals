#!/usr/bin/env python3
"""Pinned HLE-Diamond runner for OpenAI-compatible endpoints. No tools or paid calls by default."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT/'protocols/hle-diamond.json').read_text())
UPSTREAM = ROOT/'.local/hle/upstream'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
    temporary.replace(path)


def prepare(path):
    if not path.exists():
        path.mkdir(parents=True)
        subprocess.run(['git','init',str(path)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git','-C',str(path),'remote','add','origin',PROTOCOL['evaluator_repository']],check=True)
    remote=subprocess.check_output(['git','-C',str(path),'remote','get-url','origin'],text=True).strip()
    if remote!=PROTOCOL['evaluator_repository']:raise ValueError('Evaluator directory has an unrelated Git remote')
    if subprocess.check_output(['git','-C',str(path),'status','--porcelain'],text=True).strip():raise ValueError('Evaluator directory has local changes; refusing checkout')
    subprocess.run(['git','-C',str(path),'fetch','--depth','1','origin',PROTOCOL['evaluator_revision']],check=True)
    subprocess.run(['git','-C',str(path),'checkout','--detach',PROTOCOL['evaluator_revision']],check=True)
    return prompts(path)


def prompts(path):
    revision=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    if revision!=PROTOCOL['evaluator_revision']:
        raise ValueError('Evaluator revision does not match protocol; run prepare')
    # Read constants as data; do not execute upstream modules or initialize their API clients.
    result={}
    for filename,name in [('run_model_predictions.py','SYSTEM_PROMPT'),('run_judge_results.py','JUDGE_PROMPT')]:
        source=path/'hle_eval'/filename
        expected=subprocess.check_output(['git','-C',str(path),'show',f'HEAD:hle_eval/{filename}'])
        if source.read_bytes()!=expected:
            raise ValueError('Pinned evaluator source has local modifications')
        tree=ast.parse(expected.decode())
        for statement in tree.body:
            if isinstance(statement,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in statement.targets):
                result[name]=ast.literal_eval(statement.value)
    if set(result)!={'SYSTEM_PROMPT','JUDGE_PROMPT'}:
        raise ValueError('Upstream prompt format changed')
    return result


def load_questions(mode, limit=None):
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise ValueError('Install requirements-hle.txt in a Python 3.11/3.12 virtualenv first') from exc
    dataset=load_dataset(PROTOCOL['dataset'], revision=PROTOCOL['dataset_revision'],split=PROTOCOL['split'])
    questions=[dict(row) for row in dataset]
    for q in questions:q['partition']=str(q.get('partition','')).strip().lower()
    validate_questions(questions)
    return select_questions(questions,mode,limit)


def validate_questions(questions):
    if len(questions)!=PROTOCOL['expected_tasks']:
        raise ValueError('Unexpected dataset size; do not substitute original HLE or a rolling set')
    if len({q['id'] for q in questions})!=len(questions):
        raise ValueError('Duplicate dataset task IDs')
    counts={p:sum(q.get('partition')==p for q in questions) for p in PROTOCOL['expected_partition_counts']}
    if counts!=PROTOCOL['expected_partition_counts']:
        raise ValueError('Unexpected dataset partition counts')
    if sum(bool(q.get('image')) for q in questions)!=PROTOCOL['expected_image_tasks']:
        raise ValueError('Unexpected image-task count')


def select_questions(questions,mode,limit=None):
    if mode=='text-only-subset':
        questions=[q for q in questions if not q.get('image')]
    if limit is not None:
        if limit<=0: raise ValueError('limit must be positive')
        questions=questions[:limit]
    if not questions:raise ValueError('Empty task selection')
    return questions


def messages(question, system, mode):
    content=[{'type':'text','text':question['question']}]
    if mode=='multimodal' and question.get('image'):
        if not isinstance(question['image'],str):
            raise ValueError('Expected upstream image URL/data-URL string')
        content.append({'type':'image_url','image_url':{'url':question['image']}})
    return [{'role':'system','content':system},{'role':'user','content':content}]


def validate_endpoint(base_url):
    parsed=urlparse(base_url)
    if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use a plain HTTP(S) endpoint URL; keep credentials in environment variables')
    return base_url.rstrip('/')+'/chat/completions'


def request_completion(base_url, key_env, payload):
    url=validate_endpoint(base_url)
    key=os.environ.get(key_env,'')
    headers={'Content-Type':'application/json'}
    if key:headers['Authorization']='Bearer '+key
    request=Request(url,data=json.dumps(payload).encode(),headers=headers,method='POST')
    with urlopen(request,timeout=600) as response:
        return json.load(response)


def run_prediction(questions, system, config, request_fn):
    """One attempt per task; failures remain present and are never silently retried."""
    result={}
    for q in questions:
        payload=dict(model=config['model'],messages=messages(q,system,config['input_mode']),temperature=config['temperature'],stream=False)
        payload[config['token_parameter']]=config['max_tokens']
        if config.get('reasoning_effort'):payload['reasoning_effort']=config['reasoning_effort']
        if config.get('seed') is not None:payload['seed']=config['seed']
        try:
            reply=request_fn(payload)
            choice=reply['choices'][0]
            text=choice['message']['content']
            if not isinstance(text,str) or not text.strip():raise ValueError('Empty model response')
            result[q['id']]=dict(status='answered',response=text,finish_reason=choice.get('finish_reason'),usage=reply.get('usage'))
        except Exception as exc:
            result[q['id']]=dict(status='generation_error',error_type=type(exc).__name__)
    return result


def judge_payload(question,prediction,prompt,model,effort):
    schema={'type':'object','properties':{'extracted_final_answer':{'type':'string'},'reasoning':{'type':'string'},'correct':{'type':'string','enum':['yes','no']},'confidence':{'type':'integer','minimum':0,'maximum':100},'strict':{'type':'boolean','enum':[True]}},'required':['extracted_final_answer','reasoning','correct','confidence','strict'],'additionalProperties':False}
    payload=dict(model=model,messages=[{'role':'user','content':prompt.format(question=question['question'],correct_answer=question['answer'],response=prediction['response'])}],max_completion_tokens=4096,response_format={'type':'json_schema','json_schema':{'name':'ExtractedAnswer','strict':True,'schema':schema}})
    if effort:payload['reasoning_effort']=effort
    return payload


def validate_judgment(value):
    if not isinstance(value,dict) or value.get('correct') not in ('yes','no') or value.get('strict') is not True:
        raise ValueError('Invalid judge output')
    if type(value.get('confidence')) is not int or not 0<=value['confidence']<=100:
        raise ValueError('Invalid judge confidence')
    if any(not isinstance(value.get(k),str) for k in ('extracted_final_answer','reasoning')):
        raise ValueError('Invalid judge extraction')
    return value


def summarize(manifest,predictions,judgments):
    task_ids=manifest['task_ids']
    if len(set(task_ids))!=len(task_ids) or not task_ids:raise ValueError('Invalid manifest IDs')
    if manifest['config']['limit'] is None:
        expected=PROTOCOL['expected_tasks']-(PROTOCOL['expected_image_tasks'] if manifest['config']['input_mode']=='text-only-subset' else 0)
        if len(task_ids)!=expected:raise ValueError('Full-track task count differs from protocol; do not label a partial run full')
    if set(predictions)!=set(task_ids):raise ValueError('Prediction task IDs differ from frozen manifest')
    if any(predictions[i].get('status') not in ('answered','generation_error') for i in task_ids):raise ValueError('Unknown generation status')
    answered=[i for i in task_ids if predictions[i]['status']=='answered']
    if any(i not in judgments or judgments[i].get('status')!='graded' for i in answered):
        raise ValueError('Judge failures/missing grades remain; rerun judge before reporting')
    def stats(ids):
        correct=sum(predictions[i]['status']=='answered' and validate_judgment(judgments[i]['judgment'])['correct']=='yes' for i in ids)
        n=len(ids);p=correct/n if n else 0
        # Wilson interval remains sensible even for small pilots and all-fail results.
        z=1.96;den=1+z*z/n if n else 1
        mid=(p+z*z/(2*n))/den if n else 0
        half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den if n else 0
        return dict(correct=correct,n=n,accuracy_percent=100*p,wilson_95_percent=[100*max(0,mid-half),100*min(1,mid+half)])
    return dict(metric='pass@1_accuracy',input_mode=manifest['config']['input_mode'],task_set='development-subset' if manifest['config']['limit'] else ('text-only-subset' if manifest['config']['input_mode']=='text-only-subset' else 'full-1000'),overall=stats(task_ids),partitions={p:stats([i for i in task_ids if manifest['partitions'][i]==p]) for p in PROTOCOL['expected_partition_counts'] if any(manifest['partitions'][i]==p for i in task_ids)},generation_errors=len(task_ids)-len(answered),truncated_responses=sum(predictions[i].get('finish_reason')=='length' for i in answered))


def private_run_path(path):
    path=path.resolve()
    if not path.is_relative_to((ROOT/'.local').resolve()):
        raise ValueError('Run artifacts must stay under ignored .local/; dataset-derived responses must not enter the public repository')
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',type=Path,default=UPSTREAM)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('plan');sub.add_parser('prepare')
    predict=sub.add_parser('predict')
    predict.add_argument('--model',required=True);predict.add_argument('--base-url',required=True)
    predict.add_argument('--output',type=Path,required=True)
    predict.add_argument('--input-mode',choices=['multimodal','text-input-full','text-only-subset'],default='text-input-full')
    predict.add_argument('--max-tokens',type=int,default=16384);predict.add_argument('--temperature',type=float,default=0)
    predict.add_argument('--seed',type=int);predict.add_argument('--reasoning-effort')
    predict.add_argument('--token-parameter',choices=['max_tokens','max_completion_tokens'],default='max_tokens')
    predict.add_argument('--limit',type=int)
    predict.add_argument('--api-key-env',default='HLE_MODEL_API_KEY')
    judge=sub.add_parser('judge');judge.add_argument('--run',type=Path,required=True)
    judge.add_argument('--model',required=True);judge.add_argument('--base-url',required=True)
    judge.add_argument('--reasoning-effort');judge.add_argument('--api-key-env',default='HLE_JUDGE_API_KEY')
    report=sub.add_parser('report');report.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='plan':print(json.dumps(PROTOCOL,indent=2));return
    if args.command=='prepare':prepare(args.upstream);print('Pinned evaluator ready. No dataset or inference calls performed.');return
    if hasattr(args,'run'):args.run=private_run_path(args.run)
    if hasattr(args,'output'):args.output=private_run_path(args.output)
    if hasattr(args,'base_url'):validate_endpoint(args.base_url)
    if args.command=='report':
        manifest=json.loads((args.run/'manifest.json').read_text());predictions=json.loads((args.run/'predictions.json').read_text());judgments=json.loads((args.run/'judgments.json').read_text())
        print(json.dumps(summarize(manifest,predictions,judgments),indent=2));return
    prompt=prompts(args.upstream)
    if args.command=='predict':
        if args.output.exists():raise ValueError('Output directory already exists; use a new run directory to prevent accidental retakes or overwrites')
        if args.limit is not None and args.limit<=0:raise ValueError('limit must be positive')
        if args.max_tokens<=0 or not math.isfinite(args.temperature) or args.temperature<0:raise ValueError('Invalid decoding budget')
        config={k:getattr(args,k) for k in ('model','input_mode','max_tokens','temperature','seed','reasoning_effort','token_parameter','limit')}
        questions=load_questions(args.input_mode,args.limit)
        manifest=dict(protocol=PROTOCOL,config=config,task_ids=[q['id'] for q in questions],partitions={q['id']:q['partition'] for q in questions},prompts_sha256=digest(prompt),created_at=datetime.now(timezone.utc).isoformat())
        manifest['software_versions']={'python':sys.version.split()[0],'datasets':importlib.metadata.version('datasets')}
        manifest['run_fingerprint']=digest(manifest)
        save(args.output/'manifest.json',manifest)
        # Persist after every task so an interrupted run cannot lose successful answers.
        result={}
        for i,q in enumerate(questions,1):
            result.update(run_prediction([q],prompt['SYSTEM_PROMPT'],config,lambda body:request_completion(args.base_url,args.api_key_env,body)))
            save(args.output/'predictions.json',result)
            print(f'{i}/{len(questions)} tasks attempted',flush=True)
        return
    manifest=json.loads((args.run/'manifest.json').read_text())
    questions=load_questions(manifest['config']['input_mode'],manifest['config']['limit'])
    if [q['id'] for q in questions]!=manifest['task_ids']:raise ValueError('Task manifest no longer matches dataset')
    if digest(prompt)!=manifest['prompts_sha256']:raise ValueError('Prompt fingerprints differ from run')
    predictions=json.loads((args.run/'predictions.json').read_text())
    judge_config=dict(model=args.model,reasoning_effort=args.reasoning_effort,prompt_sha256=digest(prompt['JUDGE_PROMPT']))
    config_path=args.run/'judge-config.json'
    if config_path.exists() and json.loads(config_path.read_text())!=judge_config:raise ValueError('Judge recipe changed; use a separate grading run')
    save(config_path,judge_config)
    output=args.run/'judgments.json';judgments=json.loads(output.read_text()) if output.exists() else {}
    for q in questions:
        prediction=predictions.get(q['id'])
        if prediction is None:raise ValueError('Incomplete prediction file; do not silently change denominator')
        if prediction['status']!='answered' or judgments.get(q['id'],{}).get('status')=='graded':continue
        try:
            reply=request_completion(args.base_url,args.api_key_env,judge_payload(q,prediction,prompt['JUDGE_PROMPT'],args.model,args.reasoning_effort))
            value=validate_judgment(json.loads(reply['choices'][0]['message']['content']))
            judgments[q['id']]=dict(status='graded',judgment=value)
        except Exception as exc:judgments[q['id']]=dict(status='judge_error',error_type=type(exc).__name__)
        save(output,judgments)
    if not output.exists():save(output,judgments)
    print(json.dumps(summarize(manifest,predictions,judgments),indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError,KeyError) as exc:
        print(f'HLE run stopped: {exc}',file=sys.stderr);sys.exit(1)
