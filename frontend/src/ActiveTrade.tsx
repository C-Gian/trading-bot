import { PaperTrade } from './api';
import { money, rMultiple, statusCopy, timeLeft, when } from './format';
import { Advanced, Badge, KeyValues } from './ui';

export function ActiveTrade({
  trade, busy, onUpdate,
}: { trade: PaperTrade; busy: boolean; onUpdate: () => void }) {
  const copy = statusCopy(trade.status);
  const entered = trade.entry_price ?? trade.reference_price;

  return (
    <section className="surface pad" aria-label="Simulazione in corso">
      <div className="tradehead">
        <div className="stack-sm">
          <span className="eyebrow">La tua simulazione</span>
          <p className="tradestate">{copy.label}</p>
          <p className="lede">{copy.body}</p>
        </div>
        <Badge tone={copy.tone} dot={!copy.closed}>
          {copy.closed ? 'Chiusa' : 'In corso'}
        </Badge>
      </div>

      <div className="levels">
        <div className="level">
          <div className="label">{trade.entry_time ? 'Ingresso simulato' : 'Ingresso previsto'}</div>
          <div className="num">{money(entered)}</div>
        </div>
        <div className="level">
          <div className="label">Stop</div>
          <div className="num stop">{money(trade.stop_price)}</div>
        </div>
        <div className="level">
          <div className="label">Obiettivo</div>
          <div className="num target">{money(trade.target_price)}</div>
        </div>
        {copy.closed ? (
          <>
            <div className="level">
              <div className="label">Uscita</div>
              <div className="num">{money(trade.exit_price)}</div>
            </div>
            <div className="level">
              <div className="label">Risultato</div>
              <div className={`num ${trade.net_r === null ? '' : trade.net_r >= 0 ? 'target' : 'stop'}`.trim()}>
                {rMultiple(trade.net_r)}
              </div>
            </div>
          </>
        ) : (
          <div className="level">
            <div className="label">Scadenza</div>
            <div className="num">{timeLeft(trade.expiry_time)}</div>
          </div>
        )}
      </div>

      <div className="row" style={{ marginTop: 'var(--s5)' }}>
        {!copy.closed && (
          <button className="btn primary" onClick={onUpdate} disabled={busy}>
            Aggiorna trade
          </button>
        )}
        <p className="footnote grow">
          {copy.closed
            ? `Chiusa il ${when(trade.exit_time)} UTC.`
            : `In questa versione l’aggiornamento è manuale: niente si muove da solo. Scadenza ${when(trade.expiry_time)} UTC.`}
        </p>
      </div>

      <Advanced>
        <KeyValues
          rows={[
            ['Identificativo', trade.trade_id],
            ['Stato interno', trade.status],
            ['Strategia', `${trade.strategy_version} · ${trade.variant}`],
            ['Stato scientifico', trade.research_status],
            ['Champion', trade.champion_status],
            ['Classe di evidenza', trade.evidence_version],
            ['Esecuzione', trade.execution_model_version],
            ['Regola di ingresso', trade.entry_execution],
            ['Fill ambiguo', trade.ambiguous_fill_policy],
            ['Momento del segnale', trade.signal_time],
            ['Minuto di ingresso', trade.entry_minute],
            ['Motivo di uscita', trade.exit_reason ?? '—'],
            ['Dettaglio risoluzione', trade.resolution_detail],
            ['Ultimo aggiornamento', trade.last_update_time],
          ]}
        />
      </Advanced>
    </section>
  );
}
