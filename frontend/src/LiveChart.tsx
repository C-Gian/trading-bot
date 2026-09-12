import { useEffect, useRef, useState } from 'react';
import { CandlestickSeries, createChart, UTCTimestamp } from 'lightweight-charts';
import { LiveMarket, readLiveMarket } from './api';

export type PlanLines = { reference: number | null; stop: number | null; target: number | null; source: string } | null;

/**
 * Current BTCUSDT candles with the current plan drawn as horizontal price lines.
 * Only the live plan or active trade is overlaid: no past trade is ever marked, so the
 * chart cannot imply paper trades existed before they actually did.
 */
export function LiveChart({ plan }: { plan: PlanLines }) {
  const host = useRef<HTMLDivElement>(null);
  const [market, setMarket] = useState<LiveMarket | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    try {
      setMarket(await readLiveMarket());
    } catch {
      setMarket(null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!host.current || !market || market.candles.length === 0) return;
    const chart = createChart(host.current, { layout: { background: { color: '#10151c' }, textColor: '#cbd5e1' } });
    const series = chart.addSeries(CandlestickSeries);
    series.setData(market.candles.map(candle => ({
      time: Math.floor(new Date(candle.open_time).getTime() / 1000) as UTCTimestamp,
      open: candle.open, high: candle.high, low: candle.low, close: candle.close,
    })));
    if (plan) {
      const lines: [number | null, string, string][] = [
        [plan.reference, '#93c5fd', 'REFERENCE / ENTRY'],
        [plan.stop, '#f87171', 'STOP'],
        [plan.target, '#4ade80', 'TARGET'],
      ];
      for (const [price, color, title] of lines) {
        if (price !== null) series.createPriceLine({ price, color, lineWidth: 1, title });
      }
    }
    return () => chart.remove();
  }, [market, plan]);

  return <section className="card" aria-label="Current market">
    <h2>BTCUSDT — current market</h2>
    <p className="banner">CURRENT PUBLIC MARKET DATA — READ ONLY · PAPER RESEARCH · NOT LIVE TRADING</p>
    <button onClick={load} disabled={busy}>LOAD MARKET</button>
    {market === null && <p>No market data loaded. Click LOAD MARKET.</p>}
    {market !== null && market.status !== 'OK' && <p>Market data unavailable: {market.detail}</p>}
    {market !== null && market.status === 'OK' && <p>{market.symbol} · {market.interval} · {market.detail}</p>}
    {plan
      ? <p>Plan overlay — reference/entry: {plan.reference ?? '—'} · stop: {plan.stop ?? '—'} · target: {plan.target ?? '—'} ({plan.source})</p>
      : <p>No plan overlay. Run ANALYZE MARKET or create a paper trade.</p>}
    <div ref={host} className="chart" aria-label="current candlestick chart" />
  </section>;
}
