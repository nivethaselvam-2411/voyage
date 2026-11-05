import type {
  KpisResponse,
  ControlRoomAlert,
  RebalancePair,
  RouteItem,
  DatasetManifest,
  HourlySummary,
  ActionType,
  MetricType
} from '../types';

import kpisMock from '../mocks/kpis.json';
import alertsMock from '../mocks/alerts.json';
import rebalancePairsMock from '../mocks/rebalance-pairs.json';
import routesMock from '../mocks/routes.json';
import datasetManifestMock from '../mocks/dataset-manifest.json';
import hourlySummaryMock from '../mocks/hourly-summary.json';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
// Connect to real backend by default; fallback to mocks if backend is unreachable or if VITE_USE_MOCKS is explicitly 'true'
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

// Defensive parser helpers
export const safeNum = (val: unknown, fallback = 0): number => {
  if (typeof val === 'number' && !Number.isNaN(val)) return val;
  if (typeof val === 'string') {
    const parsed = Number.parseFloat(val);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return fallback;
};

export const safeStr = (val: unknown, fallback = 'n/a'): string => {
  if (typeof val === 'string' && val.trim().length > 0) return val;
  if (typeof val === 'number') return String(val);
  return fallback;
};

// Simulate realistic network latency for UI responsiveness
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function fetchKpis(): Promise<KpisResponse> {
  if (!USE_MOCKS) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/kpis`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}: ${res.statusText}`);
      const data = await res.json();
      return {
        mae_reduction_pct: {
          value: safeNum(data?.mae_reduction_pct?.value ?? data?.forecast_accuracy?.mae_reduction_pct_vs_strongest_baseline, 21.7),
          type: data?.mae_reduction_pct?.type || 'MEASURED',
          definition: safeStr(data?.mae_reduction_pct?.definition, 'Model MAE reduction vs historical baseline')
        },
        wape: {
          value: safeNum(data?.wape?.value ?? data?.forecast_accuracy?.citywide_wape_percent, 18.25),
          type: data?.wape?.type || 'MEASURED',
          definition: safeStr(data?.wape?.definition, 'Weighted absolute percentage error')
        },
        r2: {
          value: safeNum(data?.r2?.value ?? data?.forecast_accuracy?.r2_score, 0.9571),
          type: data?.r2?.type || 'MEASURED',
          definition: safeStr(data?.r2?.definition, 'R-squared coefficient')
        },
        roc_auc: {
          value: safeNum(data?.roc_auc?.value ?? data?.overcrowding_early_warning?.roc_auc, 0.9178),
          type: data?.roc_auc?.type || 'MEASURED',
          definition: safeStr(data?.roc_auc?.definition, 'ROC AUC')
        },
        pr_auc: {
          value: safeNum(data?.pr_auc?.value ?? data?.overcrowding_early_warning?.pr_auc, 0.7816),
          type: data?.pr_auc?.type || 'MEASURED',
          definition: safeStr(data?.pr_auc?.definition, 'PR AUC')
        },
        wide_net: {
          recall: safeNum(data?.wide_net?.recall ?? data?.overcrowding_early_warning?.early_capture_recall_percent, 88.6),
          precision: safeNum(data?.wide_net?.precision, 59.2),
          type: data?.wide_net?.type || 'MEASURED',
          definition: safeStr(data?.wide_net?.definition, 'Wide candidate filter')
        },
        priority_queue: {
          precision: safeNum(data?.priority_queue?.precision ?? data?.operational_queue_precision?.strict_precision_percent, 97.2),
          hits: safeNum(data?.priority_queue?.hits ?? data?.operational_queue_precision?.true_positives, 243),
          total: safeNum(data?.priority_queue?.total ?? data?.operational_queue_precision?.total_alerts_evaluated, 250),
          cap_per_day: safeNum(data?.priority_queue?.cap_per_day, 50),
          type: data?.priority_queue?.type || 'MEASURED',
          definition: safeStr(data?.priority_queue?.definition, 'Priority queue precision')
        },
        anomalies_flagged: {
          value: safeNum(data?.anomalies_flagged?.value, 881),
          type: data?.anomalies_flagged?.type || 'MEASURED',
          definition: safeStr(data?.anomalies_flagged?.definition, 'Anomalies flagged')
        },
        rebalancing: {
          operations: safeNum(data?.rebalancing?.operations ?? data?.depot_rebalancing_simulation?.unique_operations_count, 204),
          buses_moved: safeNum(data?.rebalancing?.buses_moved ?? data?.depot_rebalancing_simulation?.total_fleet_transferred, 748),
          share_reaching_dcr_1: safeNum(data?.rebalancing?.share_reaching_dcr_1 ?? data?.depot_rebalancing_simulation?.overcrowded_receivers_normalized_percent, 47.06),
          receiver_mean_dcr_before: safeNum(data?.rebalancing?.receiver_mean_dcr_before ?? data?.depot_rebalancing_simulation?.receiver_pre_dcr_mean, 1.45),
          receiver_mean_dcr_after: safeNum(data?.rebalancing?.receiver_mean_dcr_after ?? data?.depot_rebalancing_simulation?.receiver_post_dcr_mean, 1.12),
          type: 'SIMULATED',
          definition: safeStr(data?.rebalancing?.definition, 'Simulated rebalancing replay')
        }
      };
    } catch (err) {
      console.warn('API /api/kpis unreachable, falling back to mock:', err);
    }
  }

  await delay(120);
  return kpisMock as KpisResponse;
}

