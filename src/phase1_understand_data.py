"""
PHASE 1: UNDERSTAND THE DATA — Optimised (selective columns + compact dtypes)
Reads only the essential columns; uses smallest possible dtypes.
"""

import os, sys, re, gc, warnings
from pathlib import Path
from datetime import datetime
from collections import defaultdict

_mpl_dir = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')), 'mpl_cfg')
os.makedirs(_mpl_dir, exist_ok=True)
os.environ['MPLCONFIGDIR'] = _mpl_dir

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import seaborn as sns
warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path("c:/Users/nivet/Downloads/Theme 4/Theme 4")
ETM_DIR    = ROOT / "ETM" / "ETM"
OUT_CHARTS = ROOT / "outputs" / "charts"
OUT_TABLES = ROOT / "outputs" / "tables"
DATA_CLEAN = ROOT / "data" / "clean"
FINDINGS   = ROOT / "outputs" / "findings.md"
for d in [OUT_CHARTS, OUT_TABLES, DATA_CLEAN]:
    d.mkdir(parents=True, exist_ok=True)

def log(msg): print(msg, flush=True)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: FILE INVENTORY
# ══════════════════════════════════════════════════════════════════════════════
log("=" * 70)
log("PHASE 1 — STEP 1: FILE INVENTORY")
log("=" * 70)
etm_files = sorted(ETM_DIR.glob("Ticket-Data-*.csv.bz2"))
log(f"\nETM ticket files found: {len(etm_files)}")
for f in etm_files:
    log(f"  {f.name}  ({f.stat().st_size/1e6:.1f} MB compressed)")

stops_xlsx = ROOT / "Tambaram, Avadi, GCC Bus Stops List  1.xlsx"
shp_files  = list(ROOT.rglob("*.shp"))
log(f"\nBus Stops file: {stops_xlsx.name}")
log(f"\nShapefiles found: {len(shp_files)}")
for s in shp_files:
    log(f"  {s.relative_to(ROOT)}")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: SCHEMA — peek first file (nrows=200 → tiny memory)
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 1 — STEP 2: SCHEMA (first 200 rows)")
log("=" * 70)

import bz2
with bz2.open(etm_files[0], 'rt', encoding='utf-8', errors='replace') as f:
    df_peek = pd.read_csv(f, nrows=200)

COLUMNS = list(df_peek.columns)
log(f"\nColumns ({len(COLUMNS)}): {COLUMNS}")
log(f"\nDtypes:\n{df_peek.dtypes.to_string()}")
log(f"\nSample rows:\n{df_peek.head(3).to_string()}")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: STREAMING with pandas chunked — ONLY essential columns, compact dtypes
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 1 — STEP 3: STREAMING AGGREGATION")
log("=" * 70)

# Read ONLY these columns — saves ~65% memory vs all 36 cols
USECOLS   = ['date', 'time', 'passenger_count', 'passenger_amount',
             'depot', 'schedule_no', 'source', 'destination',
             'payment_type', 'ticket_type', 'route_service_type', 'KM']

# Compact dtypes for the numeric columns (read as object first, convert after)
DTYPE_MAP = {
    'passenger_count':  'int16',   # max 200
    'passenger_amount': 'float32',
    'KM':               'float32',
}

CHUNKSIZE = 500_000   # larger chunks are faster if memory allows; adjust if OOM

_route_re = re.compile(r'[OEo]-([^-]+)-')
DOW_NAMES = {0:'Mon',1:'Tue',2:'Wed',3:'Thu',4:'Fri',5:'Sat',6:'Sun'}

agg_daily     = defaultdict(lambda: {'tickets':0,'passengers':0,'revenue':0.0})
agg_hourly    = defaultdict(lambda: {'tickets':0,'passengers':0})
agg_dow_hour  = defaultdict(float)
agg_depot     = defaultdict(float)
agg_route     = defaultdict(float)
agg_src       = defaultdict(float)
agg_dst       = defaultdict(float)
agg_payment   = defaultdict(int)
agg_ttype     = defaultdict(int)
agg_stype     = defaultdict(int)

total_raw   = 0
total_clean = 0
qc          = defaultdict(int)
km_sample   = []

def extract_route(sched):
    if pd.isna(sched): return 'UNK'
    s = str(sched)
    m = _route_re.search(s)
    if m: return m.group(1)
    parts = s.split('-')
    return parts[1] if len(parts) >= 2 else 'UNK'

