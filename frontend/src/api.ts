export type Coverage={start:string;end:string};
export type Health={health:string;status:string;project_phase:string;development_data_available:boolean;development_coverage:Coverage;real_money_authorized:boolean};
export type FamilyBudget={family_id:string;experiments_consumed:number;experiments_limit:number;trials_consumed:number;trials_limit:number};
export type Research={champion:string;experiments_completed:number;evidence:string;backtest_substrate:string;engine_version:string;execution_model_version:string;cost_model_version:string;synthetic_validation:string;search_memory?:{version:string;status:string;families_tracked:number}|null;adaptive_search?:{material_economic_hypotheses:number;configuration_variants:number;profile_trials:number;adaptive_decisions:number;result_dependent_forks:number;supervised_model_fits?:number}|null;selected_family?:{name:string;terminal_classification:string}|null;wp005_integrity?:{status:string;source_provenance_classification:string;independent_reconciliation:string;integrity_replay_profiles:number;matched_control_classification:string}|null;remote_ci?:{policy:string;work_packages:Record<string,{status:string;head:string;run_id:number;evidence:string}>}|null;latest_family?:{name:string;root_family:string;primary_experiment_id:string;novelty_classification:string;terminal_classification:string}|null;order_flow_substrate?:{version:string;status:string;content_hash:string;eligible_1h_buckets:number;eligible_4h_buckets:number;oracle_reconciliation:string}|null;artifact_storage?:{version:string;status:string;trial_artifact_format:string;historical_evidence_rewritten:boolean}|null;supervised_challenger?:{version:string;status:string;primary:string;secondary:string;model_fits:number;terminal_classification:string;leakage_audit:string;model_reconciliation:string}|null;exogenous_foundation?:{contract_version:string;status:string;gdelt:{version:string;status:string;hourly_rows:number};alfred:{version:string;status:string;series:number};combined_context:{version:string;status:string;rows:number};asof_reconciliation:string;adaptive_design:string}|null;sealed_evaluation?:{version:string;status:string;dataset_state:string;authorized_btc_queries:number;consumed_btc_queries:number;isolation:string;seal_eligible_candidates:number;candidates_assessed:number}|null;family_budgets?:FamilyBudget[]};
export type ExperimentSummary={experiment_id:string;classification:string;primary_metric:string;primary_result:number|null;trade_count:number|null;validation_status:string;evidence_window?:string};
export type ExperimentPayload={evidence_stage:string;latest_checkpoint:string;next_checkpoint:string;experiments:ExperimentSummary[]};
export type Candle={open_time:string;open:number;high:number;low:number;close:number;complete?:boolean};
export type CandlePayload={classification:string;coverage:Coverage;candles:Candle[]};
export async function request<T>(url:string):Promise<T>{const response=await fetch(url);if(!response.ok)throw new Error(`API ${response.status}`);return response.json() as Promise<T>}
export type AnalysisFeatures={breakout:boolean;persistent_up:boolean;participation:boolean;signed_efficiency:number|null;relative_volume:number|null};
export type AnalysisPlan={direction:string;entry_rule:string;entry_semantics:string;execution_model:string;exit_policy:string;reference_price:number;stop_price:number;target_price:number;stop_fraction:number;target_fraction:number;max_hold_minutes:number;expiry_time:string;leverage:boolean;short:boolean;order_placed:boolean};
export type Analysis={analysis_version:string;classification:string;symbol:string;strategy_version:string;variant:string;feature_version:string;prospective_features_version?:string;analysis_id?:string;features?:AnalysisFeatures;research_status:string;champion_status:string;analysis_time:string;signal_time:string|null;data_status:string;data_detail:string;decision:'NO_TRADE'|'LONG';plan:AnalysisPlan|null;reference_price?:number;paper_trade_persisted:boolean;real_money:boolean;paper_trades_completed?:number;real_money_authorized?:boolean;review_bundle:string};
export async function analyseMarket():Promise<Analysis>{const response=await fetch('/api/v1/product/analysis',{method:'POST'});if(!response.ok)throw new Error(`API ${response.status}`);return response.json() as Promise<Analysis>}
export type PaperTrade={trade_id:string;evidence_version:string;evidence_stage:string;initiation_mode:string;analysis_id:string;strategy_version:string;variant:string;research_status:string;champion_status:string;symbol:string;direction:string;status:'PERSISTING_INTENT'|'PENDING_ENTRY'|'OPEN'|'CLOSED_TARGET'|'CLOSED_STOP'|'CLOSED_EXPIRY'|'INVALIDATED'|'INVALIDATED_ENTRY_UNAVAILABLE'|'INVALIDATED_INTENT_PERSISTENCE';created_at:string;analysis_completed_at:string;intent_persisted_at:string|null;signal_timestamp:string;signal_time:string;signal_age_seconds:number|null;entry_not_before:string|null;entry_execution:string;entry_minute:string|null;ambiguous_fill_policy:string;execution_model_version:string;reference_price:number|null;stop_price:number|null;target_price:number|null;stop_fraction:number;target_fraction:number;max_hold_minutes:number;expiry_time:string|null;entry_time:string|null;entry_price:number|null;exit_time:string|null;exit_price:number|null;exit_reason:string|null;net_r:number|null;holding_minutes:number|null;resolution_detail:string;last_update_time:string;real_money:boolean};
export type PaperListing={evidence_version:string;evidence_stage:string;initiation_mode:string;contract:string;research_status:string;champion_status:string;strategy_version:string;execution_model_version:string;entry_timeout_opportunities:number;max_hold_minutes:number;statuses:string[];active:PaperTrade[];recent:PaperTrade[];recorded:number;paper_entry_status:string;paper_entry_block_reason:string;real_money:boolean};
export type PaperLifecycle={evidence_version:string;updated:number;trades:PaperTrade[];errors:{trade_id:string;error:string}[];real_money:boolean};
async function send<T>(url:string):Promise<T>{const response=await fetch(url,{method:'POST'});const body=await response.json().catch(()=>null);if(!response.ok)throw new Error(body?.detail??`API ${response.status}`);return body as T}
export function createPaperTrade(){return send<{analysis_id:string;trade:PaperTrade;real_money:boolean}>('/api/v1/product/paper-trades')}
export function advancePaperTrades(){return send<PaperLifecycle>('/api/v1/product/paper-trades/lifecycle')}
export function readPaperTrades(){return request<PaperListing>('/api/v1/product/paper-trades')}
export type LiveCandle={open_time:string;open:number;high:number;low:number;close:number};
export type LiveMarket={classification:string;symbol:string;interval:string;status:string;detail:string;candles:LiveCandle[]};
export type PaperStatistics={statistics_version:string;evidence_version:string;evidence_stage:string;label:string;development_backtest_metrics_included:boolean;total_paper_trades:number;pending_entry:number;open:number;active:number;closed:number;invalidated:number;closed_target:number;closed_stop:number;expiries:number;realized_trades:number;wins:number;losses:number;breakeven:number;win_rate:number|null;mean_realized_r:number|null;cumulative_realized_r:number|null;expectancy_r_per_trade:number|null;max_drawdown_r:number|null;best_realized_r:number|null;worst_realized_r:number|null;empty:boolean;empty_detail:string|null;champion_status:string;real_money:boolean};
export function readLiveMarket(){return request<LiveMarket>('/api/v1/product/market/recent')}
export function readPaperStatistics(){return request<PaperStatistics>('/api/v1/product/paper-trades/statistics')}

