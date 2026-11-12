import json, sys
from collections import Counter
report=json.load(open(sys.argv[1],encoding='utf-8'))
counts=Counter(v.get('Severity') for result in report.get('Results',[]) for v in result.get('Vulnerabilities',[]))
print('HIGH:',counts['HIGH'])
print('CRITICAL:',counts['CRITICAL'])
