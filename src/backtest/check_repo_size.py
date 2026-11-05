import subprocess
from pathlib import Path

res = subprocess.run(['git', 'status', '-u', '--porcelain'], capture_output=True, text=True)
tracked_size = 0
file_count = 0

for line in res.stdout.splitlines():
    if line.startswith('?? '):
        fname = line[3:].strip('"')
        p = Path(fname)
        if p.is_file():
            tracked_size += p.stat().st_size
            file_count += 1
        elif p.is_dir():
            for sub in p.rglob('*'):
                if sub.is_file():
                    tracked_size += sub.stat().st_size
                    file_count += 1

print(f"Total Git-tracked repository size: {tracked_size / (1024*1024):.2f} MB across {file_count} files.")