export type ShadowTrade={trade_id:string;status:string;entry_time:string|null;entry_price:number|null;stop_price:number|null;target_price:number|null;expiry_time:string|null;resolution_detail:string;real_money:boolean};
export type ProspectiveObserver={status:'ACTIVE'|'STOPPED'|'DEGRADED';automatic_collection?:string;label:string;observer_version:string;evidence_version:string;evidence_stage:string;initiation_mode:string;strategy_version:string;feature_version?:string;research_status?:string;champion_status?:string;max_decision_latency_seconds?:number;first_scientific_review_completed_trades?:number;last_evaluated_hourly_boundary:string|null;last_heartbeat:string|null;next_expected_boundary:string|null;last_successful_market_fetch?:string|null;current_error?:string|null;missed_prospective_decisions:number|null;raw_prospective_long_signals:number|null;suppressed_long_signals:number|null;open_shadow_trade:ShadowTrade|null;completed_shadow_trades:number|null;audit_chain_version?:string;audit_events?:number|null;evidence_integrity?:'VALID'|'INVALID';supersedes?:string;supersedes_status?:string;build_provenance_verified?:boolean|null;build_provenance_sha256?:string|null;observer_lease_held?:boolean|null;manual_evidence_included:boolean;order_placement:boolean;credentials:boolean;real_money:boolean};
export function readProspectiveObserver(){return request<ProspectiveObserver>('/api/v1/product/prospective-observer')}

