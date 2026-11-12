"""Compare rebuilds after the same one-line change in a separate build context."""
from pathlib import Path
import shutil
import subprocess
import time
import uuid

root = Path(__file__).resolve().parent.parent
evidence = root / 'evidence'
evidence.mkdir(exist_ok=True)
context = root.parent / ('devops-benchmark-' + uuid.uuid4().hex[:8])
context.mkdir()
for name in ('app.py', 'index.html', 'requirements.txt', 'Dockerfile', 'Dockerfile.bad', '.dockerignore'):
    shutil.copy2(root / name, context / name)


def build(label, dockerfile, phase):
    log = evidence / f'build-{label}-{phase}.txt'
    start = time.perf_counter()
    with log.open('w', encoding='utf-8') as output:
        run = subprocess.run(['docker', 'build', '--progress=plain', '-f', dockerfile,
                              '-t', f'devops-final-bench:{label}', '.'],
                             cwd=context, stdout=output, stderr=subprocess.STDOUT)
    elapsed = time.perf_counter() - start
    if run.returncode:
        raise RuntimeError(f'Build {label}/{phase} failed; see {log}')
    return elapsed


build('good', 'Dockerfile', 'warm')
build('bad', 'Dockerfile.bad', 'warm')
with (context / 'app.py').open('a', encoding='utf-8') as f:
    f.write('\n# Cache comparison ' + uuid.uuid4().hex + '\n')
good = build('good', 'Dockerfile', 'changed')
bad = build('bad', 'Dockerfile.bad', 'changed')
result = ('One-line code change; warm cache\n'
          f'Good Dockerfile: {good:.2f} s\nBad Dockerfile: {bad:.2f} s\n'
          'Detailed build output is in build-good-changed.txt and build-bad-changed.txt.\n')
(evidence / 'build-times.txt').write_text(result, encoding='utf-8')
print(result)
