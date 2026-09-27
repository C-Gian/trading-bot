import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { G2LatestPanel, G2Replay } from './G2Replay';
import type { G2Current, G2View } from './g2Api';

const utility = (side: string, margin: number) => ({
  side, fit_id: 'F', predicted_utility: 0.9, residual_q10: -0.4, residual_count: 2400,
  residual_span_days: 31, evidence_status: 'PREQUENTIAL_READY', prudential_margin: margin,
});

function current(action: 'LONG' | 'SHORT' | 'NO_TRADE', reasons: string[]): G2Current {
  return {
    state: {
      state_id: 'S', decision_time: '2001-09-02T10:15:00Z', max_source_time: '2001-09-02T10:15:00Z', price: 31000,
      raw_terms: [0.01, 0.02, 0.001, 0.1, 0.2, -0.05, 0.001, 0.02],
      term_status: Array(8).fill('AVAILABLE'), sigma_4h: 0.009, atr14_1h: 120, price_response: 0.1,
      status: 'AVAILABLE', daily: [['return', 0.01]], weekly: [['return', 0.02]],
    },
    prediction: {
      prediction_id: 'P', decision_time: '2001-09-02T10:15:00Z', target_time: '2001-09-02T14:15:00Z', fit_id: 'F',
      raw_terms: [], scaled_terms: [], contributions: [0.1, 0, 0, 0, 0, 0, 0, 0], intercept: 0.01, mu_z: 0.2,
      mean_return: 0.002, median_return: 0.0018, q10: -0.01, q50: 0.0018, q90: 0.012, p_positive: 0.57,
      sigma_4h: 0.009, calibration_status: 'PREQUENTIAL_CDF_UNCALIBRATED', residual_source: 'PREQUENTIAL_CDF_UNCALIBRATED',
      residual_count: 2500, view_strength_z: 0.2, strength_label: 'WEAK', direction: 'UP',
      evidence_status: [['model_support', 'FITTED']], reason_codes: ['FORECAST_AVAILABLE', 'PREQUENTIAL_CDF_UNCALIBRATED'],
      max_source_time: '2001-09-02T10:15:00Z', training_start: null, training_end: null, latest_label_time: null,
    },
    decision: {
      decision_id: 'D', prediction_id: 'P', decision_time: '2001-09-02T10:15:00Z', available_at: '2001-09-02T10:15:00Z',
      action, policy_selection: 'LONG_SELECTED', reason_codes: reasons,
      long_utility: utility('LONG', 0.5), short_utility: utility('SHORT', -0.2), forecast_direction: 'UP',
      position_state: 'OPEN', risk: { equity: 10000, peak_equity: 10000, drawdown: 0, drawdown_stop_active: false, position_open: true, open_trade_id: 'T' },
      stop_distance: 240, reference_price: 31000, intended_entry_time: null, intended_expiry_time: null, cycle_role: 'CYCLE_SHADOW_ONLY',
    },
    cycle: {
      runtime_role: 'SHADOW_ONLY', forecast_coefficients: 0, policy_coefficients: 0, veto_authority: 'NONE',
      reason_codes: ['CYCLE_SHADOW_ONLY'],
      scales: [{ nominal_scale: '3h', input_resolution: '15m', warmup_ready: true, quality_label: 'USABLE', dominant_period_minutes: 210, phase_degrees: 12, projection_amplitude: 0.3, period_stability: 0.01, slope_direction: 'RISING', last_turn_kind: null, reason_code: null }],
    },
    risk: { kind: 'ENTRY', equity: 10000, peak_equity: 10000, drawdown: 0, drawdown_stop_active: false, position_open: true },
    open_position: null, fit: [],
  };
}

function view(action: 'LONG' | 'SHORT' | 'NO_TRADE', reasons: string[]): G2View {
  return {
    mode: 'CAUSAL_CURSOR', session_id: 'G2SES-0001', status: 'PAUSED', speed: 3600, speeds: [900, 3600], step_units: ['15m', '1h', '1d'],
    label: 'NOT PERFORMANCE EVIDENCE', run_key: 'G2-SYN-V0-ENGINEERING', run_id: 'RUN', evidence_class: 'SYNTHETIC_FIXTURE_NOT_MARKET_EVIDENCE',
    cursor: '2001-09-02T10:15:00Z', dataset_start: '2001-01-01T00:00:00Z', dataset_end: '2001-09-20T00:00:00Z',
    candles: [
      { open_time: '2001-09-02T09:45:00Z', available_at: '2001-09-02T10:00:00Z', open: 100, high: 102, low: 99, close: 101, complete: true },
      { open_time: '2001-09-02T10:00:00Z', available_at: '2001-09-02T10:15:00Z', open: 101, high: 103, low: 100, close: 102, complete: true },
    ],
    prediction_markers: [
      { prediction_id: 'P0', decision_time: '2001-09-02T10:00:00Z', direction: 'UNAVAILABLE', median_return: null, status: 'UNAVAILABLE' },
      { prediction_id: 'P', decision_time: '2001-09-02T10:15:00Z', direction: 'UP', median_return: 0.0018, status: 'PREQUENTIAL_CDF_UNCALIBRATED' },
    ],
    decision_markers: [{ decision_id: 'D', decision_time: '2001-09-02T10:15:00Z', action, policy_selection: 'LONG_SELECTED', reason_codes: reasons }],
    fills: [], closed_trades: [], current: current(action, reasons), visible_counts: {},
    production_action: 'NO_TRADE', validated_strategy: null, cycle_role: 'SHADOW',
  };
}

