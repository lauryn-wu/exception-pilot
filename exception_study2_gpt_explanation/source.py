"""Validate archived bytes and source bindings without decoding Qwen tokens or following paths."""
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path, PurePosixPath
from exception_pilot.core import digest
from exception_review.providers import loads
from exception_study2_current import VERSION as SOURCE_VERSION
from exception_study2_current.planning import contract as source_contract
from exception_study2_explanation.source import sealed, sha_bytes, match_key
from exception_study2_native.tables import parse as parse_table
from . import SOURCE_SHA256, SOURCE_PLAN, SOURCE_CONTRACT


class Source:
    def __init__(self, archive):
        self.data = Path(archive).read_bytes()
        if sha_bytes(self.data) != SOURCE_SHA256:
            raise ValueError('Source ZIP SHA256 differs')
        with zipfile.ZipFile(BytesIO(self.data)) as z:
            names = z.namelist()
            if len(names) != len(set(names)) or any(n.startswith('/') or '..' in PurePosixPath(n).parts for n in names):
                raise ValueError('Unsafe source archive')
            self.files = {n: z.read(n) for n in names}
        manifest = self.json('bundle-manifest.json')
        if set(self.files) != set(manifest['files']) | {'bundle-manifest.json'}:
            raise ValueError('Source manifest population differs')
        for name, info in manifest['files'].items():
            data = self.files[name]
            if info != dict(bytes=len(data), sha256=sha_bytes(data)):
                raise ValueError('Source manifest checksum differs: ' + name)
        self.seals_checked = 0
        for name in self.files:
            if name.endswith('.json'):
                obj = self.json(name)
                if isinstance(obj, dict) and 'artifact_hash' in obj:
                    sealed(obj, name); self.seals_checked += 1
        self.plan = self.seal('plan.json')
        if (self.plan['artifact_hash'] != SOURCE_PLAN or self.plan['code_contract'] != SOURCE_CONTRACT
                or source_contract() != SOURCE_CONTRACT or self.plan['protocol'] != SOURCE_VERSION
                or self.plan['kind'] != 'screen'):
            raise ValueError('Source protocol/plan/code differs')
        if any(manifest[k] != self.plan['artifact_hash' if k == 'plan_hash' else k] for k in ('protocol','plan_hash','code_contract')):
            raise ValueError('Source manifest binding differs')
        design = sealed(self.plan['design'], 'design')
        reqs = self.plan['requests']
        if len(reqs) != 384 or [r['cell'] for r in reqs] != design['cells']:
            raise ValueError('Source population differs')
        tables = {match_key(t): t for t in design['tables']}
        for r in reqs:
            cell, q = r['cell'], r['request']; table = tables[match_key(cell)]
            if (q['prompt'] != cell['prompt'] or q['prompt_hash'] != digest(cell['prompt'])
                    or cell['prompt_hash'] != q['prompt_hash'] or q['cell_id'] != cell['id']
                    or q['expected'] != cell['expected'] or q['thinking'] is not cell['thinking']
                    or q['input_hash'] != digest(q['input_ids']) or r['request_hash'] != digest(q)
                    or any(cell.get(k) != v for k,v in table.items()) or table['table'] not in q['prompt']):
                raise ValueError('Source prompt/table/request binding differs')
            target = [x for x in parse_table(table['table']) if x['plate'] == table['target_plate']]
            if len(target) != 1 or target[0]['label'] != cell['expected']:
                raise ValueError('Actual recorded source label differs')
        self.execution = self.seal('execution.json')
        self.operations = self.verify_operations('', self.plan, reqs)
        smoke = self.seal('technical-smoke/plan.json'); gate = self.seal('smoke-evidence.json')
        prefixes = self.seal('technical-smoke/smoke-prefixes.json')
        smoke_ex = self.seal('technical-smoke/execution.json')
        ops = self.verify_operations('technical-smoke/', smoke, smoke['requests'] + prefixes['requests'])
        if (len(ops) != 8 or smoke['artifact_hash'] != self.plan['smoke']['plan_hash']
                or gate['plan_hash'] != smoke['artifact_hash'] or prefixes['plan_hash'] != smoke['artifact_hash']
                or gate['execution_hash'] != smoke_ex['artifact_hash']
                or gate['backend_hash'] != self.execution['backend_hash']
                or gate['operations'] != {k:v['artifact_hash'] for k,v in ops.items()}):
            raise ValueError('Source smoke evidence differs')
        self.cases = [r for r in reqs if r['cell']['wording'] == 'original' and r['cell']['thinking'] is False]
        if (len(self.cases) != 96 or len({match_key(r['cell']) for r in self.cases}) != 96
                or Counter(r['cell']['relation'] for r in self.cases) != {'support':48,'conflict':48}
                or len({r['cell']['world'] for r in self.cases}) != 24
                or Counter(r['cell']['block'] for r in self.cases) != {0:24,1:24,2:24,3:24}):
            raise ValueError('Expected 96 original-wording cases, 24 worlds, four blocks')
        self.binding = dict(zip_sha256=SOURCE_SHA256, plan_hash=SOURCE_PLAN, code_contract=SOURCE_CONTRACT,
                            execution_hash=self.execution['artifact_hash'], manifest_sha256=sha_bytes(self.files['bundle-manifest.json']),
                            verified_returns=384, verified_smoke_returns=8, sealed_files=self.seals_checked,
                            validation_scope='Archived seals, file hashes, prompt/table/operation bindings and saved input-ID identity. No independent Qwen token decoding, template rendering, or inference.')

    def json(self, name):
        return loads(self.files[name])

    def seal(self, name):
        return sealed(self.json(name), name)

    def verify_operations(self, prefix, plan, requests):
        ex = self.seal(prefix + 'execution.json')
        binding = dict(protocol=SOURCE_VERSION, plan_hash=plan['artifact_hash'], code_contract=SOURCE_CONTRACT, measurement_mode='LIVE_LOCAL')
        if (any(ex.get(k) != v for k,v in binding.items()) or ex['backend_hash'] != digest(ex['backend'])
                or ex['backend'] != self.execution['backend']):
            raise ValueError('Source execution differs')
        results = {}; files = set(); dispatches = set()
        for r in requests:
            q = r['request']; rh = digest(q)
            if rh != r['request_hash'] or q['input_hash'] != digest(q['input_ids']):
                raise ValueError('Source request hash differs')
            oid = 'v5/' + SOURCE_VERSION + '/' + rh + '/attempt-1'
            identity = dict(binding, id=oid, request=q, request_hash=rh, stage='current_native_generation')
            for name, status in (('request','planned'),('started','started'),('returned','returned')):
                path = prefix + 'operations-v5/' + digest(oid) + '/' + name + '.json'; files.add(path)
                op = self.seal(path)
                if op['status'] != status or any(op.get(k) != v for k,v in identity.items()):
                    raise ValueError('Source operation differs')
            raw = op['result']
            if raw['actual_input_ids'] != q['input_ids'] or raw['input_ids_verified'] is not True:
                raise ValueError('Saved source input identity differs')
            name = prefix + 'dispatches/' + digest(oid) + '.json'; dispatches.add(name)
            d = self.seal(name)
            if d['request_hash'] != rh or d['backend_hash'] != ex['backend_hash']:
                raise ValueError('Source dispatch differs')
            for terminal in ('started','finished'):
                invocation = self.seal(prefix + 'invocations/' + d['invocation'] + '/' + terminal + '.json')
                if any(invocation.get(k) != v for k,v in binding.items()):
                    raise ValueError('Source invocation differs')
            results[r['cell']['id']] = op
        if ({n for n in self.files if n.startswith(prefix+'operations-v5/')} != files
                or {n for n in self.files if n.startswith(prefix+'dispatches/')} != dispatches):
            raise ValueError('Source journal population differs')
        return results

    def reference(self, r):
        op = self.operations[r['cell']['id']]
        return dict(cell_id=r['cell']['id'], request_hash=r['request_hash'], operation_hash=op['artifact_hash'],
                    source_member='operations-v5/' + digest(op['id']) + '/returned.json')
