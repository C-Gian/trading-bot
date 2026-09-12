import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';

const priceLines: { price: number; title: string }[] = [];
const setData = vi.fn();
const removed = vi.fn();
vi.mock('lightweight-charts', () => ({
  CandlestickSeries: {},
  createChart: () => ({
    addSeries: () => ({
      setData,
      createPriceLine: (line: { price: number; title: string }) => { priceLines.push(line); },
    }),
    remove: removed,
  }),
}));

const health = {
  health: 'ok', status: 'STRATEGY_RESEARCH', project_phase: 'STRATEGY_RESEARCH',
  development_data_available: true,
  development_coverage: { start: '2017-08-17T04:00:00Z', end: '2024-12-31T23:59:00Z' },
  real_money_authorized: false,
};
const research = { champion: 'NONE', experiments_completed: 15, evidence: 'NONE' };
const experiments = { evidence_stage: 'NONE', latest_checkpoint: 'WP-010C', next_checkpoint: '—', experiments: [] };
const market = {
  classification: 'CURRENT PUBLIC MARKET DATA — READ ONLY',
  symbol: 'BTCUSDT', interval: '1h', status: 'OK', detail: '3 completed 1h candles',
  candles: [
    { open_time: '2026-03-05T09:00:00Z', open: 48000, high: 49200, low: 47800, close: 49000 },
    { open_time: '2026-03-05T10:00:00Z', open: 49000, high: 50500, low: 48800, close: 50000 },
    { open_time: '2026-03-05T11:00:00Z', open: 50000, high: 51000, low: 49500, close: 50800 },
  ],
};

const analysisBase = {
  analysis_version: 'PAPER_RESEARCH_ANALYSIS_V1',
  classification: 'EXPERIMENTAL PAPER RESEARCH — NOT AN APPROVED LIVE STRATEGY',
  symbol: 'BTCUSDT', strategy_version: 'ALIGNED_PARTICIPATION_CONTINUATION_V1', variant: 'ALIGNED',
  feature_version: 'CONTINUATION_FEATURES_V2', analysis_id: 'a'.repeat(64),
  research_status: 'PAPER_RESEARCH_CANDIDATE', champion_status: 'NONE',
  analysis_time: '2026-03-05T12:30:00Z', signal_time: '2026-03-05T12:00:00Z',
  data_status: 'OK', data_detail: 'completed contiguous lookback available',
  paper_trade_persisted: false, real_money: false,
};
const noTrade = { ...analysisBase, decision: 'NO_TRADE', plan: null };
const longAnalysis = {
  ...analysisBase, decision: 'LONG', reference_price: 50000,
  plan: {
    direction: 'LONG', entry_rule: 'NEXT_1M_OPEN', entry_semantics: 'next completed 1m open',
    execution_model: 'PROSPECTIVE_PAPER_EXECUTION_V1', exit_policy: 'FIXED_TARGET_OR_STOP_OR_24H',
    reference_price: 50000, stop_price: 49000, target_price: 52000,
    stop_fraction: 0.02, target_fraction: 0.04, max_hold_minutes: 1440,
    expiry_time: '2026-03-06T12:00:00Z', leverage: false, short: false, order_placed: false,
  },
};

