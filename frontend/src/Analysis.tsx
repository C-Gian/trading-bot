import { useState } from 'react';
import { Analysis, analyseMarket } from './api';

const price = (value: number) => value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function AnalyzeMarket() {
  const [result, setResult] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  async function run() {
    setBusy(true);
    setFailed(false);
    try {
      setResult(await analyseMarket());
    } catch {
      setResult(null);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }
  return <section className="card" aria-label="Analyze Market">
    <button onClick={run} disabled={busy}>ANALYZE MARKET</button>
    <p className="banner">EXPERIMENTAL PAPER RESEARCH — NOT AN APPROVED LIVE STRATEGY</p>
    <p>NOT CHAMPION / NOT LIVE TRADING</p>
    {failed && <p>Analysis unavailable. No trade plan is implied.</p>}
    {!result && !failed && <p>No analysis has been run. Analysis runs only when you request it.</p>}
    {result && <>
      <p>{result.symbol} · PAPER RESEARCH · {result.variant} candidate · {result.research_status}</p>
      <p>Strategy: {result.strategy_version} · Champion: {result.champion_status}</p>
      <p>Analysis timestamp: {result.analysis_time}</p>
      <p>Signal time: {result.signal_time ?? 'none'} · Market data: {result.data_status}</p>
      {result.decision === 'NO_TRADE' && <p><b>NO_TRADE</b>{result.data_status === 'OK' ? '' : ` — ${result.data_detail}`}</p>}
      {result.plan && <>
        <p><b>LONG (paper only)</b></p>
        <p>Reference: {price(result.plan.reference_price)}</p>
        <p>Entry: {result.plan.entry_rule} — {result.plan.entry_semantics}</p>
        <p>Stop: {price(result.plan.stop_price)} ({(result.plan.stop_fraction * 100).toFixed(0)}%)</p>
        <p>Target: {price(result.plan.target_price)} ({(result.plan.target_fraction * 100).toFixed(0)}%)</p>
        <p>Expiry: {result.plan.expiry_time} ({result.plan.max_hold_minutes} minutes maximum hold)</p>
      </>}
      <p>Paper trade persisted: no · Order placed: no · Real money: no</p>
    </>}
  </section>;
}