for fp in etm_files:
    fname = fp.name
    day_raw = 0; day_clean = 0
    log(f"\n  Processing: {fname} ...")

    with bz2.open(fp, 'rt', encoding='utf-8', errors='replace') as f:
        reader = pd.read_csv(
            f,
            usecols=USECOLS,
            dtype={'passenger_count': 'Int16',   # nullable int to avoid cast failures
                   'passenger_amount': 'float32',
                   'KM': 'float32'},
            low_memory=True,
            chunksize=CHUNKSIZE,
            on_bad_lines='skip',
        )
        for chunk in reader:
            n = len(chunk)
            total_raw += n
            day_raw   += n

            # --- Date / time parsing (vectorised) ---
            chunk['date_parsed'] = pd.to_datetime(
                chunk['date'], dayfirst=True, errors='coerce')
            bad_date = chunk['date_parsed'].isna().sum()
            qc['date_fail'] += bad_date

            chunk['hour'] = pd.to_numeric(
                chunk['time'].str.split(':').str[0], errors='coerce')
            chunk['hour'] = chunk['hour'].clip(0, 23)

            chunk['dow'] = chunk['date_parsed'].dt.dayofweek
            chunk['date_str'] = chunk['date_parsed'].dt.strftime('%Y-%m-%d')

            # --- QC on numeric ---
            pax = chunk['passenger_count'].fillna(0)
            amt = chunk['passenger_amount'].fillna(0.0)
            qc['neg_pax']   += int((pax < 0).sum())
            qc['zero_pax']  += int((pax == 0).sum())
            qc['large_pax'] += int((pax > 200).sum())
            qc['neg_amt']   += int((amt < 0).sum())

            # --- Filter ---
            mask = (
                chunk['date_parsed'].notna() &
                pax.between(1, 200) &
                (amt >= 0)
            )
            chunk = chunk[mask].copy()
            nc = len(chunk)
            total_clean += nc
            day_clean   += nc

            # Recalc after filter
            pax = chunk['passenger_count'].fillna(0).astype(float)
            amt = chunk['passenger_amount'].fillna(0.0).astype(float)

            # KM sample
            km_ok = chunk['KM'].dropna()
            if len(km_sample) < 50_000:
                km_sample.extend(km_ok.sample(min(1000, len(km_ok))).tolist()
                                 if len(km_ok) > 1000 else km_ok.tolist())

            # Route
            chunk['route_id'] = chunk['schedule_no'].apply(extract_route)

            # --- Accumulators ---
            # Daily
            for ds, grp in chunk.groupby('date_str', sort=False):
                agg_daily[ds]['tickets']    += len(grp)
                agg_daily[ds]['passengers'] += pax.loc[grp.index].sum()
                agg_daily[ds]['revenue']    += amt.loc[grp.index].sum()

            # Hourly
            for h, grp in chunk.groupby('hour', sort=False):
                h = int(h)
                agg_hourly[h]['tickets']    += len(grp)
                agg_hourly[h]['passengers'] += pax.loc[grp.index].sum()

            # DoW × Hour (vectorised sum)
            dh = chunk.assign(pax=pax)
            for (dow, h), grp in dh.groupby(['dow', 'hour'], sort=False):
                agg_dow_hour[(int(dow), int(h))] += grp['pax'].sum()

            # Depot / route / stops
            dep_grp = chunk.assign(pax=pax).groupby('depot')['pax'].sum()
            for k, v in dep_grp.items():
                agg_depot[k] += v

            rt_grp = chunk.assign(pax=pax).groupby('route_id')['pax'].sum()
            for k, v in rt_grp.items():
                agg_route[k] += v

            src_grp = chunk.assign(pax=pax).groupby('source')['pax'].sum()
            for k, v in src_grp.items():
                agg_src[k.strip().upper()] += v

            dst_grp = chunk.assign(pax=pax).groupby('destination')['pax'].sum()
            for k, v in dst_grp.items():
                agg_dst[k.strip().upper()] += v

            # Categoricals
            for pt, cnt in chunk['payment_type'].str.upper().value_counts().items():
                agg_payment[pt] += cnt
            for tt, cnt in chunk['ticket_type'].value_counts().items():
                agg_ttype[tt] += cnt
            for st, cnt in chunk['route_service_type'].value_counts().items():
                agg_stype[st] += cnt

            del chunk; gc.collect()

    log(f"    {fname}: {day_raw:,} raw → {day_clean:,} clean")

