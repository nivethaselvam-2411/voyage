import sys, time
sys.path.append('src')
from phase1_parallel_pipeline import process_single_file

t0 = time.time()
print('Starting Day 4...', flush=True)
res = process_single_file('ETM/ETM/Ticket-Data-2026-03-04.csv.bz2')
t1 = time.time()
print(f"Done Day 4 in {t1-t0:.2f}s: {res['qc']}", flush=True)

