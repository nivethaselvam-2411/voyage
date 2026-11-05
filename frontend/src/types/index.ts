export type MetricType = 'MEASURED' | 'SIMULATED' | 'PREDICTED';

export interface BaseKpi {
  value: number;
  type: MetricType;
  definition: string;
  unit?: string;
}

export interface WideNetKpi {
  recall: number;
  precision: number;
  type: MetricType;
  definition: string;
}

export interface PriorityQueueKpi {
  precision: number;
  hits: number;
  total: number;
  cap_per_day: number;
  type: MetricType;
  definition: string;
}

export interface RebalancingKpi {
  operations: number;
  buses_moved: number;
  share_reaching_dcr_1: number;
  receiver_mean_dcr_before: number;
  receiver_mean_dcr_after: number;
  type: 'SIMULATED';
  definition: string;
}

export interface KpisResponse {
  mae_reduction_pct: BaseKpi;
  wape: BaseKpi;
  r2: BaseKpi;
  roc_auc: BaseKpi;
  pr_auc: BaseKpi;
  wide_net: WideNetKpi;
  priority_queue: PriorityQueueKpi;
  anomalies_flagged: BaseKpi;
  rebalancing: RebalancingKpi;
}

export type ActionType = 'fleet_injection' | 'short_turn';

export interface ControlRoomAlert {
  id: string;
  route: string;
  depot: string;
  time_window: string;
  predicted_dcr: number;
  expected_deficit_pax: number;
  action_type: ActionType;
  reason: string;
  expected_impact: string;
  type?: MetricType;
}

export interface RebalancePair {
  depot: string;
  date: string;
  hour: number;
  receiver_route: string;
  donor_route: string;
  k: number;
  receiver_buses: number;
  donor_buses: number;
  receiver_dcr_before: number;
  receiver_dcr_after: number;
  donor_dcr_before: number;
  donor_dcr_after: number;
  type: 'SIMULATED';
  receiver_passengers?: number;
  donor_passengers?: number;
}

export interface RouteItem {
  route_id: string;
  origin?: string;
  destination?: string;
  corridor?: string;
  hour: number;
  planned_buses_ex_ante: number;
  actual_active_buses: number;
  actual_passengers: number;
  predicted_passengers: number;
  predicted_demand_to_capacity_ratio: number;
  actual_demand_to_capacity_ratio: number;
  overcrowding_risk_probability: number;
  is_overcrowded_predicted: boolean;
  is_overcrowded_actual: boolean;
  recommended_action: string;
  depot?: string;
  type?: MetricType;
}

export type DcrStatus = 'surplus' | 'balanced' | 'near-capacity' | 'over-capacity';

/** Per-hour aggregate stats across all routes — from hourly-summary.json */
export interface HourlySummaryEntry {
  hour: number;
  total_routes: number;
  overcrowded_routes: number;
  critical_routes: number;
  avg_dcr: number;
  total_boardings: number;
}

export type HourlySummary = Record<string, HourlySummaryEntry>;

export interface DatasetFile {
  name: string;
  description: string;
  size: string;
  records: string;
  format: string;
  path: string;
}

export interface DatasetDepot {
  name: string;
  code?: string;
  primary_routes?: string[];
  buses_estimated?: number;
  // New fields from generated manifest
  routes?: number;
  sample_routes?: string[];
}

export interface DatasetStop {
  zone: string;
  name: string;
  lat: number;
  lng?: number;  // old field name
  lon?: number;  // new field name from generate_mocks.py
}

export interface DatasetTicketSample {
  ticket_no: string;
  date: string;
  time: string;
  depot: string;
  fleet_no: string;
  route: string;
  source: string;
  destination: string;
  passenger_count: number;
  ticket_type: string;
  total_ticket_amount: string;
  waybill_no: string;
}

export interface DatasetManifest {
  // Legacy fields (old hand-crafted manifest)
  theme?: string;
  hackathon?: string;
  problem_statement?: string;
  source_authority?: string;
  // New generated manifest fields
  generated_at?: string;
  etm_days?: number[];
  total_tickets_sampled?: number;
  total_passengers_sampled?: number;
  total_routes?: number;
  total_depots?: number;
  total_stops?: number;
  women_ticket_percent?: number;
  files: DatasetFile[];
  summary?: {
    etm_days?: number;
    etm_period?: string;
    total_routes?: number;
    total_stops?: number;
    total_depots?: number;
    active_buses?: number;
    daily_ridership?: string;
    women_free_ticket_share?: string;
    multimodal_layers?: string[];
  };
  depots: DatasetDepot[];
  // Legacy field names
  sample_stops?: DatasetStop[];
  sample_tickets?: DatasetTicketSample[];
  // New field names from generated manifest
  stops?: DatasetStop[];
  telemetry_samples?: DatasetTicketSample[];
}