log(f"\nAll files processed.")
log(f"Total raw rows:   {total_raw:,}")
log(f"Total clean rows: {total_clean:,}")
log(f"Rows removed:     {total_raw - total_clean:,}  "
    f"({(total_raw-total_clean)/total_raw*100:.2f}%)")
log(f"QC issues: {dict(qc)}")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: BUS STOPS
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 1 — STEP 4: BUS STOPS")
log("=" * 70)
stops_gcc      = pd.read_excel(stops_xlsx, sheet_name='GCC')
stops_avadi    = pd.read_excel(stops_xlsx, sheet_name='Avadi')
stops_tambaram = pd.read_excel(stops_xlsx, sheet_name='Tambaram')
stops_gcc['municipality']      = 'GCC'
stops_avadi['municipality']    = 'Avadi'
stops_tambaram['municipality'] = 'Tambaram'
stops_all = pd.concat([stops_gcc, stops_avadi, stops_tambaram], ignore_index=True)
stops_all.columns = [c.strip() for c in stops_all.columns]
log(f"Bus stops total: {len(stops_all):,}  "
    f"(GCC {len(stops_gcc)}, Avadi {len(stops_avadi)}, Tambaram {len(stops_tambaram)})")
log(f"Columns: {list(stops_all.columns)}")
log(f"Lat range: {stops_all['Latitude'].min():.4f} – {stops_all['Latitude'].max():.4f}")
log(f"Lon range: {stops_all['Longitude'].min():.4f} – {stops_all['Longitude'].max():.4f}")
stops_all.to_csv(OUT_TABLES / "bus_stops_all.csv", index=False)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: JOIN QUALITY
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 1 — STEP 5: JOIN QUALITY")
log("=" * 70)
etm_stops_set = set(agg_src.keys()) | set(agg_dst.keys())
ref_stops_set = set(s.strip().upper() for s in stops_all['Bus Stop Name'].dropna())
matched       = etm_stops_set & ref_stops_set
pct_match     = len(matched) / len(etm_stops_set) * 100 if etm_stops_set else 0
log(f"Unique stops in ETM:         {len(etm_stops_set):,}")
log(f"Unique stops in reference:   {len(ref_stops_set):,}")
log(f"Exact name match:            {len(matched):,} ({pct_match:.1f}%)")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 6: SUMMARY STATS
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 1 — STEP 6: SUMMARY STATISTICS")
log("=" * 70)

n_dates     = len(agg_daily)
total_tix   = sum(v['tickets']    for v in agg_daily.values())
total_pax   = sum(v['passengers'] for v in agg_daily.values())
total_rev   = sum(v['revenue']    for v in agg_daily.values())
avg_fare    = total_rev / total_pax if total_pax else 0
avg_pax_day = total_pax / n_dates  if n_dates else 0

log(f"""
=== MARCH 2026 — CHENNAI MTC ETM KEY METRICS ===
  Total ticket transactions:    {total_tix:>14,.0f}
  Total passengers:             {total_pax:>14,.0f}
  Total revenue:                ₹{total_rev:>13,.0f}
  Unique depots:                {len(agg_depot):>14,}
  Unique routes (extracted):    {len(agg_route):>14,}
  Unique boarding stops:        {len(agg_src):>14,}
  Unique alighting stops:       {len(agg_dst):>14,}
  Avg daily passengers:         {avg_pax_day:>14,.0f}
  Avg fare per passenger:       ₹{avg_fare:>13.2f}
  Date range:                   {min(agg_daily)} to {max(agg_daily)}
""")

log("KM statistics (sample):")
if km_sample:
    ka = np.array(km_sample, dtype=float)
    log(f"  Count: {len(ka):,}  Min: {ka.min():.1f}  Max: {ka.max():.1f}"
        f"  Mean: {ka.mean():.1f}  Median: {np.median(ka):.1f}")
    log(f"  >200km: {(ka>200).sum():,}  <0km: {(ka<0).sum():,}")

log("\nPayment types:")
for k, v in sorted(agg_payment.items(), key=lambda x: -x[1])[:10]:
    log(f"  {k}: {v:,}")
log("\nTicket types:")
for k, v in sorted(agg_ttype.items(), key=lambda x: -x[1])[:10]:
    log(f"  {k}: {v:,}")
log("\nService types:")
for k, v in sorted(agg_stype.items(), key=lambda x: -x[1])[:10]:
    log(f"  {k}: {v:,}")
