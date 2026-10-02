"""Final idiomatic German editing for the authorized local comparison."""
import json
from concurrent.futures import ThreadPoolExecutor
from compare_approaches import OUT, BOOK_INFO, GLOSSARY, Calls, save


def refine(name):
    path = OUT / (name + '.json')
    if not path.exists():
        return
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('idiomatic_revision') or value.get('status') == 'failed':
        return
    calls = Calls(name + '-translation')
    task = (
        'Perform the final German publishing edit of this translation, using the English as '
        'the authority for meaning. Return {"sections": [{"title": string, "text": string}], '
        '"notes": string}. Return EVERY section in order, COMPLETE and unabridged. '
        'The German must sound originally written by a skilled German nonfiction author. '
        'Correct literal English collocations and false friends. For example, a business prize '
        'is a Gewinnchance, not a Preis to pay; markets up for grabs are markets whose leadership '
        'is still open, not markets zur Disposition; win a market means establishing leadership, '
        'not winning cloud computing; organizational debt means accumulated organizational '
        'problems, not financial borrowing; execute means implement or work, not ausfuehren '
        'without an object. These are translation guidance only, not new book claims. '
        'Use normal umlauts, never fruehe in place of frühe. Replace clumsy constructions like '
        'klassisches Wachstum eines wachsenden Unternehmens with klassisches Scale-up-Wachstum. '
        'Do not mechanically replace words where their literal meaning is actually intended. '
        'Preserve deliberate author metaphors, humor, all figures, examples, limitations and '
        'attributions. Use natural German equivalents for idioms. Maintain consistent address '
        'and terminology within each text. Do not add explanations, fix omissions in the English '
        'abridgement, or alter its selection of ideas. No editorial preface. Plain hyphens only.')
    if BOOK_INFO:
        task = ('Perform the final German publishing edit of this historical-biography translation, '
                'using the English as the authority for meaning. Return {"sections": '
                '[{"title": string, "text": string}], "notes": string}. Return EVERY section '
                'in order, COMPLETE and unabridged. Make collocations, idioms and sentence rhythm '
                'natural German. Preserve all dates, examples, figures, qualifications, quotations '
                'and attribution. Distinguish historical speakers from the narrator, maintaining '
                'the force and register of each voice. Do not add background explanations or '
                'fix omissions in the English abridgement. Do not alter the selection of ideas. '
                'Use proper umlauts and plain hyphens. ' + GLOSSARY)
    result = calls.ask(task, {'english': value['en'], 'german': value['de']})
    if len(result['sections']) != len(value['en']):
        raise ValueError('Section count changed')
    for before, after in zip(value['de'], result['sections']):
        if len(after['text'].split()) < len(before['text'].split()) * .8:
            raise ValueError('Translation unexpectedly shortened')
        after['text'] = after['text'].replace('\u2014', '-').replace('\u2013', '-')
    value['de'] = result['sections']
    value['idiomatic_revision'] = True
    value['translation_notes'] += '\nFinales Sprachlektorat: ' + result.get('notes', '')
    value['translation'] = calls.metrics()
    save(path, value)
    print(name, 'German publishing edit complete', flush=True)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(refine, ['original', 'original_idea', 'current', 'hybrid']))
