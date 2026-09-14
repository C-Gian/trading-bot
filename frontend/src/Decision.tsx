import { Analysis } from './api';
import { checksSummary, dataStatusCopy, gateChecks, when } from './format';
import { Advanced, Checks, Debug, KeyValues } from './ui';

export function Decision({
  analysis, busy, canSimulate, blockedReason, onAnalyze, onSimulate, onCopyAnalysis,
}: {
  analysis: Analysis | null;
  busy: boolean;
  canSimulate: boolean;
  blockedReason: string | null;
  onAnalyze: () => void;
  onSimulate: () => void;
  onCopyAnalysis: () => void;
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

          <div className="notice">
            Il prezzo di ingresso verrà definito solo dopo la registrazione, su un minuto futuro.
            Stop e obiettivo saranno calcolati dal prezzo effettivo di ingresso.
          </div>

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
        <button className="btn ghost block" onClick={onCopyAnalysis} disabled={busy}>
          Copia analisi
        </button>
      )}

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
                  ['Regola di ingresso', 'Al primo minuto futuro dopo la registrazione'],
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