log("\nTop 20 routes by passengers:")
for k, v in sorted(agg_route.items(), key=lambda x: -x[1])[:20]:
    log(f"  {k}: {v:,.0f}")
log("\nTop 20 depots by passengers:")
for k, v in sorted(agg_depot.items(), key=lambda x: -x[1])[:20]:
    log(f"  {k}: {v:,.0f}")
log("\nTop 20 boarding stops:")
for k, v in sorted(agg_src.items(), key=lambda x: -x[1])[:20]:
    log(f"  {k}: {v:,.0f}")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7: SAVE TABLES
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 1 — STEP 7: SAVING TABLES")
log("=" * 70)

daily_df = pd.DataFrame([
    {'date':k,'tickets':v['tickets'],'passengers':v['passengers'],'revenue':v['revenue']}
    for k,v in agg_daily.items()
]).sort_values('date').reset_index(drop=True)
daily_df['date']       = pd.to_datetime(daily_df['date'])
daily_df['dow']        = daily_df['date'].dt.day_name()
daily_df['dow_num']    = daily_df['date'].dt.dayofweek
daily_df['is_weekend'] = daily_df['dow_num'].isin([5,6])
daily_df.to_csv(OUT_TABLES/"daily_summary.csv", index=False)
daily_df.to_parquet(DATA_CLEAN/"daily_summary.parquet", index=False)

hourly_df = pd.DataFrame([
    {'hour':h,'tickets':v['tickets'],'passengers':v['passengers']}
    for h,v in agg_hourly.items()
]).sort_values('hour').reset_index(drop=True)
hourly_df.to_csv(OUT_TABLES/"hourly_summary.csv", index=False)

dow_hour_df = pd.DataFrame([
    {'dow_num':k[0],'hour':k[1],'passengers':v}
    for k,v in agg_dow_hour.items()
])
dow_hour_df.to_csv(OUT_TABLES/"dow_hour_heatmap.csv", index=False)

depot_df = pd.DataFrame([{'depot':k,'passengers':v}
    for k,v in agg_depot.items()]).sort_values('passengers',ascending=False)
depot_df.to_csv(OUT_TABLES/"depot_summary.csv", index=False)

route_df = pd.DataFrame([{'route_id':k,'passengers':v}
    for k,v in agg_route.items()]).sort_values('passengers',ascending=False)
route_df.to_csv(OUT_TABLES/"route_summary.csv", index=False)

src_df = pd.DataFrame([{'stop':k,'passengers':v}
    for k,v in agg_src.items()]).sort_values('passengers',ascending=False)
src_df.to_csv(OUT_TABLES/"boarding_stops_summary.csv", index=False)

dst_df = pd.DataFrame([{'stop':k,'passengers':v}
    for k,v in agg_dst.items()]).sort_values('passengers',ascending=False)
dst_df.to_csv(OUT_TABLES/"alighting_stops_summary.csv", index=False)

pd.DataFrame([{'payment_type':k,'count':v} for k,v in agg_payment.items()]
    ).sort_values('count',ascending=False).to_csv(OUT_TABLES/"payment_types.csv",index=False)
pd.DataFrame([{'ticket_type':k,'count':v} for k,v in agg_ttype.items()]
    ).sort_values('count',ascending=False).to_csv(OUT_TABLES/"ticket_types.csv",index=False)
pd.DataFrame([{'service_type':k,'count':v} for k,v in agg_stype.items()]
    ).sort_values('count',ascending=False).to_csv(OUT_TABLES/"service_types.csv",index=False)

log("All tables saved.")

