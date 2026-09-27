// G2-01 engineering replay API. The backend G2 core is authoritative for every state, forecast,
// decision, fill and accounting value; the UI only displays what the causal cursor returns and
// never derives an action, margin or outcome itself.

export type G2Run = {
  run_key: string; label: string; evidence_class: string; evidence_label: string; description: string;
  dataset_start: string; dataset_end: string; computed: boolean; run_id: string | null; review_available: boolean;
};
export type G2Utility = {
  side: string; fit_id: string | null; predicted_utility: number | null; residual_q10: number | null;
  residual_count: number; residual_span_days: number | null; evidence_status: string; prudential_margin: number | null;
};
export type G2Decision = {
  decision_id: string; prediction_id: string; decision_time: string; available_at: string;
  action: 'LONG' | 'SHORT' | 'NO_TRADE'; policy_selection: string; reason_codes: string[];
  long_utility: G2Utility; short_utility: G2Utility; forecast_direction: string; position_state: string;
  risk: { equity: number; peak_equity: number; drawdown: number; drawdown_stop_active: boolean; position_open: boolean; open_trade_id: string | null };
  stop_distance: number | null; reference_price: number | null; intended_entry_time: string | null; intended_expiry_time: string | null;
  cycle_role: string;
};
export type G2Prediction = {
  prediction_id: string; decision_time: string; target_time: string; fit_id: string | null;
  raw_terms: (number | null)[]; scaled_terms: (number | null)[]; contributions: (number | null)[];
  intercept: number | null; mu_z: number | null; mean_return: number | null; median_return: number | null;
  q10: number | null; q50: number | null; q90: number | null; p_positive: number | null; sigma_4h: number | null;
  calibration_status: string; residual_source: string; residual_count: number; view_strength_z: number | null;
  strength_label: string | null; direction: string; evidence_status: [string, string | number | null][];
  reason_codes: string[]; max_source_time: string | null; training_start: string | null; training_end: string | null;
  latest_label_time: string | null;
};
export type G2State = {
  state_id: string; decision_time: string; max_source_time: string | null; price: number | null;
  raw_terms: (number | null)[]; term_status: string[]; sigma_4h: number | null; atr14_1h: number | null;
  price_response: number | null; status: string; daily: [string, string | number | null][]; weekly: [string, string | number | null][];
};
export type G2CycleScale = {
  nominal_scale: string; input_resolution: string; warmup_ready: boolean; quality_label: string;
  dominant_period_minutes: number | null; phase_degrees: number | null; projection_amplitude: number | null;
  period_stability: number | null; slope_direction: string; last_turn_kind: string | null; reason_code: string | null;
};
export type G2Cycle = { runtime_role: string; forecast_coefficients: number; policy_coefficients: number; veto_authority: string; reason_codes: string[]; scales: G2CycleScale[] };
export type G2Fill = {
  fill_id: string; trade_id: string; intent_id: string; kind: 'ENTRY' | 'EXIT' | 'ENTRY_REJECTED'; side: string;
  event_time: string; available_at: string; raw_price: number | null; accounting_price: number | null;
  quantity: number; friction_cost: number; reason_codes: string[];
};
export type G2Risk = { kind: string; equity: number; peak_equity: number; drawdown: number; drawdown_stop_active: boolean; position_open: boolean };
export type G2Current = {
  state: G2State | null; prediction: G2Prediction | null; decision: G2Decision | null; cycle: G2Cycle | null;
  risk: G2Risk | null; open_position: G2Fill | null; fit: { head: string; status: string; fit_boundary: string; rows: number }[];
};
export type G2View = {
  mode: 'CAUSAL_CURSOR'; session_id: string; status: 'READY' | 'RUNNING' | 'PAUSED' | 'COMPLETE';
  speed: number; speeds: number[]; step_units: string[]; label: string; run_key: string; run_id: string;
  evidence_class: string; cursor: string; dataset_start: string; dataset_end: string;
  candles: { open_time: string; available_at: string; open: number; high: number; low: number; close: number; complete: boolean }[];
  prediction_markers: { prediction_id: string; decision_time: string; direction: string; median_return: number | null; status: string }[];
  decision_markers: { decision_id: string; decision_time: string; action: string; policy_selection: string; reason_codes: string[] }[];
  fills: G2Fill[]; closed_trades: { trade_id: string; side: string; exit_kind: string; realized_net_r: number; violation_flags: string[] }[];
  current: G2Current; visible_counts: Record<string, number>;
  production_action: 'NO_TRADE'; validated_strategy: null; cycle_role: string;
};
export type G2Latest = {
  mode: string; label: string; run_key: string; run_id: string; evidence_class: string; cursor: string;
  current: G2Current; production_action: 'NO_TRADE'; validated_strategy: null;
};
export type G2Lineage = Record<string, unknown>;

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? `API ${response.status}`);
  return payload as T;
}
const post = <T,>(url: string, body: unknown) =>
  call<T>(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const readG2Runs = async () => (await call<{ runs?: G2Run[] }>('/api/v1/g2/runs')).runs ?? [];
export const readG2Latest = (key: string) => call<G2Latest>(`/api/v1/g2/runs/${encodeURIComponent(key)}/latest`);
export const createG2Session = (run_key: string) => post<G2View>('/api/v1/g2/replay/sessions', { run_key });
export const controlG2 = (session: string, action: 'start' | 'pause' | 'step' | 'speed', extra: { speed?: number; unit?: string } = {}) =>
  post<G2View>(`/api/v1/g2/replay/sessions/${encodeURIComponent(session)}/control`, { action, ...extra });
export const tickG2 = (session: string, wall_seconds: number) =>
  post<G2View>(`/api/v1/g2/replay/sessions/${encodeURIComponent(session)}/tick`, { wall_seconds });
export const readG2Lineage = (session: string, decision: string) =>
  call<G2Lineage>(`/api/v1/g2/replay/sessions/${encodeURIComponent(session)}/lineage/${encodeURIComponent(decision)}`);
