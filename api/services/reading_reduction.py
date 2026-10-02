"""Pure planning primitives for ordered, redundancy-aware reading editions.

Similarity proposes pairs. Only explicitly confirmed repeated source spans affect
budgets. No topic community, embedding score, or global ranking deletes content.
"""
import math
import heapq
import re
import numpy as np
from api.services.abridgement import audit_statements

VERSION = 'reading-reduction-1'


def word_count(text):
    return len(text.split())


def prepare(chapters, unit_limit=160, block_limit=480):
    units, blocks = [], []
    for chapter_index, chapter in enumerate(chapters):
        current = []
        def flush():
            if current:
                bid = len(blocks)
                blocks.append({'id': bid, 'chapter': chapter_index, 'title': chapter['title'],
                    'unit_ids': [u['id'] for u in current],
                    'text': '\n\n'.join(u['text'] for u in current)})
                for u in current:
                    u['block'] = bid
                current.clear()
        for paragraph in re.split(r'\n\s*\n', chapter['text']):
            paragraph = ' '.join(paragraph.split())
            if not paragraph:
                continue
            pieces, pending = [], ''
            for sentence in audit_statements(paragraph):
                if pending and word_count(pending + ' ' + sentence) > unit_limit:
                    pieces.append(pending)
                    pending = ''
                pending = (pending + ' ' + sentence).strip()
            if pending:
                pieces.append(pending)
            for piece in pieces:
                if current and sum(word_count(u['text']) for u in current) + word_count(piece) > block_limit:
                    flush()
                u = {'id': len(units), 'chapter': chapter_index, 'text': piece}
                units.append(u)
                current.append(u)
        flush()
    return units, blocks


def candidate_pairs(vectors, threshold=.55, neighbors=2, limit=32):
    v = np.asarray(vectors, dtype=float)
    if not len(v):
        return []
    v = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
    similarity = v @ v.T
    pairs = {}
    for i in range(len(v)):
        ordered = sorted((j for j in range(len(v)) if j != i), key=lambda j: (-similarity[i, j], j))
        for j in ordered[:neighbors]:
            if similarity[i, j] >= threshold:
                a, b = sorted((i, j))
                pairs[a, b] = float(similarity[i, j])
    return [{'a': a, 'b': b, 'similarity': score} for (a, b), score in
        sorted(pairs.items(), key=lambda p: (-p[1], p[0]))[:limit]]


def accepted_repetitions(decisions, pairs, units):
    allowed = {(p['a'], p['b']) for p in pairs}
    accepted, rejected = [], []
    for item in decisions:
        reason = None
        a, b = item.get('a'), item.get('b')
        if type(a) is not int or type(b) is not int or (a, b) not in allowed:
            raise ValueError('Unknown or reversed candidate pair')
        if item.get('relation') not in {'same_claim', 'partial_repeat', 'new_information', 'different_event', 'callback', 'uncertain'}:
            raise ValueError('Unknown repetition relation')
        if item['relation'] not in {'same_claim', 'partial_repeat'}:
            continue
        if item.get('confidence', 0) < .85 or item.get('safe_to_shorten_later') is not True:
            reason = 'uncertain_or_narrative_function'
        qa = ' '.join(item.get('earlier_span', '').split())
        qb = ' '.join(item.get('later_span', '').split())
        if not qa or not qb or qa not in units[a]['text'] or qb not in units[b]['text']:
            reason = 'source_span_not_exact'
        if word_count(qa) < 4 or word_count(qb) < 4:
            reason = 'span_too_short'
        if reason:
            rejected.append({**item, 'rejected_reason': reason})
        else:
            accepted.append({**item, 'earlier_span': qa, 'later_span': qb})
    return accepted, rejected


def allocate(blocks, units, repetitions, ratio):
    if not 0 < ratio <= 1:
        raise ValueError('Ratio must be in (0, 1]')
    lengths = [word_count(b['text']) for b in blocks]
    if not lengths:
        return []
    target = max(len(blocks), round(sum(lengths) * ratio))
    # Overlapping repeated spans count only once. Never zero an entire block.
    covered = {}
    for r in repetitions:
        uid = r['b']
        source = units[uid]['text']
        start = source.index(r['later_span'])
        positions = covered.setdefault(uid, set())
        positions.update(range(start, start + len(r['later_span'])))
    repeated = [0.] * len(blocks)
    for uid, positions in covered.items():
        u = units[uid]
        repeated[u['block']] += word_count(u['text']) * len(positions) / len(u['text'])
    weights = [max(n * .25, n - .7 * r) for n, r in zip(lengths, repeated)]
    low = [min(n, max(1, math.floor(n * ratio * .5))) for n in lengths]
    result = low[:]
    heap = [(-weights[i] / (result[i] + 1), i) for i, n in enumerate(lengths) if result[i] < n]
    heapq.heapify(heap)
    remaining = target - sum(result)
    while remaining > 0 and heap:
        _, i = heapq.heappop(heap)
        result[i] += 1
        remaining -= 1
        if result[i] < lengths[i]:
            heapq.heappush(heap, (-weights[i] / (result[i] + 1), i))
    return result


def validate_sections(value, expected_ids):
    sections = value.get('sections')
    if not isinstance(sections, list) or [s.get('id') for s in sections] != expected_ids:
        raise ValueError('Every requested block ID must occur exactly once in source order')
    if any(not isinstance(s.get('text'), str) or not s['text'].strip() for s in sections):
        raise ValueError('Empty reading block')
    for s in sections:
        s['text'] = s['text'].replace('\u2014', '-').replace('\u2013', '-')
    return sections
