"""
Fix wording across markdown, json, and reports.
Replaces:
- 'crush load' -> 'demand above capacity'
- 'crush' -> 'capacity deficit'
- 'load factor' -> 'demand-to-capacity ratio (DCR)'
- '3,454 of its buses have GPS' / '3,454 buses' -> 'bus fleet equipped with GPS transponders'
"""
from pathlib import Path

replacements = [
    ("crush load", "demand above capacity"),
    ("Crush Load", "Demand Above Capacity"),
    ("crush", "capacity deficit"),
    ("Crush", "Capacity Deficit"),
    ("load factor", "demand-to-capacity ratio (DCR)"),
    ("Load Factor", "Demand-to-Capacity Ratio (DCR)"),
    ("3,454 Active Buses", "Citywide Active Bus Fleet"),
    ("all 3,454 of its buses have GPS", "its bus fleet is equipped with GPS transponders"),
    ("3,454 GPS buses", "GPS-equipped bus fleet")
]

target_files = [
    Path("profile.md"),
    Path("outputs/backtest/profile.md"),
    Path("outputs/tables/dashboard_feed.json"),
    Path("outputs/findings.md"),
    Path("src/recommendation_config.json"),
    Path("outputs/backtest/backtest_report.md")
]

for p in target_files:
    if p.exists():
        text = p.read_text(encoding='utf-8', errors='ignore')
        orig = text
        for old_str, new_str in replacements:
            text = text.replace(old_str, new_str)
        if text != orig:
            p.write_text(text, encoding='utf-8')
            print(f"Updated wording in: {p}")

print("Term replacement completed successfully.")

