import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Replay, ReplayChart } from './Replay';
import { candleIndexFor, decisionGlyphs, fillMarks, predictionGlyphs } from './replayGlyphs';
import type { ReplayPrediction, ReplayView } from './replayApi';

const candle = (open_time: string, price: number) => ({
  open_time, available_at: '', open: price, high: price + 5, low: price - 5, close: price + 1, quality: 'COMPLETE',
});
const prediction = (issue: string, direction: ReplayPrediction['predicted_direction'], id: string): ReplayPrediction => ({
  prediction_id: id, issue_time: issue, available_at: issue, target_end: '2001-01-30T14:15:00Z',
  predicted_direction: direction, directional_bias: 'BULLISH', probability_up: 0.62, probability_down: 0.38,
  probability_status: 'UNCALIBRATED_SYNTHETIC_FIXTURE_VALUE_NOT_A_PROBABILITY',
  mean_terminal_return: 0.003, median_terminal_return: 0.0025, lower_quantile_return: -0.001,
  upper_quantile_return: 0.007, quantile_levels: [0.1, 0.9], standardized_strength: 0.75,
  prior_risk_scale: 0.004, support_status: 'SYNTHETIC', conviction: 'HIGH', playbook_context: [],
  unavailable_reason: null, supporting_reasons: [], opposing_reasons: [],
});
const actionability = { setup_ready: true, data_ready: true, execution_ready: true, risk_eligible: true, occupancy_free: true, final_decision: 'LONG', blockers: [] };

