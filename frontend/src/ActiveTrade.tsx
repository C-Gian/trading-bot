import { PaperTrade } from './api';
import { duration, money, rMultiple, statusCopy, timeLeft, when } from './format';
import { Advanced, Badge, Debug, KeyValues } from './ui';

export function ActiveTrade({
  trade, busy, onUpdate,
}: { trade: PaperTrade; busy: boolean; onUpdate: () => void }) {
  const copy = statusCopy(trade.status);
  const pending = trade.status === 'PENDING_ENTRY';
  const recovering = trade.status === 'PERSISTING_INTENT';
  const awaitingEntry = pending || recovering;

  return (
    <section className="surface pad" aria-label="Simulazione in corso">
      <div className="tradehead">
        <div className="stack-sm">
          <span className="eyebrow">La tua simulazione</span>
          <p className="tradestate">{pending ? 'Ingresso in attesa' : copy.label}</p>
          <p className="lede">{pending
            ? 'L’ingresso viene preso solo su un minuto futuro non ancora osservato quando il trade paper viene registrato.'
            : copy.body}</p>
        </div>
        <Badge tone={copy.tone} dot={!copy.closed}>
          {copy.closed ? 'Chiusa' : 'In corso'}
        </Badge>
      </div>

      {awaitingEntry ? (
        <div className="pad" style={{ paddingInline: 0 }}>
          <KeyValues rows={recovering ? [
            ['Stato', 'Registrazione incompleta'],
            ['Ingresso', 'Non consentito'],
            ['Decisione presa', when(trade.analysis_completed_at)],
          ] : [
            ['Stato', 'Paper LONG registrato'],
            ['Ingresso', 'In attesa'],
            ['Decisione presa', when(trade.analysis_completed_at)],
            ['Ingresso non prima di', when(trade.entry_not_before)],
            ['Età del segnale', duration(trade.signal_age_seconds)],
          ]} />
        </div>
      ) : <div className="levels">
        <div className="level">
          <div className="label">Ingresso simulato · {when(trade.entry_time)} UTC</div>
          <div className="num">{money(trade.entry_price)}</div>
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
      </div>}

      <div className="row" style={{ marginTop: 'var(--s5)' }}>
        {!copy.closed && (
          <button className="btn primary" onClick={onUpdate} disabled={busy}>
            Aggiorna trade
          </button>
        )}
        <p className="footnote grow">
          {copy.closed
            ? `Chiusa il ${when(trade.exit_time)} UTC.`
            : recovering
              ? 'Aggiorna lo stato: un ingresso non può essere creato da questa registrazione incompleta.'
              : pending
              ? `Aggiorna dopo ${when(trade.entry_not_before)} UTC per cercare il primo minuto consentito.`
              : `In questa versione l’aggiornamento è manuale: niente si muove da solo. Scadenza ${when(trade.expiry_time)} UTC.`}
        </p>
      </div>

      <Advanced>
        <KeyValues
          rows={[
            ['Strategia', `${trade.strategy_version} · ${trade.variant}`],
            ['Stato della strategia', 'Candidata sperimentale in modalità paper'],
            ['Strategia approvata', trade.champion_status === 'NONE' ? 'Nessuna' : trade.champion_status],
            ['Momento del segnale', when(trade.signal_time)],
            ['Decisione completata', when(trade.analysis_completed_at)],
            ['Intento persistito', when(trade.intent_persisted_at)],
            ['Ingresso non prima di', when(trade.entry_not_before)],
            ['Età del segnale', duration(trade.signal_age_seconds)],
            ['Ingresso simulato', trade.entry_time ? when(trade.entry_time) : 'non ancora avvenuto'],
            ['Scadenza', when(trade.expiry_time)],
            ['Durata massima', `${trade.max_hold_minutes} minuti`],
            ['Ultimo aggiornamento', when(trade.last_update_time)],
          ]}
        />
        <Debug>
          <KeyValues
            rows={[
              ['Identificativo', trade.trade_id],
              ['Stato interno', trade.status],
              ['Classe di evidenza', trade.evidence_version],
              ['Classificazione', trade.evidence_stage],
              ['Avvio', trade.initiation_mode],
              ['Esecuzione', trade.execution_model_version],
              ['Regola di ingresso', trade.entry_execution],
              ['Fill ambiguo', trade.ambiguous_fill_policy],
              ['Minuto di ingresso', trade.entry_minute],
              ['Motivo di uscita', trade.exit_reason ?? '—'],
              ['Dettaglio risoluzione', trade.resolution_detail],
            ]}
          />
        </Debug>
      </Advanced>
    </section>
  );
}
