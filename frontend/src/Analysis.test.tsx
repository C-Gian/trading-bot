import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AnalyzeMarket } from './Analysis';

const base = {
  analysis_version: 'PAPER_RESEARCH_ANALYSIS_V1',
  classification: 'EXPERIMENTAL PAPER RESEARCH — NOT AN APPROVED LIVE STRATEGY',
  symbol: 'BTCUSDT',
  strategy_version: 'ALIGNED_PARTICIPATION_CONTINUATION_V1',
  variant: 'ALIGNED',
  feature_version: 'CONTINUATION_FEATURES_V2',
  research_status: 'PAPER_RESEARCH_CANDIDATE',
  champion_status: 'NONE',
  analysis_time: '2026-03-05T12:30:00Z',
  signal_time: '2026-03-05T12:00:00Z',
  data_status: 'OK',
  data_detail: 'completed contiguous lookback available',
  paper_trade_persisted: false,
  real_money: false,
  paper_trades_completed: 0,
  real_money_authorized: false,
};
const noTrade = { ...base, decision: 'NO_TRADE', plan: null };
const long = {
  ...base,
  decision: 'LONG',
  reference_price: 50000,
  plan: {
    direction: 'LONG', entry_rule: 'NEXT_1M_OPEN',
    entry_semantics: 'Paper entry at the next completed 1m open after the signal hour.',
    execution_model: 'EXECUTION_MODEL_V2', exit_policy: 'FIXED_TARGET_OR_STOP_OR_24H',
    reference_price: 50000, stop_price: 49000, target_price: 52000,
    stop_fraction: 0.02, target_fraction: 0.04, max_hold_minutes: 1440,
    expiry_time: '2026-03-06T12:00:00Z', leverage: false, short: false, order_placed: false,
  },
};
const incomplete = { ...base, data_status: 'INCOMPLETE_MARKET_DATA', data_detail: 'received 4/26 hourly and 44/44 four-hour completed bars', signal_time: null, decision: 'NO_TRADE', plan: null };

function mockAnalysis(payload: unknown, ok = true) {
  const fetcher = vi.fn(async (_url: string, init?: RequestInit) => { void _url; void init; if (!ok) throw new Error('offline'); return { ok: true, json: async () => payload }; });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('Analyze Market paper research', () => {
  it('does not analyse until the user asks', async () => {
    const fetcher = mockAnalysis(noTrade);
    render(<AnalyzeMarket />);
    expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getByText(/No analysis has been run/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'ANALYZE MARKET' }));
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toBe('/api/v1/product/analysis');
    expect(fetcher.mock.calls[0][1]).toMatchObject({ method: 'POST' });
  });

  it('labels the surface as paper research that is not a champion or live', async () => {
    mockAnalysis(noTrade);
    render(<AnalyzeMarket />);
    const panel = screen.getByRole('region', { name: 'Analyze Market' });
    expect(panel).toHaveTextContent('EXPERIMENTAL PAPER RESEARCH — NOT AN APPROVED LIVE STRATEGY');
    expect(panel).toHaveTextContent('NOT CHAMPION / NOT LIVE TRADING');
  });

  it('shows a NO_TRADE result with its research labels', async () => {
    mockAnalysis(noTrade);
    render(<AnalyzeMarket />);
    await userEvent.click(screen.getByRole('button', { name: 'ANALYZE MARKET' }));
    const panel = screen.getByRole('region', { name: 'Analyze Market' });
    expect(await screen.findByText('NO_TRADE')).toBeInTheDocument();
    expect(panel).toHaveTextContent('BTCUSDT · PAPER RESEARCH · ALIGNED candidate · PAPER_RESEARCH_CANDIDATE');
    expect(panel).toHaveTextContent('Champion: NONE');
    expect(panel).toHaveTextContent('2026-03-05T12:30:00Z');
    expect(panel).toHaveTextContent('Paper trade persisted: no · Order placed: no · Real money: no');
  });

  it('shows a LONG paper plan with entry, stop, target and expiry', async () => {
    mockAnalysis(long);
    render(<AnalyzeMarket />);
    await userEvent.click(screen.getByRole('button', { name: 'ANALYZE MARKET' }));
    const panel = screen.getByRole('region', { name: 'Analyze Market' });
    expect(await screen.findByText('LONG (paper only)')).toBeInTheDocument();
    expect(panel).toHaveTextContent('Reference: 50,000.00');
    expect(panel).toHaveTextContent('Entry: NEXT_1M_OPEN');
    expect(panel).toHaveTextContent('Stop: 49,000.00 (2%)');
    expect(panel).toHaveTextContent('Target: 52,000.00 (4%)');
    expect(panel).toHaveTextContent('Expiry: 2026-03-06T12:00:00Z (1440 minutes maximum hold)');
    expect(panel).toHaveTextContent('NOT CHAMPION / NOT LIVE TRADING');
  });

  it('fails closed to NO_TRADE when market data is incomplete', async () => {
    mockAnalysis(incomplete);
    render(<AnalyzeMarket />);
    await userEvent.click(screen.getByRole('button', { name: 'ANALYZE MARKET' }));
    expect(await screen.findByText('NO_TRADE')).toBeInTheDocument();
    const panel = screen.getByRole('region', { name: 'Analyze Market' });
    expect(panel).toHaveTextContent('INCOMPLETE_MARKET_DATA');
    expect(panel).not.toHaveTextContent('LONG (paper only)');
  });

  it('shows no trade plan when the request fails', async () => {
    mockAnalysis(noTrade, false);
    render(<AnalyzeMarket />);
    await userEvent.click(screen.getByRole('button', { name: 'ANALYZE MARKET' }));
    expect(await screen.findByText(/Analysis unavailable\. No trade plan is implied\./)).toBeInTheDocument();
  });

  it('offers no order, buy, sell or real-money control', async () => {
    mockAnalysis(long);
    render(<AnalyzeMarket />);
    await userEvent.click(screen.getByRole('button', { name: 'ANALYZE MARKET' }));
    await screen.findByText('LONG (paper only)');
    expect(screen.queryByRole('button', { name: /real money|place order|buy|sell|execute|confirm trade/i })).not.toBeInTheDocument();
    expect(screen.getAllByRole('button')).toHaveLength(1);
  });
});
