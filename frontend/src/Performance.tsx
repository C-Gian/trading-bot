import { PaperStatistics, PaperTrade } from './api';
import { count, day, money, percent, rMultiple, statusCopy } from './format';
import { Advanced, Empty, KeyValues, Section, Stat } from './ui';

export function Performance({ stats }: { stats: PaperStatistics | null }) {
  if (!stats) {
    return (
      <Section title="Andamento" label="Andamento" hint="Risultati delle simulazioni">
        <Empty title="Caricamento…" body="Stiamo leggendo i risultati delle tue simulazioni." />
      </Section>
    );
  }

  if (stats.empty) {
    return (
      <Section title="Andamento" label="Andamento" hint="Risultati delle simulazioni">
        <Empty
          title="Nessun risultato ancora"
          body="Le statistiche appariranno dopo i primi paper trade completati."
        />
        <div className="pad" style={{ paddingTop: 0 }}>
          <Advanced>
            <KeyValues
              rows={[
                ['Simulazioni registrate', count(stats.total_paper_trades)],
                ['In corso', count(stats.active)],
                ['Classe di evidenza', stats.evidence_version],
                ['Versione statistiche', stats.statistics_version],
                ['Champion', stats.champion_status],
              ]}
            />
          </Advanced>
        </div>
      </Section>
    );
  }

  const cumulative = stats.cumulative_realized_r;
  const mean = stats.expectancy_r_per_trade;

  return (
    <Section
      title="Andamento"
      label="Andamento"
      hint="Solo simulazioni completate — non sono risultati di test storici"
    >
      <div className="pad">
        <div className="stats">
          <Stat
            label="Trade completati"
            value={count(stats.realized_trades)}
            note={stats.active > 0 ? `${stats.active} ancora in corso` : undefined}
          />
          <Stat
            label="Vinti / Persi"
            value={`${count(stats.wins)} / ${count(stats.losses)}`}
            note={stats.win_rate === null ? undefined : `${percent(stats.win_rate)} di successo`}
          />
          <Stat
            label="Media per trade"
            value={rMultiple(mean)}
            tone={mean === null ? undefined : mean >= 0 ? 'pos' : 'neg'}
            note="1 R = il rischio iniziale simulato"
          />
          <Stat
            label="Risultato cumulativo"
            value={rMultiple(cumulative)}
            tone={cumulative === null ? undefined : cumulative >= 0 ? 'pos' : 'neg'}
            note={stats.max_drawdown_r === null ? undefined : `Calo massimo ${rMultiple(stats.max_drawdown_r)}`}
          />
        </div>

        <p className="footnote" style={{ marginTop: 'var(--s4)' }}>
          Le simulazioni ancora aperte non entrano in questi numeri.
        </p>

        <Advanced>
          <KeyValues
            rows={[
              ['Simulazioni registrate', count(stats.total_paper_trades)],
              ['In attesa di ingresso', count(stats.pending_entry)],
              ['Aperte', count(stats.open)],
              ['Chiuse', count(stats.closed)],
              ['Annullate', count(stats.invalidated)],
              ['Chiuse in obiettivo', count(stats.closed_target)],
              ['Chiuse in stop', count(stats.closed_stop)],
              ['Scadute', count(stats.expiries)],
              ['Miglior risultato', rMultiple(stats.best_realized_r)],
              ['Peggior risultato', rMultiple(stats.worst_realized_r)],
              ['Classe di evidenza', stats.evidence_version],
              ['Versione statistiche', stats.statistics_version],
              ['Champion', stats.champion_status],
            ]}
          />
        </Advanced>
      </div>
    </Section>
  );
}

export function TradeHistory({ trades }: { trades: PaperTrade[] }) {
  const rows = [...trades].reverse();
  return (
    <Section title="Simulazioni recenti" label="Simulazioni recenti">
      {rows.length === 0 ? (
        <Empty
          title="Nessuna simulazione"
          body="Quando il bot proporrà un ingresso e tu lo simulerai, comparirà qui."
        />
      ) : (
        <div className="tablewrap">
          <table className="table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Tipo</th>
                <th>Ingresso</th>
                <th>Uscita</th>
                <th>Esito</th>
                <th>Risultato</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(trade => {
                const copy = statusCopy(trade.status);
                return (
                  <tr key={trade.trade_id}>
                    <td>{day(trade.signal_time)}</td>
                    <td>Long</td>
                    <td className="num">{money(trade.entry_price)}</td>
                    <td className="num">{money(trade.exit_price)}</td>
                    <td className={copy.tone === 'pos' ? 'pos' : copy.tone === 'neg' ? 'neg' : ''}>
                      {copy.label}
                    </td>
                    <td className={`num ${trade.net_r === null ? '' : trade.net_r >= 0 ? 'pos' : 'neg'}`.trim()}>
                      {rMultiple(trade.net_r)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}
