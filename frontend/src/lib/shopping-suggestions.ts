import type { ShoppingItem } from '$lib/types';

export type ShoppingSearchTile = { title: string; category: string; known: boolean };

// A small, local catalogue makes the first shopping trip useful too.  Personal
// entries take precedence and become the "recently used" suggestions later.
const catalogue = [
  'Äpfel', 'Avocado', 'Bananen', 'Beeren', 'Blumenkohl', 'Brot', 'Butter', 'Champignons', 'Eier', 'Gurke',
  'Haferflocken', 'Hähnchen', 'Joghurt', 'Käse', 'Kartoffeln', 'Karotten', 'Knoblauch', 'Milch', 'Mozzarella', 'Nudeln',
  'Olivenöl', 'Orangen', 'Paprika', 'Reis', 'Salat', 'Skyr', 'Spinat', 'Tomaten', 'Zitronen', 'Zwiebeln',
  'Kaffee', 'Mineralwasser', 'Saft', 'Tee', 'Mehl', 'Zucker', 'Salz', 'Pfeffer', 'Passata', 'Bohnen',
  'Waschmittel', 'Spülmittel', 'Küchenrolle', 'Müllbeutel', 'Toilettenpapier', 'Zahnpasta', 'Shampoo', 'Batterien',
];

const categoryFor = (title: string) => {
  const value = normalized(title);
  if (/(apfel|avocado|banane|beere|blumenkohl|champignon|gurke|kartoffel|karotte|knoblauch|paprika|salat|spinat|tomate|zitrone|zwiebel)/.test(value)) return 'produce';
  if (/(butter|ei|hahnchen|joghurt|kase|milch|mozzarella|skyr)/.test(value)) return 'dairy';
  if (/brot/.test(value)) return 'bakery';
  if (/(kaffee|mineralwasser|saft|tee)/.test(value)) return 'beverage';
  if (/(wasch|spul|kuchenrolle|mull|toilettenpapier|zahnpasta|shampoo|batterie)/.test(value)) return 'household';
  return 'pantry';
};

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

/** Search-mode tiles intentionally contain only catalogue matches. A term with
 * no match becomes one neutral initials tile, matching the quick-list flow. */
export function shoppingSearchTiles(query: string): ShoppingSearchTile[] {
  const needle = normalized(query);
  if (!needle) return [];
  const matches = catalogue.filter((title) => normalized(title).includes(needle));
  if (!matches.length) return [{ title: query.trim(), category: 'other', known: false }];
  return matches.slice(0, 12).map((title) => ({ title, category: categoryFor(title), known: true }));
}
