import { ReactNode } from 'react';
import { Tone } from './format';

export function Surface({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`surface ${className}`.trim()}>{children}</div>;
}

export function Section({
  title, hint, label, children, actions,
}: {
  title: string; hint?: string; label?: string; children: ReactNode; actions?: ReactNode;
}) {
  return (
    <section className="surface" aria-label={label ?? title}>
      <header className="sechead">
        <div>
          <h2>{title}</h2>
          {hint && <p className="hint">{hint}</p>}
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}

export function Badge({
  tone = 'neutral', children, dot = false,
}: { tone?: Tone | 'paper'; children: ReactNode; dot?: boolean }) {
  return (
    <span className={`badge ${tone}`}>
      {dot && <i className="dot" />}
      {children}
    </span>
  );
}

export function Stat({
  label, value, note, tone,
}: { label: string; value: ReactNode; note?: string; tone?: Tone }) {
  return (
    <div className="stat">
      <span className="label">{label}</span>
      <span className={`value ${tone === 'pos' ? 'pos' : tone === 'neg' ? 'neg' : ''}`.trim()}>
        {value}
      </span>
      {note && <span className="note">{note}</span>}
    </div>
  );
}

export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty">
      <p className="title">{title}</p>
      <p className="body">{body}</p>
    </div>
  );
}

/** Everything technical lives here, collapsed. The Owner never needs to open it. */
export function Advanced({ children }: { children: ReactNode }) {
  return (
    <details className="advanced">
      <summary>Dettagli avanzati</summary>
      {children}
    </details>
  );
}

export function KeyValues({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="kv">
      {rows.map(([key, value]) => (
        <div key={key}>
          <dt>{key}</dt>
          <dd>{value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  );
}
