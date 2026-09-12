import { useEffect, useRef, useState } from 'react';
import { CandlestickSeries, createChart, UTCTimestamp } from 'lightweight-charts';
import { CandlePayload, request } from './api';

const WINDOW =
  '/api/v1/market/candles?symbol=BTCUSDT&timeframe=1h' +
  '&start=2024-11-20T00:00:00Z&end=2024-12-31T23:59:00Z&limit=1000';

/**
 * Historical development data, kept in the advanced Research area only. It is the frozen
 * research dataset, not the current market, and never drives the product flow.
 */
export function Market({ available }: { available: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const [payload, setPayload] = useState<CandlePayload | null>(null);

  useEffect(() => {
    if (!available) return;
    let live = true;
    request<CandlePayload>(WINDOW)
      .then(next => { if (live) setPayload(next); })
      .catch(() => { if (live) setPayload(null); });
    return () => { live = false; };
  }, [available]);

  const candles = payload?.candles?.filter(candle => candle.complete !== false) ?? [];

  useEffect(() => {
    if (!host.current || candles.length === 0) return;
    const chart = createChart(host.current, {
      autoSize: true,
      layout: { background: { color: 'transparent' }, textColor: '#98a1b3', attributionLogo: false },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.035)' },
        horzLines: { color: 'rgba(255,255,255,0.035)' },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
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
    return () => chart.remove();
  }, [candles]);

  const coverage = payload?.coverage;
  return (
    <>
      <p className="footnote">
        Dati storici di sviluppo — non è il mercato attuale.
        {coverage ? ` Copertura ${coverage.start} → ${coverage.end}.` : ''}
      </p>
      {candles.length > 0 ? (
        <div ref={host} className="chart" aria-label="Grafico storico di sviluppo" />
      ) : (
        <div className="chartstate">
          <p>{available ? 'Caricamento dei dati storici…' : 'Dati storici non installati.'}</p>
        </div>
      )}
    </>
  );
}
