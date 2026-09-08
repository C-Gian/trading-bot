import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';

vi.mock('lightweight-charts', () => ({ CandlestickSeries: {}, createChart: () => ({ addSeries: () => ({ setData: vi.fn() }), remove: vi.fn() }) }));
const health = { health: 'fixture-health', status: 'EXECUTOR_COMPLETE_PENDING_REVIEW', project_phase: 'BASELINE_RESEARCH', development_data_available: true, development_coverage: { start: '2017-08-17T04:00:00Z', end: '2024-12-31T23:59:00Z' }, real_money_authorized: false };
const research = { champion: 'NONE', experiments_completed: 6, evidence: 'NONE', backtest_substrate: 'VALIDATED', engine_version: 'BACKTEST_ENGINE_V2', execution_model_version: 'EXECUTION_MODEL_V2', cost_model_version: 'BTCUSDT_SPOT_COST_V1', synthetic_validation: 'PASS' };
const experiments = { evidence_stage: 'DEVELOPMENT BACKTEST / CONTROLS', latest_checkpoint: 'WP-003', next_checkpoint: 'Research Director review', experiments: [{ experiment_id: 'EXP-CTRL-006-NO-TRADE', classification: 'NEGATIVE_CONTROL', primary_metric: 'No applicable trade metric', primary_result: null, trade_count: 0, validation_status: 'PASS' }] };
function mockApi(ok = true) { vi.stubGlobal('fetch', vi.fn(async (url: string) => { if (!ok) throw new Error('offline'); const payload = url.includes('system/health') ? health : url.includes('research/status') ? research : url.includes('research/experiments') ? experiments : { classification: 'HISTORICAL DEVELOPMENT DATA — NOT CURRENT MARKET', coverage: health.development_coverage, candles: [] }; return { ok: true, json: async () => payload }; })); }
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('truthful phase UI', () => {
  it('sources health and keeps analysis unavailable', async () => { mockApi(); render(<App />); expect(await screen.findByText(/fixture-health/)).toBeInTheDocument(); expect(screen.getByRole('button', { name: 'ANALYZE MARKET' })).toBeDisabled(); expect(screen.getByText('No approved strategy')).toBeInTheDocument(); });
  it('renders backend unavailable', async () => { mockApi(false); render(<App />); await waitFor(() => expect(screen.getByText(/Backend: unavailable/)).toBeInTheDocument()); });
  it('contains no fabricated advice or real-money controls', async () => { mockApi(); render(<App />); await screen.findByText(/fixture-health/); expect(screen.queryByText(/^NO_TRADE$/)).not.toBeInTheDocument(); expect(screen.queryByText(/^LONG/)).not.toBeInTheDocument(); expect(screen.queryByRole('button', { name: /real money|place order|buy|sell/i })).not.toBeInTheDocument(); });
  it('shows historical classification and coverage', async () => { mockApi(); render(<App />); await screen.findByText(/fixture-health/); await userEvent.click(screen.getByRole('button', { name: 'Market' })); expect(await screen.findByText('HISTORICAL DEVELOPMENT DATA — NOT CURRENT MARKET')).toBeInTheDocument(); expect(await screen.findByText(/2017-08-17T04:00:00Z.*2024-12-31T23:59:00Z/)).toBeInTheDocument(); });
  it('keeps Statistics empty and labels development research', async () => { mockApi(); render(<App />); await screen.findByText(/fixture-health/); await userEvent.click(screen.getByRole('button', { name: 'Statistics' })); expect(screen.getByText('No approved strategy performance statistics exist.')).toBeInTheDocument(); await userEvent.click(screen.getByRole('button', { name: 'Research Lab' })); expect(screen.getByText(/Champion: NONE/)).toBeInTheDocument(); expect(screen.getByText(/DEVELOPMENT RESEARCH/)).toBeInTheDocument(); expect(screen.getByText(/EXP-CTRL-006-NO-TRADE/)).toBeInTheDocument(); });
});
