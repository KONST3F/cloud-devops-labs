import subprocess, time, os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
env=dict(os.environ,COMPOSE_PROJECT_NAME='devops-star')
compose=['docker','compose','-f','compose.yaml','-f','compose.star.yaml']
def run(args, expected=(0,)):
 print('$ '+' '.join(args),flush=True)
 p=subprocess.run(args,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
 print(p.stdout.rstrip(),flush=True)
 if p.returncode not in expected: raise RuntimeError(f'exit {p.returncode}')
 return p.stdout.strip()
url=['curl.exe','--noproxy','*','-ksS','--max-time','5','--resolve','notes.local:443:127.0.0.1','https://notes.local/api/health']
run(compose+['ps'])
run(url)
id=run(compose+['ps','-q','db'])
before=int(run(['docker','inspect','--format','{{.RestartCount}}',id]))
run(['docker','exec','-u','postgres',id,'pg_ctl','-D','/var/lib/postgresql/data','stop','-m','immediate'], expected=(0,137))
for _ in range(60):
 time.sleep(1)
 state=subprocess.run(['docker','inspect','--format','{{.State.Health.Status}} {{.RestartCount}}',id],capture_output=True,text=True).stdout.strip().split()
 if len(state)==2 and state[0]=='healthy' and int(state[1])>before: break
else: raise RuntimeError('Database did not recover')
run(['docker','inspect','--format','{{.State.Status}} / {{.State.Health.Status}} / {{.State.StartedAt}} / restarts={{.RestartCount}}',id])
for _ in range(30):
 p=subprocess.run(url,cwd=root,env=env,capture_output=True,text=True)
 if p.returncode==0 and '"status": "ok"' in p.stdout: break
 time.sleep(1)
else: raise RuntimeError('Service did not recover')
run(url)
print('Database restarted and service responds again.')
