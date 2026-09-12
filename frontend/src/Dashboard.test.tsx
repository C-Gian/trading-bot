import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import { LiveChart } from './LiveChart';
import { PaperStatistics } from './PaperStatistics';

const priceLines: { price: number; title: string }[] = [];
const setData = vi.fn();
vi.mock('lightweight-charts', () => ({
  CandlestickSeries: {},
  createChart: () => ({
    addSeries: () => ({ setData, createPriceLine: (line: { price: number; title: string }) => { priceLines.push(line); } }),
    remove: vi.fn(),
  }),
}));

const health = { health: 'fixture-health', status: 'X', project_phase: 'P', development_data_available: true, development_coverage: { start: 'a', end: 'b' }, real_money_authorized: false };
const market = {
  classification: 'CURRENT PUBLIC MARKET DATA — READ ONLY',
  symbol: 'BTCUSDT', interval: '1h', status: 'OK', detail: '2 completed 1h candles',
  candles: [
    { open_time: '2026-03-05T10:00:00Z', open: 49000, high: 50500, low: 48800, close: 50000 },
    { open_time: '2026-03-05T11:00:00Z', open: 50000, high: 51000, low: 49500, close: 50800 },
  ],
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
  ...emptyStats, total_paper_trades: 4, open: 1, active: 1, closed: 3, closed_target: 2, closed_stop: 1,
  expiries: 0, realized_trades: 3, wins: 2, losses: 1, win_rate: 0.6666666,
  mean_realized_r: 0.5, cumulative_realized_r: 1.5, expectancy_r_per_trade: 0.5,
  max_drawdown_r: -1.25, best_realized_r: 2, worst_realized_r: -1, empty: false, empty_detail: null,
};

function mockApi(overrides: Record<string, unknown> = {}) {
  const calls: { url: string; method: string }[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, method: init?.method ?? 'GET' });
    const map: Record<string, unknown> = {
      'system/health': health,
      'research/status': { champion: 'NONE' },
      'research/experiments': { evidence_stage: 'NONE', experiments: [] },
      'product/market/recent': market,
      'paper-trades/statistics': emptyStats,
      ...overrides,
    };
    const key = Object.keys(map).find(k => url.includes(k));
    return { ok: true, json: async () => (key ? map[key] : {}) };
  }));
  return calls;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); priceLines.length = 0; setData.mockClear(); });