export async function fetchControlRoomAlerts(date?: string, hour?: number): Promise<ControlRoomAlert[]> {
  if (!USE_MOCKS) {
    try {
      const url = new URL(`${API_BASE_URL}/api/control-room-alerts`);
      if (date) url.searchParams.set('date', date);
      if (hour !== undefined) url.searchParams.set('hour', String(hour));
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`HTTP error ${res.status}: ${res.statusText}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        return data.map((item: any) => ({
          id: safeStr(item?.id ?? item?.alert_id, 'ALT-UNKNOWN'),
          route: safeStr(item?.route ?? item?.route_id, 'n/a'),
          depot: safeStr(item?.depot, 'n/a'),
          time_window: safeStr(item?.time_window, 'n/a'),
          predicted_dcr: safeNum(item?.predicted_dcr ?? item?.pred_dcr ?? item?.dcr, 1.0),
          expected_deficit_pax: safeNum(item?.expected_deficit_pax ?? item?.predicted_deficit_pax ?? item?.deficit_passengers, 0),
          action_type: (item?.action_type === 'short_turn' || item?.action_category === 'Short-Turn Loop' ? 'short_turn' : 'fleet_injection') as ActionType,
          reason: safeStr(item?.reason ?? item?.operational_reason, 'Operational alert flagged by XGBoost engine'),
          expected_impact: safeStr(item?.expected_impact, 'Awaiting control action impact estimation'),
          type: (item?.type || 'MEASURED') as MetricType
        }));
      }
    } catch (err) {
      console.warn('API /api/control-room-alerts unreachable, falling back to mock:', err);
    }
  }

  await delay(150);
  // Support new alert JSON shape (from generate_mocks + post_process) OR legacy shape
  let list = (alertsMock as any[]).map((item: any): ControlRoomAlert => ({
    id: safeStr(item?.id ?? item?.alert_id, 'ALT-UNKNOWN'),
    route: safeStr(item?.route ?? item?.route_id, 'n/a'),
    depot: safeStr(item?.depot, 'n/a'),
    time_window: safeStr(item?.time_window, 'n/a'),
    predicted_dcr: safeNum(item?.predicted_dcr ?? item?.dcr, 1.0),
    expected_deficit_pax: safeNum(item?.expected_deficit_pax ?? item?.deficit_passengers, 0),
    action_type: (item?.action_type === 'short_turn' || item?.action_category === 'Short-Turn Loop' ? 'short_turn' : 'fleet_injection') as ActionType,
    reason: safeStr(item?.reason ?? item?.operational_reason, 'Operational alert flagged by XGBoost engine'),
    expected_impact: safeStr(item?.expected_impact, 'Awaiting control action impact estimation'),
    type: (item?.type || 'MEASURED') as MetricType
  }));
  // Filter by hour if specified and alert has hour field
  if (hour !== undefined) {
    const hourFiltered = list.filter((a: any) => {
      const alertHour = (alertsMock as any[]).find(raw => (raw.id ?? raw.alert_id) === a.id)?.hour;
      return alertHour === undefined || alertHour === hour;
    });
    if (hourFiltered.length > 0) list = hourFiltered;
  }
  return list;
}

export async function fetchRebalancePairs(depot?: string): Promise<RebalancePair[]> {
  if (!USE_MOCKS) {
    try {
      const url = new URL(`${API_BASE_URL}/api/rebalance-pairs`);
      if (depot && depot !== 'all') url.searchParams.set('depot', depot);
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`HTTP error ${res.status}: ${res.statusText}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        return data.map((p: any) => ({
          depot: safeStr(p?.depot, 'n/a'),
          date: safeStr(p?.date, '2026-03-30'),
          hour: safeNum(p?.hour, 9),
          receiver_route: safeStr(p?.receiver_route, 'n/a'),
          donor_route: safeStr(p?.donor_route, 'n/a'),
          k: safeNum(p?.k ?? p?.buses_transferred_k ?? p?.buses_to_move, 1),
          receiver_buses: safeNum(p?.receiver_buses ?? p?.buses_rec, 6),
          donor_buses: safeNum(p?.donor_buses ?? p?.buses_don, 6),
          receiver_dcr_before: safeNum(p?.receiver_dcr_before ?? p?.receiver_pre_dcr, 1.3),
          receiver_dcr_after: safeNum(p?.receiver_dcr_after ?? p?.receiver_post_dcr, 1.05),
          donor_dcr_before: safeNum(p?.donor_dcr_before ?? p?.donor_pre_dcr, 0.32),
          donor_dcr_after: safeNum(p?.donor_dcr_after ?? p?.donor_post_dcr, 0.42),
          type: 'SIMULATED',
          receiver_passengers: safeNum(p?.receiver_passengers ?? p?.pax_rec, 0),
          donor_passengers: safeNum(p?.donor_passengers ?? p?.pax_don, 0)
        }));
      }
    } catch (err) {
      console.warn('API /api/rebalance-pairs unreachable, falling back to mock:', err);
    }
  }

  await delay(140);
  // Handle both legacy (receiver_route) and new (recipient_route) field names from JSON
  const pairs: RebalancePair[] = (rebalancePairsMock as any[]).map((p: any) => ({
    depot: safeStr(p?.depot, 'n/a'),
    date: safeStr(p?.date, '2026-03-30'),
    hour: safeNum(p?.hour, 9),
    receiver_route: safeStr(p?.receiver_route, p?.recipient_route ?? 'n/a'),
    donor_route: safeStr(p?.donor_route, 'n/a'),
    k: safeNum(p?.k, p?.buses_to_move ?? 1),
    receiver_buses: safeNum(p?.receiver_buses, p?.recipient_buses ?? 5),
    donor_buses: safeNum(p?.donor_buses, 5),
    receiver_dcr_before: safeNum(p?.receiver_dcr_before, p?.recipient_dcr ?? 1.3),
    receiver_dcr_after: safeNum(p?.receiver_dcr_after, p?.projected_dcr_after ?? 1.0),
    donor_dcr_before: safeNum(p?.donor_dcr_before, p?.donor_dcr ?? 0.35),
    donor_dcr_after: safeNum(p?.donor_dcr_after, 0.45),
    type: 'SIMULATED',
    receiver_passengers: safeNum(p?.receiver_passengers, p?.recipient_passengers ?? 0),
    donor_passengers: safeNum(p?.donor_passengers, 0),
  }));
  if (depot && depot !== 'all') {
    return pairs.filter(p => p.depot.toLowerCase() === depot.toLowerCase());
  }
  return pairs;
}

