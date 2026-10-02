"""Render the local bilingual reading comparison without dependencies or network."""
import html
import json
from pathlib import Path

NAMES = {'original': 'Original', 'original_idea': 'Ursprungsidee', 'current': 'Aktueller Ansatz', 'hybrid': 'Hybrid'}
DESCRIPTIONS = {
    'original': 'Ungekürzter Buchausschnitt aus vier aufeinanderfolgenden Abschnitten.',
    'original_idea': 'Embeddings, Louvain-Gruppen und feste Auswahlregeln. Danach schreibt das LLM aus den ausgewählten Originalpassagen. Neue Umsetzung der Ursprungsidee, kein unveränderter Legacy-Durchlauf.',
    'current': 'Bestehender Zusammenfassungskern: LLM-Inhaltskarten, Redaktionsplan, Gewichtung, Schreiben aus Originalstellen und satzweise Quellenprüfung. Vergleichsziel: 600 Wörter.',
    'hybrid': 'Dieselbe technische Vorauswahl mit größerem Kandidatenbudget. Das LLM wählt daraus passende Begründungen und Beispiele und schreibt die Fassung.'}


def render(folder, model):
    values = {name: json.loads((folder / (name + '.json')).read_text(encoding='utf-8')) for name in NAMES}
    info_path = folder / 'selection-info.json'
    info = json.loads(info_path.read_text(encoding='utf-8')) if info_path.exists() else {}
    for name, value in values.items():
        for stage in ['generation', 'diagnostic', 'translation']:
            records = [json.loads(p.read_text(encoding='utf-8'))
                       for p in (folder / 'calls' / (name + '-' + stage)).glob('*.json')]
            if records:
                value[stage] = {k: round(sum(r[k] for r in records), 2)
                                for k in ['input_tokens', 'output_tokens', 'seconds']} | {'calls': len(records)}
    embedded = json.loads((folder / 'embeddings.json').read_text(encoding='utf-8'))
    esc = html.escape
    language_rows = []
    for language, label, sub in [('en', 'English', 'Original und drei gekürzte Lesefassungen'),
                                  ('de', 'Deutsch', 'Vollständige Übersetzungen der jeweiligen englischen Fassung')]:
        cards = []
        for name, value in values.items():
            if value.get('status') == 'failed':
                cards.append('<article class="card" data-method="' + name + '"><header><span class="kicker">'
                    + esc(NAMES[name]) + '</span><h3>Lauf fehlgeschlagen</h3></header><div class="reader" lang="de"><p>'
                    + esc(value['failure']) + '</p><p>Es liegt keine freigegebene Lesefassung oder Übersetzung vor.</p></div></article>')
                continue
            text = '\n\n'.join(s['title'] + '\n\n' + s['text'] for s in value[language])
            (folder / f'{name}-{language}.txt').write_text(text, encoding='utf-8')
            words = sum(len(s['text'].split()) for s in value[language])
            paragraphs = ''.join('<section><h4>' + esc(s['title']) + '</h4>' +
                ''.join('<p>' + esc(p) + '</p>' for p in s['text'].split('\n') if p.strip()) + '</section>'
                for s in value[language])
            display_words = f'{words:,}'.replace(',', '.')
            cards.append(f'''<article class="card" data-method="{name}">
              <header><span class="kicker">{esc(NAMES[name])}</span><h3>{display_words} Wörter</h3>
              <a href="{name}-{language}.txt" download>Text herunterladen</a></header>
              <div class="reader" lang="{language}" tabindex="0" aria-label="{esc(NAMES[name])}, {label}">{paragraphs}</div>
              <footer><label>Dein Eindruck<textarea data-note="{name}-{language}" placeholder="Lesefluss, Stil, Verständlichkeit ..."></textarea></label></footer>
            </article>''')
        language_rows.append(f'<section id="{language}" class="language"><h2>{label}</h2><p class="subtitle">{sub}</p><div class="grid">' + ''.join(cards) + '</div></section>')
    rows = []
    diagnostics = []
    for name, value in values.items():
        for stage, title in [('generation', 'Kürzung inkl. interner Prüfung und Längenabgleich'), ('diagnostic', 'Gemeinsame Abschlussdiagnose'), ('translation', 'Übersetzung inkl. zweisprachiger Revision')]:
            if stage in value:
                m = value[stage]
                rows.append(f'<tr><td>{NAMES[name]}</td><td>{title}</td><td>{m["input_tokens"]:,}</td><td>{m["output_tokens"]:,}</td><td>{m["seconds"]:.1f}</td><td>{m["calls"]}</td></tr>')
        if 'review' in value:
            bits = []
            for key, title in [('factual_issues', 'Mögliche Bedeutungsfehler'), ('important_omissions', 'Mögliche wichtige Auslassungen'), ('style_observations', 'Stilbeobachtungen')]:
                items = value['review'].get(key, [])
                bits.append('<h4>' + title + '</h4><ul>' + ''.join('<li>' + esc(x) + '</li>' for x in items) + ('<li>Keine gemeldet.</li>' if not items else '') + '</ul>')
            diagnostics.append('<details><summary>' + NAMES[name] + '</summary>' + ''.join(bits) + '</details>')
    methods = ''.join('<li><strong>' + NAMES[n] + ':</strong> ' + esc(DESCRIPTIONS[n]) + '</li>' for n in NAMES)
    document = TEMPLATE.replace('<!--ROWS-->', ''.join(language_rows)).replace('<!--METRICS-->', ''.join(rows))
    document = document.replace('<!--METHODS-->', methods).replace('<!--DIAGNOSTICS-->', ''.join(diagnostics))
    if any(v.get('status') == 'failed' for v in values.values()):
        document = document.replace('Ein Buch. Vier Fassungen.', 'Ein Buch. Drei Lesefassungen.')
        document = document.replace('Vier Fassungen im Vergleich', 'Verifikationslauf im Vergleich')
        document = document.replace('Original und drei gekürzte Lesefassungen', 'Original, zwei gekürzte Lesefassungen und ein fehlgeschlagener Lauf')
        document = document.replace('Vergleiche das Original mit drei Kürzungsverfahren.', 'Zwei Kürzungsverfahren liefern Lesetexte. Der zusätzliche Ansatz scheiterte an seiner Quellenprüfung.')
        document = document.replace('Alle vier Fassungen', 'Alle Ergebnisse')
        document = document.replace('Alle drei Verfahren erhalten abschließend', 'Die fertiggestellten Kurzfassungen erhalten abschließend')
        document = document.replace('für alle drei fertigen englischen Texte', 'für die verfügbaren fertigen englischen Kurzfassungen')
    notes_path = folder / 'verification-notes.json'
    verification_notes = json.loads(notes_path.read_text(encoding='utf-8')) if notes_path.exists() else []
    if verification_notes:
        notes_html = '<details><summary>Zusätzlicher Quellenabgleich nach dem Lesen</summary><p>Diese Befunde wurden direkt mit dem gewählten Originalausschnitt abgeglichen. Die englischen Versuchsergebnisse wurden dafür nicht nachträglich verändert.</p><ul>'
        notes_html += ''.join('<li><strong>' + esc(NAMES[n['method']]) + ':</strong> ' + esc(n['finding']) + '</li>' for n in verification_notes)
        document = document.replace('</main>', notes_html + '</ul></details></main>')
    document = document.replace('MODEL_NAME', esc(model)).replace('EMBED_TOKENS', str(embedded['input_tokens'])).replace('EMBED_SECONDS', str(embedded['seconds']))
    if (folder / 'current-final-audit.json').exists():
        document = document.replace('Der aktuelle Ansatz enthält zusätzlich seine interne satzweise Prüfung.',
            'Der aktuelle Ansatz enthält zusätzlich seine interne satzweise Prüfung. In diesem reparierten Lauf '
            'erhält auch sein Längenabgleich das Original; nach dem letzten Umschreiben wird die endgültige '
            'englische Fassung erneut satzweise geprüft und bei Bedarf korrigiert. Die Prüfregeln sind damit '
            'strenger als bei Ursprungsidee und Hybrid. Deren Texte bleiben unverändert. '
            '<a href="current-final-audit.json">Protokoll der Endprüfung</a>.')
    if info:
        document = document.replace('Lesevergleich / 29. September 2026',
            'Lesevergleich / ' + esc(info.get('run_date', info.get('date', ''))))
        document = document.replace('Blitzscaling |', esc(info['book_title']) + ' |')
        document = document.replace('Blitzscaling, vier zusammenhängende Abschnitte mit 3.906 englischen Wörtern.',
            esc(info['book_title']) + ' von ' + esc(info['author']) + '. Zufällig ausgewählter Ausschnitt aus '
            + esc(info['chapter_title']) + ' mit ' + f"{info['words']:,}".replace(',', '.') + ' englischen Wörtern.')
        document = document.replace('blitz-comparison-', folder.name + '-')
        document = document.replace('Dies ist ein einzelner Vergleichslauf',
            'Zufallsauswahl aus ' + str(info['candidate_windows']) + ' möglichen zusammenhängenden Ausschnitten '
            'in nummerierten Kapiteln, ohne erneute Auswahl nach Sichtung. Start im Kapitel bei Textblock '
            + str(info['first_chunk_zero_based'] + 1) + '. <a href="selection-info.json">Auswahlprotokoll</a>. '
            'Dies ist ein einzelner Vergleichslauf')
        if info.get('aborted_preflight'):
            prior = info['aborted_preflight']
            document = document.replace('Unterschiedliche Modelle haben unterschiedliche Tokenpreise;',
                'Ein wegen fehlerhafter Absatzumbrüche abgebrochener Vorlauf ist hier nicht enthalten. '
                'Dort wurden bereits ' + str(prior['recorded_input_tokens']) + ' Eingabe- und '
                + str(prior['recorded_output_tokens']) + ' Ausgabetokens protokolliert; beim Abbruch '
                'noch laufende Anfragen sind möglicherweise nicht erfasst. Die Textauswahl blieb gleich. '
                'Unterschiedliche Modelle haben unterschiedliche Tokenpreise;')
    (folder / 'index.html').write_text(document, encoding='utf-8')
    save_report = {'model': model, 'target_words': 600, 'tolerance': [570, 630], 'source_selection': info,
                   'verification_notes': verification_notes,
                   'embedding': {k: v for k, v in embedded.items() if k != 'vectors'},
                   'methods': {n: {k: v for k, v in val.items() if k not in ['en', 'de']} for n, val in values.items()}}
    (folder / 'comparison-report.json').write_text(json.dumps(save_report, ensure_ascii=False, indent=2), encoding='utf-8')


