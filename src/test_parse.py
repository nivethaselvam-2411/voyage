import time, bz2, csv, re, os
import pandas as pd
import numpy as np

t0 = time.time()
fp = 'ETM/ETM/Ticket-Data-2026-03-01.csv.bz2'
records = []
_route_re = re.compile(r'[OEo]-([^-]+)-')

with bz2.open(fp, 'rt', encoding='utf-8', errors='replace') as f:
    r = csv.reader(f)
    header = next(r)
    idx = {name: i for i, name in enumerate(header)}
    i_date = idx['date']
    i_time = idx['time']
    i_pax = idx['passenger_count']
    i_amt = idx['passenger_amount']
    i_depot = idx['depot']
    i_fleet = idx['fleet_no']
    i_wb = idx['waybill_no']
    i_sched = idx['schedule_no']
    i_stype = idx['route_service_type']
    i_ttype = idx['ticket_type']
    i_src = idx['source']
    i_dst = idx['destination']
    i_ptype = idx['payment_type']
    i_km = idx['KM']
    i_trip = idx['trip_no']
    
    for row in r:
        try:
            pax = int(row[i_pax])
            amt = float(row[i_amt]) if row[i_amt] else 0.0
            if pax < 1 or pax > 200 or amt < 0:
                continue
            time_str = row[i_time]
            hour = int(time_str[:2]) if len(time_str) >= 2 else 0
            sched = row[i_sched]
            m = _route_re.search(sched)
            route = m.group(1) if m else (sched.split('-')[1] if '-' in sched else 'UNK')
            
            records.append((
                row[i_date],
                hour,
                row[i_depot],
                row[i_fleet],
                row[i_wb],
                route,
                row[i_src].strip().upper(),
                row[i_dst].strip().upper(),
                pax,
                amt,
                row[i_ptype],
                row[i_stype]
            ))
        except Exception:
            continue

df = pd.DataFrame(records, columns=['date', 'hour', 'depot', 'fleet_no', 'waybill_no', 'route_id', 'source', 'destination', 'pax', 'amt', 'payment_type', 'service_type'])
for col in ['depot', 'fleet_no', 'waybill_no', 'route_id', 'source', 'destination', 'payment_type', 'service_type']:
    df[col] = df[col].astype('category')
df['hour'] = df['hour'].astype('int8')
df['pax'] = df['pax'].astype('int16')
df['amt'] = df['amt'].astype('float32')

print(f"Parsed {len(df)} rows in {time.time()-t0:.2f}s. Memory: {df.memory_usage(deep=True).sum()/1e6:.1f} MB")
out_p = 'data/clean/day_2026-03-01.parquet'
df.to_parquet(out_p, compression='snappy')
print(f"Parquet saved in {time.time()-t0:.2f}s. Size: {os.path.getsize(out_p)/1e6:.1f} MB")
