"""Resumable API calls with an append-only record for every actual attempt."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4
from openai import OpenAI


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


class Meter:
    def __init__(self, folder, api_key, model, client=None):
        self.folder, self.model = Path(folder), model
        # Disable implicit SDK retries: every API attempt must have its own record.
        self.client = client or OpenAI(api_key=api_key, timeout=240, max_retries=0)
        self.lock = Lock()
        self.key_locks = {}

    def call(self, owner, phase, payload, system=None, embedding=False):
        requested_model = 'text-embedding-3-small' if embedding else self.model
        key = hashlib.sha256(json.dumps([requested_model, system, payload, embedding,
            None if embedding else {'reasoning_effort': 'low', 'max_completion_tokens': 20000}],
            ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        with self.lock:
            key_lock = self.key_locks.setdefault(key, Lock())
        with key_lock:
            return self._call(owner, phase, payload, system, embedding, requested_model, key)

    def _call(self, owner, phase, payload, system, embedding, requested_model, key):
        cache = self.folder / 'cache' / (key + '.json')
        if cache.exists():
            record = json.loads(cache.read_text(encoding='utf-8'))
            self.event({'kind': 'local_cache_hit', 'owner': owner, 'phase': phase, 'key': key,
                        'record_id': record['record_id']})
            return record['value']
        for attempt in range(2):
            rid = uuid4().hex
            record = {'record_id': rid, 'key': key, 'owner': owner, 'phase': phase,
                      'requested_model': requested_model, 'started_at': datetime.now(timezone.utc).isoformat(),
                      'attempt': attempt + 1, 'status': 'started', 'usage': None}
            path = self.folder / 'calls' / (rid + '.json')
            dump(path, record)
            started = time.monotonic()
            try:
                if embedding:
                    response = self.client.embeddings.create(model=requested_model, input=payload)
                else:
                    response = self.client.chat.completions.create(model=requested_model,
                        messages=[{'role': 'system', 'content': system},
                                  {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}],
                        response_format={'type': 'json_object'}, max_completion_tokens=20000,
                        **({'reasoning_effort': 'low'} if requested_model.startswith(('gpt-5', 'o3', 'o4')) else {}))
                record.update(status='received', model=response.model, seconds=round(time.monotonic()-started, 3),
                    response_id=getattr(response, 'id', None), request_id=getattr(response, '_request_id', None),
                    usage=response.usage.model_dump() if response.usage else None)
                if embedding:
                    value = [d.embedding for d in response.data]
                else:
                    record['finish_reason'] = response.choices[0].finish_reason
                    record['raw'] = response.choices[0].message.content
                    dump(path, record)
                    if record['finish_reason'] != 'stop':
                        raise ValueError('Incomplete model output')
                    value = json.loads(record['raw'])
                record['status'] = 'complete'
                record['value'] = value
                dump(path, record)
                dump(cache, record)
                self.event({'kind': 'api_result', 'owner': owner, 'phase': phase, 'key': key, 'record_id': rid})
                return value
            except Exception as error:
                record.update(status='failed', seconds=round(time.monotonic()-started, 3),
                              error_type=type(error).__name__)
                dump(path, record)
                if attempt or isinstance(error, ValueError):
                    raise

    def event(self, value):
        with self.lock:
            self.folder.mkdir(parents=True, exist_ok=True)
            with (self.folder / 'events.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(value) + '\n')

    def report(self):
        rows = {}
        for path in (self.folder / 'calls').glob('*.json'):
            r = json.loads(path.read_text(encoding='utf-8'))
            key = (r['owner'], r['phase'], r.get('model', r['requested_model']))
            row = rows.setdefault(key, {'owner': key[0], 'phase': key[1], 'model': key[2],
                'calls': 0, 'input': 0, 'output': 0, 'cached_input': 0, 'reasoning': 0,
                'unknown_usage': 0, 'unknown_cache_details': 0, 'unknown_reasoning_details': 0,
                'failed': 0, 'seconds': 0.})
            row['calls'] += 1
            row['failed'] += int(r['status'] != 'complete')
            row['seconds'] += r.get('seconds', 0)
            u = r.get('usage')
            if u is None:
                row['unknown_usage'] += 1
                continue
            row['input'] += u.get('prompt_tokens', 0)
            row['output'] += u.get('completion_tokens', 0)
            pd, cd = u.get('prompt_tokens_details') or {}, u.get('completion_tokens_details') or {}
            row['cached_input'] += pd.get('cached_tokens') or 0
            row['reasoning'] += cd.get('reasoning_tokens') or 0
            if r['phase'] != 'embeddings':
                row['unknown_cache_details'] += int(pd.get('cached_tokens') is None)
                row['unknown_reasoning_details'] += int(cd.get('reasoning_tokens') is None)
        return sorted(rows.values(), key=lambda r: (r['owner'], r['phase'], r['model']))
