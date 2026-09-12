"""Build a local, searchable gallery from the Playwright audit screenshots."""
from pathlib import Path
from html import escape
import json

root = Path(__file__).resolve().parents[2] / 'docs/evidence/2026-09-12-ui-audit'
results = json.loads((root / 'after/results.json').read_text())
files = sorted((root / 'after').glob('*.png'))
cards = ''.join(f'<a class="card" href="after/{escape(p.name)}" data-name="{escape(p.stem)}"><img loading="lazy" src="after/{escape(p.name)}" alt="{escape(p.stem)}"><span>{escape(p.stem)}</span></a>' for p in files)
(root / 'index.html').write_text('''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cronicl UI-Prüfung</title><style>
body{margin:0;background:#c9cbc3;color:#192019;font:16px system-ui}header{position:sticky;top:0;padding:20px;background:#c9cbc3;border-bottom:1px solid #90938a}h1{margin:0 0 8px;font-size:24px}p{margin:8px 0}input,select{font:inherit;padding:10px;border:1px solid #90938a;border-radius:8px;background:#bdc0b7;color:inherit}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:20px;padding:20px}.card{display:flex;flex-direction:column;color:inherit;border:1px solid #90938a;border-radius:10px;overflow:hidden;text-decoration:none}.card img{width:100%;height:360px;object-fit:contain;object-position:top;background:#b8bab2}.card span{padding:12px;overflow-wrap:anywhere}.card[hidden]{display:none}:focus-visible{outline:3px solid #285f8d;outline-offset:3px}
</style><header><h1>Cronicl · UI/UX-Prüfung</h1><p>''' + str(len(files)) + ''' Screenshots · 320 / 390 / 1440 Pixel · synthetische Testdaten</p><label>Ansicht <select id="size"><option value="">Alle Größen</option><option>small</option><option>mobile</option><option>desktop</option></select></label> <label>Suche <input id="query" type="search" placeholder="z. B. calendar, training, error"></label><p><a href="README.md">Prüfbericht und Grenzen</a> · <a href="after/results.json">Testergebnisse</a></p></header><main>''' + cards + '''</main><script>const size=document.querySelector('#size'),query=document.querySelector('#query');function filter(){for(const card of document.querySelectorAll('.card'))card.hidden=!(card.dataset.name.startsWith(size.value)&&card.dataset.name.includes(query.value.toLowerCase()));}size.onchange=filter;query.oninput=filter;</script></html>''')
print(f'Gallery: {len(files)} screenshots, {len(results)} checked states')
