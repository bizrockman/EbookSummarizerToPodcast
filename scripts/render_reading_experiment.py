"""Offline comparison UI for the controlled reduction experiment."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def card_usage(rows, method, ratio, ratios, events):
    """Attribute actual calls once; distribute shared analysis over planned levels."""
    owner = f'{method}-{round(ratio * 100)}'
    own = [r for r in rows if r['owner'] == owner]
    shared = [r for r in rows if r['owner'] == 'shared'] if method == 'redundancy' else []
    index, count = ratios.index(ratio), len(ratios)
    fields = ['input', 'output', 'cached_input', 'reasoning']
    # Integer shares reconcile exactly with the measured total across all levels.
    share = {k: sum(r[k] // count + int(index < r[k] % count) for r in shared) for k in fields}
    total = {k: sum(r[k] for r in own) + share[k] for k in fields}
    return {'total': total, 'own': own, 'shared': shared, 'share': share,
        'shared_levels': count, 'unknown_usage': sum(r['unknown_usage'] for r in own + shared),
        'local_cache_hits': sum(e['kind'] == 'local_cache_hit' and e['owner'] == owner for e in events)}


def render(root):
    root = Path(root)
    books = {}
    downloads = []
    metadata = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (folder / 'manifest.json').exists():
            continue
        m = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        original = json.loads((folder / 'original.json').read_text(encoding='utf-8'))
        editions = {}
        for method in m['methods']:
            for ratio in m['ratios']:
                key = f'{method}-{round(ratio*100)}'
                path = folder / (key + '.json')
                if not path.exists():
                    continue
                value = json.loads(path.read_text(encoding='utf-8'))
                editions[key] = {k: value[k] for k in ['en', 'de', 'target_words', 'actual_words',
                    'within_length_tolerance', 'block_words', 'block_budgets', 'review', 'quality_status',
                    'accepted_repetitions']}
        for key, value in {'original': original, **editions}.items():
            for lang in ['en', 'de']:
                path = folder / f'{key}-{lang}.txt'
                path.write_text('\n\n'.join(s['text'] for s in value[lang]), encoding='utf-8')
                downloads.append(path)
        usage = json.loads((folder / 'usage.json').read_text(encoding='utf-8')) if (folder / 'usage.json').exists() else []
        analysis = json.loads((folder / 'analysis.json').read_text(encoding='utf-8')) if (folder / 'analysis.json').exists() else None
        events = []
        if (folder / 'events.jsonl').exists():
            for line in (folder / 'events.jsonl').read_text(encoding='utf-8').splitlines():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        records = []
        for path in (folder / 'calls').glob('*.json'):
            record = json.loads(path.read_text(encoding='utf-8'))
            records.append({k: record[k] for k in ['record_id', 'key', 'owner', 'phase',
                'requested_model', 'model', 'started_at', 'attempt', 'status', 'seconds',
                'response_id', 'request_id', 'finish_reason', 'usage', 'error_type'] if k in record})
        records.sort(key=lambda r: (r['started_at'], r['record_id']))
        journal = folder / 'api-usage.json'
        journal.write_text(json.dumps({'calls': records, 'reuse_events': events},
            ensure_ascii=False, indent=2), encoding='utf-8')
        metadata.extend([folder / 'manifest.json', journal])
        books[folder.name] = {'manifest': m, 'original': original, 'editions': editions,
            'usage': usage, 'analysis': analysis, 'local_cache_hits': sum(e['kind']=='local_cache_hit' for e in events),
            'card_usage': {f'{method}-{round(ratio*100)}': card_usage(usage, method, ratio, m['ratios'], events)
                for method in m['methods'] for ratio in m['ratios']}}
    data = json.dumps(books, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    (root / 'index.html').write_text(TEMPLATE.replace('/*DATA*/{}', data), encoding='utf-8')
    (root / 'report.json').write_text(json.dumps(books, ensure_ascii=False, indent=2), encoding='utf-8')
    with ZipFile(root / 'lesevergleich.zip', 'w', ZIP_DEFLATED) as z:
        for p in [root / 'index.html', root / 'report.json', *downloads, *metadata]:
            z.write(p, p.relative_to(root).as_posix())


TEMPLATE = r'''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lesefassungen im Vergleich | Zwei Bücher, drei Lesestufen</title><style>
:root{color-scheme:light;--bg:#f0f3ec;--paper:#fffef9;--ink:#203b35;--muted:#60736d;--line:#d4ddd5}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}main{max-width:1800px;margin:auto;padding:28px 30px 70px}h1{font:500 clamp(30px,3vw,46px)/1.15 Georgia,serif;max-width:1000px;margin:12px 0 20px}h2{font:400 30px Georgia,serif;margin:30px 0 12px}h3{font-size:16px;margin:4px 0}.kicker{font-size:12px;text-transform:uppercase;letter-spacing:.1em;font-weight:700}.lead{max-width:1000px;color:var(--muted)}a{color:inherit;text-underline-offset:4px}.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;border-block:1px solid var(--line);padding:15px 0;margin:24px 0}.toolbar label{display:flex;gap:8px;align-items:center}select,button{font:inherit;background:var(--paper);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:8px;cursor:pointer}select#book{max-width:340px}nav{display:flex;gap:18px;margin-left:auto}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;align-items:start}.grid.pair{grid-template-columns:repeat(2,minmax(0,1fr))}.card{background:var(--paper);border:1px solid var(--line);border-radius:10px;overflow:hidden}.card header{padding:18px 20px;border-bottom:1px solid var(--line);min-height:148px}.reader{height:600px;overflow:auto;padding:6px 22px 20px;font:17px/1.75 Georgia,serif;overflow-wrap:anywhere;scrollbar-gutter:stable}.reader.expanded{height:auto}.reader p{white-space:pre-line}.card footer{padding:14px 20px;border-top:1px solid var(--line);font-size:13px}textarea{display:block;width:100%;min-height:72px;border:1px solid var(--line);border-radius:5px;background:transparent;padding:8px;font:14px system-ui}.small{font-size:13px;color:var(--muted)}.flag{color:#805015}.hidden{display:none!important}details{margin:22px 0;padding:18px 22px;background:var(--paper);border:1px solid var(--line);border-radius:10px}summary{font-weight:600;cursor:pointer}.table{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:9px;text-align:right;border-bottom:1px solid var(--line)}td:nth-child(-n+3),th:nth-child(-n+3){text-align:left}li{margin-bottom:10px}#en,#de{scroll-margin-top:20px}button:hover{background:#e0e9df}
@media(max-width:1100px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:650px){main{padding:20px 15px}.grid,.grid.pair{grid-template-columns:1fr}.toolbar label{flex-wrap:wrap}select#book{max-width:90vw}nav{margin-left:0}.reader{height:450px}}
@media print{.toolbar,textarea,footer,details{display:none}.grid,.grid.pair{display:block}.reader{height:auto}.card{break-before:page}}
.token-panel{margin:10px 0 12px}.token-caption{font-size:11px;color:var(--muted)}.token-totals{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:5px 0;font-variant-numeric:tabular-nums}.token-totals div{display:flex;flex-direction:column}.token-totals span{font-size:11px;color:var(--muted)}.token-totals strong{font-size:19px;font-weight:600}.card details.card-usage{margin:7px 0 0;padding:0;border:0;border-radius:0;background:transparent;font-size:12px}.card-usage summary{font-weight:500}.card-usage p{font-size:12px;margin:9px 0}.card-usage td,.card-usage th{padding:6px 4px;font-size:11px}.card-usage td:not(:first-child),.card-usage th:not(:first-child){text-align:right}.card-usage td:first-child{overflow-wrap:anywhere}.card-usage .table{margin-top:8px}
</style></head><body><main><div class="kicker">Neuer Vergleichslauf / Blockweise Kürzung</div><h1>Weniger Wiederholung.<br>Wie viel Buch bleibt?</h1>
<p class="lead">Zwei bereits bekannte Buchausschnitte, drei Verfahren und drei Restlängen. Englisch steht oben, Deutsch darunter. Die bisherigen Versuche bleiben als Referenz erhalten. Dieser Lauf untersucht Ausschnitte, keine vollständigen Bücher; ein Roman ist noch nicht enthalten.</p>
<div class="toolbar"><label>Buch <select id="book"></select></label><label>Restlänge <select id="ratio"><option value="60">60 %</option><option value="40">40 %</option><option value="20">20 %</option></select></label><label>Ansicht <select id="mode"><option value="all">Alle vier Fassungen</option><option value="pair">Zwei vergleichen</option></select></label><label class="pair-control hidden">Links <select id="left"></select></label><label class="pair-control hidden">Rechts <select id="right"></select></label><button id="expand" aria-pressed="false">Texte ausklappen</button><nav><a href="#en">English</a><a href="#de">Deutsch</a></nav></div>
<p id="description" class="small"></p><section id="en"><h2>English</h2><div class="grid"></div></section><section id="de"><h2>Deutsch</h2><div class="grid"></div></section>
<h2>Deine Lesebewertung</h2><p>Was liest sich wie ein gekürztes Buch? Wo fehlen Zusammenhänge oder anschauliche Beispiele? Notizen werden je Buch, Stufe, Verfahren und Sprache lokal gespeichert.</p><button id="export">Notizen herunterladen</button> <a href="lesevergleich.zip" download>Alle Texte und Vorschau als ZIP</a><p id="status" class="small" role="status"></p>
<details><summary>Was die Verfahren unterscheidet</summary><ul><li><strong>Blockweise:</strong> Jeder ursprüngliche Leseblock bekommt ein proportionales Budget und bleibt vertreten. Das LLM kürzt innerhalb der Blöcke.</li><li><strong>Mit Redundanzprüfung:</strong> Derselbe Ablauf, zusätzlich Embedding-Suche und einmalige Prüfung ähnlicher Stellen. Nur bestätigte wiederholte Aussagen verringern das Budget am späteren Ort. Eigenständige Ereignisse, Ergänzungen und Rückbezüge werden nicht allein wegen Ähnlichkeit entfernt.</li><li><strong>Direktes LLM:</strong> Der vollständige Ausschnitt wird mit einem gemeinsamen Längenziel übergeben. Die Inhaltsauswahl liegt beim Modell.</li></ul><p>Alle Varianten verwenden dasselbe konfigurierte Schreibmodell, höchstens zwei Längenreparaturen und dieselbe Abschlussdiagnose mit höchstens einer inhaltlichen Korrekturrunde. Danach gibt es keine freie globale Umschreibung. Verbleibende Hinweise und Längenabweichungen werden angezeigt. Eine LLM-Diagnose garantiert keine Fehlerfreiheit.</p><p>Die Budgettoleranz beträgt pro Block 15 %, die angezeigte Gesamttoleranz 10 %. 60 % bedeutet 60 % des ursprünglichen Wortumfangs, nicht 60 % weniger. Jede Stufe arbeitet aus dem Original. Übergänge werden beim blockweisen Schreiben berücksichtigt; eine separate satzweise Prüfung und ein eigenes kleines Prüfmodell sind in diesem ersten Versuch nicht implementiert.</p><p>Die beiden Originalübersetzungen wurden aus dem vorigen Vergleich übernommen. Neue Übersetzungen entstehen aus der jeweiligen englischen Fassung mit anschließender zweisprachiger Überarbeitung. Es handelt sich nicht um eine menschliche Fachübersetzung.</p></details>
<details><summary>Erkannte Wiederholungen und Entscheidungen</summary><div id="analysis"></div></details>
<details><summary>Tokenverbrauch und Kostenbasis</summary><p class="small">Tatsächliche API-Aufrufe einschließlich Wiederholungen und Fehlversuchen. Gemeinsame Analyse fällt einmal je Buchausschnitt an und wird nicht jedem Verfahren erneut zugerechnet. Sie wird nur für die Variante mit Redundanzprüfung benötigt und kann über deren drei Stufen verteilt werden. Für eine einzelne Stufe wäre der volle Analyseaufwand relevant.</p><p id="usage-summary" class="small"></p><div class="table"><table><thead><tr><th>Variante</th><th>Schritt</th><th>Modell</th><th>Aufrufe</th><th>Input</th><th>davon API-Cache</th><th>Output</th><th>davon Reasoning</th><th>Sekunden</th><th>Fehler / unbekannter Verbrauch</th></tr></thead><tbody id="usage"></tbody></table></div><p class="small">Cache-Tokens sind Teil des Inputs; Reasoning-Tokens sind Teil des Outputs, nicht zusätzlich zu addieren. Lokal wiederverwendete Antworten erzeugen keinen neuen API-Verbrauch. Bei identischen Anfragen zwischen Varianten wird der tatsächliche Verbrauch dem ersten Aufrufer zugeordnet; die Tabelle schätzt daher keine unabhängig gestarteten Einzelvarianten. API-Timeouts können berechnet worden sein, obwohl keine Verbrauchsdaten vorliegen; diese sind ausdrücklich unbekannt. Zeiten sind summierte Antwortzeiten, keine gesamte Wartezeit. Preise werden noch nicht geschätzt; Modellkennung und rohe API-Verbrauchsdaten bleiben für spätere Kostenberechnungen erhalten. <a href="https://developers.openai.com/api/reference/resources/chat" target="_blank" rel="noopener">OpenAI-Verbrauchsfelder</a>.</p><p class="small"><a id="raw-usage" download>API-Verbrauch je Aufruf und lokale Wiederverwendungen</a> · <a id="manifest" download>Quelle und Parameter</a></p></details>
<details><summary>Automatische Hinweise erst nach dem Lesen ansehen</summary><div id="reviews"></div></details>
<p class="small"><a href="report.json" download>Vergleich und Messdaten herunterladen</a> · <a href="../comparison-20260929/">Bisheriger Blitzscaling-Vergleich</a> · <a href="../hearst-verification/">Bisheriger Hearst-Vergleich</a></p>
</main><script>
const data=/*DATA*/{};
const names={original:'Original',blocks:'Blockweise',redundancy:'Mit Redundanzprüfung',direct:'Direktes LLM'};
const phases={embeddings:'Embeddings',repetition_analysis:'Redundanzanalyse',writing:'Schreiben',length_repair:'Längenreparatur',verification:'Prüfung',quality_repair:'Inhaltliche Korrektur',translation:'Übersetzung',translation_review:'Sprachlektorat'};
const $=id=>document.getElementById(id);let expanded=false;const memory={};
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
for(const [key,b] of Object.entries(data)){const o=el('option',b.manifest.title);o.value=key;$('book').append(o)}
for(const id of ['left','right'])for(const [key,name] of Object.entries(names)){const o=el('option',name);o.value=key;$(id).append(o)}$('left').value='blocks';$('right').value='redundancy';
const params=new URLSearchParams(location.search);
if(Object.keys(data).includes(params.get('book')))$('book').value=params.get('book');
if(['60','40','20'].includes(params.get('ratio')))$('ratio').value=params.get('ratio');
if(['all','pair'].includes(params.get('mode')))$('mode').value=params.get('mode');
for(const id of ['left','right'])if(Object.keys(names).includes(params.get(id)))$(id).value=params.get(id);
function noteKey(method,lang){return 'reading-v1:'+[$('book').value,$('ratio').value,method,lang].join(':')}
function tokenPanel(b,method,ratio){const panel=el('div',undefined,'token-panel');panel.append(el('div','API-Tokens gesamt · Lauf EN + DE','token-caption'));
const info=method==='original'?null:b.card_usage[method+'-'+ratio],totals=el('div',undefined,'token-totals');
for(const [key,label] of [['input','Input'],['output','Output']]){const d=el('div');d.append(el('span',label),el('strong',(info?.total[key]||0).toLocaleString('de-DE')));totals.append(d)}panel.append(totals);
if(info?.unknown_usage)panel.append(el('div','Zusätzlicher Verbrauch unbekannt','small flag'));
const detail=el('details',undefined,'card-usage');detail.append(el('summary','Token-Details'));
if(method==='original'){detail.append(el('p','Original und vorhandene Übersetzung übernommen: keine neuen API-Aufrufe. Die historischen Übersetzungskosten sind hier nicht erfasst.'));panel.append(detail);return panel}
detail.append(el('p','Die Summe umfasst Schreiben, Reparaturen, Prüfungen, Übersetzung und Sprachlektorat. Englisch und Deutsch zeigen denselben Gesamtlauf; die beiden Kacheln nicht addieren.'));
const container=el('div',undefined,'table'),table=el('table'),head=el('thead'),heading=el('tr');for(const label of ['Schritt / Aufrufe','Input','Output'])heading.append(el('th',label));head.append(heading);table.append(head);const body=el('tbody');
for(const r of info.own){const tr=el('tr');for(const c of [(phases[r.phase]||r.phase)+' ('+r.calls+')',r.input.toLocaleString('de-DE'),r.output.toLocaleString('de-DE')])tr.append(el('td',c));body.append(tr)}
if(info.shared.length){const tr=el('tr');for(const c of ['Analyseanteil 1/'+info.shared_levels,info.share.input.toLocaleString('de-DE'),info.share.output.toLocaleString('de-DE')])tr.append(el('td',c));body.append(tr)}table.append(body);container.append(table);detail.append(container);
if(info.shared.length){const full=info.shared.reduce((a,r)=>({input:a.input+r.input,output:a.output+r.output,calls:a.calls+r.calls}),{input:0,output:0,calls:0});detail.append(el('p',`Embeddings und Redundanzanalyse wurden einmal je Buch berechnet: ${full.input.toLocaleString('de-DE')} Input / ${full.output.toLocaleString('de-DE')} Output bei ${full.calls} Aufrufen. Hier ist 1/${info.shared_levels} für die drei geplanten Stufen enthalten. Für einen einzelnen Lauf wäre die volle Analyse relevant.`))}
detail.append(el('p',`In der Summe enthalten: ${info.total.cached_input.toLocaleString('de-DE')} API-Cache-Tokens im Input und ${info.total.reasoning.toLocaleString('de-DE')} Reasoning-Tokens im Output. Diese Anteile nicht zusätzlich addieren. ${info.local_cache_hits} lokale Wiederverwendungen ohne neue API-Kosten.`));
const models=[...new Set([...info.own,...info.shared].map(r=>r.model))];detail.append(el('p','Modelle: '+models.join(', ')));panel.append(detail);return panel}
function update(){const key=$('book').value,b=data[key],ratio=$('ratio').value,pair=$('mode').value==='pair';if(!b)return;
try{const url=new URL(location.href);for(const id of ['book','ratio','mode','left','right'])url.searchParams.set(id,$(id).value);history.replaceState(null,'',url)}catch{}
$('raw-usage').href=key+'/api-usage.json';$('manifest').href=key+'/manifest.json';
document.querySelectorAll('.pair-control').forEach(e=>e.classList.toggle('hidden',!pair));
$('description').textContent=`${b.manifest.words.toLocaleString('de-DE')} Wörter im Original. Ziel: ${Math.round(b.manifest.words*Number(ratio)/100).toLocaleString('de-DE')} englische Wörter. Modell: ${b.manifest.model}. ${Object.keys(b.editions).length} von 9 Fassungen fertig.`;
for(const lang of ['en','de']){const grid=document.querySelector('#'+lang+' .grid');grid.replaceChildren();grid.classList.toggle('pair',pair);
for(const method of Object.keys(names)){if(pair&&method!==$('left').value&&method!==$('right').value)continue;const v=method==='original'?b.original:b.editions[method+'-'+ratio],card=el('article',undefined,'card');card.dataset.method=method;card.style.order=pair?(method===$('left').value?'0':'1'):'';
const header=el('header');header.append(el('div',names[method],'kicker'));const reader=el('div',undefined,'reader'+(expanded?' expanded':''));reader.lang=lang;reader.tabIndex=0;reader.setAttribute('aria-label',names[method]+', '+lang);
if(v){const words=v[lang].reduce((n,s)=>n+s.text.trim().split(/\s+/).length,0);header.append(el('h3',words.toLocaleString('de-DE')+' Wörter'),tokenPanel(b,method,ratio));if(method!=='original'){header.append(el('div','Englischer Umfang: '+(100*v.actual_words/b.manifest.words).toLocaleString('de-DE',{maximumFractionDigits:1})+' % des Originals','small'));header.append(el('div',v.within_length_tolerance?'Im Zielbereich':'Längenziel verfehlt','small'+(v.within_length_tolerance?'':' flag')));header.append(el('div',v.review.issues.length?'Prüfhinweise vorhanden':'Keine Fehler von der Prüfung gemeldet','small'))}const a=el('a','Text herunterladen','small');a.href=key+'/'+(method==='original'?'original':method+'-'+ratio)+'-'+lang+'.txt';a.download='';header.append(a);for(const s of v[lang])for(const p of s.text.split(/\n\s*\n/))if(p.trim())reader.append(el('p',p));}
else{header.append(el('h3','Noch nicht fertig'));reader.append(el('p','Diese Fassung wurde noch nicht abgeschlossen. Bereits fertige Fassungen bleiben verfügbar.'))}
const footer=el('footer'),label=el('label','Dein Eindruck'),ta=el('textarea');const nk=noteKey(method,lang);try{ta.value=memory[nk]??localStorage.getItem(nk)??''}catch{ta.value=memory[nk]||''}ta.addEventListener('input',()=>{memory[nk]=ta.value;try{localStorage.setItem(nk,ta.value)}catch{$('status').textContent='Lokales Speichern nicht möglich. Bitte Notizen exportieren.'}});label.append(ta);footer.append(label);card.append(header,reader,footer);grid.append(card)}}
$('analysis').replaceChildren();if(b.analysis){$('analysis').append(el('p',`${b.analysis.candidates.length} ähnliche Paare geprüft; ${b.analysis.accepted.length} Wiederholungen für die Budgetplanung bestätigt; ${b.analysis.rejected.length} vorgeschlagene Zusammenführungen technisch verworfen.`));for(const r of b.analysis.decisions){const d=el('details'),ok=b.analysis.accepted.some(a=>a.a===r.a&&a.b===r.b);d.append(el('summary',`Passagen ${r.a+1} / ${r.b+1}: ${r.relation}${ok?' - berücksichtigt':''}`),el('p',r.reason));if(r.earlier_span)d.append(el('p','Früher: '+r.earlier_span));if(r.later_span)d.append(el('p','Später: '+r.later_span));$('analysis').append(d)}}else $('analysis').append(el('p','Analyse noch nicht abgeschlossen.'));
$('usage').replaceChildren();for(const r of b.usage.filter(r=>r.owner==='shared'||r.owner.endsWith('-'+ratio))){const tr=el('tr');const cache=r.unknown_cache_details?'teilweise unbekannt':r.cached_input.toLocaleString('de-DE'),reason=r.unknown_reasoning_details?'teilweise unbekannt':r.reasoning.toLocaleString('de-DE');for(const c of [r.owner,phases[r.phase]||r.phase,r.model,r.calls,r.input.toLocaleString('de-DE'),cache,r.output.toLocaleString('de-DE'),reason,r.seconds.toFixed(1),r.failed+' / '+r.unknown_usage])tr.append(el('td',String(c)));$('usage').append(tr)}
const total=b.usage.reduce((a,r)=>({input:a.input+r.input,output:a.output+r.output,unknown:a.unknown+r.unknown_usage}),{input:0,output:0,unknown:0});$('usage-summary').textContent=`Tabelle: ausgewählte Stufe plus gemeinsame Analyse. Bisher insgesamt für dieses Buch über alle Stufen: ${total.input.toLocaleString('de-DE')} Input- und ${total.output.toLocaleString('de-DE')} Output-Tokens; ${total.unknown} Versuche mit unbekanntem Verbrauch. ${b.local_cache_hits} lokale Wiederverwendungen. Historische Originalübersetzung nicht enthalten.`;
$('reviews').replaceChildren();for(const method of ['blocks','redundancy','direct']){const v=b.editions[method+'-'+ratio];if(!v)continue;const d=el('details');d.append(el('summary',names[method]),el('p',v.review.reading_notes||''));for(const i of v.review.issues)d.append(el('p',`Block ${i.section_id+1}: ${i.explanation}`));if(!v.review.issues.length)d.append(el('p','Keine konkreten Fehler gemeldet. Das ist keine Garantie.'));const lengths=el('details');lengths.append(el('summary','Wortbudget und tatsächliche Länge je Block'));for(const [id,target] of Object.entries(v.block_budgets)){const actual=v.block_words[id],ok=actual>=Math.max(1,target*.85)&&actual<=target*1.15;lengths.append(el('p',`Block ${Number(id)+1}: ${actual} Wörter bei ${target} Zielwörtern${ok?'':' - außerhalb der Blocktoleranz'}`,'small'+(ok?'':' flag')))}d.append(lengths);$('reviews').append(d)}}
for(const id of ['book','ratio','mode','left','right'])$(id).addEventListener('change',update);
$('expand').addEventListener('click',()=>{expanded=!expanded;$('expand').setAttribute('aria-pressed',String(expanded));$('expand').textContent=expanded?'Kompakte Lesespalten':'Texte ausklappen';update()});
$('export').addEventListener('click',()=>{const notes={...memory};try{for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k.startsWith('reading-v1:'))notes[k]=localStorage.getItem(k)}}catch{}const u=URL.createObjectURL(new Blob([JSON.stringify(notes,null,2)],{type:'application/json;charset=utf-8'}));const a=el('a');a.href=u;a.download='lesebewertung.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);$('status').textContent='Notizen zum Download bereitgestellt.'});update();
</script></body></html>'''
