"""Verify the compose lab with its own containers and named volume."""
import json
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
evidence = root / 'evidence'
evidence.mkdir(exist_ok=True)
lines = []


def command(args, expect=0):
    shown = subprocess.list2cmdline(args)
    result = subprocess.run(args, cwd=root, text=True, encoding='utf-8', errors='replace',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines.append('$ ' + shown + '\n' + result.stdout.rstrip() + f'\n(exit {result.returncode})\n')
    if result.returncode != expect:
        raise RuntimeError(f'Unexpected exit code for {shown}')
    return result.stdout.strip()


command(['docker', 'compose', 'ps', '--format', '{{.Service}} {{.State}} {{.Health}}'])
command(['docker', 'image', 'inspect', 'devops-final-backend-a:latest', 'devops-final:bad',
         '--format', '{{.RepoTags}} {{.Size}} bytes'])
assert command(['docker', 'compose', 'exec', '-T', 'backend-a', 'whoami']) == 'app'
command(['docker', 'compose', 'exec', '-T', 'backend-a', 'python', '-c',
         "import socket; socket.create_connection(('db',5432),3); print('backend -> db: connected')"])
container = command(['docker', 'compose', 'ps', '-q', 'db']).strip()
ip = command(['docker', 'inspect', '--format', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', container])
command(['docker', 'compose', 'exec', '-T', 'web', 'nc', '-vz', '-w', '3', ip, '5432'], expect=1)
lines.append('Frontend cannot connect to the database address.\n')

base = ['curl.exe', '--noproxy', '*', '-ksS', '--resolve', 'notes.local:443:127.0.0.1']
created = command(base + ['-H', 'Content-Type: application/json', '--data',
                          '{"body":"Volume persistence check"}', 'https://notes.local/api/notes'])
created_id = json.loads(created)['id']
old_id = command(['docker', 'compose', 'ps', '-q', 'db'])
command(['docker', 'compose', 'stop', 'db'])
command(['docker', 'compose', 'rm', '-f', 'db'])
command(['docker', 'compose', 'up', '-d', '--no-deps', 'db'])
new_id = command(['docker', 'compose', 'ps', '-q', 'db'])
if old_id == new_id:
    raise RuntimeError('Database container was not recreated')
for _ in range(30):
    result = subprocess.run(['docker', 'compose', 'exec', '-T', 'db', 'pg_isready', '-U', 'labuser', '-d', 'notes'],
                            cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        break
    time.sleep(1)
else:
    raise RuntimeError('Database did not become ready')
body = command(base + ['https://notes.local/api/notes'])
if not any(n['id'] == created_id and n['body'] == 'Volume persistence check' for n in json.loads(body)['notes']):
    raise RuntimeError('New record did not survive container recreation')
lines.append('The inserted record survived removal and recreation of the database container.\n')
text = '\n'.join(lines)
(evidence / 'lab2-check.txt').write_text(text, encoding='utf-8')
print(text)
