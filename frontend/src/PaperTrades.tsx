import { useState } from 'react';
import { PaperListing, PaperTrade, advancePaperTrades, createPaperTrade, readPaperTrades } from './api';

const ACTIVE = ['PENDING_ENTRY', 'OPEN'];
const price = (value: number | null) => value === null ? '—' : value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function Trade({ trade }: { trade: PaperTrade }) {
  const closed = !ACTIVE.includes(trade.status);
  return <article className="card" aria-label={`Paper trade ${trade.trade_id}`}>
    <b>{trade.status}</b> · {trade.symbol} {trade.direction}
    <p>Strategy: {trade.strategy_version} ({trade.variant}) · {trade.research_status}</p>
    <p>Signal time: {trade.signal_time}</p>
    <p>Entry: {trade.entry_time ?? 'pending'} @ {price(trade.entry_price)} ({trade.entry_execution})</p>
    <p>Stop: {price(trade.stop_price)} · Target: {price(trade.target_price)}</p>
    <p>Expiry: {trade.expiry_time} ({trade.max_hold_minutes} minutes maximum hold)</p>
    {closed && <p>Exit: {trade.exit_reason ?? '—'} at {trade.exit_time ?? '—'} @ {price(trade.exit_price)}</p>}
    {closed && <p>Realized R: {trade.net_r === null ? '—' : trade.net_r.toFixed(6)}</p>}
    <p>{trade.resolution_detail}</p>
    <p>FUTURE PAPER EVIDENCE · {trade.evidence_version} · NOT CHAMPION · NOT LIVE TRADING</p>
  </article>;
}

export function PaperTrades() {
  const [listing, setListing] = useState<PaperListing | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>, done: string) {
    setBusy(true);
    setNotice(null);
    try {
      await action();
      setListing(await readPaperTrades());
      setNotice(done);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Request failed.');
    } finally {
      setBusy(false);
    }
  }

  const active = listing?.active ?? [];
  const history = [...(listing?.recent ?? [])].reverse();
  return <section className="card" aria-label="Paper trades">
    <h2>Paper trades</h2>
    <p className="banner">FUTURE PAPER EVIDENCE · PAPER RESEARCH · NOT CHAMPION · NOT LIVE TRADING</p>
    <div>
      <button onClick={() => run(createPaperTrade, 'Paper trade created.')} disabled={busy}>CREATE PAPER TRADE</button>
      <button onClick={() => run(advancePaperTrades, 'Lifecycle updated.')} disabled={busy}>UPDATE PAPER TRADE</button>
      <button onClick={() => run(async () => undefined, 'Loaded.')} disabled={busy}>REFRESH</button>
    </div>
    {notice && <p role="status">{notice}</p>}
    <h3>Active</h3>
    {active.length === 0
      ? <p>No active paper trade.</p>
      : active.map(trade => <Trade key={trade.trade_id} trade={trade} />)}
    <h3>Recent history</h3>
    {listing === null
      ? <p>No paper trades loaded yet.</p>
      : history.length === 0
        ? <p>No paper trades recorded yet.</p>
        : history.map(trade => <Trade key={`h-${trade.trade_id}`} trade={trade} />)}
    <p>Recorded: {listing?.recorded ?? 0} · Genuine completed paper trades count only after Owner review. Orders: no · Real money: no</p>
  </section>;
}