TEMPLATE = r'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blitzscaling | Vier Fassungen im Vergleich</title>
<style>
:root{color-scheme:light;--ink:#203b35;--muted:#60736d;--line:#d4ddd5;--paper:#fffef9;--bg:#f0f3ec}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}main{max-width:1800px;margin:auto;padding:40px 32px 80px}h1{font:500 clamp(32px,4vw,56px)/1.12 Georgia,serif;max-width:900px;margin:12px 0 18px}h2{font:400 32px/1.2 Georgia,serif;margin-bottom:6px}h3{margin:4px 0;font-size:16px;font-weight:500}h4{font:600 18px/1.4 Georgia,serif;margin:20px 0 12px}p{margin:0 0 16px}.lead{max-width:820px;color:var(--muted)}.kicker{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:700}a{color:inherit;text-underline-offset:4px}button,select{font:inherit;border:1px solid var(--line);border-radius:7px;background:var(--paper);padding:8px 12px;color:var(--ink);cursor:pointer}button:hover{background:#e0e9df}button[aria-pressed=true]{background:var(--ink);color:white}.toolbar{display:flex;gap:12px;flex-wrap:wrap;align-items:center;padding:16px 0;border-block:1px solid var(--line);margin:28px 0}.toolbar label{display:flex;align-items:center;gap:8px}.jump{margin-left:auto;display:flex;gap:18px}.language{scroll-margin-top:20px;margin-top:38px}.subtitle{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;align-items:start}.grid.pair{grid-template-columns:repeat(2,minmax(0,1fr))}.card{background:var(--paper);border:1px solid var(--line);border-radius:12px;overflow:hidden}.card header{padding:20px 22px 16px;border-bottom:1px solid var(--line);min-height:116px}.card header a{font-size:13px;color:var(--muted)}.reader{height:600px;overflow:auto;padding:4px 22px 24px;font:17px/1.75 Georgia,serif;scrollbar-gutter:stable;overflow-wrap:anywhere}.reader p{white-space:pre-line}.reader:focus{outline:2px solid #618a78;outline-offset:-3px}.card footer{border-top:1px solid var(--line);padding:14px 20px;font-size:13px}textarea{width:100%;margin-top:5px;background:transparent;border:1px solid var(--line);border-radius:5px;padding:8px;min-height:72px;resize:vertical;font:14px/1.4 system-ui;color:var(--ink)}details{margin:20px 0;background:var(--paper);padding:18px 22px;border:1px solid var(--line);border-radius:10px}summary{cursor:pointer;font-weight:600}details p,details ul{margin-top:14px}li{margin-bottom:10px}table{border-collapse:collapse;width:100%;font-size:14px;margin-top:20px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line)}th:nth-child(n+3),td:nth-child(n+3){text-align:right;font-variant-numeric:tabular-nums}.table-wrap{overflow:auto}.fine{font-size:13px;color:var(--muted)}.hidden{display:none!important}.reader.expanded{height:auto;overflow:visible}.status{min-height:24px}.small{font-size:14px}
@media(max-width:1100px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}main{padding:24px 18px}}@media(max-width:640px){.grid,.grid.pair{grid-template-columns:1fr}.jump{margin-left:0}.reader{height:480px}.toolbar{gap:10px}.card header{min-height:0}}
@media print{body{background:white}main{padding:0}.toolbar,.card footer,.card header a{display:none}.grid,.grid.pair{display:block}.card{break-before:page;border:0}.reader{height:auto;overflow:visible}details{display:none}}
main{padding-top:28px}h1{font-size:clamp(30px,3vw,44px)}.toolbar{margin:20px 0;padding:12px 0}.language{margin-top:26px}.card header{padding:16px 22px;min-height:100px}
</style></head><body><main>
<div class="kicker">Lesevergleich / 29. September 2026</div>
<h1>Ein Buch. Vier Fassungen.<br>Zwei Sprachen.</h1>
<p class="lead">Blitzscaling, vier zusammenhängende Abschnitte mit 3.906 englischen Wörtern. Vergleiche das Original mit drei Kürzungsverfahren. Alle Kurzfassungen zielen auf 600 Wörter, mit einer Toleranz von 5 %. Darunter steht dieselbe Auswahl auf Deutsch.</p>
<div class="toolbar">
<label>Ansicht <select id="mode"><option value="all">Alle vier Fassungen</option><option value="pair">Zwei Fassungen vergleichen</option></select></label>
<label class="pair-control hidden">Links <select id="left"><option value="original">Original</option><option value="original_idea">Ursprungsidee</option><option value="current">Aktueller Ansatz</option><option value="hybrid">Hybrid</option></select></label>
<label class="pair-control hidden">Rechts <select id="right"><option value="original_idea">Ursprungsidee</option><option value="current">Aktueller Ansatz</option><option value="hybrid">Hybrid</option><option value="original">Original</option></select></label>
<button id="expand" aria-pressed="false">Texte vollständig ausklappen</button>
<nav class="jump" aria-label="Sprachen"><a href="#en">English</a><a href="#de">Deutsch</a></nav></div>
<p class="fine">Jede Lesespalte lässt sich separat scrollen. Im Paarvergleich stehen die gewählten Fassungen breiter nebeneinander. Die Übersetzungen wurden aus der jeweiligen englischen Fassung erstellt und anschließend zweisprachig vom LLM überarbeitet.</p>
<!--ROWS-->
<section style="margin-top:40px"><h2>Deine Lesebewertung</h2><p class="subtitle">Welche Fassung würdest du als Hörbuch weiterhören? Notizen werden nach Möglichkeit nur in diesem Browser gespeichert. Exportiere sie zur sicheren Aufbewahrung.</p><button id="export">Notizen herunterladen</button><p id="status" class="fine status" role="status"></p></section>
<details><summary>Wie die Fassungen entstanden sind</summary><ul><!--METHODS--></ul><p>Alle drei Verfahren erhalten abschließend denselben Auftrag zum Längenabgleich. Dieser zusätzliche Schritt kann die Texte verändern und gehört zum gemessenen Aufwand. Die anschließende gemeinsame Diagnose verändert die Texte nicht. Der aktuelle Ansatz enthält zusätzlich seine interne satzweise Prüfung.</p><p>Dies ist ein einzelner Vergleichslauf auf einem Buchausschnitt, kein allgemeines Ranking. Die Kurzfassungen teilen ein Längenziel, nicht zwingend dieselbe Inhaltsauswahl. Deutsche Wortzahlen müssen nicht den englischen entsprechen.</p><p>Das Original bleibt einschließlich seiner ursprünglichen Zeichensetzung unverändert. Für die deutschen Fassungen wurden natürliche deutsche Wendungen, konsistente Fachbegriffe und korrekte Zahlengrößen vorgegeben. Eine professionelle menschliche Übersetzung wurde nicht beauftragt.</p></details>
<details><summary>Tokenverbrauch und Modelllaufzeiten</summary><p class="small">Schreib- und Übersetzungsmodell: MODEL_NAME. Erfasst ist der gesamte Aufwand dieser Vergleichserstellung, einschließlich verworfener Längenversuche und erneuter Durchläufe. Das ist keine bereinigte Messung eines einzelnen Produktionslaufs. Zeiten sind die summierten Antwortzeiten der Modellaufrufe, keine garantierte Gesamtlaufzeit. Parallele Verarbeitung und Wiederaufnahme aus gespeicherten Antworten beeinflussen die Wartezeit. Ausgabetokens enthalten gegebenenfalls interne Reasoning-Tokens.</p><div class="table-wrap"><table><thead><tr><th>Fassung</th><th>Schritt</th><th>Eingabetokens</th><th>Ausgabetokens</th><th>Sekunden</th><th>Aufrufe</th></tr></thead><tbody><!--METRICS--></tbody></table></div><p class="small">Gemeinsame Embeddings: text-embedding-3-small, EMBED_TOKENS Eingabetokens, EMBED_SECONDS Sekunden. Für Ursprungsidee und Hybrid gemeinsam einmal berechnet. Bei separater Ausführung fällt dieser Aufwand bei jedem der beiden Verfahren an. Unterschiedliche Modelle haben unterschiedliche Tokenpreise; die Tabelle enthält keine Dollar-Schätzung.</p></details>
<details><summary>Automatische Hinweise erst nach dem Lesen ansehen</summary><p>Dies sind fehlbare LLM-Einschätzungen zum Quellenbezug und zur Auswahl, keine objektiven Qualitätsurteile. Sie wurden für alle drei fertigen englischen Texte mit demselben Prüfauftrag erzeugt.</p><!--DIAGNOSTICS--></details>
<p class="fine">Lokale Vergleichsseite. Keine externen Schriften, Dienste oder Datenübertragung beim Öffnen. <a href="comparison-report.json" download>Messdaten herunterladen</a></p>
</main><script>
const mode=document.getElementById('mode'),left=document.getElementById('left'),right=document.getElementById('right');
function update(){const pair=mode.value==='pair';document.querySelectorAll('.pair-control').forEach(e=>e.classList.toggle('hidden',!pair));document.querySelectorAll('.grid').forEach(g=>{g.classList.toggle('pair',pair);g.querySelectorAll('.card').forEach(c=>{c.classList.toggle('hidden',pair&&c.dataset.method!==left.value&&c.dataset.method!==right.value);c.style.order=pair?(c.dataset.method===left.value?'0':'1'):''})})}
[mode,left,right].forEach(e=>e.addEventListener('change',update));document.getElementById('expand').addEventListener('click',function(){const expanded=this.getAttribute('aria-pressed')!=='true';this.setAttribute('aria-pressed',expanded);this.textContent=expanded?'Kompakte Lesespalten':'Texte vollständig ausklappen';document.querySelectorAll('.reader').forEach(e=>e.classList.toggle('expanded',expanded))});
const notes={};document.querySelectorAll('[data-note]').forEach(e=>{try{e.value=localStorage.getItem('blitz-comparison-'+e.dataset.note)||''}catch{}notes[e.dataset.note]=e.value;e.addEventListener('input',()=>{notes[e.dataset.note]=e.value;try{localStorage.setItem('blitz-comparison-'+e.dataset.note,e.value)}catch{document.getElementById('status').textContent='Lokales Speichern nicht verfügbar. Bitte Notizen exportieren.'}})});
document.getElementById('export').addEventListener('click',()=>{const text=Object.entries(notes).map(([name,note])=>name+'\n'+note).join('\n\n');const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='lesevergleich-notizen.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('status').textContent='Notizen zum Herunterladen bereitgestellt.'});
</script></body></html>'''
