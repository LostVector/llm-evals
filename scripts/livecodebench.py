import argparse,ast,hashlib,json,sys,urllib.request,time,subprocess,uuid
try:
 from scripts.gpqa_diamond import private_path,request_completion
except ModuleNotFoundError:
 from gpqa_diamond import private_path,request_completion
from pathlib import Path
from types import SimpleNamespace

def scorer_infrastructure_error(value):
    """Do not turn upstream TestRunnerError metadata into a wrong answer."""
    if isinstance(value,str):
        try:value=json.loads(value)
        except ValueError:return False
    if isinstance(value,dict):
        return value.get('error_code')==-5 or any(scorer_infrastructure_error(v) for v in value.values() if isinstance(v,(dict,list)))
    if isinstance(value,list):return any(scorer_infrastructure_error(v) for v in value)
    return False

def main():
    parser=argparse.ArgumentParser(description='Pinned LiveCodeBench v6 window; generation plus isolated official grading.')
    parser.add_argument('--config',type=private_path,required=True)
    parser.add_argument('--dataset-dir',type=private_path,required=True)
    parser.add_argument('--upstream',type=private_path,required=True)
    parser.add_argument('--output',type=private_path,required=True)
    parser.add_argument('--limit',type=int,default=131)
    parser.add_argument('--start-index',type=int,default=0,help='Disjoint worker range; caller must avoid overlap')
    parser.add_argument('--image',default='llm-evals-lcb:local')
    args=parser.parse_args()
    if not 0<=args.start_index<args.limit<=131: raise ValueError('Require 0 <= start-index < limit <= 131')
    root=Path(__file__).resolve().parents[1]
    config=json.loads(args.config.read_text())
    protocol=json.loads((root/'protocols/livecodebench-v6-window.json').read_text())
    revision=subprocess.check_output(['git','-C',str(args.upstream),'rev-parse','HEAD'],text=True).strip()
    if revision!=protocol['harness_revision']:raise ValueError('Wrong upstream harness revision')
    if subprocess.check_output(['git','-C',str(args.upstream),'status','--porcelain'],text=True).strip():raise ValueError('Upstream checkout has modifications')
    out=args.output;out.mkdir(exist_ok=True,parents=True)
    source=args.upstream/'lcb_runner/prompts/code_generation.py'
    tree=ast.parse(source.read_text());nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ('PromptConstants','get_generic_question_template_answer')]
    ns={'CodeGenerationProblem':SimpleNamespace};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
    rows=[]
    for file in sorted(args.dataset_dir.glob('test*.jsonl')):
     with file.open() as stream:
      for line in stream:
       row=json.loads(line)
       if protocol['window_start_inclusive']<=row['contest_date']<protocol['window_end_exclusive']:rows.append(row)
    rows.sort(key=lambda r:(r['contest_date'],r['platform'],r['question_id']))
    settings=protocol['generation']
    ids=[r['platform']+'/'+r['question_id'] for r in rows]
    if ids!=protocol['task_ids']:raise ValueError('Dataset does not match frozen task set')
    if hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()!=protocol['selected_rows_sha256']:raise ValueError('Task content does not match pinned dataset')
    manifest={'protocol':protocol,'deployment':config['deployment'],'model':config['model'],'rows_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'scorer_image':subprocess.check_output(['docker','image','inspect',args.image,'--format','{{.Id}}'],text=True).strip()}
    manifest_path=out/'manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text())!=manifest:raise ValueError('Existing output has a different manifest')
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    for i,row in enumerate(rows[:args.limit]):
     if i<args.start_index:continue
     responsepath=out/f'{i:03}-response.json'
     if not responsepath.exists():
      reqbody={'stream':True,'stream_options':{'include_usage':True},'model':config['model'],'messages':[{'role':'system','content':ns['PromptConstants'].SYSTEM_MESSAGE_GENERIC},{'role':'user','content':ns['get_generic_question_template_answer'](SimpleNamespace(**row))}],**settings}
      headers={'Content-Type':'application/json'}
      if config.get('api_key'):headers['Authorization']='Bearer '+config['api_key']
      req=urllib.request.Request(config['base_url'].rstrip('/')+'/chat/completions',data=json.dumps(reqbody).encode(),headers=headers)
      start=time.monotonic()
      opener=urllib.request.build_opener(urllib.request.ProxyHandler({})) if config.get('bypass_proxy') else urllib.request.build_opener()
      response=request_completion(opener,req,out/'infrastructure-events.jsonl')
      responsepath.write_text(json.dumps({'seconds':time.monotonic()-start,'response':response},indent=2)+'\n')
      print('generated',i,flush=True)
     record=json.loads(responsepath.read_text());content=record['response']['choices'][0]['message'].get('content') or ''
     lines=content.split('\n');fences=[j for j,l in enumerate(lines) if '```' in l]
     code='\n'.join(lines[fences[-2]+1:fences[-1]]) if len(fences)>=2 else ''
     scorepath=out/f'{i:03}-score.json'
     if not scorepath.exists():
      payload={'row':row,'generations':[[code]]}
      container='llm-evals-lcb-'+uuid.uuid4().hex
      cmd=['docker','run','--name',container,'--rm','-i','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','2g','--cpus','1','--tmpfs','/tmp:rw,nosuid,nodev,size=128m',args.image]
      try:
       run=subprocess.run(cmd,input=json.dumps(payload),text=True,capture_output=True,timeout=900)
      finally:
       subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
      (out/f'{i:03}-grader.log').write_text(run.stderr)
      if run.returncode: raise RuntimeError('Scorer infrastructure error: '+str(run.returncode))
      result=json.loads(run.stdout)
      if scorer_infrastructure_error(result[2]):raise RuntimeError('Official scorer reported TestRunnerError; no task score recorded')
      scorepath.write_text(json.dumps({'index':i,'task':ids[i],'result':result},indent=2)+'\n')
      print('scored',i,result[0]['pass@1'],flush=True)

if __name__=='__main__':main()
