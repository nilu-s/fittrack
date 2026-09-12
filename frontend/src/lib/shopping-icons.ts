export type ShoppingIconCategory = 'produce' | 'dairy' | 'bakery' | 'pantry' | 'frozen' | 'beverage' | 'household' | 'other';

export type ShoppingIconDefinition = { key: string; label: string; category: ShoppingIconCategory; aliases: string[] };

export const shoppingIcons: ShoppingIconDefinition[] = [
  { key: 'apple', label: 'Apfel', category: 'produce', aliases: ['apfel', 'birne', 'beeren', 'obst'] },
  { key: 'orange', label: 'Orange', category: 'produce', aliases: ['orange', 'mandarine', 'grapefruit'] },
  { key: 'strawberry', label: 'Erdbeeren', category: 'produce', aliases: ['erdbeere', 'himbeere', 'beeren'] },
  { key: 'banana', label: 'Banane', category: 'produce', aliases: ['banane'] },
  { key: 'carrot', label: 'Gemüse', category: 'produce', aliases: ['karotte', 'paprika', 'gurke', 'brokkoli', 'zwiebel'] },
  { key: 'tomato', label: 'Tomate', category: 'produce', aliases: ['tomate'] },
  { key: 'salad', label: 'Salat', category: 'produce', aliases: ['salat', 'spinat', 'kohl'] },
  { key: 'potato', label: 'Kartoffel', category: 'produce', aliases: ['kartoffel'] },
  { key: 'lemon', label: 'Zitrone', category: 'produce', aliases: ['zitrone', 'limette'] },
  { key: 'mushroom', label: 'Pilze', category: 'produce', aliases: ['pilze', 'champignon'] },
  { key: 'milk', label: 'Milch', category: 'dairy', aliases: ['milch', 'sahne', 'butter'] },
  { key: 'cheese', label: 'Käse', category: 'dairy', aliases: ['käse', 'mozzarella', 'feta'] },
  { key: 'yogurt', label: 'Joghurt', category: 'dairy', aliases: ['joghurt', 'skyr', 'quark'] },
  { key: 'egg', label: 'Eier', category: 'dairy', aliases: ['eier', 'ei'] },
  { key: 'meat', label: 'Fleisch', category: 'dairy', aliases: ['fleisch', 'hack', 'steak'] },
  { key: 'chicken', label: 'Huhn', category: 'dairy', aliases: ['huhn', 'hähnchen', 'geflügel'] },
  { key: 'fish', label: 'Fisch', category: 'dairy', aliases: ['fisch', 'lachs', 'thunfisch'] },
  { key: 'bread', label: 'Brot', category: 'bakery', aliases: ['brot', 'toast'] },
  { key: 'croissant', label: 'Gebäck', category: 'bakery', aliases: ['brötchen', 'croissant'] },
  { key: 'pasta', label: 'Pasta', category: 'pantry', aliases: ['pasta', 'nudeln', 'spaghetti', 'penne'] },
  { key: 'rice', label: 'Reis', category: 'pantry', aliases: ['reis', 'couscous', 'quinoa'] },
  { key: 'oil', label: 'Öl & Essig', category: 'pantry', aliases: ['öl', 'essig'] },
  { key: 'canned', label: 'Vorrat', category: 'pantry', aliases: ['bohnen', 'linsen', 'hafer', 'passata'] },
  { key: 'spices', label: 'Gewürze', category: 'pantry', aliases: ['salz', 'zucker', 'gewürz', 'mehl'] },
  { key: 'cereal', label: 'Müsli', category: 'pantry', aliases: ['müsli', 'cerealien', 'cornflakes'] },
  { key: 'chocolate', label: 'Schokolade', category: 'pantry', aliases: ['schokolade', 'süßigkeit', 'praline'] },
  { key: 'chips', label: 'Chips', category: 'pantry', aliases: ['chips', 'snack', 'nüsse'] },
  { key: 'cookies', label: 'Kekse', category: 'pantry', aliases: ['kekse', 'keks'] },
  { key: 'coffee', label: 'Kaffee', category: 'beverage', aliases: ['kaffee', 'espresso'] },
  { key: 'water', label: 'Wasser', category: 'beverage', aliases: ['wasser', 'sprudel'] },
  { key: 'juice', label: 'Saft', category: 'beverage', aliases: ['saft', 'smoothie', 'limonade'] },
  { key: 'tea', label: 'Tee', category: 'beverage', aliases: ['tee'] },
  { key: 'soda', label: 'Limo', category: 'beverage', aliases: ['cola', 'limo', 'brause'] },
  { key: 'beer', label: 'Bier', category: 'beverage', aliases: ['bier'] },
  { key: 'wine', label: 'Wein', category: 'beverage', aliases: ['wein', 'sekt'] },
  { key: 'icecream', label: 'Tiefkühl', category: 'frozen', aliases: ['tiefkühl', 'tk', 'eis'] },
  { key: 'cleaner', label: 'Reiniger', category: 'household', aliases: ['reiniger', 'spülmittel'] },
  { key: 'toilet-paper', label: 'Toilettenpapier', category: 'household', aliases: ['toilettenpapier', 'klopapier'] },
  { key: 'laundry', label: 'Wäsche', category: 'household', aliases: ['waschmittel', 'wäsche'] },
  { key: 'soap', label: 'Seife', category: 'household', aliases: ['seife', 'duschgel'] },
  { key: 'toothpaste', label: 'Zahnpasta', category: 'household', aliases: ['zahnpasta', 'zahnbürste'] },
  { key: 'shampoo', label: 'Shampoo', category: 'household', aliases: ['shampoo', 'conditioner'] },
  { key: 'paper-towels', label: 'Küchenrolle', category: 'household', aliases: ['küchenrolle', 'küchenpapier'] },
  { key: 'batteries', label: 'Batterien', category: 'household', aliases: ['batterie', 'akkus'] },
  { key: 'flowers', label: 'Blumen', category: 'household', aliases: ['blumen', 'pflanze'] },
  { key: 'pet', label: 'Tierfutter', category: 'household', aliases: ['tierfutter', 'katzen', 'hunde'] },
];

export const shoppingIconByKey = new Map(shoppingIcons.map((icon) => [icon.key, icon]));

// Existing lists stored a category key as their icon key.  Keep those entries
// recognisable until the user edits them; no data migration is needed for a
// purely visual catalogue upgrade.
const legacyCategoryIcons: Record<string, string> = {
  produce: 'carrot', dairy: 'milk', bakery: 'bread', pantry: 'canned',
  frozen: 'icecream', beverage: 'water', household: 'cleaner'
};

export function resolveShoppingIcon(iconKey: string) {
  return shoppingIconByKey.get(iconKey) ?? shoppingIconByKey.get(legacyCategoryIcons[iconKey]);
}

export function suggestedShoppingIcons(query: string, limit = 6) {
  const value = query.trim().toLocaleLowerCase('de');
  if (!value) return shoppingIcons.slice(0, limit);
  const matches = shoppingIcons.filter((icon) => icon.label.toLocaleLowerCase('de').includes(value) || icon.aliases.some((alias) => value.includes(alias) || alias.includes(value)));
  return matches.slice(0, limit);
}
