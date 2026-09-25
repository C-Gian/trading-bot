// Pure display mapping from backend replay records to candle annotations. Nothing here scores,
// decides or computes a trading outcome: it only places what the causal view already contains.
import type { ReplayCandle, ReplayDecision, ReplayFill, ReplayPrediction, ReplayRealization } from './replayApi';

const FIFTEEN_MINUTES = 15 * 60 * 1000;

export type PredictionGlyph = { candleIndex: number; symbol: string; tone: string; prediction: ReplayPrediction; realization: ReplayRealization | null };
export type DecisionGlyph = { candleIndex: number; symbol: string; tone: string; decision: ReplayDecision };
export type FillMark = { position: number; symbol: string; tone: string; fill: ReplayFill };

export function predictionSymbol(direction: ReplayPrediction['predicted_direction']): string {
  return { UP: '▲', DOWN: '▼', NEUTRAL: '●', UNAVAILABLE: '○' }[direction];
}

export function decisionSymbol(action: ReplayDecision['action']): string {
  return { LONG: 'L', SHORT: 'S', NO_TRADE: '·' }[action];
}

/** The eligible decision candle is the completed 15m candle whose close equals the issue time. */
export function candleIndexFor(candles: ReplayCandle[], issueTime: string): number {
  const opened = new Date(Date.parse(issueTime) - FIFTEEN_MINUTES).toISOString().replace('.000Z', 'Z');
  return candles.findIndex(candle => candle.open_time === opened);
}

export function predictionGlyphs(
  candles: ReplayCandle[], predictions: ReplayPrediction[], realizations: ReplayRealization[],
): PredictionGlyph[] {
  const matured = new Map(realizations.map(item => [item.prediction_id, item]));
  return predictions
    .map(prediction => {
      const realization = matured.get(prediction.prediction_id) ?? null;
      const tone = realization?.direction_correct === true ? 'hit'
        : realization?.direction_correct === false ? 'miss'
          : prediction.predicted_direction === 'UNAVAILABLE' ? 'muted' : 'pending';
      return {
        candleIndex: candleIndexFor(candles, prediction.issue_time),
        symbol: predictionSymbol(prediction.predicted_direction),
        tone, prediction, realization,
      };
    })
    .filter(glyph => glyph.candleIndex >= 0);
}

export function decisionGlyphs(candles: ReplayCandle[], decisions: ReplayDecision[]): DecisionGlyph[] {
  return decisions
    .map(decision => ({
      candleIndex: candleIndexFor(candles, decision.decision_time),
      symbol: decisionSymbol(decision.action),
      tone: decision.action === 'LONG' ? 'long' : decision.action === 'SHORT' ? 'short' : 'flat',
      decision,
    }))
    .filter(glyph => glyph.candleIndex >= 0);
}

/** Entry/exit marks sit at their actual simulated execution minute inside the 15m candle. */
export function fillMarks(candles: ReplayCandle[], fills: ReplayFill[]): FillMark[] {
  if (candles.length === 0) return [];
  const first = Date.parse(candles[0].open_time);
  return fills
    .filter(fill => fill.kind === 'ENTRY' || fill.kind === 'EXIT')
    .map(fill => ({
      position: (Date.parse(fill.event_time) - first) / FIFTEEN_MINUTES,
      symbol: fill.kind === 'ENTRY' ? (fill.side === 'LONG' ? '↑' : '↓') : '×',
      tone: fill.side === 'LONG' ? 'long' : 'short',
      fill,
    }))
    .filter(mark => mark.position >= 0 && mark.position <= candles.length);
}
