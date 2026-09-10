/** Deterministic quick capture. Never contacts a model or resolves a place. */
export type QuickEntry = { title: string; date: string; time: string | null; weekdays: number[] | null; error?: string };
const weekdays = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag', 'samstag', 'sonntag'];
export function parseQuickEntry(text: string, reference: string): QuickEntry {
  let title = text.trim();
  const result: QuickEntry = { title, date: reference, time: null, weekdays: null };
  const day = new Date(`${reference}T12:00:00`);
  if (!Number.isFinite(day.getTime())) return { ...result, error: 'Bitte wähle einen gültigen Tag.' };
  // Complex repetitions must not accidentally become a weekly routine.
  if (/\b(alle\s+\w+\s+wochen|monatlich|jährlich|jeden\s+(zweiten|dritten|letzten))\b/i.test(title)) {
    return { ...result, error: 'Diese Wiederholung bitte in den Details oder mit der KI planen.' };
  }
  const routine = title.match(/\b(?:jeden|jede|immer am)\s+(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b/i);
  const daily = title.match(/\b(?:täglich|taeglich|jeden tag)\b/i);
  if (routine) { result.weekdays = [weekdays.indexOf(routine[1].toLowerCase())]; title = title.replace(routine[0], ''); }
  else if (daily) { result.weekdays = [0, 1, 2, 3, 4, 5, 6]; title = title.replace(daily[0], ''); }
  const time = title.match(/\b(?:um\s+)?([01]?\d|2[0-3])(?::([0-5]\d)(?:\s*uhr)?|\s*uhr)\b/i);
  if (time) { result.time = `${time[1].padStart(2, '0')}:${time[2] ?? '00'}`; title = title.replace(time[0], ''); }
  if (/\b(?:um\s+\d{1,2}(?::\d{2})?|\d{1,2}:\d{2})\b/i.test(title)) return { ...result, error: 'Uhrzeit nicht eindeutig. Bitte als 17:30 oder 17 Uhr angeben.' };
  if (!result.weekdays) {
    const relative = title.match(/(?<![\p{L}\p{N}_])(übermorgen|uebermorgen|morgen|heute)(?![\p{L}\p{N}_])/iu);
    const weekday = title.match(/\b(?:(nächsten|naechsten|kommenden|am)\s+)?(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b/i);
    const explicit = title.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
    if ([relative, weekday, explicit].filter(Boolean).length > 1) return { ...result, error: 'Mehrere Datumsangaben erkannt. Bitte einen Termin wählen.' };
    if (explicit) {
      const parsed = new Date(`${explicit[0]}T12:00:00`);
      if (!Number.isFinite(parsed.getTime()) || parsed.getFullYear() !== Number(explicit[1]) || parsed.getMonth() + 1 !== Number(explicit[2]) || parsed.getDate() !== Number(explicit[3])) return { ...result, error: 'Dieses Datum existiert nicht.' };
      day.setTime(parsed.getTime()); title = title.replace(explicit[0], '');
    } else if (relative) {
      const word = relative[1].toLowerCase(); day.setDate(day.getDate() + (word === 'heute' ? 0 : word === 'morgen' ? 1 : 2)); title = title.replace(relative[0], '');
    } else if (weekday) {
      let delta = (weekdays.indexOf(weekday[2].toLowerCase()) - (day.getDay() + 6) % 7 + 7) % 7;
      if (weekday[1] && weekday[1].toLowerCase() !== 'am') delta ||= 7;
      day.setDate(day.getDate() + delta); title = title.replace(weekday[0], '');
    }
  }
  result.title = title.replace(/\s+/g, ' ').replace(/^[\s,.-]+|[\s,.-]+$/g, '');
  result.date = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
  if (!result.title) result.error = 'Bitte ergänze einen Titel.';
  return result;
}
