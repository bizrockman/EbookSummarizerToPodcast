"""Package the completed eight-text comparison; no external requests."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from compare_approaches import OUT, BOOK_TITLE, save
from api.config.settings import settings
from render_comparison import render, NAMES


def main():
    corrections = {
        'wenn der potenzielle Preis groß und der Wettbewerb hart ist':
            'wenn viel zu gewinnen ist und der Wettbewerb hart ist',
        'Wenn der zu gewinnende Preis groß genug ist und der Wettbewerb darum intensiv genug':
            'Wenn genug zu gewinnen ist und der Wettbewerb darum intensiv genug ist',
        'Wenn der Preis groß ist und der Wettbewerb hart':
            'Wenn viel zu gewinnen ist und der Wettbewerb hart ist',
        'die strategisch hohe Position in seinem Ökosystem einnimmt':
            'eine strategisch überlegene Position in seinem Ökosystem einnimmt',
        'mit über 100 Prozent Einsatz zu liefern': 'mit mehr als 100 Prozent Einsatz zu arbeiten',
        'hart genug zu drücken, um das Zeitfenster zu nutzen':
            'entschlossen genug voranzugehen, um das Zeitfenster zu nutzen',
        'fruehe Skalierung': 'frühe Skalierung',
        'die Anwendung von Hurdle Rates': 'die Anwendung von Mindestrenditen',
        'Ausbruchschancen': 'Chancen auf einen Durchbruch',
        "die Society mit großem 'S'": 'die feine Gesellschaft',
        'die Gesellschaft mit großem G': 'die feine Gesellschaft',
        'wurden seine Eltern zunehmend unvereinbar': 'kamen seine Eltern immer weniger miteinander aus',
        'wurden sein Vater und seine Mutter "unvereinbar': 'kamen sein Vater und seine Mutter "nicht mehr miteinander aus',
    }
    for name in NAMES:
        path = OUT / (name + '.json')
        value = json.loads(path.read_text(encoding='utf-8'))
        if value.get('status') == 'failed':
            continue
        assert value.get('idiomatic_revision'), name + ': publishing edit missing'
        if name != 'original':
            assert 570 <= sum(len(s['text'].split()) for s in value['en']) <= 630
        edits = []
        for section in value['de']:
            for before, after in corrections.items():
                if before in section['text']:
                    edits.append({'before': before, 'after': after})
                    section['text'] = section['text'].replace(before, after)
            section['text'] = section['text'].replace('\u2014', '-').replace('\u2013', '-')
            section['title'] = section['title'].replace('\u2014', '-').replace('\u2013', '-')
        value.setdefault('copyedits', []).extend(edits)
        save(path, value)
    render(OUT, settings.openai_default_model)
    instructions = (BOOK_TITLE + ': lokaler Lesevergleich\n\n'
                    'index.html im Browser öffnen. Alle Texte sind in der Seite enthalten.\n'
                    'Die verfügbaren TXT-Dateien können separat gelesen werden.\n'
                    'Fehlgeschlagene Verfahren sind auf der Seite ausdrücklich gekennzeichnet.\n'
                    'Notizen bei Bedarf herunterladen. Die lokale Browserspeicherung hängt vom Browser ab.\n'
                    'Messdaten: comparison-report.json.\n'
                    'Die Seite benötigt weder einen Server noch Internetzugang.\n')
    (OUT / 'LIESMICH.txt').write_text(instructions, encoding='utf-8')
    with ZipFile(OUT / 'lesevergleich.zip', 'w', ZIP_DEFLATED) as package:
        for path in [OUT / 'index.html', OUT / 'comparison-report.json', *OUT.glob('*-en.txt'), *OUT.glob('*-de.txt'), OUT / 'LIESMICH.txt']:
            package.write(path, path.name)
        if (OUT / 'selection-info.json').exists():
            package.write(OUT / 'selection-info.json', 'selection-info.json')
        if (OUT / 'current-final-audit.json').exists():
            package.write(OUT / 'current-final-audit.json', 'current-final-audit.json')
    for name in NAMES:
        v = json.loads((OUT / (name + '.json')).read_text(encoding='utf-8'))
        if v.get('status') == 'failed':
            print(name, 'failed:', v['failure'])
            continue
        print(name, {lang: sum(len(s['text'].split()) for s in v[lang]) for lang in ['en', 'de']})


if __name__ == '__main__':
    main()
