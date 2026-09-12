import { Analysis } from './api';
import { checksSummary, dataStatusCopy, gateChecks, money, when } from './format';
import { Advanced, Checks, Debug, KeyValues } from './ui';

const PLAN_ROWS: { key: 'entry' | 'stop' | 'target' | 'expiry'; label: string; why: string }[] = [
  { key: 'entry', label: 'Ingresso', why: 'Prezzo a cui simuliamo l’ingresso' },
  { key: 'stop', label: 'Stop', why: 'Se scende qui, chiudiamo la simulazione' },
  { key: 'target', label: 'Obiettivo', why: 'Se sale qui, prendiamo profitto' },
  { key: 'expiry', label: 'Scadenza', why: 'Il trade viene chiuso comunque entro questo momento' },
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
  const checks = gateChecks(analysis?.features);
  const summary = checksSummary(checks);
  // Analysing is the primary action whenever there is no simulate button to outrank it.
  const analyzeIsPrimary = !canSimulate;

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
        <div className="stack">
          <div className="stack-sm">
            <p className="verdict">Nessun trade ora</p>
            <p className="lede">
              Le condizioni attuali non soddisfano abbastanza criteri per simulare un ingresso.
            </p>
          </div>
          {checks.length > 0 && (
            <div className="stack-sm">
              <span className="eyebrow">Perché</span>
              <Checks items={checks} />
              {summary && <p className="summary">{summary}</p>}
            </div>
          )}
          <p className="footnote">Analisi delle {when(analysis.analysis_time)} UTC</p>
        </div>
      )}

      {analysis && !dataIssue && plan && (
        <div className="stack">
          <div className="stack-sm">
            <p className="verdict go">Possibile long</p>
            <p className="lede">Solo simulazione — nessun denaro reale viene investito.</p>
          </div>

          {checks.length > 0 && (
            <div className="stack-sm">
              <span className="eyebrow">Perché</span>
              <Checks items={checks} />
              {summary && <p className="summary">{summary}</p>}
            </div>
          )}

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

      <button
        className={`btn ${analyzeIsPrimary ? 'primary block' : 'ghost'}`}
        onClick={onAnalyze}
        disabled={busy}
      >
        {analysis ? 'Analizza di nuovo' : 'Analizza ora'}
      </button>

      {analysis && (
        <Advanced>
          <KeyValues
            rows={[
              ['Strategia', `${analysis.strategy_version} · ${analysis.variant}`],
              ['Stato della strategia', 'Candidata sperimentale in modalità paper'],
              ['Strategia approvata', analysis.champion_status === 'NONE' ? 'Nessuna' : analysis.champion_status],
              ['Momento del segnale', when(analysis.signal_time)],
              ['Qualità dei dati', analysis.data_status === 'OK' ? 'Completi' : 'Incompleti'],
              ...(plan
                ? ([
                  ['Regola di ingresso', 'Alla prima apertura del minuto successivo'],
                  ['Uscita', 'Obiettivo, stop oppure scadenza'],
                  ['Durata massima', `${plan.max_hold_minutes} minuti`],
                  ['Distanza dello stop', `${(plan.stop_fraction * 100).toFixed(0)}%`],
                  ['Distanza dell’obiettivo', `${(plan.target_fraction * 100).toFixed(0)}%`],
                ] as [string, string][])
                : []),
            ]}
          />
          <Debug>
            <KeyValues
              rows={[
                ['Versione analisi', analysis.analysis_version],
                ['Versione feature', analysis.feature_version],
                ['Stato scientifico', analysis.research_status],
                ['Dettaglio dati', analysis.data_detail],
                ['Identificativo analisi', analysis.analysis_id ?? '—'],
                ...(plan
                  ? ([
                    ['Regola interna', plan.entry_rule],
                    ['Modello di esecuzione', plan.execution_model],
                    ['Politica di uscita', plan.exit_policy],
                  ] as [string, string][])
                  : []),
              ]}
            />
          </Debug>
        </Advanced>
      )}
    </section>
  );
}