describe('V1 dashboard', () => {
  it('renders the chart only after an explicit load and never on mount', async () => {
    mockApi();
    render(<LiveChart plan={null} />);
    expect(setData).not.toHaveBeenCalled();
    expect(screen.getByText('No market data loaded. Click LOAD MARKET.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'LOAD MARKET' }));
    expect(await screen.findByText(/2 completed 1h candles/)).toBeInTheDocument();
    expect(setData).toHaveBeenCalledTimes(1);
    expect(setData.mock.calls[0][0]).toHaveLength(2);
  });

  it('overlays reference, stop and target price lines for the current plan', async () => {
    mockApi();
    render(<LiveChart plan={{ reference: 50000, stop: 49000, target: 52000, source: 'current ALIGNED analysis' }} />);
    await userEvent.click(screen.getByRole('button', { name: 'LOAD MARKET' }));
    await screen.findByText(/2 completed 1h candles/);
    expect(priceLines.map(line => [line.title, line.price])).toEqual([
      ['REFERENCE / ENTRY', 50000], ['STOP', 49000], ['TARGET', 52000],
    ]);
    expect(screen.getByRole('region', { name: 'Current market' })).toHaveTextContent('current ALIGNED analysis');
  });

  it('draws no plan overlay when there is no analysis or active trade', async () => {
    mockApi();
    render(<LiveChart plan={null} />);
    await userEvent.click(screen.getByRole('button', { name: 'LOAD MARKET' }));
    await screen.findByText(/2 completed 1h candles/);
    expect(priceLines).toHaveLength(0);
    expect(screen.getByText(/No plan overlay/)).toBeInTheDocument();
  });

  it('reports unavailable market data without inventing candles', async () => {
    mockApi({ 'product/market/recent': { ...market, status: 'MARKET_DATA_UNAVAILABLE', detail: 'offline', candles: [] } });
    render(<LiveChart plan={null} />);
    await userEvent.click(screen.getByRole('button', { name: 'LOAD MARKET' }));
    expect(await screen.findByText(/Market data unavailable: offline/)).toBeInTheDocument();
    expect(setData).not.toHaveBeenCalled();
  });

  it('shows an explicit empty statistics state', async () => {
    mockApi();
    render(<PaperStatistics />);
    expect(screen.getByText('No statistics loaded. Click LOAD STATISTICS.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'LOAD STATISTICS' }));
    const panel = screen.getByRole('region', { name: 'Paper statistics' });
    expect(await within(panel).findByText(/No terminal paper trade has produced a realized return yet\./)).toBeInTheDocument();
    expect(panel).toHaveTextContent('Total paper trades: 0');
    expect(panel).not.toHaveTextContent('Win rate:');
  });

  it('renders realized statistics with pending and open excluded', async () => {
    mockApi({ 'paper-trades/statistics': filledStats });
    render(<PaperStatistics />);
    await userEvent.click(screen.getByRole('button', { name: 'LOAD STATISTICS' }));
    const panel = screen.getByRole('region', { name: 'Paper statistics' });
    expect(await within(panel).findByText(/Win rate: 66\.7%/)).toBeInTheDocument();
    expect(panel).toHaveTextContent('Total paper trades: 4');
    expect(panel).toHaveTextContent('Realized trades: 3');
    expect(panel).toHaveTextContent('Mean realized R: 0.5000');
    expect(panel).toHaveTextContent('Cumulative realized R: 1.5000');
    expect(panel).toHaveTextContent('Expectancy R/trade: 0.5000');
    expect(panel).toHaveTextContent('Maximum realized drawdown R: -1.2500');
    expect(panel).toHaveTextContent('Pending and open trades are excluded from realized results.');
  });

  it('labels statistics as future paper evidence, never backtest performance', async () => {
    mockApi();
    render(<PaperStatistics />);
    const panel = screen.getByRole('region', { name: 'Paper statistics' });
    expect(panel).toHaveTextContent('FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE');
    expect(panel).toHaveTextContent('NOT CHAMPION · NOT LIVE TRADING');
  });

  it('assembles chart, analysis, paper trades and statistics without running anything on startup', async () => {
    const calls = mockApi();
    render(<App />);
    await screen.findByText(/fixture-health/);
    expect(calls.every(call => call.method === 'GET')).toBe(true);
    expect(calls.some(call => call.url.includes('product/'))).toBe(false);
    expect(setData).not.toHaveBeenCalled();
    for (const name of ['Current market', 'Analyze Market', 'Paper trades', 'Paper statistics']) {
      expect(screen.getByRole('region', { name })).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: 'ANALYZE MARKET' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'LOAD MARKET' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'LOAD STATISTICS' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: /place order|buy|sell|withdraw|deposit|real money|go live/i })).not.toBeInTheDocument();
  });

  it('keeps the paper research and evidence labels across the dashboard', async () => {
    mockApi();
    render(<App />);
    await screen.findByText(/fixture-health/);
    expect(screen.getByRole('region', { name: 'Current market' })).toHaveTextContent('PAPER RESEARCH · NOT LIVE TRADING');
    expect(screen.getByRole('region', { name: 'Analyze Market' })).toHaveTextContent('NOT CHAMPION / NOT LIVE TRADING');
    expect(screen.getByRole('region', { name: 'Paper trades' })).toHaveTextContent('FUTURE PAPER EVIDENCE · PAPER RESEARCH · NOT CHAMPION · NOT LIVE TRADING');
    expect(screen.getByRole('region', { name: 'Paper statistics' })).toHaveTextContent('FUTURE PAPER EVIDENCE — NOT BACKTEST PERFORMANCE');
  });
});
