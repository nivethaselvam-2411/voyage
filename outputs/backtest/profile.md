# TransitIQ: Organiser Dataset Profile & Validation Report

**Scope:** 31 Days (2026-03-01 to 2026-03-31) | Citywide Active Bus Fleet | 705 Routes | 16 Depots  
**Total Records Analyzed:** ~67.8 Million ETM Ticket Transactions (349,799 Route-Hour Slots)  
**File Verified:** `day_2026-03-01.parquet` (Representative daily corpus: 1,738,503 rows)

---

## 1. Organiser Data Integrity & Physical Sanity Checks

| Check Item | Result | Integrity Status | Analytical Finding |
| :--- | :---: | :---: | :--- |
| **Origin & Destination (OD) Stages** | **1,277 Sources / 1,218 Destinations** | **100% Present** | `source` and `destination` boarding/alighting stages have **0% missing values**. OD passenger flow is directly measurable. |
| **Impossible Passenger Counts** | **Max Pax / Ticket = 9** (Mean: 1.22) | **Physically Realistic** | **0 tickets** exceed 10 passengers. Matches physical limits of handheld ETM paper slips. |
| **Zero-Fare & Concessions Capture** | **51.27% of tickets are ₹0.0** | **Fully Captured** | **Women's Free Travel (Vidiyal Payanam) is 45.19% of pax volume** (`Women Ticket`). Concessions are NOT missing. |
| **ETM Upload Gaps Across Hours** | **Continuous 24-Hour Coverage** | **Zero Hour Gaps** | Trough at 01:00 (3.3k pax/hr); dual peaks at 09:00 (149k pax/hr) and 17:00-18:00 (148k pax/hr). |
| **Temporal Span & Lookback Buffer** | **Exactly 31 Days (March 1-31)** | **Burn-in Enforced** | March 1–7 preserved strictly as un-trained 7-day lookback reservoir for `lag_7d_pax` and `rolling_mean_7d`. |

---

## 2. Fare Breakdown & Concession Recording (Sample Day: 1,738,503 Tickets)

The Tamil Nadu zero-fare women's travel scheme (*Vidiyal Payanam*) and social concessions are recorded as dedicated ticket categories on the conductor ETM:

| Ticket Category | Tickets Issued | Passengers | Fare Charged (INR) | Share of Passengers | Zero-Fare Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Adult Ticket (Paid)** | 847,124 | 1,119,002 | ₹18,509,270 | 52.83% | Standard Paid Fare |
| **Women Ticket (Free Scheme)** | **850,568** | **957,300** | **₹0.0** | **45.19%** | **Vidiyal Payanam Zero-Fare** |
| **Senior Citizen Concession** | 33,847 | 34,733 | ₹0.0 | 1.64% | Senior Zero-Fare Pass |
| **Persons with Disabilities** | 6,593 | 6,733 | ₹0.0 | 0.32% | Concession Zero-Fare |
| **Transgender Concession** | 193 | 237 | ₹0.0 | 0.01% | Concession Zero-Fare |
| **Total Daily Sample** | **1,738,503** | **2,118,160** | **₹18,509,688** | **100.0%** | **51.27% Zero-Fare Tickets** |

---

## 3. Fleet Service Types & Operational Constraints

Fleet rebalancing cannot blindly swap buses between service classes without violating fare structures and depot permits:

| Service Type | Share of Operations | Fare Structure | Rebalancing Compatibility |
| :--- | :---: | :--- | :--- |
| **Ordinary** | **69.92%** | Base fare ₹5–₹15 (Women's free travel applies) | **Primary donor/receiver pool** |
| **Deluxe (Non-AC)** | **20.74%** | Higher flat/stage fare (No free travel) | Separate premium pool only |
| **Deluxe EV** | **4.34%** | Electric fleet (Charging constraints) | Requires depot EV charger sync |
| **Small Bus Express** | **1.78%** | Feeder minibus (Narrow corridors) | Feeder-only corridors |
| **A/C & A/C EV** | **2.08%** | Air-conditioned premium | High-fare corridors only |
| **Express** | **0.37%** | Skip-stop / limited halt | Express-only routes |

*Recommendation:* Fleet transfers must only occur **within the same service tier** (e.g. Ordinary to Ordinary) to preserve tariff and passenger entitlements.

---

## 4. Ground Truth Definition, Base Rate & Model Value-Add

| Metric / Parameter | Baseline Schedule Average `[MEASURED]` | Corrected 60-min ML Model `[MEASURED]` | Net Value Added by ML |
| :--- | :---: | :---: | :---: |
| **Test Period Base Rate** | 25.23% (14,327 / 56,781 slots have DCR > 1.0) | 25.23% | — |
| **Early Capture Recall** | **58.20%** (Same-hour last-week baseline) | **88.60%** (Catches 9 in 10 deficits) | **+30.40% Recall Gain** |
| **Top-50 Queue Precision** | **84.80%** (Historical route share baseline) | **97.20%** (Action Priority Queue) | **+12.40% Absolute Precision** |
| **Passenger Forecast MAE** | **50.24 pax** (Train schedule mean) | **39.35 pax** (Strict 60m ex-ante) | **21.7% Error Reduction** |
| **Dynamic Surge Coverage** | 0.0% (Static timetable detects zero dynamic surges) | **44.0% of queue** (Non-chronic routes) | **Captures unpredictable momentum** |

---

## 5. Summary of Known Data Limitations (Pitch Honesty Protocol)

1. **Proxy Ground Truth:** Demand-to-Capacity Ratio (DCR) is derived from ticket counts divided by rated capacity ($P / (B 	imes 70)$), not physical load-cell sensors or automated passenger counters (APC). In extreme overcrowding, conductor ticket skipping may result in a 5–15% undercount.
2. **Directional Aggregation:** The route-hour level data pools UP and DOWN trips. Rebalancing proposals are advisory for depot managers who refine the dispatch by peak direction.
3. **Counterfactual Rebalancing:** Post-transfer DCR reductions (e.g. 1.43x down to 1.11x) are mathematical counterfactuals assuming travel demand remains fixed. In reality, improved frequency may induce latent demand.
4. **ETM Headway Proxy:** Empty bunched buses issue fewer tickets, which can dampen ticket-derived headway signals. ETM proxies must be combined with MTC's live GPS departure pings for complete operational visibility.
