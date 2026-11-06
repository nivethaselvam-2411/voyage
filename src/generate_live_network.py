"""
Generates real-time live network simulation data for Marina Sentinel Live Map.
Extracts real GIS polylines from Public Transport/MTC/routes_merged.shp
and couples them with passenger occupancy estimation and ex-ante delay prediction.
"""
import struct
import json
import math
import random
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent

# 1. Read DBF
dbf_path = ROOT / "Public Transport/MTC/routes_merged.dbf"
shp_path = ROOT / "Public Transport/MTC/routes_merged.shp"

with open(dbf_path, "rb") as f:
    f.read(4)
    num_records = struct.unpack('<I', f.read(4))[0]
    header_size = struct.unpack('<H', f.read(2))[0]
    record_size = struct.unpack('<H', f.read(2))[0]
    f.read(20)
    num_fields = (header_size - 33) // 32
    fields, field_lens = [], []
    for _ in range(num_fields):
        desc = f.read(32)
        fields.append(desc[:11].split(b'\x00')[0].decode('ascii', errors='ignore'))
        field_lens.append(desc[16])
    f.seek(header_size)
    dbf_records = []
    for i in range(num_records):
        rec = f.read(record_size)
        if not rec or rec[0] == 0x2A:
            dbf_records.append(None)
            continue
        offset = 1
        row = {}
        for name, flen in zip(fields, field_lens):
            row[name] = rec[offset:offset+flen].decode('latin1', errors='ignore').strip()
            offset += flen
        dbf_records.append(row)

# 2. Read SHP
shp_polylines = []
with open(shp_path, "rb") as f_shp:
    f_shp.seek(100)
    for i in range(num_records):
        hdr = f_shp.read(8)
        if not hdr:
            break
        rec_num, content_len = struct.unpack('>2i', hdr)
        stype = struct.unpack('<i', f_shp.read(4))[0]
        bbox = struct.unpack('<4d', f_shp.read(32))
        num_parts, num_points = struct.unpack('<2i', f_shp.read(8))
        parts = struct.unpack(f'<{num_parts}i', f_shp.read(4 * num_parts))
        pts = [struct.unpack('<2d', f_shp.read(16)) for _ in range(num_points)]
        # convert to [lat, lng]
        lat_lngs = [[round(p[1], 5), round(p[0], 5)] for p in pts]
        shp_polylines.append(lat_lngs)

# Target high-ridership corridors
key_corridors_spec = [
    {"route": "102CT", "name": "OMR Express Corridor (Broadway ↔ Kelambakkam)", "depot": "Adyar Depot", "color": "#2563EB", "search": "102"},
    {"route": "29C", "name": "Central Arterial (Perambur ↔ Besant Nagar)", "depot": "Perambur Depot", "color": "#DC2626", "search": "29C"},
    {"route": "21G", "name": "GST Trunk (Broadway ↔ Tambaram)", "depot": "Tambaram Depot", "color": "#D97706", "search": "21G"},
    {"route": "19B", "name": "IT Suburban (T.Nagar ↔ Siruseri)", "depot": "Saidapet Depot", "color": "#7C3AED", "search": "19B"},
    {"route": "18A", "name": "Grand Southern Arterial (Central ↔ Tambaram)", "depot": "T.Nagar Depot", "color": "#059669", "search": "18A"},
    {"route": "23C", "name": "Chetpet Crossway (Ayanavaram ↔ Besant Nagar)", "depot": "Ayanavaram Depot", "color": "#0891B2", "search": "23C"},
    {"route": "48C", "name": "West Circular (Vallalar Nagar ↔ CMBT Koyambedu)", "depot": "Vyasarpadi Depot", "color": "#DB2777", "search": "48C"},
    {"route": "44", "name": "North Harbor (Broadway ↔ Manali)", "depot": "Tondiarpet Depot", "color": "#475569", "search": "44"}
]

def downsample_polyline(pts, target=50):
    if len(pts) <= target:
        return pts
    step = len(pts) / target
    return [pts[int(i * step)] for i in range(target)]

def calculate_bearing(p1, p2):
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    deg = math.degrees(initial_bearing)
    return round((deg + 360) % 360, 1)

def point_at_fraction(pts, frac):
    idx_float = (len(pts) - 1) * frac
    idx_floor = int(idx_float)
    idx_ceil = min(idx_floor + 1, len(pts) - 1)
    remainder = idx_float - idx_floor
    p1 = pts[idx_floor]
    p2 = pts[idx_ceil]
    lat = round(p1[0] + (p2[0] - p1[0]) * remainder, 5)
    lng = round(p1[1] + (p2[1] - p1[1]) * remainder, 5)
    bearing = calculate_bearing(p1, p2)
    return [lat, lng], bearing

corridors = []
buses = []
bus_id_counter = 1001

