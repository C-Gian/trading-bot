/** Italian presentation layer. Internal enum names never reach the Owner. */

const num = new Intl.NumberFormat('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const whole = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 0 });
const dateTime = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
});
const dayOnly = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit', month: 'short', timeZone: 'UTC',
});

export const money = (value: number | null | undefined) =>
  value === null || value === undefined ? '—' : num.format(value);

export const count = (value: number | null | undefined) =>
  value === null || value === undefined ? '—' : whole.format(value);

export const percent = (value: number | null | undefined) =>
  value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`;

const signedPercent = new Intl.NumberFormat('it-IT', {
  minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'exceptZero',
});

/** Session change, e.g. "+5,83%". */
export const changePercent = (ratio: number) => `${signedPercent.format(ratio * 100)}%`;

const signed = new Intl.NumberFormat('it-IT', {
  minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'exceptZero',
});

/** R is a multiple of the initial simulated risk; two decimals is plenty. */
export const rMultiple = (value: number | null | undefined) =>
  value === null || value === undefined ? '—' : `${signed.format(value)} R`;

export const when = (iso: string | null | undefined) =>
  !iso ? '—' : dateTime.format(new Date(iso));

export const day = (iso: string | null | undefined) => (!iso ? '—' : dayOnly.format(new Date(iso)));

export function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  if (seconds < 60) return `${Math.floor(seconds)} secondi`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return minutes > 0 ? `${hours}h ${minutes}min` : `${hours}h`;
  return `${minutes} minuti`;
}

/** "fra 3h 20min" / "scaduto" — never a raw timestamp diff. */
export function timeLeft(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return '—';
  const ms = new Date(iso).getTime() - now.getTime();
  if (ms <= 0) return 'tempo scaduto';
  const hours = Math.floor(ms / 3_600_000);
  const minutes = Math.round((ms % 3_600_000) / 60_000);
  return hours > 0 ? `fra ${hours}h ${minutes}min` : `fra ${minutes}min`;
}

export type Tone = 'pos' | 'neg' | 'neutral';

type StatusCopy = { label: string; tone: Tone; closed: boolean; body: string };

const STATUS: Record<string, StatusCopy> = {
  PERSISTING_INTENT: {
    label: 'Registrazione da verificare',
    tone: 'neutral',
    closed: false,
    body: 'La registrazione si è interrotta prima di autorizzare un ingresso.',
  },
  PENDING_ENTRY: {
    label: 'In attesa di ingresso',
    tone: 'neutral',
    closed: false,
    body: 'La simulazione è registrata e aspetta il prezzo di ingresso.',
  },
  OPEN: {
    label: 'Trade attivo',
    tone: 'neutral',
    closed: false,
    body: 'La simulazione è in corso: non ha ancora toccato stop, obiettivo o scadenza.',
  },
  CLOSED_TARGET: {
    label: 'Chiuso in profitto',
    tone: 'pos',
    closed: true,
    body: 'La simulazione ha raggiunto l’obiettivo.',
  },
  CLOSED_STOP: {
    label: 'Chiuso in perdita',
    tone: 'neg',
    closed: true,
    body: 'Il prezzo è sceso fino allo stop e la simulazione è stata chiusa.',
  },
  CLOSED_EXPIRY: {
    label: 'Scaduto',
    tone: 'neutral',
    closed: true,
    body: 'Il tempo massimo è finito e la simulazione è stata chiusa al prezzo del momento.',
  },
  INVALIDATED: {
    label: 'Annullato',
    tone: 'neutral',
    closed: true,
    body: 'Non è stato possibile simulare l’ingresso, quindi il trade non è valido.',
  },
  INVALIDATED_ENTRY_UNAVAILABLE: {
    label: 'Ingresso non disponibile',
    tone: 'neutral',
    closed: true,
    body: 'Nessuno dei cinque minuti futuri consentiti era disponibile: la simulazione è stata annullata.',
  },
  INVALIDATED_INTENT_PERSISTENCE: {
    label: 'Registrazione annullata',
    tone: 'neutral',
    closed: true,
    body: 'La registrazione iniziale non si è completata: nessun ingresso era consentito.',
  },
};

const UNKNOWN: StatusCopy = {
  label: 'Stato non disponibile',
  tone: 'neutral',
  closed: false,
  body: 'Lo stato di questa simulazione non è leggibile.',
};

export const statusCopy = (status: string): StatusCopy => STATUS[status] ?? UNKNOWN;

/** Why creation was refused, said plainly. Server text is technical. */
export function refusalCopy(message: string): string {
  if (/already PENDING_ENTRY or OPEN/i.test(message))
    return 'C’è già una simulazione in corso. Aggiornala o aspetta che si chiuda.';
  if (/already exists for this analysis/i.test(message))
    return 'Questa analisi ha già una simulazione registrata.';
  if (/NO_TRADE/i.test(message))
    return 'L’analisi non propone nessun ingresso, quindi non c’è niente da simulare.';
  if (/sound market data/i.test(message))
    return 'I dati di mercato non erano completi: nessuna simulazione è stata creata.';
  return 'Non è stato possibile creare la simulazione in questo momento.';
}

/** Why an analysis could not be produced. */
export function dataStatusCopy(status: string): string | null {
  if (status === 'OK') return null;
  if (status === 'NO_VALIDATED_STRATEGY')
    return 'Nessuna strategia validata: System G1 è in sviluppo sintetico, quindi il bot resta su NO_TRADE.';
  if (status === 'RESEARCH_PARKED')
    return 'La ricerca è sospesa: non esiste una strategia validata, quindi il bot resta su NO_TRADE.';
  if (status === 'MARKET_DATA_UNAVAILABLE')
    return 'Non è stato possibile leggere i dati di mercato. Riprova tra poco.';
  return 'I dati di mercato non sono completi, quindi il bot non si esprime.';
}

/** One plain sentence about what Bitcoin just did, from the candles the API returned. */
export function marketSummary(ratio: number | null, candles: number): string | null {
  if (ratio === null || candles < 2) return null;
  const span = candles >= 48
    ? `${Math.round(candles / 24)} giorni`
    : candles === 1 ? 'un’ora' : `${candles} ore`;
  const size = Math.abs(ratio * 100);
  if (size < 0.1) return `Bitcoin è sostanzialmente stabile rispetto a ${span} fa.`;
  const move = signedPercent.format(Math.abs(ratio * 100)).replace('+', '');
  return ratio > 0
    ? `Bitcoin è in rialzo del ${move}% rispetto a ${span} fa.`
    : `Bitcoin è in calo del ${move}% rispetto a ${span} fa.`;
}

export type Check = { label: string; state: string; ok: boolean; body: string };

/**
 * The three frozen ALIGNED gates, said in human language. No feature name, formula or
 * threshold appears here - those stay in the technical disclosure.
 */
export function gateChecks(features: {
  breakout: boolean; persistent_up: boolean; participation: boolean;
} | undefined): Check[] {
  if (!features) return [];
  return [
    {
      label: 'Direzione del mercato',
      ok: features.persistent_up,
      state: features.persistent_up ? 'Favorevole' : 'Non favorevole',
      body: features.persistent_up
        ? 'Nelle ultime settimane il prezzo ha spinto più in su che in giù.'
        : 'Negli ultimi giorni il mercato non ha una direzione chiara verso l’alto.',
    },
    {
      label: 'Forza del movimento',
      ok: features.breakout,
      state: features.breakout ? 'Favorevole' : 'Non abbastanza forte',
      body: features.breakout
        ? 'Il prezzo ha superato i massimi delle ultime ore.'
        : 'Il prezzo non ha superato i massimi delle ultime ore.',
    },
    {
      label: 'Conferma dai volumi',
      ok: features.participation,
      state: features.participation ? 'Confermato' : 'Non confermato',
      body: features.participation
        ? 'Il movimento è accompagnato da scambi superiori alla media.'
        : 'Gli scambi sono nella media: poche persone stanno seguendo il movimento.',
    },
  ];
}

/** The bot enters only when all three agree. */
export function checksSummary(checks: Check[]): string | null {
  if (checks.length === 0) return null;
  const missing = checks.filter(check => !check.ok).length;
  if (missing === 0) return 'Tutti e tre i controlli sono favorevoli.';
  return missing === 1
    ? 'Un controllo su tre non è favorevole, e al bot servono tutti e tre.'
    : `${missing} controlli su tre non sono favorevoli, e al bot servono tutti e tre.`;
}
