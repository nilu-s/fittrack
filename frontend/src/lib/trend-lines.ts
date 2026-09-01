import type { TrendPoint } from './types';

export type TrendLineState = 'actual' | 'interpolated' | 'baseline';

export interface TrendLineDay {
  date: string;
  value: number;
  state: TrendLineState;
}

/**
 * Builds the shared app trend rule for a fixed date range:
 * real observations are connected directly, gaps are interpolated, and the
 * first/last observed value is carried as a baseline beyond the data range.
 */
export function buildTrendLine(points: TrendPoint[], endDate: string, days: number): TrendLineDay[] {
  const knownPoints = points
    .filter((point): point is TrendPoint & { value: number } => point.value != null)
    .map((point) => ({ date: point.date, value: Number(point.value), time: new Date(`${point.date}T00:00`).getTime() }))
    .sort((a, b) => a.time - b.time);
  const known = new Map(knownPoints.map((point) => [point.date, point.value]));
  const end = new Date(`${endDate}T00:00`);
  const line: TrendLineDay[] = [];

  for (let offset = days - 1; offset >= 0; offset--) {
    const current = new Date(end);
    current.setDate(current.getDate() - offset);
    const date = localDateString(current);
    const value = known.get(date);
    if (value != null) line.push({ date, value, state: 'actual' });
    else line.push({ date, value: Number.NaN, state: 'baseline' });
  }

  if (!knownPoints.length) return [];

  for (const day of line) {
    if (day.state === 'actual') continue;
    const time = new Date(`${day.date}T00:00`).getTime();
    const before = knownPoints.findLast((point) => point.time < time);
    const after = knownPoints.find((point) => point.time > time);
    if (before && after) {
      day.value = before.value + (after.value - before.value) * (time - before.time) / (after.time - before.time);
      day.state = 'interpolated';
    } else if (before) {
      day.value = before.value;
    } else if (after) {
      day.value = after.value;
    }
  }

  return line;
}

export function trendSegmentPaths(
  days: TrendLineDay[],
  coords: Array<{ x: number; y: number }>,
): Record<'actual' | 'interpolated' | 'baseline', string> {
  const paths: Record<TrendLineState, string[]> = { actual: [], interpolated: [], baseline: [] };
  for (let index = 0; index < coords.length - 1; index++) {
    const state: TrendLineState = index < 0 || index >= days.length - 1 || days[index].state === 'baseline' || days[index + 1].state === 'baseline'
      ? 'baseline'
      : days[index].state === 'actual' && days[index + 1].state === 'actual'
        ? 'actual'
        : 'interpolated';
    paths[state].push(`M${coords[index].x.toFixed(1)},${coords[index].y.toFixed(1)} L${coords[index + 1].x.toFixed(1)},${coords[index + 1].y.toFixed(1)}`);
  }
  return {
    actual: paths.actual.join(' '),
    interpolated: paths.interpolated.join(' '),
    baseline: paths.baseline.join(' '),
  };
}

function localDateString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
