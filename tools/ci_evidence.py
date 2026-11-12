import json, subprocess, sys
runs={'test':43199472586,'security':43199535996,'good':43200383287,'bad':43199953291}
name=sys.argv[1]
if name=='local':
 for args in (['docker','ps','--filter','name=devops-ci-local','--format','{{.Names}} {{.Status}} {{.Ports}}'], ['curl.exe','--noproxy','*','--fail','--silent','--show-error','http://127.0.0.1:18083/api/health']):
  print('$ '+' '.join(args),flush=True)
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
  print(p.stdout.strip(),flush=True)
  if p.returncode: raise RuntimeError('Command failed')
 sys.exit(0)
run=runs[name]; repo='KONST3F/cloud-devops-labs'
def gh(args):
 p=subprocess.run(['gh']+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
 if p.returncode: raise RuntimeError(p.stderr)
 return p.stdout
api='repos/'+repo+'/actions/runs/'+str(run)
print('$ gh api '+api,flush=True)
r=json.loads(gh(['api',api])); print('url:',r['html_url']); print('status:',r['status'],'conclusion:',r['conclusion'])
if r['status']!='completed': raise RuntimeError('Run is not complete yet')
print('$ gh api '+api+'/jobs',flush=True)
jobs=json.loads(gh(['api',api+'/jobs']))['jobs']
for job in jobs:
 print(job['name']+': '+str(job['conclusion']))
 for step in job.get('steps',[]):
  if step['conclusion'] in ('failure',) or step['name'] in ('Security gate','Publish image','Deploy on temporary GitHub runner and check'):
   print('  '+step['name']+': '+str(step['conclusion']))
print('$ gh run view '+str(run)+' --log (relevant lines)',flush=True)
logs=gh(['run','view',str(run),'--repo',repo,'--log'])
for line in logs.splitlines():
 if (name=='test' and ('FAIL: test_demo_failure' in line or 'AssertionError:' in line)) or (name in ('security','good') and (' HIGH: ' in line or ' CRITICAL: ' in line or 'Total: 9 (CRITICAL:' in line or '{"status": "ok"' in line)):
  print(line,flush=True)
