import { useCallback, useEffect, useRef, useState } from 'react';
import {
  G2Current, G2Latest, G2Lineage, G2Run, G2View,
  controlG2, createG2Session, readG2Latest, readG2Lineage, readG2Runs, tickG2,
} from './g2Api';
import { Badge, KeyValues, Section } from './ui';

// Presentation only: every value below is copied from the authoritative G2 API response.
const TICK_MS = 500;
const WIDTH = 900;
const HEIGHT = 300;
const PAD = 28;
const VISIBLE = 96;
const COLUMNS = [
  'LOCAL_STRUCTURE', 'CONTEXT_STRUCTURE', 'PRICE_EXTENSION', 'RELATIVE_PARTICIPATION',
  'TAKER_IMBALANCE', 'VOLATILITY_STATE', 'LOCAL_STRUCTURE_X_PARTICIPATION', 'IMBALANCE_X_PRICE_RESPONSE',
];
export const NOT_PERFORMANCE = 'NOT PERFORMANCE EVIDENCE';

const num = (value: number | null | undefined, digits = 4) => value == null ? '—' : value.toFixed(digits);
const pct = (value: number | null | undefined, digits = 2) => value == null ? '—' : `${(value * 100).toFixed(digits)}%`;
const time = (value: string | null | undefined) => value ? value.replace('T', ' ').replace(/:00(\.000)?Z$/, ' UTC').replace('+00:00', ' UTC') : '—';

export function G2Chart({ view, onDecision }: { view: G2View; onDecision: (id: string) => void }) {
  const candles = view.candles.slice(-VISIBLE);
  if (candles.length === 0) return <p className="summary pad">Nessuna candela 15m completata al cursore virtuale.</p>;
  const high = Math.max(...candles.map(c => c.high));
  const low = Math.min(...candles.map(c => c.low));
  const span = high - low || 1;
  const step = (WIDTH - 2 * PAD) / VISIBLE;
  const index = new Map(candles.map((c, i) => [c.available_at, i]));
  const x = (i: number) => PAD + i * step + step / 2;
  const y = (price: number) => PAD + (HEIGHT - 2 * PAD) * (1 - (price - low) / span);
  const at = (moment: string) => index.get(moment.replace('+00:00', 'Z'));
  return (
    <svg className="replay-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Grafico replay G2">
      {candles.map((c, i) => (
        <g key={c.open_time} data-testid="g2-candle">
          <line x1={x(i)} x2={x(i)} y1={y(c.high)} y2={y(c.low)} className="wick" />
          <rect x={x(i) - step * 0.35} width={step * 0.7} y={y(Math.max(c.open, c.close))}
            height={Math.max(1, Math.abs(y(c.open) - y(c.close)))} className={c.close >= c.open ? 'candle up' : 'candle down'} />
        </g>
      ))}
      {view.prediction_markers.map(p => {
        const i = at(p.decision_time);
        if (i === undefined) return null;
        const symbol = p.direction === 'UP' ? '▴' : p.direction === 'DOWN' ? '▾' : p.direction === 'NEUTRAL' ? '·' : '○';
        return (
          <text key={p.prediction_id} data-testid="g2-prediction" data-direction={p.direction}
            x={x(i)} y={y(candles[i].high) - 6} textAnchor="middle"
            className={`glyph prediction ${p.direction === 'UNAVAILABLE' ? 'muted' : 'pending'}`}>{symbol}</text>
        );
      })}
      {view.decision_markers.map(d => {
        const i = at(d.decision_time);
        if (i === undefined) return null;
        return (
          <text key={d.decision_id} data-testid="g2-decision" data-action={d.action} tabIndex={0}
            x={x(i)} y={y(candles[i].low) + 16} textAnchor="middle"
            className={`glyph decision ${d.action === 'LONG' ? 'long' : d.action === 'SHORT' ? 'short' : 'flat'}`}
            onClick={() => onDecision(d.decision_id)} onFocus={() => onDecision(d.decision_id)}>
            {d.action === 'LONG' ? 'L' : d.action === 'SHORT' ? 'S' : '×'}
          </text>
        );
      })}
    </svg>
  );
}

