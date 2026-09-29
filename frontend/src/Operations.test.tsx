import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Operations, formatDuration, type Job } from './Operations';

const job = (patch: Partial<Job> = {}): Job => ({
  job_id: 'g2-02-development-batch-1', job_type: 'g2-02-development-batch', status: 'RUNNING',
  phase: 'simulate batch', phase_index: 2, phase_count: 6, last_completed_phase: 'verify authorization',
  completed_units: 2_500_000, total_units: 10_000_000, unit_label: 'simulated minutes (all systems)',
  phase_percent: 25, elapsed_seconds: 125, eta_seconds: 375, eta_basis: 'CURRENT_PHASE_RATE',
  heartbeat_age_seconds: 1.2, stale: false, message: 'running: G2-V0', exit_code: null, error: null,
  children: [{ worker: 'G2-V0', status: 'RUNNING', phase: 'simulate' }], log_tail: ['phase 2/6: simulate batch'],
  ...patch,
});

function mockFetch(jobs: Job[]) {
  const fetchMock = vi.fn(async (url: string) => ({
    ok: true,
    json: async () => url.endsWith('/jobs') ? { evidence: 'OPERATIONAL_TELEMETRY_NOT_SCIENTIFIC_EVIDENCE', jobs } : jobs[0],
  }));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('Operations', () => {
  it('shows phase, measured progress, elapsed, ETA and heartbeat of a running job', async () => {
    mockFetch([job()]);
    render(<Operations intervalMs={60_000} />);
    expect(await screen.findByText('g2-02-development-batch')).toBeInTheDocument();
    expect(screen.getByText('simulate batch')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '25');
    expect(screen.getByText(/Trascorsi 2:05/)).toBeInTheDocument();
    expect(screen.getByText(/ETA 6:15/)).toBeInTheDocument();
    expect(screen.getByText(/Heartbeat 1s fa/)).toBeInTheDocument();
    expect(screen.getByText('Non è evidenza scientifica')).toBeInTheDocument();
  });

  it('never fabricates a percent or ETA and flags a stale heartbeat', async () => {
    mockFetch([job({ phase_percent: null, total_units: null, completed_units: null, eta_seconds: null, stale: true })]);
    render(<Operations intervalMs={60_000} />);
    expect(await screen.findByText('STALE — nessun heartbeat')).toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.getByText(/ETA sconosciuto/)).toBeInTheDocument();
  });

  it('shows the operational log tail for a selected job', async () => {
    const fetchMock = mockFetch([job()]);
    render(<Operations intervalMs={60_000} />);
    fireEvent.click(await screen.findByText('Mostra log'));
    await waitFor(() => expect(screen.getByLabelText('Log operativo', { selector: 'pre' })).toHaveTextContent('phase 2/6'));
    expect(fetchMock.mock.calls.every(([url]) => String(url).startsWith('/api/v1/operations/'))).toBe(true);
  });

  it('formats durations', () => {
    expect(formatDuration(null)).toBe('sconosciuto');
    expect(formatDuration(3725)).toBe('1:02:05');
  });
});
