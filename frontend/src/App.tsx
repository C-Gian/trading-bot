import { useCallback, useEffect, useState } from 'react';
import {
  Analysis, ExperimentPayload, Health, PaperListing, PaperStatistics, Research,
  ResearchRunnerPayload, ResearchRun, ResearchRunnerCandidate,
  advancePaperTrades, analyseMarket, createPaperTrade, readPaperStatistics, readPaperTrades, request,
  readResearchRunner, readResearchRun, startResearchRun,
} from './api';
import { MarketHero, PlanLines } from './MarketHero';
import { Decision } from './Decision';
import { ActiveTrade } from './ActiveTrade';
import { Performance, TradeHistory } from './Performance';
import { Market } from './Market';
import { Advanced, Badge, Empty, KeyValues, Section } from './ui';
import { refusalCopy } from './format';

const PRIMARY = ['Dashboard', 'Trade', 'Risultati'] as const;
const SECONDARY = ['Research', 'Altro'] as const;
type Page = (typeof PRIMARY)[number] | (typeof SECONDARY)[number];

function researchMetric(value: number|null|undefined, suffix = ' R/trade') {
  return value == null ? '—' : `${value >= 0 ? '+' : ''}${value.toFixed(4)}${suffix}`;
}

function ResearchLab({
  candidates, candidate, run, onSelect, onStart, onCopy,
}: {
  candidates: ResearchRunnerCandidate[]; candidate: ResearchRunnerCandidate|null; run: ResearchRun|null;
  onSelect: (candidateId: string) => void;
  onStart: () => void; onCopy: () => void;
}) {
  const running = run?.status === 'RUNNING' || run?.status === 'QUEUED';
  const completed = run?.status === 'COMPLETED' && run.result;
  const failed = run?.status === 'FAILED';
  const stage = run?.stage ?? (candidate ? 'READY' : 'VALIDATING_INPUTS');
  return (
    <>
      <div className="pagehead research-head">
        <div>
          <p className="eyebrow">Laboratorio locale</p>
          <h1>Research Lab</h1>
          <p className="lede">Esegui localmente un candidato scientifico già preparato e congelato.</p>
        </div>
        <Badge tone="paper">Solo ricerca · nessun denaro reale</Badge>
      </div>
      <section className="research-grid" aria-label="Research Lab">
        <Section title="Candidato disponibile" label="Candidato disponibile" hint="Allowlist locale">
          <div className="pad research-candidate">
            {candidate ? (
              <>
                {candidates.length > 1 && <label className="research-picker">
                  <span>Candidato</span>
                  <select value={candidate.candidate_id} onChange={event => onSelect(event.target.value)} disabled={running}>
                    {candidates.map(item => <option key={item.candidate_id} value={item.candidate_id}>{item.display_name}{item.run_type === 'REPRODUCTION_ONLY' ? ' · storico' : ''}</option>)}
                  </select>
                </label>}
                <div className="row research-candidate-title">
                  <div className="grow"><h3>{candidate.display_name}</h3><p className="summary">{candidate.purpose}</p></div>
                  <Badge tone="neutral">{candidate.status}</Badge>
                </div>
                <p className="research-warning">{candidate.scientific_warning}</p>
                <p className="summary">{candidate.run_type === 'NEW_EXPERIMENT'
                  ? 'Esperimento di sviluppo preregistrato. Il risultato richiederà review e non crea evidenza sigillata.'
                  : 'Riproduzione storica: non cambia i contatori scientifici e non crea evidenza sigillata.'}</p>
                <button className="btn primary block research-cta" onClick={onStart} disabled={running || !candidate.required_data.ready || !candidate.runnable}>
                  {running ? 'TEST IN CORSO…' : 'AVVIA TEST STORICO'}
                </button>
                <p className="research-local-note">Il test viene eseguito localmente sul tuo PC. Non usa AI durante il calcolo.</p>
                {!candidate.required_data.ready && <p className="notice warn">Dati locali richiesti non pronti: il test non può partire.</p>}
                {!candidate.runnable && <p className="notice warn">Questo candidato è bloccato dal gate retrospettivo e non può essere eseguito.</p>}
              </>
            ) : <Empty title="Nessun candidato disponibile" body="Il registro locale non è raggiungibile." />}
          </div>
        </Section>

        <Section title={running ? 'Esecuzione in corso' : completed ? 'Risultato' : failed ? 'Esecuzione interrotta' : 'Stato del test'} label="Stato del test">
          <div className="pad research-status">
            {running && <>
              <div className="research-progress-label"><strong>{stage.replaceAll('_', ' ')}</strong><span>{Math.round(run?.progress ?? 0)}%</span></div>
              <div className="research-progress" role="progressbar" aria-valuenow={Math.round(run?.progress ?? 0)} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${Math.max(0, Math.min(100, run?.progress ?? 0))}%` }} /></div>
              <p className="summary">{run?.detail ?? 'Preparazione deterministica'} · Tempo: {Math.floor(run?.elapsed_seconds ?? 0)} s · Puoi lasciare aperta questa pagina.</p>
            </>}
            {!running && !completed && !failed && <p className="summary">Pronto. Il calcolo parte solo dopo il tuo clic e usa esclusivamente il runner deterministico locale.</p>}
            {failed && <div className="research-failure"><Badge tone="neg">{run?.status}</Badge><p>{run?.error ?? 'Il test è stato interrotto. Nessun risultato scientifico è stato modificato.'}</p></div>}
            {completed && run.result && <>
              <div className="research-results-grid">
                <div><span>Expectancy netta</span><strong className={run.result.default_expectancy_r != null && run.result.default_expectancy_r >= 0 ? 'pos' : 'neg'}>{researchMetric(run.result.default_expectancy_r)}</strong></div>
                <div><span>Trade</span><strong>{run.result.trade_count ?? '—'}</strong></div>
                <div><span>Anni / fold positivi</span><strong>{run.result.nonnegative_folds ?? '—'} / {run.result.fold_count ?? '—'}</strong></div>
                <div><span>Stress costi</span><strong>{researchMetric(run.result.double_cost_expectancy_r)}</strong></div>
                <div><span>Confronto controllo</span><strong>{researchMetric(run.result.primary_minus_control_r)}</strong></div>
                <div><span>Verdetto</span><strong>{run.result.verdict}</strong></div>
              </div>
              <div className="row research-actions"><button className="btn primary" onClick={onCopy}>COPIA RISULTATO PER REVIEW</button><Badge tone="neutral">{candidate?.run_type === 'NEW_EXPERIMENT' ? 'Sviluppo · review richiesta' : 'Riproduzione · non nuova evidenza'}</Badge></div>
              <Advanced>
                <div className="pad research-details"><KeyValues rows={[
                  ['Run ID', run.run_id], ['Codice', run.result.code_head ?? '—'], ['Zero costi', researchMetric(run.result.zero_cost_expectancy_r)],
                  ['Delay 1h', researchMetric(run.result.delay_expectancy_r)], ['Controllo default', researchMetric(run.result.control_default_expectancy_r)],
                  ['Correlazione OOS', run.result.oos_correlation == null ? '—' : run.result.oos_correlation.toFixed(4)], ['Riconciliazione', run.result.reconciliation_status],
                  ['Runtime', run.result.runtime_version ?? candidate?.runtime_version ?? 'Runtime storico non dichiarato'],
                  ['Tempi per fase', run.result.stage_timings?.stage_order.map(stage => `${stage}: ${run.result?.stage_timings?.duration_seconds[stage].toFixed(3)} s`).join(' · ') ?? 'Non disponibili per il runtime storico'],
                  ['Tipo evidenza', run.result.scientific_evidence_type], ['Dataset', Object.entries(run.result.dataset_identities ?? {}).map(([key, value]) => `${key}: ${value}`).join(' · ') || '—'],
                  ['Hash riproduzione', Object.entries(run.result.runtime_artifact_hashes ?? {}).map(([key, value]) => `${key}: ${value}`).join(' · ') || '—'],
                ]} /></div>
              </Advanced>
            </>}
          </div>
        </Section>
      </section>
    </>
  );
}

export function App() {
  const [page, setPage] = useState<Page>('Dashboard');
  const [health, setHealth] = useState<Health | null>();
  const [research, setResearch] = useState<Research | null>(null);
  const [experiments, setExperiments] = useState<ExperimentPayload | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [paper, setPaper] = useState<PaperListing | null>(null);
  const [stats, setStats] = useState<PaperStatistics | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [runner, setRunner] = useState<ResearchRunnerPayload | null>(null);
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  // Read-only status only. Never analyses and never creates or advances a paper trade.
  useEffect(() => {
    request<Health>('/api/v1/system/health').then(setHealth).catch(() => setHealth(null));
    request<Research>('/api/v1/research/status').then(setResearch).catch(() => setResearch(null));
    request<ExperimentPayload>('/api/v1/research/experiments').then(setExperiments).catch(() => setExperiments(null));
    readPaperTrades().then(setPaper).catch(() => setPaper(null));
    readPaperStatistics().then(setStats).catch(() => setStats(null));
    readResearchRunner().then(payload => {
      setRunner(payload);
      setRun(payload.current_or_last_run ?? null);
      const active = payload.current_or_last_run;
      setSelectedCandidateId(
        active && ['QUEUED', 'RUNNING'].includes(active.status)
          ? active.candidate_id
          : (payload.candidates.find(item => item.runnable) ?? payload.candidates[0])?.candidate_id ?? null,
      );
    }).catch(() => setRunner(null));
  }, []);

  useEffect(() => {
    if (page !== 'Research' || !run || !['QUEUED', 'RUNNING'].includes(run.status)) return undefined;
    const timer = window.setInterval(() => {
      readResearchRun(run.run_id).then(setRun).catch(() => undefined);
    }, 800);
    return () => window.clearInterval(timer);
  }, [page, run?.run_id, run?.status]);

  const refreshPaper = useCallback(async () => {
    setPaper(await readPaperTrades().catch(() => null));
    setStats(await readPaperStatistics().catch(() => null));
  }, []);

  const act = useCallback(async (action: () => Promise<unknown>, done: string | null) => {
    setBusy(true);
    setNotice(null);
    try {
      await action();
      if (done) setNotice(done);
    } catch (error) {
      setNotice(refusalCopy(error instanceof Error ? error.message : ''));
    } finally {
      setBusy(false);
    }
  }, []);

  const analyze = () => act(async () => setAnalysis(await analyseMarket()), null);
  const simulate = () => act(async () => { await createPaperTrade(); await refreshPaper(); }, 'Paper LONG registrato. Ingresso in attesa.');
  const update = () => act(async () => { await advancePaperTrades(); await refreshPaper(); }, 'Simulazione aggiornata.');
  const candidates = runner?.candidates ?? [];
  const candidate: ResearchRunnerCandidate | null = candidates.find(item => item.candidate_id === selectedCandidateId) ?? candidates[0] ?? null;
  const selectedRun = run?.candidate_id === candidate?.candidate_id ? run : null;
  const startResearch = async () => {
    if (!candidate || run?.status === 'RUNNING' || run?.status === 'QUEUED') return;
    setNotice(null);
    try {
      const started = await startResearchRun(candidate.candidate_id);
      setRun(started);
    } catch (error) {
      setNotice(refusalCopy(error instanceof Error ? error.message : 'Avvio non riuscito'));
    }
  };
  const copyReview = async () => {
    if (!run?.review_bundle) return;
    try {
      await navigator.clipboard.writeText(run.review_bundle);
      setNotice('Risultato copiato per la review.');
    } catch {
      setNotice('Impossibile copiare il risultato.');
    }
  };

  const active = paper?.active?.[0] ?? null;
  const history = paper?.recent ?? [];
  const paperEntryEnabled = paper?.paper_entry_status === 'AVAILABLE';
  const canSimulate = paperEntryEnabled && !active && analysis?.decision === 'LONG' && analysis.data_status === 'OK';
  const blockedReason = active
    ? 'C’è già una simulazione in corso. Aggiornala o aspetta che si chiuda prima di aprirne un’altra.'
    : paper?.paper_entry_block_reason ?? null;

  const plan: PlanLines = active?.entry_price != null && active.stop_price != null && active.target_price != null
    ? {
      reference: active.entry_price,
      stop: active.stop_price, target: active.target_price, origin: 'trade',
    }
    : null;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <b>Trading Bot</b>
          <span className="pair">BTCUSDT</span>
        </div>
        <Badge tone="paper">Paper — nessun denaro reale</Badge>
        <nav aria-label="Navigazione principale">
          {PRIMARY.map(item => (
            <button
              key={item}
              className="navlink"
              aria-current={page === item ? 'page' : undefined}
              onClick={() => setPage(item)}
            >
              {item}
            </button>
          ))}
          <span className="navsplit" aria-hidden="true" />
          {SECONDARY.map(item => (
            <button
              key={item}
              className="navlink secondary"
              aria-current={page === item ? 'page' : undefined}
              onClick={() => setPage(item)}
            >
              {item}
            </button>
          ))}
        </nav>
      </header>

      <main className="page">
        {notice && <p className="notice" role="status">{notice}</p>}

        {page === 'Dashboard' && (
          <>
            <div className="hero">
              <MarketHero plan={plan} />
              <Decision
                analysis={analysis}
                busy={busy}
                canSimulate={Boolean(canSimulate)}
                blockedReason={blockedReason}
                onAnalyze={analyze}
                onSimulate={simulate}
              />
            </div>
            {active && <ActiveTrade trade={active} busy={busy} onUpdate={update} />}
            <Performance stats={stats} />
            <TradeHistory trades={history} />
            <p className="footnote">
              Strategia sperimentale in modalità paper. Nessun ordine viene inviato a una borsa e
              nessun denaro reale è coinvolto.
            </p>
          </>
        )}

        {page === 'Trade' && (
          <>
            <div className="pagehead">
              <div>
                <h1>Trade</h1>
                <p className="lede">Le tue simulazioni, dalla più recente.</p>
              </div>
              <Badge tone="paper">Risultati simulati</Badge>
            </div>
            {active ? (
              <ActiveTrade trade={active} busy={busy} onUpdate={update} />
            ) : (
              <Section title="Nessuna simulazione in corso" label="Nessuna simulazione in corso">
                <Empty
                  title="Tutto fermo"
                  body="Vai alla Dashboard e premi «Analizza ora» per vedere se il bot propone un ingresso."
                />
              </Section>
            )}
            <TradeHistory trades={history} />
          </>
        )}

        {page === 'Risultati' && (
          <>
            <div className="pagehead">
              <div>
                <h1>Risultati</h1>
                <p className="lede">Come sono andate le simulazioni completate finora.</p>
              </div>
              <Badge tone="paper">Risultati simulati</Badge>
            </div>
            <Performance stats={stats} />
            <TradeHistory trades={history} />
          </>
        )}

        {page === 'Research' && <ResearchLab candidates={candidates} candidate={candidate} run={selectedRun} onSelect={setSelectedCandidateId} onStart={startResearch} onCopy={copyReview} />}

        {page === 'Altro' && (
          <>
            <div className="pagehead">
              <div>
                <h1>Altro</h1>
                <p className="lede">
                  Area tecnica: studi storici di laboratorio e stato dell’applicazione. Non serve
                  per l’uso normale.
                </p>
              </div>
            </div>
            <Section title="Stato scientifico" label="Stato scientifico">
              <div className="pad">
                <KeyValues
                  rows={[
                    ['Champion', research?.champion ?? 'NONE'],
                    ['Esperimenti completati', research?.experiments_completed ?? 0],
                    ['Evidenza prospettica', research?.evidence ?? 'NONE'],
                    ['Stadio evidenza', experiments?.evidence_stage ?? 'NONE'],
                    ['Famiglia selezionata', research?.selected_family?.name ?? '—'],
                    ['Classificazione', research?.selected_family?.terminal_classification ?? '—'],
                  ]}
                />
                <Advanced>
                  <KeyValues
                    rows={[
                      ['Motore backtest', research?.engine_version ?? '—'],
                      ['Modello esecuzione', research?.execution_model_version ?? '—'],
                      ['Modello costi', research?.cost_model_version ?? '—'],
                      ['Validazione sintetica', research?.synthetic_validation ?? '—'],
                      ['Memoria di ricerca', research?.search_memory?.version ?? '—'],
                      ['Famiglie tracciate', research?.search_memory?.families_tracked ?? '—'],
                      ['Ipotesi economiche', research?.adaptive_search?.material_economic_hypotheses ?? '—'],
                      ['Configurazioni', research?.adaptive_search?.configuration_variants ?? '—'],
                      ['Prove di profilo', research?.adaptive_search?.profile_trials ?? '—'],
                      ['Challenger supervisionato', research?.supervised_challenger?.version ?? '—'],
                      ['Esito challenger', research?.supervised_challenger?.terminal_classification ?? '—'],
                      ['Valutazione sigillata', research?.sealed_evaluation?.status ?? '—'],
                      ['Query sigillate consumate', research?.sealed_evaluation?.consumed_btc_queries ?? '—'],
                    ]}
                  />
                </Advanced>
              </div>
            </Section>
            <Section title="Dati storici di sviluppo" label="Dati storici di sviluppo">
              <div className="pad">
                <Market available={health?.development_data_available === true} />
              </div>
            </Section>
            <Section title="Stato" label="Stato">
              <div className="pad">
                <KeyValues
                  rows={[
                    ['Servizio', health === undefined ? 'verifica…' : (health?.health ?? 'non raggiungibile')],
                    ['Fase progetto', health?.project_phase ?? '—'],
                    ['Stato', health?.status ?? '—'],
                    ['Dati storici installati', health?.development_data_available ? 'sì' : 'no'],
                    ['Denaro reale autorizzato', health?.real_money_authorized ? 'sì' : 'no'],
                  ]}
                />
              </div>
            </Section>
          </>
        )}

      </main>
    </div>
  );
}