const openTrade = {
  trade_id: 'PAPER-abc123', evidence_version: 'FUTURE_PAPER_EVIDENCE_V1',
  evidence_stage: 'PROSPECTIVE_PAPER_RESEARCH_NOT_DEVELOPMENT_EVIDENCE',
  analysis_id: 'a'.repeat(64), strategy_version: 'ALIGNED_PARTICIPATION_CONTINUATION_V1',
  variant: 'ALIGNED', research_status: 'PAPER_RESEARCH_CANDIDATE', champion_status: 'NONE',
  symbol: 'BTCUSDT', direction: 'LONG', status: 'OPEN',
  created_at: '2026-03-05T12:30:00Z', signal_time: '2026-03-05T12:00:00Z',
  entry_execution: 'NEXT_1M_OPEN_EXECUTION', entry_minute: '2026-03-05T12:00:00Z',
  ambiguous_fill_policy: 'STOP_FIRST_V1', execution_model_version: 'PROSPECTIVE_PAPER_EXECUTION_V1',
  reference_price: 50000, stop_price: 49000, target_price: 52000, max_hold_minutes: 1440,
  expiry_time: '2026-03-06T12:00:00Z', entry_time: '2026-03-05T12:00:00Z', entry_price: 50010,
  exit_time: null, exit_price: null, exit_reason: null, net_r: null, holding_minutes: null,
  resolution_detail: 'public minute data is incomplete', last_update_time: '2026-03-05T13:00:00Z',
  real_money: false,
};
const wonTrade = {
  ...openTrade, trade_id: 'PAPER-won001', status: 'CLOSED_TARGET',
  exit_time: '2026-03-05T12:03:00Z', exit_price: 52000, exit_reason: 'TARGET',
  net_r: 1.9524, holding_minutes: 3, resolution_detail: 'resolved',
};

const emptyPaper = {
  evidence_version: 'FUTURE_PAPER_EVIDENCE_V1',
  evidence_stage: 'PROSPECTIVE_PAPER_RESEARCH_NOT_DEVELOPMENT_EVIDENCE',
  contract: 'docs/contracts/FUTURE_PAPER_EVIDENCE_V1.md',
  research_status: 'PAPER_RESEARCH_CANDIDATE', champion_status: 'NONE',
  strategy_version: 'ALIGNED_PARTICIPATION_CONTINUATION_V1', max_hold_minutes: 1440,
  statuses: [], active: [], recent: [], recorded: 0, real_money: false,
};
const emptyStats = {
  statistics_version: 'PAPER_STATISTICS_V1', evidence_version: 'FUTURE_PAPER_EVIDENCE_V1',
  evidence_stage: 'PROSPECTIVE_PAPER_RESEARCH_NOT_DEVELOPMENT_EVIDENCE',
  label: 'FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE',
  development_backtest_metrics_included: false,
  total_paper_trades: 0, pending_entry: 0, open: 0, active: 0, closed: 0, invalidated: 0,
  closed_target: 0, closed_stop: 0, expiries: 0, realized_trades: 0, wins: 0, losses: 0, breakeven: 0,
  win_rate: null, mean_realized_r: null, cumulative_realized_r: null, expectancy_r_per_trade: null,
  max_drawdown_r: null, best_realized_r: null, worst_realized_r: null,
  empty: true, empty_detail: 'No terminal paper trade has produced a realized return yet.',
  champion_status: 'NONE', real_money: false,
};
const filledStats = {
  ...emptyStats, total_paper_trades: 4, open: 0, active: 0, closed: 4, closed_target: 3, closed_stop: 1,
  realized_trades: 4, wins: 3, losses: 1, win_rate: 0.75, mean_realized_r: 0.62,
  cumulative_realized_r: 2.48, expectancy_r_per_trade: 0.62, max_drawdown_r: -1.1,
  best_realized_r: 1.95, worst_realized_r: -1.1, empty: false, empty_detail: null,
};

type Calls = { url: string; method: string }[];
function mockApi(overrides: Record<string, unknown> = {}, queues: Record<string, unknown[]> = {}) {
  const calls: Calls = [];
  const base: Record<string, unknown> = {
    'system/health': health,
    'research/status': research,
    'research/experiments': experiments,
    'product/market/recent': market,
    'paper-trades/statistics': emptyStats,
    'paper-trades/lifecycle': { updated: 0, trades: [], errors: [] },
    'product/analysis': noTrade,
    'paper-trades': emptyPaper,
    ...overrides,
  };
  const order = [
    'system/health', 'research/status', 'research/experiments', 'product/market/recent',
    'paper-trades/statistics', 'paper-trades/lifecycle', 'product/analysis', 'paper-trades',
  ];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, method: init?.method ?? 'GET' });
    const key = order.find(candidate => url.includes(candidate));
    if (key && queues[key]?.length) {
      const next = queues[key].shift() as { ok?: boolean; body: unknown };
      return { ok: next.ok !== false, json: async () => next.body };
    }
    return { ok: true, json: async () => (key ? base[key] : {}) };
  }));
  return calls;
}

