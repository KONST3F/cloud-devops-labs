"""Run individual local checks and save their unmodified command output."""
import json
import os
from pathlib import Path
import subprocess
import time
import sys

root = Path(__file__).resolve().parent.parent
outdir = root / 'evidence' / 'checks'
outdir.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env['COMPOSE_PROJECT_NAME'] = 'devops-final'
compose = ['docker', 'compose']
base = ['curl.exe', '--noproxy', '*', '--silent', '--show-error', '--insecure',
        '--max-time', '10', '--resolve', 'notes.local:443:127.0.0.1']
http = ['curl.exe', '--noproxy', '*', '--silent', '--show-error', '--max-time', '10',
        '--resolve', 'notes.local:80:127.0.0.1']


class Capture:
    def __init__(self, name):
        self.path = outdir / name
        self.lines = []

    def run(self, args, expected=(0,)):
        p = subprocess.run(args, cwd=root, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        self.lines.append('$ ' + subprocess.list2cmdline(args) + '\n' + p.stdout.rstrip()
                          + '\n[exit ' + str(p.returncode) + ']\n')
        print(self.lines[-1], flush=True)
        self.path.write_text('\n'.join(self.lines), encoding='utf-8')
        if p.returncode not in expected:
            raise RuntimeError(f'{self.path}: command exited {p.returncode}')
        return p.stdout


def check_config():
    c = Capture('01-nginx-config.txt')
    assert 'successful' in c.run(compose + ['exec', '-T', 'web', 'nginx', '-t'])

def check_https():
    c = Capture('02-https.txt')
    assert '301' in c.run(http + ['-I', 'http://notes.local/'])
    assert '200' in c.run(base + ['-I', 'https://notes.local/'])

def check_balance():
    c = Capture('03-balance-failover.txt')
    # Allow nginx's fail_timeout to expire if the check was just run.
    time.sleep(6)
    seen = ''
    for _ in range(4):
        seen += c.run(base + ['-D', '-', '-o', 'NUL', 'https://notes.local/api/health'])
        time.sleep(0.3)
    assert 'backend-a' in seen and 'backend-b' in seen
    try:
        c.run(compose + ['stop', 'backend-a'])
        response = c.run(base + ['-D', '-', '-o', 'NUL', 'https://notes.local/api/notes'])
        assert '200' in response and 'backend-b' in response
    finally:
        c.run(compose + ['start', 'backend-a'])

def check_admin():
    c = Capture('04-admin-docs-404.txt')
    for path in ('/admin', '/admin/'):
        assert '401' in c.run(base + ['-I', 'https://notes.local' + path])
        assert '200' in c.run(base + ['-K', 'auth/curl.conf', '-I', 'https://notes.local' + path])
    assert '200' in c.run(base + ['-I', 'https://notes.local/docs/'])
    assert '404' in c.run(base + ['-I', 'https://notes.local/nonexistent-page'])
    body = c.run(base + ['https://notes.local/nonexistent-page'])
    assert body == (root / '404.html').read_text(encoding='utf-8')

def check_vhosts():
    c = Capture('05-vhosts.txt')
    assert '200' in c.run(base + ['-I', 'https://notes.local/'])
    second = ['curl.exe', '--noproxy', '*', '--silent', '--show-error', '--insecure', '--max-time', '10',
              '--resolve', 'second.local:443:127.0.0.1', 'https://second.local/']
    assert 'Второй сайт' in c.run(second)
    unknown = ['curl.exe', '--noproxy', '*', '--silent', '--show-error', '--insecure', '--max-time', '10',
               '--resolve', 'unknown.local:443:127.0.0.1', 'https://unknown.local/']
    c.run(unknown, expected=(52, 56))

def check_limit():
    c = Capture('06-rate-limit.txt')
    codes = ''
    for _ in range(20):
        codes += c.run(base + ['-o', 'NUL', '-w', '%{http_code}', 'https://notes.local/api/health'])
    assert '429' in codes

def check_containers():
    c = Capture('07-docker-containers.txt')
    c.run(compose + ['ps'])
    assert c.run(compose + ['exec', '-T', 'backend-a', 'whoami']).strip() == 'app'
    c.run(['docker', 'image', 'inspect', 'devops-final-backend-a:latest', 'devops-final:bad',
           '--format', '{{.RepoTags}} {{.Size}} bytes'])

def check_network():
    c = Capture('08-network.txt')
    c.run(compose + ['exec', '-T', 'backend-a', 'python', '-c',
                     "import socket; socket.create_connection(('db',5432),3); print('backend -> db: connected')"])
    cid = c.run(compose + ['ps', '-q', 'db']).strip()
    ip = c.run(['docker', 'inspect', '--format', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', cid]).strip()
    c.run(compose + ['exec', '-T', 'web', 'nc', '-vz', '-w', '3', ip, '5432'], expected=(1,))

def check_volume():
    c = Capture('09-volume.txt')
    created = json.loads(c.run(base + ['-H', 'Content-Type: application/json', '--data',
                                       '{"body":"Report volume check"}', 'https://notes.local/api/notes']))
    old = c.run(compose + ['ps', '-q', 'db']).strip()
    c.run(compose + ['stop', 'db'])
    c.run(compose + ['rm', '-f', 'db'])
    c.run(compose + ['up', '-d', '--no-deps', 'db'])
    new = c.run(compose + ['ps', '-q', 'db']).strip()
    assert old != new
    for _ in range(30):
        ready = subprocess.run(compose + ['exec', '-T', 'db', 'pg_isready', '-U', 'labuser', '-d', 'notes'],
                               cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ready.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('PostgreSQL did not start')
    notes = json.loads(c.run(base + ['https://notes.local/api/notes']))
    assert any(row['id'] == created['id'] and row['body'] == 'Report volume check' for row in notes['notes'])

checks = {'config': check_config, 'https': check_https, 'balance': check_balance, 'admin': check_admin, 'vhosts': check_vhosts, 'limit': check_limit, 'containers': check_containers, 'network': check_network, 'volume': check_volume}
selected = sys.argv[1:] or list(checks)
for name in selected:
    checks[name]()
print('Selected checks passed')
