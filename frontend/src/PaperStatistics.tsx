import { useState } from 'react';
import { PaperStatistics as Stats, readPaperStatistics } from './api';

const r = (value: number | null) => value === null ? '—' : value.toFixed(4);
const pct = (value: number | null) => value === null ? '—' : `${(value * 100).toFixed(1)}%`;

export function PaperStatistics() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    try {
      setStats(await readPaperStatistics());
    } catch {
      setStats(null);
    } finally {
      setBusy(false);
    }
  }

  return <section className="card" aria-label="Paper statistics">
    <h2>Paper statistics</h2>
    <p className="banner">FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE</p>
    <p>NOT CHAMPION · NOT LIVE TRADING</p>
    <button onClick={load} disabled={busy}>LOAD STATISTICS</button>
    {stats === null && <p>No statistics loaded. Click LOAD STATISTICS.</p>}
    {stats !== null && <>
      <p>Total paper trades: {stats.total_paper_trades} · Pending entry: {stats.pending_entry} · Open: {stats.open} · Closed: {stats.closed} · Invalidated: {stats.invalidated}</p>
      <p>Wins: {stats.wins} · Losses: {stats.losses} · Expiries: {stats.expiries} · Realized trades: {stats.realized_trades}</p>
      {stats.empty
        ? <p>{stats.empty_detail ?? 'No realized paper results yet.'}</p>
        : <>
          <p>Win rate: {pct(stats.win_rate)}</p>
          <p>Mean realized R: {r(stats.mean_realized_r)}</p>
          <p>Cumulative realized R: {r(stats.cumulative_realized_r)}</p>
          <p>Expectancy R/trade: {r(stats.expectancy_r_per_trade)}</p>
          <p>Maximum realized drawdown R: {r(stats.max_drawdown_r)}</p>
        </>}
      <p>Pending and open trades are excluded from realized results. Champion: {stats.champion_status} · Real money: no</p>
    </>}
  </section>;
}