# Data dictionary
col_desc = {
    'id':'Unique ticket transaction ID','depot_code':'Depot short code',
    'depot':'Full depot name','fleet_no':'Bus vehicle number',
    'route_service_type':'Service type (Ordinary/Express/etc.)',
    'trip_no':'Trip sequence number','ticket_no':'Ticket serial within trip',
    'date':'Date of issue (DD-MM-YYYY)','time':'Time of issue (HH:MM:SS)',
    'ticket_type':'Passenger category','source':'Boarding stop name',
    'destination':'Alighting stop name','passenger_count':'Passengers on ticket',
    'luggage_count':'Luggage items','passenger_amount':'Fare (INR)',
    'luggage_amount':'Luggage fare (INR)','driver_no':'Driver ID',
    'conductor_no':'Conductor ID','waybill_no':'Trip sheet reference',
    'schedule_no':'Schedule code (encodes route/direction/shift)',
    'payment_type':'Payment method (CASH/UPI/CARD/NCMC)',
    'direction':'Route direction string','Trip_Origin':'Trip start terminus',
    'Trip_Destination':'Trip end terminus','total_ticket_amount':'Total ticket amount (INR)',
    'KM':'Journey distance (km)','duty_date':'Date of duty/shift',
    'from_stage':'Boarding fare stage','to_stage':'Alighting fare stage',
    'add_trip':'Additional trip flag (Y/N)','device_serial_number':'ETM device serial',
    'NCMC_Recharge_Amount':'NCMC recharge (mostly blank)',
    'pine_labs_transaction_no':'Pine Labs POS txn (mostly blank)',
    'merchant_id':'Merchant ID (card)','rrn_number':'Card RRN',
    'terminal_id':'POS terminal ID (mostly blank)',
}
dd = []
for c in COLUMNS:
    ex = df_peek[c].dropna().iloc[0] if c in df_peek and len(df_peek[c].dropna())>0 else 'N/A'
    dd.append({'column':c,'inferred_meaning':col_desc.get(c,'Unknown'),
        'raw_dtype':str(df_peek[c].dtype),'example':str(ex)[:60]})
pd.DataFrame(dd).to_csv(OUT_TABLES/"data_dictionary.csv",index=False)
log("  data_dictionary.csv saved")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 8: CHARTS
# ══════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 70)
log("PHASE 1 — STEP 8: CHARTS")
log("=" * 70)

# C1: Daily 3-panel
fig, axes = plt.subplots(3, 1, figsize=(14, 12))
fig.suptitle('March 2026 — Daily ETM Summary (Chennai MTC)', fontsize=14, fontweight='bold')
metrics = [('tickets','Ticket Transactions','steelblue',lambda x,_:f'{x/1e3:.0f}K'),
           ('passengers','Passengers','darkorange',lambda x,_:f'{x/1e3:.0f}K'),
           ('revenue','Revenue (INR)','seagreen',lambda x,_:f'₹{x/1e6:.1f}M')]
for ax, (m, label, col, fmt) in zip(axes, metrics):
    ax.bar(daily_df['date'], daily_df[m], color=col, edgecolor='white', lw=0.5)
    ax.set_title(f'Daily {label}'); ax.set_ylabel(label)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt))
    ax.grid(axis='y', alpha=0.3)
    for _, row in daily_df[daily_df['is_weekend']].iterrows():
        ax.axvspan(row['date'] - pd.Timedelta(hours=12),
                   row['date'] + pd.Timedelta(hours=12), alpha=0.12, color='red')
axes[0].text(0.98, 0.95, '■ Weekend', transform=axes[0].transAxes,
             ha='right', va='top', color='red', alpha=0.6, fontsize=9)
plt.tight_layout()
plt.savefig(OUT_CHARTS/"phase1_daily_summary.png", dpi=150, bbox_inches='tight')
plt.close(); log("C1: phase1_daily_summary.png")

# C2: Hourly
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('March 2026 — Hourly Demand (All 31 Days)', fontsize=13, fontweight='bold')
for ax, m, label, col in [(ax1,'tickets','Tickets','steelblue'),
                           (ax2,'passengers','Passengers','darkorange')]:
    ax.bar(hourly_df['hour'], hourly_df[m], color=col)
    ax.set_title(f'{label} by Hour'); ax.set_xlabel('Hour'); ax.set_ylabel(label)
    ax.set_xticks(range(0,24,2)); ax.grid(axis='y',alpha=0.3)
    ax.axvspan(7.5,10.5,alpha=0.15,color='red',   label='AM Peak 8–10h')
    ax.axvspan(16.5,20.5,alpha=0.15,color='orange',label='PM Peak 17–20h')
    ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(OUT_CHARTS/"phase1_hourly_distribution.png", dpi=150, bbox_inches='tight')
plt.close(); log("C2: phase1_hourly_distribution.png")

# C3: DoW×Hour heatmap
dow_pivot = dow_hour_df.pivot_table(
    index='dow_num', columns='hour', values='passengers', aggfunc='sum') / 1e3
