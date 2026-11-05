import time, bz2, csv, os
import pandas as pd

t0 = time.time()
fp = 'ETM/ETM/Ticket-Data-2026-03-04.csv.bz2'
records = []
qc_zero = 0
qc_large = 0
qc_neg_amt = 0

with bz2.open(fp, 'rt', encoding='utf-8', errors='replace') as f:
    r = csv.reader(f)
    header = next(r)
    idx = {name: i for i, name in enumerate(header)}
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
    
    for row in r:
        try:
            pax_s = row[i_pax].strip()
            pax = int(pax_s) if pax_s else 0
            if pax == 0:
                qc_zero += 1
                continue
            if pax < 1 or pax > 200:
                qc_large += 1
                continue
            amt_s = row[i_amt].strip()
            amt = float(amt_s) if amt_s and amt_s != 'NaN' else 0.0
            if amt < 0:
                qc_neg_amt += 1
                continue
            
            time_str = row[i_time].strip()
            hour = int(time_str[:2]) if len(time_str) >= 2 else 0
            
            sched = row[i_sched].strip()
            if '-' in sched:
                parts = sched.split('-')
                route = parts[1].upper() if len(parts) >= 2 else sched.upper()
            else:
                route = sched.upper()
                
            records.append((
                hour,
                row[i_depot].strip(),
                row[i_fleet].strip(),
                row[i_wb].strip(),
                route,
                row[i_src].strip().upper(),
                row[i_dst].strip().upper(),
                pax,
                amt,
                row[i_ptype].strip().upper() or 'UNKNOWN',
                row[i_stype].strip() or 'UNKNOWN',
                row[i_ttype].strip() or 'UNKNOWN'
            ))
        except Exception:
            continue

t1 = time.time()
print(f"CSV read & filter: {t1-t0:.2f}s ({len(records):,} records)")

cols = ['hour', 'depot', 'fleet_no', 'waybill_no', 'route_id', 'source', 'destination', 'pax', 'amt', 'payment_type', 'service_type', 'ticket_type']
df = pd.DataFrame(records, columns=cols)
del records # free memory

for col in ['depot', 'fleet_no', 'waybill_no', 'route_id', 'source', 'destination', 'payment_type', 'service_type', 'ticket_type']:
    df[col] = df[col].astype('category')
df['hour'] = df['hour'].astype('int8')
df['pax'] = df['pax'].astype('int16')
df['amt'] = df['amt'].astype('float32')

# Instant vectorised aggregations
hourly_pax = df.groupby('hour')['pax'].sum().to_dict()
hourly_tix = df.groupby('hour')['pax'].count().to_dict()
hourly_rev = df.groupby('hour')['amt'].sum().to_dict()
route_pax = df.groupby('route_id')['pax'].sum().to_dict()
depot_pax = df.groupby('depot')['pax'].sum().to_dict()
src_pax = df.groupby('source')['pax'].sum().to_dict()
dst_pax = df.groupby('destination')['pax'].sum().to_dict()
payment_counts = df['payment_type'].value_counts().to_dict()
ttype_counts = df['ticket_type'].value_counts().to_dict()
stype_counts = df['service_type'].value_counts().to_dict()

out_p = 'data/clean/day_2026-03-04.parquet'
df.to_parquet(out_p, compression='snappy')
t2 = time.time()
print(f"Total time for Day 4 (read + groupbys + parquet write): {t2-t0:.2f}s! Size: {os.path.getsize(out_p)/1e6:.2f} MB")

