// System G1 synthetic replay API. The backend is authoritative for every record, score and
// statistic; the UI only displays what the causal cursor view returns.

export type ReplayCandle = { open_time: string; available_at: string; open: number; high: number; low: number; close: number; quality: string };
export type Actionability = { setup_ready: boolean; data_ready: boolean; execution_ready: boolean; risk_eligible: boolean; occupancy_free: boolean; final_decision: string; blockers: string[] };
export type ReplayPrediction = {
  prediction_id: string; issue_time: string; available_at: string; target_end: string;
  predicted_direction: 'UP' | 'DOWN' | 'NEUTRAL' | 'UNAVAILABLE'; directional_bias: string;
  probability_up: number | null; probability_down: number | null; probability_status: string;
  mean_terminal_return: number | null; median_terminal_return: number | null;
  lower_quantile_return: number | null; upper_quantile_return: number | null; quantile_levels: number[];
  standardized_strength: number | null; prior_risk_scale: number | null; support_status: string;
  conviction: 'LOW' | 'MEDIUM' | 'HIGH'; playbook_context: string[]; unavailable_reason: string | null;
  supporting_reasons: string[]; opposing_reasons: string[];
};
export type ReplayRealization = {
  realization_id: string; prediction_id: string; resolution_time: string; available_at: string;
  resolution_validity: string; realized_terminal_return: number | null; realized_direction: string | null;
  direction_correct: boolean | null; magnitude_error: number | null;
};
export type ReplayDecision = {
  decision_id: string; prediction_id: string; decision_time: string; available_at: string;
  action: 'LONG' | 'SHORT' | 'NO_TRADE'; playbook_id: string | null; conviction: string;
  actionability: Actionability; blockers: string[]; trade_plan_id: string | null;
};
export type ReplayTradePlan = { trade_plan_id: string; side: 'LONG' | 'SHORT'; playbook_id: string; reference_price: string; stop_price: string; objective_price: string; max_hold_minutes: number; planned_risk_amount: string };
export type ReplayFill = { event_id: string; trade_plan_id: string; kind: 'ENTRY' | 'EXIT' | 'FUNDING' | 'ENTRY_REJECTED'; side: 'LONG' | 'SHORT'; event_time: string; available_at: string; raw_price: string | null; reason: string; funding_amount: string };
export type ReplaySignal = { signal_id: string; family: string; name: string; timeframe: string; state: string; quality: string; role: string; available_at: string };
export type ReplayCycle = { method_status: string; decision_role: string; timing_qualifier: string; scales: { nominal_scale: string; input_resolution: string; warmup: string; ready: boolean; quality_label: string; dominant_period_minutes: number | null; slope_direction: string }[] };
export type ReplayLedger = { equity: string; drawdown_fraction: string; day_loss_fraction: string; open_side: string | null; open_quantity: string; unrealized_pnl: string; daily_entry_stop: boolean; run_entry_stop: boolean };
export type ReplayStats = {
  label: string; predictions_issued: number; predictions_unavailable: number; matured: number; matured_valid: number;
  matured_unscorable: number; directional_matured: number; directional_correct: number;
  directional_hit_rate: number | null; directional_coverage: number | null; mean_absolute_return_error: number | null;
  interval_coverage: number | null; closed_trades: number; scorable_trades: number; long_trades: number;
  short_trades: number; winning_trades: number; net_pnl: string;
};
export type ReplayView = {
  mode: 'CAUSAL_CURSOR'; label: string; session_id: string; run_id: string;
  status: 'READY' | 'RUNNING' | 'PAUSED' | 'COMPLETE'; speed: number; speeds: number[];
  cursor: string; dataset_start: string; dataset_end: string;
  candles: ReplayCandle[]; predictions: ReplayPrediction[]; realizations: ReplayRealization[];
  decisions: ReplayDecision[]; trade_plans: ReplayTradePlan[]; fills: ReplayFill[];
  current: { signals: ReplaySignal[]; cycle: ReplayCycle | null; prediction: ReplayPrediction | null; decision: ReplayDecision | null; ledger: ReplayLedger };
  stats: ReplayStats; production_action: 'NO_TRADE'; validated_strategy: null;
};
export type ReplayRun = { manifest: { run_id: string; evidence_class: string; dataset_start: string; dataset_end: string }; fixture_id: string; label: string };

async function post<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? `API ${response.status}`);
  return payload as T;
}

export async function readReplayRuns(): Promise<ReplayRun[]> {
  const response = await fetch('/api/v1/g1/runs');
  if (!response.ok) throw new Error(`API ${response.status}`);
  return ((await response.json()) as { runs: ReplayRun[] }).runs;
}
export const createReplaySession = (run_id: string) => post<ReplayView>('/api/v1/g1/replay/sessions', { run_id });
export const controlReplay = (session: string, action: 'start' | 'pause' | 'step' | 'speed', speed?: number) =>
  post<ReplayView>(`/api/v1/g1/replay/sessions/${encodeURIComponent(session)}/control`, speed === undefined ? { action } : { action, speed });
export const tickReplay = (session: string, wall_seconds: number) =>
  post<ReplayView>(`/api/v1/g1/replay/sessions/${encodeURIComponent(session)}/tick`, { wall_seconds });
