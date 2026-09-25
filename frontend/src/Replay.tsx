import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReplayView, controlReplay, createReplaySession, readReplayRuns, tickReplay,
} from './replayApi';
import { DecisionGlyph, PredictionGlyph, decisionGlyphs, fillMarks, predictionGlyphs } from './replayGlyphs';
import { Badge, KeyValues, Section } from './ui';

const TICK_MS = 500;
const WIDTH = 900;
const HEIGHT = 300;
const PAD = 28;
const VISIBLE = 64;

type Detail =
  | { kind: 'prediction'; glyph: PredictionGlyph }
  | { kind: 'decision'; glyph: DecisionGlyph }
  | null;

const pct = (value: number | null | undefined, digits = 2) => value == null ? '—' : `${(value * 100).toFixed(digits)}%`;
const time = (value: string) => value.replace('T', ' ').replace(':00Z', ' UTC');

export function ReplayChart({ view, onDetail }: { view: ReplayView; onDetail: (detail: Detail) => void }) {
  const candles = view.candles.slice(-VISIBLE);
  const offset = view.candles.length - candles.length;
  if (candles.length === 0) {
    return <p className="summary pad">Nessuna candela 15m completata al cursore virtuale.</p>;
  }
  const high = Math.max(...candles.map(c => c.high));
  const low = Math.min(...candles.map(c => c.low));
  const span = high - low || 1;
  const step = (WIDTH - 2 * PAD) / VISIBLE;
  const x = (index: number) => PAD + index * step + step / 2;
  const y = (price: number) => PAD + (HEIGHT - 2 * PAD) * (1 - (price - low) / span);
  const shift = <T extends { candleIndex: number }>(items: T[]) =>
    items.map(item => ({ ...item, candleIndex: item.candleIndex - offset })).filter(item => item.candleIndex >= 0);
  const predictions = shift(predictionGlyphs(view.candles, view.predictions, view.realizations));
  const decisions = shift(decisionGlyphs(view.candles, view.decisions));
  const marks = fillMarks(candles, view.fills);
  return (
    <svg className="replay-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Grafico replay causale">
      {candles.map((candle, index) => {
        const up = candle.close >= candle.open;
        return (
          <g key={candle.open_time} data-testid="replay-candle">
            <line x1={x(index)} x2={x(index)} y1={y(candle.high)} y2={y(candle.low)} className="wick" />
            <rect
              x={x(index) - step * 0.35} width={step * 0.7}
              y={y(Math.max(candle.open, candle.close))}
              height={Math.max(1, Math.abs(y(candle.open) - y(candle.close)))}
              className={up ? 'candle up' : 'candle down'}
            />
          </g>
        );
      })}
      {predictions.map(glyph => (
        <text
          key={glyph.prediction.prediction_id}
          data-testid="prediction-glyph"
          data-direction={glyph.prediction.predicted_direction}
          data-matured={glyph.realization ? 'yes' : 'no'}
          x={x(glyph.candleIndex)} y={y(candles[glyph.candleIndex].high) - 8}
          className={`glyph prediction ${glyph.tone}`} textAnchor="middle"
          onMouseEnter={() => onDetail({ kind: 'prediction', glyph })}
          onFocus={() => onDetail({ kind: 'prediction', glyph })}
          tabIndex={0}
        >
          {glyph.symbol}
        </text>
      ))}
      {decisions.map(glyph => (
        <text
          key={glyph.decision.decision_id}
          data-testid="decision-glyph"
          data-action={glyph.decision.action}
          x={x(glyph.candleIndex)} y={y(candles[glyph.candleIndex].low) + 16}
          className={`glyph decision ${glyph.tone}`} textAnchor="middle"
          onMouseEnter={() => onDetail({ kind: 'decision', glyph })}
          onFocus={() => onDetail({ kind: 'decision', glyph })}
          tabIndex={0}
        >
          {glyph.symbol}
        </text>
      ))}
      {marks.map(mark => (
        <text
          key={mark.fill.event_id}
          data-testid="fill-mark"
          data-kind={mark.fill.kind}
          data-time={mark.fill.event_time}
          x={PAD + mark.position * step}
          y={y(Number(mark.fill.raw_price))}
          className={`glyph fill ${mark.tone}`} textAnchor="middle"
        >
          {mark.symbol}
        </text>
      ))}
    </svg>
  );
}

