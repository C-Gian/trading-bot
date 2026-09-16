import { ProspectiveObserver as ObserverState } from './api';
import { Badge, Section } from './ui';

function instant(value: string | null | undefined) {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'medium', timeZone: 'UTC' }) + ' UTC';
}

function count(value: number | null | undefined) {
  return value == null ? '—' : value;
}

function statusTone(status: ObserverState['status']) {
  if (status === 'ACTIVE') return 'pos' as const;
  if (status === 'DEGRADED') return 'neg' as const;
  return 'neutral' as const;
}

function integrityTone(observer: ObserverState | null) {
  if (!observer) return 'neutral' as const;
  if (observer.evidence_integrity === 'INVALID') return 'neg' as const;
  return observer.build_provenance_verified ? ('pos' as const) : ('neutral' as const);
}

function integrityLabel(observer: ObserverState | null) {
  if (observer?.evidence_integrity === 'INVALID') return 'LEDGER NON VALIDO';
  if (observer?.build_provenance_verified === true) return 'BUILD VERIFICATO';
  if (observer?.build_provenance_verified === false) return 'BUILD NON VERIFICATO';
  return 'BUILD NON RILEVATO';
}

export function ProspectiveObserver({ observer }: { observer: ObserverState | null }) {
  const status = observer?.status ?? 'STOPPED';
  const trade = observer?.open_shadow_trade ?? null;
  const provenance = observer?.build_provenance_sha256 ?? null;
  return (
    <Section title="Prospective Observer" label="Prospective Observer" hint="Evidenza futura automatizzata">
      <div className="observer-panel">
        <div className="observer-strip">
          <div>
            <p className="eyebrow">Osservatore BTCUSDT · UTC 1h</p>
            <strong className="observer-label">AUTOMATED PAPER RESEARCH · NO REAL MONEY</strong>
          </div>
          <Badge tone={statusTone(status)}>{status}</Badge>
        </div>

        <div className="observer-strip observer-integrity">
          <div>
            <p className="eyebrow">Integrità evidenza</p>
            <strong className="observer-provenance">
              {provenance ? `provenance ${provenance.slice(0, 12)}…` : 'provenance non registrata'}
              {observer?.observer_lease_held === false ? ' · lease non posseduto' : ''}
            </strong>
          </div>
          <Badge tone={integrityTone(observer)}>{integrityLabel(observer)}</Badge>
        </div>

        <div className="observer-timegrid">
          <div><span>Ultimo confine valutato</span><strong>{instant(observer?.last_evaluated_hourly_boundary)}</strong></div>
          <div><span>Ultimo heartbeat</span><strong>{instant(observer?.last_heartbeat)}</strong></div>
          <div><span>Prossimo confine atteso</span><strong>{instant(observer?.next_expected_boundary)}</strong></div>
          <div className={observer?.missed_prospective_decisions ? 'observer-alert' : ''}>
            <span>Decisioni perse · downtime visibile</span>
            <strong>{count(observer?.missed_prospective_decisions)}</strong>
          </div>
        </div>

        <div className="observer-counts" aria-label="Contatori osservatore prospettico">
          <div><span>LONG prospettici</span><strong>{count(observer?.raw_prospective_long_signals)}</strong></div>
          <div><span>LONG soppressi</span><strong>{count(observer?.suppressed_long_signals)}</strong></div>
          <div><span>Shadow completati</span><strong>{count(observer?.completed_shadow_trades)}</strong></div>
          <div><span>Eventi audit</span><strong>{count(observer?.audit_events)}</strong></div>
          <div><span>Review scientifica</span><strong>da {observer?.first_scientific_review_completed_trades ?? 20} trade</strong></div>
        </div>

        {trade ? (
          <div className="observer-trade">
            <div><p className="eyebrow">Shadow position aperta</p><strong>{trade.status}</strong></div>
            <dl>
              <div><dt>Entrata</dt><dd>{trade.entry_price == null ? 'in attesa' : trade.entry_price.toLocaleString('it-IT')}</dd></div>
              <div><dt>Stop</dt><dd>{trade.stop_price == null ? '—' : trade.stop_price.toLocaleString('it-IT')}</dd></div>
              <div><dt>Target</dt><dd>{trade.target_price == null ? '—' : trade.target_price.toLocaleString('it-IT')}</dd></div>
              <div><dt>Scadenza</dt><dd>{instant(trade.expiry_time)}</dd></div>
            </dl>
          </div>
        ) : <p className="observer-idle">Nessuna posizione shadow attiva. I NO_TRADE restano nel ledger prospettico.</p>}

        {observer?.current_error && <p className="observer-error" role="status">{observer.current_error}</p>}
        <p className="observer-meta">
          {observer?.evidence_version ?? 'FUTURE_SHADOW_PAPER_EVIDENCE_V1_1'} · {observer?.strategy_version ?? 'ALIGNED_PARTICIPATION_CONTINUATION_V1'} · non è performance Champion
        </p>
      </div>
    </Section>
  );
}
