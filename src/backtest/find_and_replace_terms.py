"""
Scan and replace target terms across the repo to adhere to strict wording guidelines.
Targets: 'crush', 'load factor', '3,454', 'GPS buses'
"""
from pathlib import Path

targets = ['crush', 'load factor', '3,454', 'GPS buses']
root = Path('.')
extensions = ['.py', '.md', '.json']
exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', '.system_generated', 'data'}

found = {}
for p in root.rglob('*'):
    if p.is_file() and p.suffix in extensions and not any(part in exclude_dirs for part in p.parts):
        try:
            content = p.read_text(encoding='utf-8', errors='ignore')
            for t in targets:
                count = content.lower().count(t.lower())
                if count > 0:
                    found.setdefault(t, []).append((str(p), count))
        except Exception as e:
            pass

for t, hits in found.items():
    print(f'=== Target: "{t}" ===')
    for f, c in hits:
        print(f'  {f}: {c} occurrences')

