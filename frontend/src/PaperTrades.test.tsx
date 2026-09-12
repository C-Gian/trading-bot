import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PaperTrades } from './PaperTrades';
import { App } from './App';

const pending = {
  trade_id: 'PAPER-abc123',
  evidence_version: 'FUTURE_PAPER_EVIDENCE_V1',
  evidence_stage: 'PROSPECTIVE_PAPER_RESEARCH_NOT_DEVELOPMENT_EVIDENCE',
  analysis_id: 'a'.repeat(64),
  strategy_version: 'ALIGNED_PARTICIPATION_CONTINUATION_V1',
  variant: 'ALIGNED',
  research_status: 'PAPER_RESEARCH_CANDIDATE',
  champion_status: 'NONE',
  symbol: 'BTCUSDT',
  direction: 'LONG',
  status: 'PENDING_ENTRY',
  created_at: '2026-03-05T12:30:00Z',
  signal_time: '2026-03-05T12:00:00Z',
  entry_execution: 'NEXT_1M_OPEN_EXECUTION',
  entry_minute: '2026-03-05T12:00:00Z',
  ambiguous_fill_policy: 'STOP_FIRST_V1',
  execution_model_version: 'PROSPECTIVE_PAPER_EXECUTION_V1',
  reference_price: 50000,
  stop_price: 49000,
  target_price: 52000,
  max_hold_minutes: 1440,
  expiry_time: '2026-03-06T12:00:00Z',
  entry_time: null,
  entry_price: null,
  exit_time: null,
  exit_price: null,
  exit_reason: null,
  net_r: null,
  holding_minutes: null,
  resolution_detail: 'awaiting the next 1m open after the signal hour',
  last_update_time: '2026-03-05T12:30:00Z',
  real_money: false,
};
const closed = {
  ...pending,
  status: 'CLOSED_TARGET',
  entry_time: '2026-03-05T12:00:00Z',
  entry_price: 50000,
  exit_time: '2026-03-05T12:03:00Z',
  exit_price: 52000,
  exit_reason: 'TARGET',
  net_r: 1.9524,
  holding_minutes: 3,
  resolution_detail: 'resolved by PROSPECTIVE_PAPER_EXECUTION_V1',
};
const empty = {
  evidence_version: 'FUTURE_PAPER_EVIDENCE_V1',
  evidence_stage: 'PROSPECTIVE_PAPER_RESEARCH_NOT_DEVELOPMENT_EVIDENCE',
  contract: 'docs/contracts/FUTURE_PAPER_EVIDENCE_V1.md',
  research_status: 'PAPER_RESEARCH_CANDIDATE',
  champion_status: 'NONE',
  strategy_version: 'ALIGNED_PARTICIPATION_CONTINUATION_V1',
  max_hold_minutes: 1440,
  statuses: ['PENDING_ENTRY', 'OPEN', 'CLOSED_TARGET', 'CLOSED_STOP', 'CLOSED_EXPIRY', 'INVALIDATED'],
  active: [],
  recent: [],
  recorded: 0,
  real_money: false,
};