function DetailPanel({ detail, view }: { detail: Detail; view: ReplayView }) {
  if (!detail) return <p className="summary pad">Passa sopra un simbolo per il dettaglio.</p>;
  if (detail.kind === 'prediction') {
    const p = detail.glyph.prediction;
    const r = detail.glyph.realization;
    return (
      <div className="pad" data-testid="replay-detail">
        <KeyValues rows={[
          ['Previsione emessa', time(p.issue_time)],
          ['Direzione', p.predicted_direction],
          ['Convinzione', p.conviction],
          ['Valore P(su)', `${pct(p.probability_up, 1)} (${p.probability_status})`],
          ['Rendimento medio 4h', pct(p.mean_terminal_return, 3)],
          ['Intervallo q10–q90', `${pct(p.lower_quantile_return, 3)} … ${pct(p.upper_quantile_return, 3)}`],
          ['Scadenza', time(p.target_end)],
          ['Esito', r ? `${r.resolution_validity} · ${pct(r.realized_terminal_return, 3)} · ${r.direction_correct === null ? 'n/d' : r.direction_correct ? 'corretta' : 'errata'}` : 'non ancora maturata'],
          ['Motivo non disponibile', p.unavailable_reason ?? '—'],
        ]} />
      </div>
    );
  }
  const d = detail.glyph.decision;
  const plan = view.trade_plans.find(item => item.trade_plan_id === d.trade_plan_id);
  const fills = view.fills.filter(item => item.trade_plan_id === d.trade_plan_id);
  return (
    <div className="pad" data-testid="replay-detail">
      <KeyValues rows={[
        ['Decisione', `${d.action} · ${time(d.decision_time)}`],
        ['Playbook', d.playbook_id ?? '—'],
        ['Convinzione', d.conviction],
        ['Blocchi', d.blockers.length ? d.blockers.join(', ') : 'nessuno'],
        ['Piano', plan ? `${plan.side} stop ${plan.stop_price} · obiettivo ${plan.objective_price}` : '—'],
        ['Esecuzioni', fills.length ? fills.map(f => `${f.kind} ${time(f.event_time)} ${f.raw_price ?? ''} ${f.reason}`).join(' | ') : '—'],
      ]} />
    </div>
  );
}

