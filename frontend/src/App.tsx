import { useCallback, useEffect, useState } from 'react';
import {
  Analysis, ExperimentPayload, Health, PaperListing, PaperStatistics, Research,
  advancePaperTrades, analyseMarket, createPaperTrade, readPaperStatistics, readPaperTrades, request,
} from './api';
import { MarketHero, PlanLines } from './MarketHero';
import { Decision } from './Decision';
import { ActiveTrade } from './ActiveTrade';
import { Performance, TradeHistory } from './Performance';
import { Market } from './Market';
import { Advanced, Badge, Empty, KeyValues, Section } from './ui';
import { refusalCopy } from './format';

const PRIMARY = ['Dashboard', 'Trade', 'Risultati'] as const;
const SECONDARY = ['Altro'] as const;
type Page = (typeof PRIMARY)[number] | (typeof SECONDARY)[number];

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

  // Read-only status only. Never analyses and never creates or advances a paper trade.
  useEffect(() => {
    request<Health>('/api/v1/system/health').then(setHealth).catch(() => setHealth(null));
    request<Research>('/api/v1/research/status').then(setResearch).catch(() => setResearch(null));
    request<ExperimentPayload>('/api/v1/research/experiments').then(setExperiments).catch(() => setExperiments(null));
    readPaperTrades().then(setPaper).catch(() => setPaper(null));
    readPaperStatistics().then(setStats).catch(() => setStats(null));
  }, []);

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
  const simulate = () => act(async () => { await createPaperTrade(); await refreshPaper(); }, 'Simulazione creata.');
  const update = () => act(async () => { await advancePaperTrades(); await refreshPaper(); }, 'Simulazione aggiornata.');

  const active = paper?.active?.[0] ?? null;
  const history = paper?.recent ?? [];
  const canSimulate = !active && analysis?.decision === 'LONG' && analysis.data_status === 'OK';
  const blockedReason = active
    ? 'C’è già una simulazione in corso. Aggiornala o aspetta che si chiuda prima di aprirne un’altra.'
    : null;

  const plan: PlanLines = active
    ? {
      reference: active.entry_price ?? active.reference_price,
      stop: active.stop_price, target: active.target_price, origin: 'trade',
    }
    : analysis?.plan
      ? {
        reference: analysis.plan.reference_price,
        stop: analysis.plan.stop_price, target: analysis.plan.target_price, origin: 'analysis',
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
