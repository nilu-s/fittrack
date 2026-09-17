import type { ShoppingItem } from '$lib/types';

// A small, local catalogue makes the first shopping trip useful too.  Personal
// entries take precedence and become the "recently used" suggestions later.
const catalogue = [
  'Äpfel', 'Avocado', 'Bananen', 'Beeren', 'Blumenkohl', 'Brot', 'Butter', 'Champignons', 'Eier', 'Gurke',
  'Haferflocken', 'Hähnchen', 'Joghurt', 'Käse', 'Kartoffeln', 'Karotten', 'Knoblauch', 'Milch', 'Mozzarella', 'Nudeln',
  'Olivenöl', 'Orangen', 'Paprika', 'Reis', 'Salat', 'Skyr', 'Spinat', 'Tomaten', 'Zitronen', 'Zwiebeln',
  'Kaffee', 'Mineralwasser', 'Saft', 'Tee', 'Mehl', 'Zucker', 'Salz', 'Pfeffer', 'Passata', 'Bohnen',
  'Waschmittel', 'Spülmittel', 'Küchenrolle', 'Müllbeutel', 'Toilettenpapier', 'Zahnpasta', 'Shampoo', 'Batterien',
];

function normalized(value: string) {
  return value.toLocaleLowerCase('de-DE').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ß/g, 'ss').trim();
}

export function shoppingSuggestions(query: string, items: ShoppingItem[], limit = 6): string[] {
  const needle = normalized(query);
  const personal = [...items]
    .sort((left, right) => (right.completed_at ?? right.updated_at ?? '').localeCompare(left.completed_at ?? left.updated_at ?? ''))
    .map((item) => item.title);
  const unique = [...personal, ...catalogue].filter((title, index, values) => values.findIndex((value) => normalized(value) === normalized(title)) === index);
  if (!needle) return unique.slice(0, limit);
  return unique
    .filter((title) => normalized(title).includes(needle))
    .sort((left, right) => Number(!normalized(left).startsWith(needle)) - Number(!normalized(right).startsWith(needle)))
    .slice(0, limit);
}