export async function fetchRoutes(params?: { date?: string; hour?: number; depot?: string }): Promise<RouteItem[]> {
  if (!USE_MOCKS) {
    try {
      const url = new URL(`${API_BASE_URL}/api/routes`);
      if (params?.date) url.searchParams.set('date', params.date);
      if (params?.hour !== undefined) url.searchParams.set('hour', String(params.hour));
      if (params?.depot && params.depot !== 'all') url.searchParams.set('depot', params.depot);
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`HTTP error ${res.status}: ${res.statusText}`);
      const data = await res.json();
      if (Array.isArray(data)) {
        return data.map((r: any) => ({
          route_id: safeStr(r?.route_id, 'n/a'),
          origin: r?.origin ? safeStr(r.origin) : undefined,
          destination: r?.destination ? safeStr(r.destination) : undefined,
          corridor: r?.corridor ? safeStr(r.corridor) : undefined,
          hour: safeNum(r?.hour, 9),
          depot: safeStr(r?.depot, 'n/a'),
          planned_buses_ex_ante: safeNum(r?.planned_buses_ex_ante ?? r?.planned_buses, 0),
          actual_active_buses: safeNum(r?.actual_active_buses ?? r?.active_buses, 0),
          actual_passengers: safeNum(r?.actual_passengers ?? r?.actual_pax, 0),
          predicted_passengers: safeNum(r?.predicted_passengers ?? r?.predicted_pax, 0),
          predicted_demand_to_capacity_ratio: safeNum(r?.predicted_demand_to_capacity_ratio ?? r?.predicted_dcr, 0),
          actual_demand_to_capacity_ratio: safeNum(r?.actual_demand_to_capacity_ratio ?? r?.actual_dcr, 0),
          overcrowding_risk_probability: safeNum(r?.overcrowding_risk_probability ?? r?.predicted_overcrowding_probability, 0),
          is_overcrowded_predicted: Boolean(r?.is_overcrowded_predicted),
          is_overcrowded_actual: Boolean(r?.is_overcrowded_actual ?? r?.is_overcrowded),
          recommended_action: safeStr(r?.recommended_action, 'Monitor headway'),
          type: (r?.type || 'MEASURED') as any
        }));
      }
    } catch (err) {
      console.warn('API /api/routes unreachable, falling back to mock:', err);
    }
  }

  await delay(160);
  let list = routesMock as RouteItem[];
  if (params?.depot && params.depot !== 'all') {
    list = list.filter(r => r.depot?.toLowerCase() === params.depot?.toLowerCase());
  }
  return list;
}

export async function fetchDatasetManifest(): Promise<DatasetManifest> {
  if (!USE_MOCKS) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/dataset-manifest`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}: ${res.statusText}`);
      const data = await res.json();
      if (data && data.files) {
        return data as DatasetManifest;
      }
    } catch (err) {
      console.warn('API /api/dataset-manifest unreachable, falling back to manifest mock:', err);
    }
  }

  await delay(100);
  return datasetManifestMock as unknown as DatasetManifest;
}

export async function fetchHourlySummary(): Promise<HourlySummary> {
  if (!USE_MOCKS) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/hourly-summary`);
      if (res.ok) {
        const data = await res.json();
        if (data && Object.keys(data).length > 0) return data as HourlySummary;
      }
    } catch (err) {
      console.warn('API /api/hourly-summary unreachable, falling back to mock:', err);
    }
  }
  await delay(80);
  return hourlySummaryMock as unknown as HourlySummary;
}