export type RunnerStage = 'READY'|'PREPARING_DATA'|'VALIDATING_INPUTS'|'LOAD_DATA'|'BUILD_FEATURES'|'BUILD_LABELS'|'FIT'|'PREDICT'|'FOLD_2020'|'FOLD_2021'|'FOLD_2022'|'FOLD_2023'|'FOLD_2024'|'COST_STRESS'|'PROFILES'|'RECONCILIATION'|'FINALIZING'|'COMPLETED'|'FAILED'|'INTERRUPTED';
export type ResearchRunStatus = 'QUEUED'|'RUNNING'|'COMPLETED'|'FAILED';
export type ResearchRunnerCandidate = {
  candidate_id:string; display_name:string; purpose:string; run_type:string; status:string;
  runnable:boolean;
  expected_stages:string[]; required_local_datasets:string[]; scientific_warning:string;
  scientific_evidence_type:string; execution_counts_as_new_evidence:boolean; arbitrary_execution:boolean;
  runtime_version:string;
  preregistration_frozen:boolean; preregistration_paths:string[];
  required_data:{ready:boolean;files:Record<string,boolean>}; fixed_runner_adapter:string;
};
export type ResearchResult = {
  candidate_id:string; run_id:string; status:ResearchRunStatus; classification:string; verdict:string;
  default_expectancy_r:number|null; zero_cost_expectancy_r:number|null; double_cost_expectancy_r:number|null;
  delay_expectancy_r:number|null; trade_count:number|null; nonnegative_folds:number|null; fold_count:number|null;
  minimum_fold_trades:number|null; control_default_expectancy_r:number|null; primary_minus_control_r:number|null;
  oos_correlation:number|null; reconciliation_status:string; elapsed_seconds:number|null;
  scientific_evidence_type:string; code_head?:string|null; dataset_identities?:Record<string,string>;
  runtime_artifact_hashes?:Record<string,string>; runtime_version?:string;
  stage_timings?:{record_version:number;runtime_version:string;stage_order:string[];duration_seconds:Record<string,number>;total_seconds:number};
};
export type ResearchRun = {
  run_id:string; candidate_id:string; started_at:string|null; finished_at:string|null;
  status:ResearchRunStatus; stage:RunnerStage; progress:number; detail?:string|null;
  error?:string|null; result?:ResearchResult|null; review_bundle?:string|null; elapsed_seconds:number;
  progress_fraction?:number|null; completed_work_units?:number|null; total_work_units?:number|null;
  unit_label?:string|null; last_update_at?:string|null; last_heartbeat_at?:string|null;
  heartbeat_age_seconds?:number|null;
  runtime_version?:string;
};
export type ResearchRunnerPayload = {
  runner_status:'IDLE'|'BUSY'; arbitrary_execution:boolean; maximum_active_runs:number;
  candidates:ResearchRunnerCandidate[]; current_or_last_run:ResearchRun|null;
};
export function readResearchRunner(){return request<ResearchRunnerPayload>('/api/v1/research/runner')}
export async function startResearchRun(candidate_id:string){
  const response=await fetch('/api/v1/research/runner/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({candidate_id})});
  const body=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(body?.detail??`API ${response.status}`);
  return body as ResearchRun;
}
export function readResearchRun(run_id:string){return request<ResearchRun>(`/api/v1/research/runner/runs/${encodeURIComponent(run_id)}`)}