for c_spec in key_corridors_spec:
    target_route = c_spec["route"]
    # find best shape
    best_idx = None
    max_pts = 0
    for idx, r in enumerate(dbf_records):
        if r and r.get('route_num') == target_route and len(shp_polylines[idx]) > max_pts:
            best_idx = idx
            max_pts = len(shp_polylines[idx])
    
    if best_idx is None:
        # fallback search
        for idx, r in enumerate(dbf_records):
            if r and c_spec["search"] in r.get('route_num', '') and len(shp_polylines[idx]) > max_pts:
                best_idx = idx
                max_pts = len(shp_polylines[idx])
                
    if best_idx is None or len(shp_polylines[best_idx]) < 10:
        continue
        
    raw_pts = shp_polylines[best_idx]
    clean_pts = downsample_polyline(raw_pts, target=45)
    
    dbf_row = dbf_records[best_idx]
    origin = dbf_row.get('source', 'Terminal Origin').title()
    dest = dbf_row.get('destinat', 'Terminal Dest').title()
    
    corridors.append({
        "route_id": target_route,
        "name": c_spec["name"],
        "origin": origin,
        "destination": dest,
        "depot": c_spec["depot"],
        "color": c_spec["color"],
        "waypoints": clean_pts
    })
    
    # Generate 5-7 active buses along this corridor with realistic load and delay curves
    num_buses = random.randint(5, 7)
    fractions = sorted([random.uniform(0.08, 0.92) for _ in range(num_buses)])
    
    for f in fractions:
        pos, bearing = point_at_fraction(clean_pts, f)
        
        # Load profile: peak in middle of corridor, lower at terminals
        dist_factor = math.sin(f * math.pi) # 0 at ends, 1 in middle
        base_load = 40 + int(dist_factor * random.randint(30, 58))
        
        # Introduce critical overcrowding on specific routes (e.g. 102CT, 29C, 21G)
        if target_route in ["102CT", "29C", "21G"] and dist_factor > 0.6:
            pax = random.randint(84, 98) # Crush load
        elif target_route in ["44", "48C"] and dist_factor < 0.4:
            pax = random.randint(22, 38) # Surplus / donor candidate
        else:
            pax = min(base_load + random.randint(-8, 12), 95)
            
        dcr = round(pax / 70.0, 2)
        
        # -------------------------------------------------------------
        # EX-ANTE DELAY PREDICTION ENGINE
        # Models dwell-time inflation + inbound turnaround cascade
        # -------------------------------------------------------------
        if dcr >= 1.25:
            status = "critical"
            action = f"Priority 1: Fleet Injection (+{math.ceil((pax - 70)/70)} Reserve Bus)"
            dwell_delay = round(random.uniform(7.5, 12.0), 1)
            cascade_delay = round(random.uniform(8.0, 14.0), 1)
            total_delay = round(dwell_delay + cascade_delay, 1)
            delay_status = "severe"
            advisory = f"High Delay (+{int(total_delay)}m) & Crush Load. PIS Advisory: Divert to alternate parallel Route 19B (Seats Available)."
        elif dcr >= 1.0:
            status = "crowded"
            action = "Priority 2: Short-Turn Loop at Major Interchange"
            dwell_delay = round(random.uniform(4.0, 6.5), 1)
            cascade_delay = round(random.uniform(3.5, 7.5), 1)
            total_delay = round(dwell_delay + cascade_delay, 1)
            delay_status = "moderate"
            advisory = f"Moderate Delay (+{int(total_delay)}m). Expect standing room only."
        elif dcr >= 0.70:
            status = "balanced"
            action = "Maintain Standard Operating Headway"
            dwell_delay = round(random.uniform(1.0, 2.5), 1)
            cascade_delay = round(random.uniform(0.5, 2.5), 1)
            total_delay = round(dwell_delay + cascade_delay, 1)
            delay_status = "on_time"
            advisory = "On Schedule (< 5m delay). Seats available."
        else:
            status = "surplus"
            action = "Potential Donor Candidate for Intra-Depot Lending"
            dwell_delay = 0.0
            cascade_delay = round(random.uniform(0.0, 1.8), 1)
            total_delay = round(dwell_delay + cascade_delay, 1)
            delay_status = "on_time"
            advisory = "On Schedule. High seat availability."
            
        fleet_num = f"TN-01-N-{bus_id_counter}"
        bus_id_counter += random.randint(12, 38)
        
        # Scheduled vs predicted arrival
        sched_minute = (int(f * 50) + 15) % 60
        sched_time = f"08:{sched_minute:02d} AM"
        pred_minute = (sched_minute + int(total_delay)) % 60
        pred_hour = 8 + ((sched_minute + int(total_delay)) // 60)
        pred_time = f"{pred_hour:02d}:{pred_minute:02d} AM"

        buses.append({
            "id": f"BUS-MTC-{fleet_num}",
            "fleet_no": fleet_num,
            "route": target_route,
            "route_name": f"Route {target_route} ({origin} ↔ {dest})",
            "depot": c_spec["depot"],
            "lat": pos[0],
            "lng": pos[1],
            "bearing": bearing,
            "capacity": 70,
            "passengers": pax,
            "dcr": dcr,
            "status": status,
            "speed_kmh": random.randint(18, 36),
            "progress_percent": round(f * 100, 1),
            "recommended_action": action,
            "total_boarded": int(pax * random.uniform(1.3, 1.6)),
            "total_alighted": int(pax * random.uniform(0.3, 0.6)),
            # Ex-Ante Delay Predictions
            "predicted_delay_min": total_delay,
            "departure_cascade_delay_min": cascade_delay,
            "dwell_congestion_delay_min": dwell_delay,
            "delay_status": delay_status,
            "scheduled_time": sched_time,
            "predicted_arrival_time": pred_time,
            "passenger_advisory": advisory
        })

# Top transfer hub stops across Chennai for map pins
transfer_stops = [
    {"name": "Chennai Central (M.G.R. Central)", "lat": 13.0827, "lon": 80.2755, "type": "Intermodal Hub"},
    {"name": "Broadway Bus Terminus", "lat": 13.0886, "lon": 80.2870, "type": "Major Terminal"},
    {"name": "CMBT Koyambedu", "lat": 13.0673, "lon": 80.2057, "type": "Intercity Terminal"},
    {"name": "Tambaram Sanatorium / Bus Stand", "lat": 12.9249, "lon": 80.1280, "type": "Suburban Hub"},
    {"name": "Guindy Railway Station / Metro", "lat": 13.0067, "lon": 80.2119, "type": "Interchange Hub"},
    {"name": "T. Nagar Terminus", "lat": 13.0418, "lon": 80.2341, "type": "Commercial Terminal"},
    {"name": "Tidel Park / Thiruvanmiyur", "lat": 12.9897, "lon": 80.2474, "type": "OMR Tech Gateway"},
    {"name": "Sholinganallur Junction", "lat": 12.9010, "lon": 80.2279, "type": "OMR Junction"},
    {"name": "Perambur Bus Depot / Station", "lat": 13.1116, "lon": 80.2428, "type": "North Hub"},
    {"name": "Adyar Depot / Madhya Kailash", "lat": 13.0072, "lon": 80.2529, "type": "South Arterial Hub"},
    {"name": "Saidapet Court / Bus Stop", "lat": 13.0210, "lon": 80.2230, "type": "Radial Hub"},
    {"name": "Kelambakkam Terminus", "lat": 12.7876, "lon": 80.2201, "type": "Southern Terminal"}
]

network_payload = {
    "generated_at": "2026-03-31T08:30:00Z",
    "simulated_time": "08:30 AM (Peak Morning Window)",
    "city": "Chennai",
    "operator": "Metropolitan Transport Corporation (MTC)",
    "summary": {
        "active_buses_tracked": len(buses),
        "active_corridors": len(corridors),
        "critical_overcrowded": sum(1 for b in buses if b["status"] == "critical"),
        "crowded_near_capacity": sum(1 for b in buses if b["status"] == "crowded"),
        "balanced": sum(1 for b in buses if b["status"] == "balanced"),
        "surplus_potential_donors": sum(1 for b in buses if b["status"] == "surplus"),
        "network_avg_dcr": round(sum(b["dcr"] for b in buses) / len(buses), 2),
        "total_passengers_in_transit": sum(b["passengers"] for b in buses),
        # Delay summary metrics
        "avg_predicted_delay_min": round(sum(b["predicted_delay_min"] for b in buses) / len(buses), 1),
        "severe_delay_count": sum(1 for b in buses if b["delay_status"] == "severe"),
        "moderate_delay_count": sum(1 for b in buses if b["delay_status"] == "moderate"),
        "on_time_count": sum(1 for b in buses if b["delay_status"] == "on_time")
    },
    "corridors": corridors,
    "buses": buses,
    "transfer_stops": transfer_stops
}

# Save to outputs and frontend mocks
out_demo = ROOT / "outputs/demo/live_network.json"
out_mock = ROOT / "frontend/src/mocks/live-network.json"

out_demo.parent.mkdir(parents=True, exist_ok=True)
out_mock.parent.mkdir(parents=True, exist_ok=True)

with open(out_demo, "w", encoding="utf-8") as f:
    json.dump(network_payload, f, indent=2)

with open(out_mock, "w", encoding="utf-8") as f:
    json.dump(network_payload, f, indent=2)

print(f"Generated live network with delay predictions: {len(corridors)} corridors, {len(buses)} active buses.")
print(f"Avg predicted delay: {network_payload['summary']['avg_predicted_delay_min']} mins. Severe delay: {network_payload['summary']['severe_delay_count']} buses.")
print(f"Saved to {out_demo} and {out_mock}")
