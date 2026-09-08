import { useEffect, useState } from 'react';
import { ExperimentPayload, Health, Research, request } from './api';
import { Market } from './Market';

const pages = ['Dashboard', 'Market', 'Paper Trades', 'Statistics', 'Research Lab', 'System'] as const;
type Page = typeof pages[number];

export function App() {
  const [health, setHealth] = useState<Health | null>();
  const [research, setResearch] = useState<Research | null>(null);
  const [experiments, setExperiments] = useState<ExperimentPayload | null>(null);
  const [page, setPage] = useState<Page>('Dashboard');
  useEffect(() => {
    request<Health>('/api/v1/system/health').then(setHealth).catch(() => setHealth(null));
    request<Research>('/api/v1/research/status').then(setResearch).catch(() => setResearch(null));
    request<ExperimentPayload>('/api/v1/research/experiments').then(setExperiments).catch(() => setExperiments(null));
  }, []);
  return <><header><b>TRADING BOT</b><span>PAPER ONLY</span></header><nav>{pages.map(item => <button key={item} onClick={() => setPage(item)}>{item}</button>)}</nav><main><h1>{page}</h1>
    {page === 'Dashboard' && <><div className="card">Backend: {health === undefined ? 'checking' : health?.health ?? 'unavailable'} · {health?.status ?? 'unknown'}</div><button disabled>ANALYZE MARKET</button><h2>No approved strategy</h2><p>No market analysis available yet.</p></>}
    {page === 'Market' && <Market available={health?.development_data_available === true} />}
    {page === 'Paper Trades' && <div className="card">No paper trades exist.</div>}
    {page === 'Statistics' && <div className="card">No approved strategy performance statistics exist.</div>}
    {page === 'Research Lab' && <><div className="card">Champion: {research?.champion ?? 'NONE'}<br />Experiments completed: {research?.experiments_completed ?? 0}<br />Evidence stage: {experiments?.evidence_stage ?? 'NONE'}<br />Backtest substrate: {research?.backtest_substrate ?? 'unavailable'}<br />Models: {research?.engine_version ?? 'unavailable'} / {research?.execution_model_version ?? 'unavailable'} / {research?.cost_model_version ?? 'unavailable'}<br />Synthetic validation: {research?.synthetic_validation ?? 'unavailable'} — infrastructure check only, not trading evidence.</div><p className="banner">DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE</p><div className="grid">{experiments?.experiments.map(item => <article className="card" key={item.experiment_id}><b>{item.experiment_id}</b><br />{item.classification}<br />{item.primary_metric}: {item.primary_result ?? 'N/A'}<br />Trades: {item.trade_count ?? 'N/A'} · {item.validation_status}</article>)}</div><p>Latest: {experiments?.latest_checkpoint ?? 'unavailable'} · Next: {experiments?.next_checkpoint ?? 'unavailable'}</p></>}
    {page === 'System' && <div className="card">Backend health: {health?.health ?? 'unavailable'}<br />Project: {health?.project_phase ?? 'unavailable'} / {health?.status ?? 'unavailable'}<br />Development data: {health?.development_data_available ? 'installed' : 'not installed'}<br />Real money authorized: {health?.real_money_authorized ? 'yes' : 'no'}</div>}
  </main></>;
}