export function G2CurrentDetail({ current, productionAction }: { current: G2Current; productionAction: string }) {
  const { state, prediction: p, decision: d, cycle, risk } = current;
  return (
    <div className="replay-grid">
      <Section title="Stato G2 (8 colonne)" label="Stato G2" hint={state ? `${state.status} · fonte max ${time(state.max_source_time)}` : undefined}>
        <div className="pad" data-testid="g2-state">
          {state ? (
            <KeyValues rows={[
              ...COLUMNS.map((name, i) => [name, `${num(state.raw_terms[i])} · ${state.term_status[i]}`] as [string, string]),
              ['SIGMA_4H', num(state.sigma_4h, 5)],
              ['ATR14 1h', num(state.atr14_1h, 2)],
              ['Giornaliero (solo display)', state.daily.map(([k, v]) => `${k}=${typeof v === 'number' ? v.toFixed(4) : v ?? '—'}`).join(' · ')],
            ]} />
          ) : <p className="summary">Nessuno stato ancora emesso.</p>}
        </div>
      </Section>
      <Section title="Previsione 4h" label="Previsione 4h" hint={p ? p.reason_codes.join(', ') : undefined}>
        <div className="pad" data-testid="g2-forecast">
          {p ? (
            <KeyValues rows={[
              ['Direzione', p.direction],
              ['Mediana / media', `${pct(p.median_return, 3)} / ${pct(p.mean_return, 3)}`],
              ['q10 · q50 · q90', `${pct(p.q10, 3)} · ${pct(p.q50, 3)} · ${pct(p.q90, 3)}`],
              ['p(r4h > 0)', p.p_positive == null ? '—' : `${pct(p.p_positive, 1)} — ${p.calibration_status} (non calibrata)`],
              ['Forza (display)', p.view_strength_z == null ? '—' : `${num(p.view_strength_z, 3)} · ${p.strength_label}`],
              ['Residui', `${p.residual_source} · n=${p.residual_count}`],
              ['Evidenza', p.evidence_status.map(([k, v]) => `${k}=${v}`).join(' · ')],
              ['Contributi', p.contributions.every(c => c == null) ? '—' : COLUMNS.map((c, i) => `${c.slice(0, 12)} ${num(p.contributions[i], 3)}`).join(' | ')],
              ['Training', `${time(p.training_start)} → ${time(p.training_end)} · ultima label ${time(p.latest_label_time)}`],
            ]} />
          ) : <p className="summary">Nessuna previsione ancora emessa.</p>}
        </div>
      </Section>
      <Section title="Decisione / utilità" label="Decisione G2" hint={d ? d.reason_codes.join(', ') : undefined}>
        <div className="pad" data-testid="g2-decision-detail">
          {d ? (
            <KeyValues rows={[
              ['Azione (replay)', d.action],
              ['Selezione policy', d.policy_selection],
              ['LONG utilità / q10 / margine', `${num(d.long_utility.predicted_utility, 3)} / ${num(d.long_utility.residual_q10, 3)} / ${num(d.long_utility.prudential_margin, 3)} · ${d.long_utility.evidence_status} (n=${d.long_utility.residual_count})`],
              ['SHORT utilità / q10 / margine', `${num(d.short_utility.predicted_utility, 3)} / ${num(d.short_utility.residual_q10, 3)} / ${num(d.short_utility.prudential_margin, 3)} · ${d.short_utility.evidence_status} (n=${d.short_utility.residual_count})`],
              ['Posizione', d.position_state],
              ['Stop D (2×ATR)', num(d.stop_distance, 2)],
              ['Ingresso / scadenza', `${time(d.intended_entry_time)} / ${time(d.intended_expiry_time)}`],
              ['Azione di produzione', productionAction],
            ]} />
          ) : <p className="summary">Nessuna decisione ancora emessa.</p>}
        </div>
      </Section>
      <Section title="Rischio / esecuzione" label="Rischio G2">
        <div className="pad" data-testid="g2-risk">
          {risk ? (
            <KeyValues rows={[
              ['Equity realizzata (virtuale)', num(risk.equity, 2)],
              ['Equity marcata', `${num(risk.marked_equity, 2)} · ${risk.mark_basis} · evento ${risk.kind}`],
              ['Picco / drawdown', `${num(risk.peak_equity, 2)} / ${pct(risk.drawdown, 2)}`],
              ['Blocco drawdown 5%', risk.drawdown_stop_active ? 'ATTIVO' : 'no'],
              ['Posizione aperta', current.open_position ? `${current.open_position.side} ${current.open_position.quantity} @ ${current.open_position.raw_price}` : 'nessuna'],
            ]} />
          ) : <p className="summary">—</p>}
        </div>
      </Section>
      <Section title="Ciclo — SHADOW" label="Ciclo shadow" hint={cycle ? `${cycle.runtime_role} · coeff. previsione ${cycle.forecast_coefficients} · coeff. policy ${cycle.policy_coefficients} · veto ${cycle.veto_authority}` : 'SHADOW'}>
        <div className="pad" data-testid="g2-cycle">
          <Badge tone="paper">SHADOW — nessun effetto su previsione o decisione</Badge>
          {cycle && (
            <KeyValues rows={cycle.scales.map(s => [
              `${s.nominal_scale} (${s.input_resolution})`,
              `${s.quality_label} · periodo ${num(s.dominant_period_minutes, 0)}m · ampiezza ${num(s.projection_amplitude, 3)} · stabilità ${num(s.period_stability, 3)} · ${s.last_turn_kind ?? 'nessuna svolta'}`,
            ] as [string, string])} />
          )}
        </div>
      </Section>
    </div>
  );
}

