"""Container-only adapter around the unmodified upstream code-generation grader."""
import contextlib,json,sys,pickle,zlib,base64
from lcb_runner.evaluation.compute_code_generation_metrics import codegen_metrics
payload=json.load(sys.stdin)
if 'row' in payload:
 row=payload.pop('row')
 try: private=json.loads(row['private_test_cases'])
 except (ValueError,TypeError): private=json.loads(pickle.loads(zlib.decompress(base64.b64decode(row['private_test_cases']))))
 tests=json.loads(row['public_test_cases'])+private
 sample={'input_output':json.dumps({'inputs':[t['input'] for t in tests],'outputs':[t['output'] for t in tests],'fn_name':json.loads(row['metadata']).get('func_name')})}
 payload['samples']=[sample]
assert len(payload['samples']) == len(payload['generations'])
assert all(len(g)==1 for g in payload['generations'])
with contextlib.redirect_stdout(sys.stderr):
 result=codegen_metrics(payload['samples'],payload['generations'],k_list=[1],num_process_evaluate=1,timeout=6)
print(json.dumps(result,default=lambda x:x.item() if hasattr(x,'item') else str(x)))