function mock(action: 'LONG' | 'SHORT' | 'NO_TRADE', reasons: string[]) {
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    calls.push(url);
    if (url.endsWith('/api/v1/g2/runs')) {
      return { ok: true, json: async () => ({ runs: [{ run_key: 'G2-SYN-V0-ENGINEERING', label: 'x', evidence_class: 'SYNTHETIC', evidence_label: 'NOT PERFORMANCE EVIDENCE', description: 'd', dataset_start: '', dataset_end: '', computed: true, run_id: 'RUN', review_available: false }] }) };
    }
    if (url.includes('/lineage/')) return { ok: true, json: async () => ({ decision: { decision_id: 'D' }, fills: [] }) };
    if (url.includes('/latest')) return { ok: true, json: async () => ({ mode: 'REGISTERED_RUN_LATEST_STATE', label: 'NOT PERFORMANCE EVIDENCE', run_key: 'G2-SYN-V0-ENGINEERING', run_id: 'RUN', evidence_class: 'SYNTHETIC', cursor: '2001-09-20T00:00:00Z', current: current(action, reasons), production_action: 'NO_TRADE', validated_strategy: null }) };
    return { ok: true, json: async () => view(action, reasons) };
  }));
  return calls;
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('G2 replay surface', () => {
  it('shows candles, per-candle predictions, distinct decision markers and the NOT PERFORMANCE label', async () => {
    mock('LONG', ['FORECAST_AVAILABLE', 'LONG_SELECTED', 'CYCLE_SHADOW_ONLY']);
    render(<G2Replay />);
    fireEvent.click(await screen.findByRole('button', { name: /G2-SYN-V0-ENGINEERING/ }));
    await waitFor(() => expect(screen.getAllByTestId('g2-candle')).toHaveLength(2));
    expect(screen.getAllByTestId('g2-prediction').map(n => n.getAttribute('data-direction'))).toEqual(['UNAVAILABLE', 'UP']);
    expect(screen.getAllByTestId('g2-decision').map(n => n.getAttribute('data-action'))).toEqual(['LONG']);
    expect(screen.getAllByText('NOT PERFORMANCE EVIDENCE').length).toBeGreaterThan(0);
    const cycle = screen.getByRole('region', { name: 'Ciclo shadow' });
    expect(cycle).toHaveTextContent('SHADOW');
    expect(cycle).toHaveTextContent('coeff. previsione 0');
    expect(screen.getByTestId('g2-forecast')).toHaveTextContent('non calibrata');
    expect(screen.getByTestId('g2-state')).toHaveTextContent('TAKER_IMBALANCE');
  });

  it('displays the authoritative action and never derives one from margins or direction', async () => {
    mock('NO_TRADE', ['LONG_SELECTED', 'POSITION_ALREADY_OPEN', 'CYCLE_SHADOW_ONLY']);
    render(<G2Replay />);
    fireEvent.click(await screen.findByRole('button', { name: /G2-SYN-V0-ENGINEERING/ }));
    const detail = await screen.findByTestId('g2-decision-detail');
    // positive LONG margin and an UP forecast, yet the API action is NO_TRADE: the UI shows NO_TRADE
    expect(within(detail).getByText('Azione (replay)').nextElementSibling).toHaveTextContent(/^NO_TRADE$/);
    expect(within(detail).getByText('Selezione policy').nextElementSibling).toHaveTextContent('LONG_SELECTED');
  });

  it('inspects lineage through the causal session API', async () => {
    const calls = mock('LONG', ['LONG_SELECTED']);
    render(<G2Replay />);
    fireEvent.click(await screen.findByRole('button', { name: /G2-SYN-V0-ENGINEERING/ }));
    fireEvent.click((await screen.findAllByTestId('g2-decision'))[0]);
    await waitFor(() => expect(screen.getByTestId('g2-lineage')).toHaveTextContent('"decision_id": "D"'));
    expect(calls.some(url => url.includes('/api/v1/g2/replay/sessions/G2SES-0001/lineage/D'))).toBe(true);
  });

  it('home panel loads the latest state of a registered run on explicit request only', async () => {
    const calls = mock('NO_TRADE', ['INSUFFICIENT_POLICY_EVIDENCE']);
    render(<G2LatestPanel />);
    const button = await screen.findByRole('button', { name: /Carica G2-SYN-V0-ENGINEERING/ });
    expect(calls.some(url => url.includes('/latest'))).toBe(false);
    fireEvent.click(button);
    const panel = await screen.findByTestId('g2-latest');
    await waitFor(() => expect(panel).toHaveTextContent('azione di produzione NO_TRADE'));
    expect(panel).toHaveTextContent('NOT PERFORMANCE EVIDENCE');
  });
});
