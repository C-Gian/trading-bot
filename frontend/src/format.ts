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
  if (status === 'MARKET_DATA_UNAVAILABLE')
    return 'Non è stato possibile leggere i dati di mercato. Riprova tra poco.';
  return 'I dati di mercato non sono completi, quindi il bot non si esprime.';
}