dow_pivot.index = [DOW_NAMES.get(i,i) for i in dow_pivot.index]
dow_pivot = dow_pivot.reindex(['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])
fig, ax = plt.subplots(figsize=(16,4))
sns.heatmap(dow_pivot, cmap='YlOrRd', ax=ax, linewidths=0.1,
            cbar_kws={'label':'Passengers (thousands)'})
ax.set_title('Passenger Demand Heatmap — Day of Week × Hour', fontsize=13, fontweight='bold')
ax.set_xlabel('Hour of Day'); ax.set_ylabel('Day of Week')
plt.tight_layout()
plt.savefig(OUT_CHARTS/"phase1_dow_hour_heatmap.png", dpi=150, bbox_inches='tight')
plt.close(); log("C3: phase1_dow_hour_heatmap.png")

# C4: Top 20 depots
top20_dep = depot_df.head(20).sort_values('passengers')
fig, ax = plt.subplots(figsize=(12,7))
ax.barh(top20_dep['depot'], top20_dep['passengers']/1e6, color='steelblue')
ax.set_title('Top 20 Depots by Total Passengers — March 2026', fontweight='bold')
ax.set_xlabel('Passengers (M)'); ax.grid(axis='x',alpha=0.3)
plt.tight_layout()
plt.savefig(OUT_CHARTS/"phase1_top_depots.png", dpi=150, bbox_inches='tight')
plt.close(); log("C4: phase1_top_depots.png")

# C5: Top 20 routes
top20_rt = route_df[route_df['route_id'].notna() & (route_df['route_id']!='UNK')].head(20).sort_values('passengers')
fig, ax = plt.subplots(figsize=(12,7))
ax.barh(top20_rt['route_id'].astype(str), top20_rt['passengers']/1e6, color='darkorange')
ax.set_title('Top 20 Routes by Total Passengers — March 2026', fontweight='bold')
ax.set_xlabel('Passengers (M)'); ax.grid(axis='x',alpha=0.3)
plt.tight_layout()
plt.savefig(OUT_CHARTS/"phase1_top_routes.png", dpi=150, bbox_inches='tight')
plt.close(); log("C5: phase1_top_routes.png")

# C6: Payment pie
payment_sorted = pd.DataFrame([{'k':k,'v':v} for k,v in agg_payment.items()]
    ).sort_values('v',ascending=False)
fig, ax = plt.subplots(figsize=(8,6))
ax.pie(payment_sorted['v'], labels=payment_sorted['k'], autopct='%1.1f%%',
       colors=sns.color_palette('Set2', len(payment_sorted)), startangle=140)
ax.set_title('Payment Method Distribution — March 2026', fontweight='bold')
plt.tight_layout()
plt.savefig(OUT_CHARTS/"phase1_payment_types.png", dpi=150, bbox_inches='tight')
plt.close(); log("C6: phase1_payment_types.png")

# C7: Ticket types
tt_df = pd.DataFrame([{'k':k,'v':v} for k,v in agg_ttype.items()]
    ).sort_values('v',ascending=False).head(10).sort_values('v')
fig, ax = plt.subplots(figsize=(10,5))
ax.barh(tt_df['k'], tt_df['v']/1e6, color='purple')
ax.set_title('Top 10 Ticket Types — March 2026', fontweight='bold')
ax.set_xlabel('Count (M)'); ax.grid(axis='x',alpha=0.3)
plt.tight_layout()
plt.savefig(OUT_CHARTS/"phase1_ticket_types.png", dpi=150, bbox_inches='tight')
plt.close(); log("C7: phase1_ticket_types.png")

# C8: Top 20 boarding stops
top20_src = src_df.head(20).sort_values('passengers')
fig, ax = plt.subplots(figsize=(12,8))
ax.barh(top20_src['stop'].astype(str), top20_src['passengers']/1e6, color='teal')
ax.set_title('Top 20 Boarding Stops — March 2026', fontweight='bold')
ax.set_xlabel('Passengers (M)'); ax.grid(axis='x',alpha=0.3)
plt.tight_layout()
plt.savefig(OUT_CHARTS/"phase1_top_boarding_stops.png", dpi=150, bbox_inches='tight')
plt.close(); log("C8: phase1_top_boarding_stops.png")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 9: FINDINGS.MD
# ══════════════════════════════════════════════════════════════════════════════
findings = f"""# CUMTA/MTC Smart Transit Analytics — Findings Log

## PHASE 1: Data Understanding ✓

### Dataset Inventory

| File / Dataset | Format | Records | Date Range | Granularity |
|---|---|---|---|---|
| ETM Ticket Data (31 files) | CSV.BZ2 | {total_tix:,.0f} transactions | 01-Mar-2026 – 31-Mar-2026 | Per ticket transaction |
| Bus Stops (GCC, Avadi, Tambaram) | XLSX (3 sheets) | {len(stops_all):,} stops | — | Per bus stop |
| MTC Bus Routes | Shapefile | — | — | Per route geometry |
| Metro Rail Lines + Stations | Shapefile | — | — | Per segment/station |
| Suburban Rail Network | Shapefile | — | — | Per segment |
| PT Fare Structure | PDF | — | — | Reference document |

### March 2026 Key Metrics

| Metric | Value |
|---|---|
| Total ticket transactions | {total_tix:,.0f} |
| Total passengers | {total_pax:,.0f} |
| Total revenue | ₹{total_rev:,.0f} |
| Avg fare / passenger | ₹{avg_fare:.2f} |
| Unique depots | {len(agg_depot)} |
| Unique routes (from schedule_no) | {len(agg_route)} |
| Unique boarding stops | {len(agg_src)} |
| Avg daily passengers | {avg_pax_day:,.0f} |
| Date range | 01-Mar-2026 to 31-Mar-2026 |

### ETM Data Structure (36 raw columns)

**Granularity:** One row = one ticket transaction (1+ passengers)

**Key column groups:**
- **Identity:** `id`, `ticket_no`, `waybill_no`, `schedule_no`
- **Vehicle/Operator:** `depot_code`, `depot`, `fleet_no`, `driver_no`, `conductor_no`
- **Route/Trip:** `route_service_type`, `trip_no`, `direction`, `Trip_Origin`, `Trip_Destination`
- **Spatial:** `source` (boarding), `destination` (alighting), `KM`
- **Demand:** `passenger_count`, `ticket_type`
- **Financial:** `passenger_amount`, `payment_type`
- **Temporal:** `date`, `time`, `duty_date`

**Derived:** `route_id` from `schedule_no` via regex `[OE]-([^-]+)-`

### Data Quality Summary

| Issue | Count | Action |
|---|---|---|
| Date parse failures | {qc['date_fail']:,} | Rows dropped |
| Negative passenger_count | {qc['neg_pax']:,} | Rows dropped |
| Zero passenger_count | {qc['zero_pax']:,} | Rows dropped |
| passenger_count > 200 | {qc['large_pax']:,} | Rows dropped |
| Negative passenger_amount | {qc['neg_amt']:,} | Rows dropped |
| Total rows removed | {total_raw-total_clean:,} ({(total_raw-total_clean)/total_raw*100:.2f}%) | — |
| ETM ↔ stop reference match | {pct_match:.0f}% | No join; name used as-is |

### Data Gaps & Limitations

1. **No headway/frequency data** — Cannot compute delay or service adherence directly.
2. **No actual arrival/departure timestamps per stop** — Only boarding time known.
3. **No capacity data** — Bus seating capacity per `fleet_no` absent → load factor uses assumption (~85 pax/bus).
4. **No GPS tracks** — Cannot compute speed or route adherence.
5. **No weather/event data** — External anomaly explanations unavailable.
6. **Stop name match only {pct_match:.0f}%** — Spelling differences between ETM and reference.
7. **No scheduled timetable** — Cannot compare actual vs scheduled trips.

### Phase 1 Charts

| ID | File | Description |
|---|---|---|
| C1 | `phase1_daily_summary.png` | Daily tickets, passengers, revenue (weekends shaded) |
| C2 | `phase1_hourly_distribution.png` | Hour-of-day demand with AM/PM peak bands |
| C3 | `phase1_dow_hour_heatmap.png` | Day-of-week × hour passenger heatmap |
| C4 | `phase1_top_depots.png` | Top 20 depots by total passengers |
| C5 | `phase1_top_routes.png` | Top 20 routes by total passengers |
| C6 | `phase1_payment_types.png` | Payment method breakdown |
| C7 | `phase1_ticket_types.png` | Ticket category breakdown |
| C8 | `phase1_top_boarding_stops.png` | Top 20 boarding stops |

---
*Log updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

with open(FINDINGS, 'w', encoding='utf-8') as fh:
    fh.write(findings)
log(f"\nFindings written to: {FINDINGS}")

log("\n" + "=" * 70)
log("PHASE 1 COMPLETE ✓")
log("=" * 70)