export function Replay() {
  const [view, setView] = useState<ReplayView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail>(null);
  const busy = useRef(false);

  const act = useCallback(async (call: () => Promise<ReplayView>) => {
    if (busy.current) return;
    busy.current = true;
    try {
      setView(await call());
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'errore');
    } finally {
      busy.current = false;
    }
  }, []);

  const open = useCallback(async () => {
    try {
      const runs = await readReplayRuns();
      if (runs.length) await act(() => createReplaySession(runs[0].manifest.run_id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'errore');
    }
  }, [act]);

  useEffect(() => { void open(); }, [open]);

  const session = view?.session_id;
  const running = view?.status === 'RUNNING';
  useEffect(() => {
    if (!running || !session) return;
    const timer = window.setInterval(() => { void act(() => tickReplay(session, TICK_MS / 1000)); }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [running, session, act]);

  const current = view?.current;
  const stats = view?.stats;
  return (
    <>
      <div className="pagehead">
        <div>
          <p className="eyebrow">System G1 · Checkpoint 1</p>
          <h1>Replay (sintetico)</h1>
          <p className="lede">
            Replay causale di un dataset sintetico registrato. Non sono dati BTC e non è una prova di
            performance: la strategia G1 non è validata e l’azione reale resta NO_TRADE.
          </p>
        </div>
        <Badge tone="paper">{view?.label ?? 'SYNTHETIC FIXTURE'}</Badge>
      </div>
      {error && <p className="notice" role="alert">{error}</p>}
      {view && session && (
        <>
          <Section
            title="Grafico 15m"
            label="Grafico replay"
            hint={`Cursore virtuale: ${time(view.cursor)} · stato ${view.status}`}
            actions={(
              <div className="row replay-controls">
                {running
                  ? <button className="btn" onClick={() => void act(() => controlReplay(session, 'pause'))}>Pausa</button>
                  : <button className="btn primary" disabled={view.status === 'COMPLETE'} onClick={() => void act(() => controlReplay(session, 'start'))}>Avvia</button>}
                <button className="btn" disabled={running || view.status === 'COMPLETE'} onClick={() => void act(() => controlReplay(session, 'step'))}>Passo 15m</button>
                <label className="summary">
                  Velocità{' '}
                  <select
                    aria-label="Velocità"
                    value={view.speed}
                    onChange={event => void act(() => controlReplay(session, 'speed', Number(event.target.value)))}
                  >
                    {view.speeds.map(speed => <option key={speed} value={speed}>{speed}×</option>)}
                  </select>
                </label>
              </div>
            )}
          >
            <ReplayChart view={view} onDetail={setDetail} />
            <DetailPanel detail={detail} view={view} />
          </Section>
          <div className="replay-grid">
            <Section title="Previsione corrente" label="Previsione corrente">
              <div className="pad">
                {current?.prediction ? (
                  <KeyValues rows={[
                    ['Direzione', current.prediction.predicted_direction],
                    ['Convinzione', current.prediction.conviction],
                    ['Valore P(su)', `${pct(current.prediction.probability_up, 1)} · non calibrato`],
                    ['Rendimento medio 4h', pct(current.prediction.mean_terminal_return, 3)],
                    ['Scadenza', time(current.prediction.target_end)],
                  ]} />
                ) : <p className="summary">Nessuna previsione ancora emessa.</p>}
              </div>
            </Section>
            <Section title="Decisione corrente" label="Decisione corrente">
              <div className="pad">
                {current?.decision ? (
                  <KeyValues rows={[
                    ['Azione (replay)', current.decision.action],
                    ['Playbook', current.decision.playbook_id ?? '—'],
                    ['Blocchi', current.decision.blockers.join(', ') || 'nessuno'],
                    ['Equity virtuale', current.ledger.equity.slice(0, 10)],
                    ['Posizione', current.ledger.open_side ?? 'nessuna'],
                    ['Azione di produzione', view.production_action],
                  ]} />
                ) : <p className="summary">Nessuna decisione ancora emessa.</p>}
              </div>
            </Section>
            <Section title="Segnali e stato" label="Segnali e stato" hint="Diagnostici; ciclo METHOD_NOT_READY">
              <div className="pad">
                <KeyValues rows={[
                  ...(current?.signals ?? []).map(signal => [`${signal.name}`, `${signal.state} · ${signal.quality}`] as [string, string]),
                  ['Ciclo', current?.cycle ? `${current.cycle.decision_role} · ${current.cycle.timing_qualifier}` : '—'],
                ]} />
              </div>
            </Section>
            <Section title="Statistiche maturate" label="Statistiche maturate" hint={stats?.label}>
              <div className="pad" data-testid="replay-stats">
                {stats && (
                  <KeyValues rows={[
                    ['Previsioni emesse', stats.predictions_issued],
                    ['Maturate (valide)', `${stats.matured} (${stats.matured_valid})`],
                    ['Direzionali maturate', stats.directional_matured],
                    ['Hit rate direzionale', stats.directional_hit_rate == null ? '—' : `${pct(stats.directional_hit_rate, 1)} su n=${stats.directional_matured}, copertura ${pct(stats.directional_coverage, 1)}`],
                    ['Trade chiusi (L/S)', `${stats.closed_trades} (${stats.long_trades}/${stats.short_trades})`],
                    ['P&L netto sintetico', stats.net_pnl],
                  ]} />
                )}
              </div>
            </Section>
          </div>
        </>
      )}
    </>
  );
}