function view(): ReplayView {
  return {
    mode: 'CAUSAL_CURSOR', label: 'SYNTHETIC FIXTURE - NOT MARKET EVIDENCE', session_id: 'G1-REPLAY-1', run_id: 'RUN-x',
    status: 'PAUSED', speed: 900, speeds: [60, 900, 3600, 14400], cursor: '2001-01-30T10:30:00Z',
    dataset_start: '2001-01-30T00:00:00Z', dataset_end: '2001-02-02T00:00:00Z',
    candles: [candle('2001-01-30T10:00:00Z', 100), candle('2001-01-30T10:15:00Z', 102)],
    predictions: [
      prediction('2001-01-30T10:15:00Z', 'UP', 'P1'),
      prediction('2001-01-30T10:30:00Z', 'UNAVAILABLE', 'P2'),
    ],
    realizations: [{
      realization_id: 'R1', prediction_id: 'P1', resolution_time: '2001-01-30T14:15:00Z', available_at: '2001-01-30T14:15:00Z',
      resolution_validity: 'VALID', realized_terminal_return: 0.004, realized_direction: 'UP', direction_correct: true, magnitude_error: 0.001,
    }],
    decisions: [
      { decision_id: 'D1', prediction_id: 'P1', decision_time: '2001-01-30T10:15:00Z', available_at: '2001-01-30T10:15:00Z', action: 'LONG', playbook_id: 'SYSTEM-G1-P1-DIRECTIONAL-CONTINUATION', conviction: 'HIGH', actionability, blockers: [], trade_plan_id: 'PLN-1' },
      { decision_id: 'D2', prediction_id: 'P2', decision_time: '2001-01-30T10:30:00Z', available_at: '2001-01-30T10:30:00Z', action: 'NO_TRADE', playbook_id: null, conviction: 'LOW', actionability: { ...actionability, final_decision: 'NO_TRADE', blockers: ['POSITION_OCCUPIED'] }, blockers: ['POSITION_OCCUPIED'], trade_plan_id: null },
    ],
    trade_plans: [{ trade_plan_id: 'PLN-1', side: 'LONG', playbook_id: 'P1', reference_price: '101', stop_price: '100.6', objective_price: '101.8', max_hold_minutes: 240, planned_risk_amount: '25' }],
    fills: [
      { event_id: 'F1', trade_plan_id: 'PLN-1', kind: 'ENTRY', side: 'LONG', event_time: '2001-01-30T10:15:00Z', available_at: '2001-01-30T10:16:00Z', raw_price: '101.2', reason: 'NEXT_ELIGIBLE_1M_OPEN', funding_amount: '0' },
      { event_id: 'F2', trade_plan_id: 'PLN-1', kind: 'EXIT', side: 'LONG', event_time: '2001-01-30T10:22:00Z', available_at: '2001-01-30T10:23:00Z', raw_price: '101.8', reason: 'OBJECTIVE', funding_amount: '0' },
    ],
    current: { signals: [], cycle: null, prediction: null, decision: null, ledger: { equity: '10000', drawdown_fraction: '0', day_loss_fraction: '0', open_side: null, open_quantity: '0', unrealized_pnl: '0', daily_entry_stop: false, run_entry_stop: false } },
    stats: { label: 'SYNTHETIC FIXTURE - NOT MARKET EVIDENCE', predictions_issued: 2, predictions_unavailable: 1, matured: 1, matured_valid: 1, matured_unscorable: 0, directional_matured: 1, directional_correct: 1, directional_hit_rate: 1, directional_coverage: 1, mean_absolute_return_error: 0.001, interval_coverage: 1, closed_trades: 1, scorable_trades: 1, long_trades: 1, short_trades: 0, winning_trades: 1, net_pnl: '5.00' },
    production_action: 'NO_TRADE', validated_strategy: null,
  };
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('replay annotation semantics', () => {
  it('places a prediction on the candle whose close is the issue time', () => {
    const v = view();
    expect(candleIndexFor(v.candles, '2001-01-30T10:15:00Z')).toBe(0);
    expect(candleIndexFor(v.candles, '2001-01-30T10:30:00Z')).toBe(1);
    const glyphs = predictionGlyphs(v.candles, v.predictions, v.realizations);
    expect(glyphs.map(g => [g.candleIndex, g.symbol, g.tone])).toEqual([[0, '▲', 'hit'], [1, '○', 'muted']]);
  });

  it('shows a realized score only when the backend has matured it', () => {
    const v = view();
    const pending = predictionGlyphs(v.candles, v.predictions, []);
    expect(pending[0].tone).toBe('pending');
    expect(pending[0].realization).toBeNull();
  });

  it('keeps NO_TRADE as a decision glyph and marks fills at their execution minute', () => {
    const v = view();
    expect(decisionGlyphs(v.candles, v.decisions).map(g => [g.candleIndex, g.symbol])).toEqual([[0, 'L'], [1, '·']]);
    const marks = fillMarks(v.candles, [...v.fills, { ...v.fills[0], event_id: 'F3', kind: 'FUNDING' }]);
    expect(marks.map(m => [m.fill.kind, m.position])).toEqual([['ENTRY', 1], ['EXIT', 22 / 15]]);
  });

  it('renders prediction glyphs above and decision glyphs below each eligible candle', () => {
    const onDetail = vi.fn();
    render(<ReplayChart view={view()} onDetail={onDetail} />);
    const predictions = screen.getAllByTestId('prediction-glyph');
    const decisions = screen.getAllByTestId('decision-glyph');
    expect(predictions).toHaveLength(2);
    expect(decisions.map(d => d.getAttribute('data-action'))).toEqual(['LONG', 'NO_TRADE']);
    for (let index = 0; index < 2; index += 1) {
      expect(Number(predictions[index].getAttribute('y'))).toBeLessThan(Number(decisions[index].getAttribute('y')));
    }
    expect(predictions[0].getAttribute('data-matured')).toBe('yes');
    expect(screen.getAllByTestId('fill-mark').map(m => m.getAttribute('data-kind'))).toEqual(['ENTRY', 'EXIT']);
    fireEvent.mouseEnter(predictions[0]);
    expect(onDetail).toHaveBeenCalledWith(expect.objectContaining({ kind: 'prediction' }));
  });
});

describe('replay page', () => {
  it('opens a synthetic session, shows hover details, matured stats and controls', async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, body: init?.body ? JSON.parse(String(init.body)) : null });
      if (url === '/api/v1/g1/runs') {
        return new Response(JSON.stringify({ runs: [{ manifest: { run_id: 'RUN-x', evidence_class: 'SYNTHETIC', dataset_start: '', dataset_end: '' }, fixture_id: 'F', label: 'SYNTHETIC' }] }));
      }
      const body = view();
      if (url.endsWith('/control') && calls.at(-1)?.body && (calls.at(-1)!.body as { action: string }).action === 'start') body.status = 'RUNNING';
      return new Response(JSON.stringify(body));
    }));
    render(<Replay />);
    await waitFor(() => expect(screen.getAllByTestId('decision-glyph')).toHaveLength(2));
    expect(calls[1]).toEqual({ url: '/api/v1/g1/replay/sessions', body: { run_id: 'RUN-x' } });
    fireEvent.mouseEnter(screen.getAllByTestId('decision-glyph')[1]);
    expect(screen.getByTestId('replay-detail').textContent).toContain('POSITION_OCCUPIED');
    fireEvent.mouseEnter(screen.getAllByTestId('prediction-glyph')[0]);
    expect(screen.getByTestId('replay-detail').textContent).toContain('corretta');
    expect(screen.getByTestId('replay-stats').textContent).toContain('n=1');
    expect(screen.getByText(/l’azione reale resta NO_TRADE/)).toBeTruthy();
    fireEvent.click(screen.getByText('Passo 15m'));
    await waitFor(() => expect(calls.at(-1)?.body).toEqual({ action: 'step' }));
    fireEvent.change(screen.getByLabelText('Velocità'), { target: { value: '3600' } });
    await waitFor(() => expect(calls.at(-1)?.body).toEqual({ action: 'speed', speed: 3600 }));
    fireEvent.click(screen.getByText('Avvia'));
    await waitFor(() => expect(screen.getByText('Pausa')).toBeTruthy());
  });
});