export function G2LatestPanel() {
  const [runs, setRuns] = useState<G2Run[]>([]);
  const [latest, setLatest] = useState<G2Latest | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { readG2Runs().then(setRuns).catch(() => setRuns([])); }, []);
  const load = async (key: string) => {
    setBusy(true);
    try { setLatest(await readG2Latest(key)); setError(null); } catch (reason) { setError(reason instanceof Error ? reason.message : 'errore'); } finally { setBusy(false); }
  };
  if (runs.length === 0) return null;
  return (
    <Section title="G2-V0 — ultimo stato (run di ingegneria)" label="Stato G2" hint={NOT_PERFORMANCE}
      actions={(
        <div className="row">
          {runs.map(run => (
            <button key={run.run_key} className="btn" disabled={busy} onClick={() => void load(run.run_key)}>
              {busy ? 'Calcolo…' : `Carica ${run.run_key}`}
            </button>
          ))}
        </div>
      )}>
      <div className="pad" data-testid="g2-latest">
        <Badge tone="paper">{NOT_PERFORMANCE}</Badge>
        {error && <p className="notice" role="alert">{error}</p>}
        {latest ? (
          <>
            <p className="summary">{latest.run_key} · {latest.evidence_class} · cursore {time(latest.cursor)} · azione di produzione {latest.production_action}</p>
            <G2CurrentDetail current={latest.current} productionAction={latest.production_action} />
          </>
        ) : <p className="summary">Seleziona un run registrato (il primo calcolo del run sintetico richiede circa un minuto).</p>}
      </div>
    </Section>
  );
}

export function G2Replay() {
  const [runs, setRuns] = useState<G2Run[]>([]);
  const [view, setView] = useState<G2View | null>(null);
  const [lineage, setLineage] = useState<G2Lineage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const busy = useRef(false);

  const act = useCallback(async (request: () => Promise<G2View>) => {
    if (busy.current) return;
    busy.current = true;
    try { setView(await request()); setError(null); } catch (reason) { setError(reason instanceof Error ? reason.message : 'errore'); } finally { busy.current = false; }
  }, []);

  useEffect(() => { readG2Runs().then(setRuns).catch(reason => setError(reason instanceof Error ? reason.message : 'errore')); }, []);

  const open = async (key: string) => {
    setLoading(true);
    setLineage(null);
    await act(() => createG2Session(key));
    setLoading(false);
  };

  const session = view?.session_id;
  const running = view?.status === 'RUNNING';
  useEffect(() => {
    if (!running || !session) return;
    const timer = window.setInterval(() => { void act(() => tickG2(session, TICK_MS / 1000)); }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [running, session, act]);

  const inspect = async (decision: string) => {
    if (!session) return;
    try { setLineage(await readG2Lineage(session, decision)); } catch (reason) { setError(reason instanceof Error ? reason.message : 'errore'); }
  };

  return (
    <>
      <div className="pagehead">
        <div>
          <p className="eyebrow">G2 Development System · G2-01 vertical slice</p>
          <h1>Replay G2-V0 (ingegneria)</h1>
          <p className="lede">
            Replay causale del core G2 autorevole su run di ingegneria registrati. Non è una prova di
            performance: nessuna strategia è validata e l’azione reale resta NO_TRADE.
          </p>
        </div>
        <Badge tone="paper">{NOT_PERFORMANCE}</Badge>
      </div>
      {error && <p className="notice" role="alert">{error}</p>}
      <div className="row replay-run">
        {runs.map(run => (
          <button key={run.run_key} className="btn" disabled={loading} onClick={() => void open(run.run_key)} title={run.description}>
            {run.run_key} · {run.evidence_label}
          </button>
        ))}
        {loading && <span className="summary">Calcolo del run in corso…</span>}
      </div>
      {view && session && (
        <>
          <Section title="Grafico 15m · previsioni e decisioni" label="Grafico G2"
            hint={`${view.label} · ${view.run_key} · cursore ${time(view.cursor)} · stato ${view.status}`}
            actions={(
              <div className="row replay-controls">
                {running
                  ? <button className="btn" onClick={() => void act(() => controlG2(session, 'pause'))}>Pausa</button>
                  : <button className="btn primary" disabled={view.status === 'COMPLETE'} onClick={() => void act(() => controlG2(session, 'start'))}>Avvia</button>}
                {view.step_units.map(unit => (
                  <button key={unit} className="btn" disabled={running || view.status === 'COMPLETE'}
                    onClick={() => void act(() => controlG2(session, 'step', { unit }))}>Passo {unit}</button>
                ))}
                <label className="summary">
                  Velocità{' '}
                  <select aria-label="Velocità G2" value={view.speed}
                    onChange={event => void act(() => controlG2(session, 'speed', { speed: Number(event.target.value) }))}>
                    {view.speeds.map(speed => <option key={speed} value={speed}>{speed}×</option>)}
                  </select>
                </label>
              </div>
            )}>
            <G2Chart view={view} onDecision={id => void inspect(id)} />
            <p className="summary pad">▴/▾ previsione (ogni candela) · L/S decisione · × selezione bloccata da rischio/posizione</p>
          </Section>
          <G2CurrentDetail current={view.current} productionAction={view.production_action} />
          <Section title="Lineage decisione" label="Lineage" hint="previsione → decisione → ordine → fill → chiusura (solo record visibili al cursore)">
            <pre className="pad lineage" data-testid="g2-lineage">{lineage ? JSON.stringify(lineage, null, 1) : 'Seleziona un marcatore L/S sul grafico.'}</pre>
          </Section>
        </>
      )}
    </>
  );
}
