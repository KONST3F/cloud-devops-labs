import os, subprocess, time, uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1]; env=dict(os.environ,COMPOSE_PROJECT_NAME='devops-star')
def cmd(args,ok=(0,)):
 print('$ '+' '.join(args),flush=True)
 p=subprocess.run(args,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
 print(p.stdout.rstrip(),flush=True); print('[exit %d]'%p.returncode,flush=True)
 if p.returncode not in ok: raise RuntimeError('Unexpected exit')
 return p.stdout
backend='devops-star-backend-a-1'; driver='devops-star-backend-b-1'
def load():
 p=subprocess.Popen(['docker','exec','-i',driver,'python','-'],cwd=root,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 p.stdin.write((root/'tools/star_load_worker.py').read_bytes()); p.stdin.close(); time.sleep(4)
 cmd(['docker','stats','--no-stream','--format','{{.Name}} CPU={{.CPUPerc}} MEM={{.MemUsage}}',backend])
 result=p.stdout.read().decode('utf-8','replace'); code=p.wait(); print('$ docker exec -i '+driver+' python - < tools/star_load_worker.py\n'+result+'[exit '+str(code)+']',flush=True)
 if code: raise RuntimeError('Load generator failed')
try:
 print('Tight limits: 0.10 CPU, 64 MiB',flush=True)
 cmd(['docker','update','--cpus','0.10','--memory','64m','--memory-swap','64m',backend])
 cmd(['docker','exec',backend,'cat','/sys/fs/cgroup/cpu.stat'])
 load()
 cmd(['docker','exec',backend,'cat','/sys/fs/cgroup/cpu.stat'])
 name='devops-star-oom-'+uuid.uuid4().hex[:8]
 try:
  cmd(['docker','run','--name',name,'--network','none','--memory','64m','--memory-swap','64m',
       'devops-star-backend-a','python','-c','a=bytearray(120*1024*1024); print(len(a))'],ok=(137,))
  state=cmd(['docker','inspect','--format','OOMKilled={{.State.OOMKilled}} exit={{.State.ExitCode}}',name])
  if 'OOMKilled=true' not in state: raise RuntimeError('OOM was not observed')
 finally:
  cmd(['docker','rm','-f',name])

finally:
 print('Restoring stable limits: 0.75 CPU, 256 MiB',flush=True)
 cmd(['docker','update','--cpus','0.75','--memory','256m','--memory-swap','256m',backend])
load()
cmd(['docker','inspect','--format','status={{.State.Status}} health={{.State.Health.Status}}',backend])