beforeEach(() => { priceLines.length = 0; setData.mockClear(); removed.mockClear(); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const dashboard = async () => {
  render(<App />);
  await screen.findByText(/Analisi non ancora eseguita/);
};

// ── market ────────────────────────────────────────────────────────────────

describe('mercato', () => {
  it('carica il grafico da solo, senza alcun pulsante di caricamento', async () => {
    mockApi();
    await dashboard();
    await waitFor(() => expect(setData).toHaveBeenCalledTimes(1));
    expect(setData.mock.calls[0][0]).toHaveLength(3);
    expect(screen.queryByRole('button', { name: /carica|load market/i })).not.toBeInTheDocument();
  });

  it('mostra il prezzo corrente e la variazione', async () => {
    mockApi();
    await dashboard();
    const hero = await screen.findByRole('region', { name: 'Andamento Bitcoin' });
    await waitFor(() => expect(hero).toHaveTextContent('50.800,00'));
    expect(hero).toHaveTextContent('Candele orarie');
    expect(hero).toHaveTextContent('+5,83%');
  });

  it('gestisce i dati di mercato non disponibili senza inventare candele', async () => {
    mockApi({ 'product/market/recent': { ...market, status: 'MARKET_DATA_UNAVAILABLE', candles: [] } });
    await dashboard();
    expect(await screen.findByText(/Dati di mercato non disponibili/)).toBeInTheDocument();
    expect(setData).not.toHaveBeenCalled();
  });
});

// ── analisi ───────────────────────────────────────────────────────────────

describe('analisi', () => {
  it('non analizza automaticamente all’avvio', async () => {
    const calls = mockApi();
    await dashboard();
    await waitFor(() => expect(setData).toHaveBeenCalled());
    expect(calls.every(call => call.method === 'GET')).toBe(true);
    expect(calls.some(call => call.url.includes('product/analysis'))).toBe(false);
    expect(screen.getByText(/Il bot non ha ancora valutato le condizioni attuali/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Analizza ora' })).toBeEnabled();
  });

  it('mostra lo stato NESSUN TRADE in parole semplici', async () => {
    mockApi();
    await dashboard();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    const card = screen.getByRole('region', { name: 'Decisione del bot' });
    expect(await within(card).findByText('Nessun trade ora')).toBeInTheDocument();
    expect(card).toHaveTextContent('Le condizioni attuali non soddisfano abbastanza criteri');
    expect(within(card).queryByRole('button', { name: 'Simula questo trade' })).not.toBeInTheDocument();
    expect(card).not.toHaveTextContent('breakout');
    expect(card).not.toHaveTextContent('participation');
  });

  it('mostra il piano LONG con i quattro livelli spiegati', async () => {
    mockApi({ 'product/analysis': longAnalysis });
    await dashboard();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    const card = screen.getByRole('region', { name: 'Decisione del bot' });
    expect(await within(card).findByText('Possibile long')).toBeInTheDocument();
    expect(card).toHaveTextContent('Solo simulazione — nessun denaro reale');
    expect(card).toHaveTextContent('Ingresso');
    expect(card).toHaveTextContent('Prezzo a cui simuliamo l’acquisto');
    expect(card).toHaveTextContent('Se il prezzo scende qui, chiudiamo la simulazione');
    expect(card).toHaveTextContent('Obiettivo');
    expect(card).toHaveTextContent('Scadenza');
    expect(card).toHaveTextContent('50.000,00');
    expect(card).toHaveTextContent('49.000,00');
    expect(card).toHaveTextContent('52.000,00');
  });

  it('sovrappone ingresso, stop e obiettivo sul grafico dopo l’analisi', async () => {
    mockApi({ 'product/analysis': longAnalysis });
    await dashboard();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    await waitFor(() => expect(priceLines.map(line => [line.title, line.price])).toEqual([
      ['Ingresso', 50000], ['Stop', 49000], ['Obiettivo', 52000],
    ]));
  });

  it('non disegna livelli finché non c’è né analisi né simulazione', async () => {
    mockApi();
    await dashboard();
    await waitFor(() => expect(setData).toHaveBeenCalled());
    expect(priceLines).toHaveLength(0);
  });

  it('spiega quando l’analisi non è conclusa per dati incompleti', async () => {
    mockApi({ 'product/analysis': { ...noTrade, data_status: 'INCOMPLETE_MARKET_DATA' } });
    await dashboard();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    expect(await screen.findByText('Analisi non conclusa')).toBeInTheDocument();
  });
});

// ── simulazione ───────────────────────────────────────────────────────────

describe('simulazione', () => {
  it('offre «Simula questo trade» solo quando la creazione è permessa', async () => {
    mockApi({ 'product/analysis': longAnalysis });
    await dashboard();
    expect(screen.queryByRole('button', { name: 'Simula questo trade' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    expect(await screen.findByRole('button', { name: 'Simula questo trade' })).toBeEnabled();
  });

  it('nasconde la simulazione e spiega il motivo quando una è già in corso', async () => {
    mockApi({
      'product/analysis': longAnalysis,
      'paper-trades': { ...emptyPaper, active: [openTrade], recent: [openTrade], recorded: 1 },
    });
    await dashboard();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    await screen.findByText('Possibile long');
    expect(screen.queryByRole('button', { name: 'Simula questo trade' })).not.toBeInTheDocument();
    expect(screen.getByText(/C’è già una simulazione in corso/)).toBeInTheDocument();
  });

  it('crea la simulazione solo su clic esplicito', async () => {
    const calls = mockApi({ 'product/analysis': longAnalysis }, {
      'paper-trades': [
        { body: emptyPaper },
        { body: { trade: openTrade } },
        { body: { ...emptyPaper, active: [openTrade], recent: [openTrade], recorded: 1 } },
      ],
    });
    await dashboard();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    expect(calls.filter(call => call.method === 'POST' && call.url.endsWith('paper-trades'))).toHaveLength(0);
    await userEvent.click(await screen.findByRole('button', { name: 'Simula questo trade' }));
    await waitFor(() => expect(
      calls.filter(call => call.method === 'POST' && call.url.endsWith('/paper-trades')),
    ).toHaveLength(1));
  });
});

// ── trade attivo ──────────────────────────────────────────────────────────

describe('trade attivo', () => {
  it('mostra lo stato in parole semplici con i livelli', async () => {
    mockApi({ 'paper-trades': { ...emptyPaper, active: [openTrade], recent: [openTrade], recorded: 1 } });
    await dashboard();
    const panel = await screen.findByRole('region', { name: 'Simulazione in corso' });
    expect(within(panel).getByText('Trade attivo')).toBeInTheDocument();
    expect(panel).toHaveTextContent('Ingresso simulato');
    expect(panel).toHaveTextContent('50.010,00');
    expect(panel).toHaveTextContent('49.000,00');
    expect(panel).toHaveTextContent('52.000,00');
    expect(panel).toHaveTextContent('Scadenza');
    expect(panel).toHaveTextContent(/l’aggiornamento è manuale/);
  });

  it('aggiorna il ciclo di vita solo su clic esplicito', async () => {
    const calls = mockApi({ 'paper-trades': { ...emptyPaper, active: [openTrade], recent: [openTrade], recorded: 1 } });
    await dashboard();
    await screen.findByRole('region', { name: 'Simulazione in corso' });
    expect(calls.some(call => call.url.includes('lifecycle'))).toBe(false);
    await userEvent.click(screen.getByRole('button', { name: 'Aggiorna trade' }));
    await waitFor(() => expect(
      calls.filter(call => call.url.includes('lifecycle') && call.method === 'POST'),
    ).toHaveLength(1));
  });

  it('mostra un trade chiuso con esito e risultato', async () => {
    mockApi({ 'paper-trades': { ...emptyPaper, active: [], recent: [wonTrade], recorded: 1 } });
    await dashboard();
    const history = await screen.findByRole('region', { name: 'Simulazioni recenti' });
    expect(history).toHaveTextContent('Chiuso in profitto');
    expect(history).toHaveTextContent('+1,95 R');
    expect(history).toHaveTextContent('52.000,00');
    expect(screen.queryByRole('button', { name: 'Aggiorna trade' })).not.toBeInTheDocument();
  });

  it('usa i livelli della simulazione in corso sul grafico', async () => {
    mockApi({ 'paper-trades': { ...emptyPaper, active: [openTrade], recent: [openTrade], recorded: 1 } });
    await dashboard();
    await waitFor(() => expect(priceLines.map(line => line.price)).toEqual([50010, 49000, 52000]));
  });
});

// ── andamento ─────────────────────────────────────────────────────────────

describe('andamento', () => {
  it('non mostra metriche a zero quando non ci sono risultati', async () => {
    mockApi();
    await dashboard();
    const panel = await screen.findByRole('region', { name: 'Andamento' });
    expect(within(panel).getByText('Nessun risultato ancora')).toBeInTheDocument();
    expect(panel).toHaveTextContent('Le statistiche appariranno dopo i primi paper trade completati.');
    expect(panel).not.toHaveTextContent('0,00 R');
    expect(panel).not.toHaveTextContent('Media per trade');
  });

  it('mostra le statistiche quando esistono risultati', async () => {
    mockApi({ 'paper-trades/statistics': filledStats });
    await dashboard();
    const panel = await screen.findByRole('region', { name: 'Andamento' });
    expect(panel).toHaveTextContent('Trade completati');
    expect(panel).toHaveTextContent('Vinti / Persi');
    expect(panel).toHaveTextContent('3 / 1');
    expect(panel).toHaveTextContent('75% di successo');
    expect(panel).toHaveTextContent('+0,62 R');
    expect(panel).toHaveTextContent('+2,48 R');
    expect(panel).toHaveTextContent('Le simulazioni ancora aperte non entrano in questi numeri.');
  });

  it('mostra una cronologia vuota in modo esplicito', async () => {
    mockApi();
    await dashboard();
    const history = await screen.findByRole('region', { name: 'Simulazioni recenti' });
    expect(within(history).getByText('Nessuna simulazione')).toBeInTheDocument();
  });
});

// ── linguaggio, sicurezza, dettagli avanzati ──────────────────────────────

describe('linguaggio e sicurezza', () => {
  it('tiene i dettagli tecnici chiusi per impostazione predefinita', async () => {
    mockApi({
      'product/analysis': longAnalysis,
      'paper-trades/statistics': filledStats,
      'paper-trades': { ...emptyPaper, active: [openTrade], recent: [openTrade], recorded: 1 },
    });
    await dashboard();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    await screen.findByText('Possibile long');
    const disclosures = screen.getAllByText('Dettagli avanzati');
    expect(disclosures.length).toBeGreaterThan(0);
    for (const summary of disclosures) {
      expect(summary.closest('details')).not.toHaveAttribute('open');
    }
    // Jargon may live inside the collapsed disclosures, never outside them.
    for (const jargon of [
      /PAPER_RESEARCH_CANDIDATE/, /FUTURE_PAPER_EVIDENCE_V1/, /PROSPECTIVE_PAPER_EXECUTION_V1/,
      /NOT CHAMPION/, /STOP_FIRST_V1/, /NEXT_1M_OPEN/,
    ]) {
      for (const node of screen.queryAllByText(jargon)) {
        expect(node.closest('details.advanced')).not.toBeNull();
      }
    }
  });

  it('rivela i dettagli tecnici solo quando l’utente li apre', async () => {
    mockApi({ 'product/analysis': longAnalysis });
    await dashboard();
    await userEvent.click(screen.getByRole('button', { name: 'Analizza ora' }));
    await screen.findByText('Possibile long');
    const card = screen.getByRole('region', { name: 'Decisione del bot' });
    await userEvent.click(within(card).getByText('Dettagli avanzati'));
    expect(within(card).getByText(/ALIGNED_PARTICIPATION_CONTINUATION_V1/)).toBeInTheDocument();
  });

  it('mostra un solo avviso paper persistente e nessun controllo di denaro reale', async () => {
    mockApi();
    await dashboard();
    expect(screen.getAllByText('Paper — nessun denaro reale')).toHaveLength(1);
    expect(screen.getByText(/Nessun ordine viene inviato a una borsa/)).toBeInTheDocument();
    expect(screen.queryByRole('button', {
      name: /compra|vendi|ordine|preleva|deposita|denaro reale|live/i,
    })).not.toBeInTheDocument();
  });

  it('non esegue nessuna azione di trading in background', async () => {
    const calls = mockApi();
    await dashboard();
    await waitFor(() => expect(setData).toHaveBeenCalled());
    await new Promise(resolve => setTimeout(resolve, 60));
    expect(calls.every(call => call.method === 'GET')).toBe(true);
    expect(calls.some(call => call.url.includes('lifecycle'))).toBe(false);
    expect(calls.some(call => call.url.includes('product/analysis'))).toBe(false);
  });
});

// ── navigazione ───────────────────────────────────────────────────────────

describe('navigazione', () => {
  it('separa il flusso di prodotto dalle sezioni avanzate', async () => {
    mockApi();
    await dashboard();
    const nav = screen.getByRole('navigation', { name: 'Navigazione principale' });
    for (const item of ['Dashboard', 'Trade', 'Andamento']) {
      expect(within(nav).getByRole('button', { name: item })).toBeInTheDocument();
    }
    expect(within(nav).getByRole('button', { name: 'Ricerca' })).toHaveClass('secondary');
    expect(within(nav).getByRole('button', { name: 'Sistema' })).toHaveClass('secondary');
    expect(within(nav).getByRole('button', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page');
  });

  it('apre Trade e Andamento senza analizzare nulla', async () => {
    const calls = mockApi({ 'paper-trades/statistics': filledStats });
    await dashboard();
    const nav = screen.getByRole('navigation', { name: 'Navigazione principale' });
    await userEvent.click(within(nav).getByRole('button', { name: 'Trade' }));
    expect(await screen.findByText('Tutto fermo')).toBeInTheDocument();
    await userEvent.click(within(nav).getByRole('button', { name: 'Andamento' }));
    expect(await screen.findByText('Trade completati')).toBeInTheDocument();
    expect(calls.some(call => call.url.includes('product/analysis'))).toBe(false);
  });

  it('tiene i contenuti scientifici nella sezione Ricerca', async () => {
    mockApi();
    await dashboard();
    const nav = screen.getByRole('navigation', { name: 'Navigazione principale' });
    await userEvent.click(within(nav).getByRole('button', { name: 'Ricerca' }));
    const panel = await screen.findByRole('region', { name: 'Stato scientifico' });
    expect(panel).toHaveTextContent('Champion');
    expect(panel).toHaveTextContent('NONE');
    expect(panel).toHaveTextContent('Esperimenti completati');
  });
});
