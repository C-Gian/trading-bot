import { useEffect, useRef, useState } from 'react';
import { CandlestickSeries, createChart, UTCTimestamp } from 'lightweight-charts';
import { LiveMarket, readLiveMarket } from './api';
import { changePercent, money, when } from './format';

export type PlanLines = {
  reference: number | null;
  stop: number | null;
  target: number | null;
  origin: 'analysis' | 'trade';
} | null;

const LEVELS: { key: 'reference' | 'stop' | 'target'; color: string; title: string }[] = [
  { key: 'reference', color: '#e2903f', title: 'Ingresso' },
  { key: 'stop', color: '#ef6257', title: 'Stop' },
  { key: 'target', color: '#45c98a', title: 'Obiettivo' },
];

/**
 * Current BTCUSDT candles. Read-only market data loads by itself; only the live plan is
 * drawn, so the chart never suggests a past trade that did not happen.
 */
export function MarketHero({ plan }: { plan: PlanLines }) {
  const host = useRef<HTMLDivElement>(null);
  const [market, setMarket] = useState<LiveMarket | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    readLiveMarket()
      .then(payload => { if (live) setMarket(payload); })
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, []);

  const candles = market?.status === 'OK' ? market.candles : [];

  useEffect(() => {
    if (!host.current || candles.length === 0) return;
    const chart = createChart(host.current, {
      autoSize: true,
      layout: {
        background: { color: 'transparent' },
        textColor: '#98a1b3',
        fontFamily: 'Figtree, system-ui, sans-serif',
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.035)' },
        horzLines: { color: 'rgba(255,255,255,0.035)' },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true },
      crosshair: { horzLine: { labelBackgroundColor: '#1a1f2b' }, vertLine: { labelBackgroundColor: '#1a1f2b' } },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#45c98a', downColor: '#ef6257',
      wickUpColor: 'rgba(69,201,138,0.6)', wickDownColor: 'rgba(239,98,87,0.6)',
      borderVisible: false,
    });
    series.setData(candles.map(candle => ({
      time: Math.floor(new Date(candle.open_time).getTime() / 1000) as UTCTimestamp,
      open: candle.open, high: candle.high, low: candle.low, close: candle.close,
    })));
    if (plan) {
      for (const level of LEVELS) {
        const price = plan[level.key];
        if (price !== null) {
          series.createPriceLine({
            price, color: level.color, lineWidth: 1, lineStyle: 2,
            axisLabelVisible: true, title: level.title,
          });
        }
      }
    }
    return () => chart.remove();
  }, [candles, plan]);

  const last = candles.at(-1);
  const first = candles[0];
  const change = last && first && first.open ? (last.close - first.open) / first.open : null;

  return (
    <section className="surface chartcard" aria-label="Andamento Bitcoin">
      <div className="chartbar">
        <div>
          <p className="eyebrow">Bitcoin · BTCUSDT</p>
          <div className="price">
            <span className="sym">$</span>
            <span className="val">{last ? money(last.close) : '—'}</span>
            {change !== null && (
              <span
                className="delta"
                style={{
                  color: change >= 0 ? '#45c98a' : '#ef6257',
                  background: change >= 0 ? 'rgba(69,201,138,0.12)' : 'rgba(239,98,87,0.12)',
                }}
              >
                {changePercent(change)}
              </span>
            )}
          </div>
        </div>
        <div className="meta">
          {last ? <span>Candele orarie · ultimo dato {when(last.open_time)} UTC</span> : <span>Dati di mercato</span>}
        </div>
      </div>

      {candles.length > 0 ? (
        <div ref={host} className="chart" aria-label="Grafico a candele Bitcoin" />
      ) : (
        <div className="chartstate">
          {failed || market?.status === 'MARKET_DATA_UNAVAILABLE' ? (
            <>
              <p>Dati di mercato non disponibili al momento.</p>
              <p className="footnote">Il grafico riapparirà da solo quando la connessione torna.</p>
            </>
          ) : (
            <p>Caricamento del mercato…</p>
          )}
        </div>
      )}

      {plan && candles.length > 0 && (
        <div className="legend">
          {LEVELS.filter(level => plan[level.key] !== null).map(level => (
            <span key={level.key}>
              <i style={{ background: level.color }} />
              {level.title} {money(plan[level.key])}
            </span>
          ))}
          <span className="grow" />
          <span className="footnote">
            {plan.origin === 'trade' ? 'Livelli della simulazione in corso' : 'Livelli dell’analisi corrente'}
          </span>
        </div>
      )}
    </section>
  );
}
