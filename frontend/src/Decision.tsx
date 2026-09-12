import { Analysis } from './api';
import { dataStatusCopy, money, when } from './format';
import { Advanced, KeyValues } from './ui';

const PLAN_ROWS: { key: 'entry' | 'stop' | 'target' | 'expiry'; label: string; why: string }[] = [
  { key: 'entry', label: 'Ingresso', why: 'Prezzo a cui simuliamo l’acquisto' },
  { key: 'stop', label: 'Stop', why: 'Se il prezzo scende qui, chiudiamo la simulazione' },
  { key: 'target', label: 'Obiettivo', why: 'Il livello che la simulazione punta a raggiungere' },
  { key: 'expiry', label: 'Scadenza', why: 'Oltre questo momento la simulazione si chiude comunque' },
];

export function Decision({
  analysis, busy, canSimulate, blockedReason, onAnalyze, onSimulate,
}: {
  analysis: Analysis | null;
  busy: boolean;
  canSimulate: boolean;
  blockedReason: string | null;
  onAnalyze: () => void;
  onSimulate: () => void;
}) {
  const plan = analysis?.plan ?? null;
  const dataIssue = analysis ? dataStatusCopy(analysis.data_status) : null;

  return (
    <section className="surface decision" aria-label="Decisione del bot">
      <span className="eyebrow">Cosa dice il bot</span>

      {!analysis && (
        <div className="stack-sm">
          <p className="verdict">Analisi non ancora eseguita</p>
          <p className="lede">Il bot non ha ancora valutato le condizioni attuali del mercato.</p>
        </div>
      )}

      {analysis && dataIssue && (
        <div className="stack-sm">
          <p className="verdict">Analisi non conclusa</p>
          <p className="lede">{dataIssue}</p>
        </div>
      )}

      {analysis && !dataIssue && analysis.decision === 'NO_TRADE' && (
        <div className="stack-sm">
          <p className="verdict">Nessun trade ora</p>
          <p className="lede">
            Le condizioni attuali non soddisfano abbastanza criteri per simulare un ingresso.
          </p>
          <p className="footnote">Analisi delle {when(analysis.analysis_time)} UTC</p>
        </div>
      )}

      {analysis && !dataIssue && plan && (
        <div className="stack">
          <div className="stack-sm">
            <p className="verdict go">Possibile long</p>
            <p className="lede">Solo simulazione — nessun denaro reale viene investito.</p>
          </div>

          <dl className="planrows">
            {PLAN_ROWS.map(row => (
              <div className="planrow" key={row.key}>
                <dt>
                  {row.label}
                  <span className="why">{row.why}</span>
                </dt>
                {row.key === 'expiry' ? (
                  <dd className="when">{when(plan.expiry_time)}</dd>
                ) : (
                  <dd className={row.key === 'entry' ? '' : row.key}>
                    {money(
                      row.key === 'entry' ? plan.reference_price
                        : row.key === 'stop' ? plan.stop_price : plan.target_price,
                    )}
                  </dd>
                )}
              </div>
            ))}
          </dl>

          {canSimulate ? (
            <button className="btn primary block" onClick={onSimulate} disabled={busy}>
              Simula questo trade
            </button>
          ) : (
            blockedReason && <p className="notice">{blockedReason}</p>
          )}
        </div>
      )}

      <div className="row">
        <button
          className={`btn ${analysis ? 'ghost' : 'primary'} ${analysis ? '' : 'block'}`.trim()}
          onClick={onAnalyze}
          disabled={busy}
        >
          {analysis ? 'Analizza di nuovo' : 'Analizza ora'}
        </button>
      </div>

      {analysis && (
        <Advanced>
          <KeyValues
            rows={[
              ['Strategia', `${analysis.strategy_version} · ${analysis.variant}`],
              ['Stato scientifico', analysis.research_status],
              ['Champion', analysis.champion_status],
              ['Versione analisi', analysis.analysis_version],
              ['Feature', analysis.feature_version],
              ['Momento del segnale', analysis.signal_time ?? '—'],
              ['Qualità dati', `${analysis.data_status} — ${analysis.data_detail}`],
              ['Identificativo analisi', analysis.analysis_id ?? '—'],
              ...(plan
                ? ([
                  ['Regola di ingresso', plan.entry_rule],
                  ['Modello di esecuzione', plan.execution_model],
                  ['Politica di uscita', plan.exit_policy],
                  ['Durata massima', `${plan.max_hold_minutes} minuti`],
                ] as [string, string][])
                : []),
            ]}
          />
        </Advanced>
      )}
    </section>
  );
}
