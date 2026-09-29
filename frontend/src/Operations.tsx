// Read-only Operations surface: long-job progress telemetry from /api/v1/operations.
// It never starts, stops or configures a job and never shows scientific results: the payload is
// operational telemetry only. Percent and ETA are shown only when the backend reports them.
import { useEffect, useState } from 'react';
import { request } from './api';
import { Badge, Empty, Section } from './ui';

export type JobChild = { worker: string; status: string | null; phase?: string | null; completed_units?: number; message?: string | null };
export type Job = {
  job_id: string; job_type: string; status: 'QUEUED' | 'RUNNING' | 'PASS' | 'FAIL' | 'CANCELLED';
  phase: string | null; phase_index: number; phase_count: number; last_completed_phase: string | null;
  completed_units: number | null; total_units: number | null; unit_label: string | null;
  phase_percent: number | null; elapsed_seconds: number; eta_seconds: number | null; phase_eta_seconds?: number | null; eta_basis: string;
  heartbeat_age_seconds: number | null; stale: boolean; message: string | null;
  exit_code: number | null; error: string | null; children: JobChild[]; log_tail?: string[];
};
export type JobList = { evidence: string; jobs: Job[] };

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return 'sconosciuto';
  const safe = Math.max(0, Math.floor(seconds));
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = safe % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

function tone(job: Job): 'pos' | 'neg' | 'neutral' | 'paper' {
  if (job.stale) return 'neg';
  if (job.status === 'PASS') return 'pos';
  if (job.status === 'FAIL' || job.status === 'CANCELLED') return 'neg';
  return 'paper';
}

function JobCard({ job, selected, onSelect }: { job: Job; selected: boolean; onSelect: () => void }) {
  const measured = job.phase_percent != null && job.total_units != null && job.completed_units != null;
  return (
    <article className="ops-job" aria-label={`Job ${job.job_id}`}>
      <div className="row ops-job-head">
        <div className="grow">
          <h3>{job.job_type}</h3>
          <p className="summary ops-id">{job.job_id}</p>
        </div>
        <Badge tone={tone(job)}>{job.stale ? 'STALE — nessun heartbeat' : job.status}</Badge>
      </div>
      <p className="ops-phase">Fase {job.phase_index}/{job.phase_count}: <strong>{job.phase ?? '—'}</strong></p>
      {measured ? (
        <>
          <div className="research-progress" role="progressbar" aria-valuenow={job.phase_percent!} aria-valuemin={0} aria-valuemax={100}>
            <span style={{ width: `${Math.max(0, Math.min(100, job.phase_percent!))}%` }} />
          </div>
          <p className="summary">{job.phase_percent!.toFixed(1)}% · {job.completed_units!.toLocaleString('it-IT')} / {job.total_units!.toLocaleString('it-IT')} {job.unit_label ?? 'unità'}</p>
        </>
      ) : job.status === 'RUNNING' ? <div className="research-activity" role="status"><span aria-hidden="true" /> In corso (avanzamento non misurabile)</div> : null}
      <div className="research-live-meta">
        <span>Trascorsi {formatDuration(job.elapsed_seconds)}</span>
        <span>ETA {job.status === 'RUNNING' ? formatDuration(job.eta_seconds) : '—'}</span>
        {job.status === 'RUNNING' && job.eta_seconds == null && job.phase_eta_seconds != null && <span>ETA fase {formatDuration(job.phase_eta_seconds)}</span>}
        <span>Heartbeat {job.heartbeat_age_seconds == null ? '—' : `${Math.floor(job.heartbeat_age_seconds)}s fa`}</span>
      </div>
      {job.message && <p className="summary">{job.message}</p>}
      {job.error && <p className="notice warn">{job.error}</p>}
      {job.children.length > 0 && (
        <ul className="ops-children">
          {job.children.map(child => (
            <li key={child.worker}><strong>{child.worker}</strong> · {child.status ?? '—'}{child.phase ? ` · ${child.phase}` : ''}</li>
          ))}
        </ul>
      )}
      <button className="btn" onClick={onSelect} aria-pressed={selected}>{selected ? 'Log visualizzato' : 'Mostra log'}</button>
    </article>
  );
}

export function Operations({ intervalMs = 2000 }: { intervalMs?: number }) {
  const [list, setList] = useState<JobList | null>(null);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<Job | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => {
      request<JobList>('/api/v1/operations/jobs')
        .then(payload => { if (alive) { setList(payload); setFailed(false); } })
        .catch(() => { if (alive) setFailed(true); });
      if (selected) {
        request<Job>(`/api/v1/operations/jobs/${encodeURIComponent(selected)}`)
          .then(payload => { if (alive) setDetail(payload); })
          .catch(() => undefined);
      }
    };
    load();
    const timer = window.setInterval(load, intervalMs);
    return () => { alive = false; window.clearInterval(timer); };
  }, [intervalMs, selected]);

  const jobs = list?.jobs ?? [];
  return (
    <>
      <div className="pagehead">
        <div>
          <p className="eyebrow">Telemetria operativa</p>
          <h1>Operazioni</h1>
          <p className="lede">Stato dei job lunghi eseguiti su questo PC (controlli, run di sviluppo). Solo lettura.</p>
        </div>
        <Badge tone="neutral">Non è evidenza scientifica</Badge>
      </div>
      {failed && <p className="notice warn">Servizio operazioni non raggiungibile.</p>}
      <Section title="Job attivi e recenti" label="Job attivi e recenti">
        <div className="pad ops-list">
          {jobs.length === 0 ? <Empty title="Nessun job registrato" body="I job lunghi compariranno qui mentre sono in esecuzione." /> : jobs.map(job => (
            <JobCard key={job.job_id} job={job} selected={selected === job.job_id} onSelect={() => setSelected(job.job_id)} />
          ))}
        </div>
      </Section>
      {selected && (
        <Section title="Log operativo" label="Log operativo" hint={selected}>
          <pre className="pad ops-log" aria-label="Log operativo">{(detail?.log_tail ?? []).join('\n') || '—'}</pre>
        </Section>
      )}
    </>
  );
}