type Reply = { ok: boolean; body: unknown };
function mockApi(replies: Record<string, Reply[]>) {
  const calls: { url: string; method: string }[] = [];
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, method: init?.method ?? 'GET' });
    const key = Object.keys(replies).find(k => url.includes(k));
    const queue = key ? replies[key] : undefined;
    const reply = queue && (queue.length > 1 ? queue.shift()! : queue[0]);
    if (!reply) return { ok: true, json: async () => ({}) };
    return { ok: reply.ok, json: async () => reply.body };
  });
  vi.stubGlobal('fetch', fetcher);
  return { fetcher, calls };
}
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('paper trade workflow', () => {
  it('runs nothing on mount and shows a clean empty state after loading', async () => {
    const { fetcher } = mockApi({ 'paper-trades': [{ ok: true, body: empty }] });
    render(<PaperTrades />);
    expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getByText('No active paper trade.')).toBeInTheDocument();
    expect(screen.getByText('No paper trades loaded yet.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'REFRESH' }));
    expect(await screen.findByText('No paper trades recorded yet.')).toBeInTheDocument();
  });

  it('creates a paper trade and shows the active PENDING_ENTRY trade', async () => {
    const { calls } = mockApi({
      'paper-trades/lifecycle': [{ ok: true, body: { updated: 0, trades: [], errors: [] } }],
      'paper-trades': [
        { ok: true, body: { analysis_id: 'a'.repeat(64), trade: pending, real_money: false } },
        { ok: true, body: { ...empty, active: [pending], recent: [pending], recorded: 1 } },
      ],
    });
    render(<PaperTrades />);
    await userEvent.click(screen.getByRole('button', { name: 'CREATE PAPER TRADE' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Paper trade created.');
    expect(calls[0]).toEqual({ url: '/api/v1/product/paper-trades', method: 'POST' });
    const card = screen.getAllByRole('article', { name: /Paper trade PAPER-abc123/ })[0];
    expect(card).toHaveTextContent('PENDING_ENTRY');
    expect(card).toHaveTextContent('BTCUSDT LONG');
    expect(card).toHaveTextContent('ALIGNED_PARTICIPATION_CONTINUATION_V1');
    expect(card).toHaveTextContent('Signal time: 2026-03-05T12:00:00Z');
    expect(card).toHaveTextContent('Entry: pending');
    expect(card).toHaveTextContent('NEXT_1M_OPEN_EXECUTION');
    expect(card).toHaveTextContent('Stop: 49,000.00 · Target: 52,000.00');
    expect(card).toHaveTextContent('Expiry: 2026-03-06T12:00:00Z (1440 minutes maximum hold)');
  });

  it('shows the occupancy reason instead of failing mysteriously', async () => {
    mockApi({
      'paper-trades': [
        { ok: false, body: { detail: 'one paper trade is already PENDING_ENTRY or OPEN' } },
      ],
    });
    render(<PaperTrades />);
    await userEvent.click(screen.getByRole('button', { name: 'CREATE PAPER TRADE' }));
    expect(await screen.findByRole('status')).toHaveTextContent('one paper trade is already PENDING_ENTRY or OPEN');
  });

  it('shows the NO_TRADE reason when creation is refused', async () => {
    mockApi({
      'paper-trades': [
        { ok: false, body: { detail: 'analysis is NO_TRADE; no paper trade is created' } },
      ],
    });
    render(<PaperTrades />);
    await userEvent.click(screen.getByRole('button', { name: 'CREATE PAPER TRADE' }));
    expect(await screen.findByRole('status')).toHaveTextContent('analysis is NO_TRADE');
  });

  it('advances the lifecycle only when asked and renders the closed trade', async () => {
    const { calls } = mockApi({
      'paper-trades/lifecycle': [{ ok: true, body: { updated: 1, trades: [closed], errors: [] } }],
      'paper-trades': [{ ok: true, body: { ...empty, active: [], recent: [closed], recorded: 1 } }],
    });
    render(<PaperTrades />);
    expect(calls).toHaveLength(0);
    await userEvent.click(screen.getByRole('button', { name: 'UPDATE PAPER TRADE' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Lifecycle updated.');
    expect(calls[0]).toEqual({ url: '/api/v1/product/paper-trades/lifecycle', method: 'POST' });
    expect(screen.getByText('No active paper trade.')).toBeInTheDocument();
    const card = screen.getByRole('article', { name: /Paper trade PAPER-abc123/ });
    expect(card).toHaveTextContent('CLOSED_TARGET');
    expect(card).toHaveTextContent('Entry: 2026-03-05T12:00:00Z @ 50,000.00');
    expect(card).toHaveTextContent('Exit: TARGET at 2026-03-05T12:03:00Z @ 52,000.00');
    expect(card).toHaveTextContent('Realized R: 1.952400');
    expect(card).toHaveTextContent('resolved by PROSPECTIVE_PAPER_EXECUTION_V1');
  });

  it('labels every trade and the panel as future paper evidence', async () => {
    mockApi({ 'paper-trades': [{ ok: true, body: { ...empty, active: [pending], recent: [pending], recorded: 1 } }] });
    render(<PaperTrades />);
    const panel = screen.getByRole('region', { name: 'Paper trades' });
    expect(panel).toHaveTextContent('FUTURE PAPER EVIDENCE · PAPER RESEARCH · NOT CHAMPION · NOT LIVE TRADING');
    await userEvent.click(screen.getByRole('button', { name: 'REFRESH' }));
    const card = (await screen.findAllByRole('article', { name: /Paper trade/ }))[0];
    expect(card).toHaveTextContent('FUTURE PAPER EVIDENCE');
    expect(card).toHaveTextContent('FUTURE_PAPER_EVIDENCE_V1');
    expect(card).toHaveTextContent('NOT CHAMPION');
    expect(card).toHaveTextContent('NOT LIVE TRADING');
    expect(panel).toHaveTextContent('Orders: no · Real money: no');
  });

  it('offers no order, buy, sell, withdrawal or real-money control', async () => {
    mockApi({ 'paper-trades': [{ ok: true, body: empty }] });
    render(<PaperTrades />);
    expect(screen.queryByRole('button', { name: /place order|buy|sell|withdraw|deposit|real money|live/i })).not.toBeInTheDocument();
    expect(screen.getAllByRole('button').map(b => b.textContent)).toEqual([
      'CREATE PAPER TRADE', 'UPDATE PAPER TRADE', 'REFRESH',
    ]);
  });
});

describe('dashboard integration', () => {
  it('exposes analyze and paper trade actions without running either on startup', async () => {
    const { calls } = mockApi({
      'system/health': [{ ok: true, body: { health: 'fixture-health', status: 'X', project_phase: 'P', development_data_available: true, development_coverage: { start: 'a', end: 'b' }, real_money_authorized: false } }],
      'research/status': [{ ok: true, body: { champion: 'NONE' } }],
      'research/experiments': [{ ok: true, body: { evidence_stage: 'NONE', experiments: [] } }],
    });
    render(<App />);
    await screen.findByText(/fixture-health/);
    expect(calls.every(call => call.method === 'GET')).toBe(true);
    expect(calls.some(call => call.url.includes('product/'))).toBe(false);
    const panel = screen.getByRole('region', { name: 'Paper trades' });
    expect(within(panel).getByRole('button', { name: 'CREATE PAPER TRADE' })).toBeEnabled();
    expect(within(panel).getByRole('button', { name: 'UPDATE PAPER TRADE' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'ANALYZE MARKET' })).toBeEnabled();
    expect(panel).toHaveTextContent('NOT LIVE TRADING');
  });
});
