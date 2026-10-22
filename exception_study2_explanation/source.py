"""Read the pinned evidence archive directly; never follow archived absolute paths."""
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from exception_pilot.core import digest
from exception_study2_current import VERSION as SOURCE_VERSION, MODEL, REVISION, ENGINE, RUNTIME, SAMPLER
from exception_study2_current.adapter import parse_result as historical_score
from exception_study2_current.planning import contract as original_contract, request as original_request
from exception_study2_current.planning import smoke_design
from exception_study2_native.tables import parse as parse_table
from . import SOURCE_ZIP, SOURCE_LOG, SOURCE_SHA256, LOG_SHA256, SOURCE_PLAN, SOURCE_CONTRACT
from .parsing import metadata_errors


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sealed(value, name):
    if not isinstance(value, dict) or value.get('artifact_hash') != digest({k: v for k, v in value.items() if k != 'artifact_hash'}):
        raise ValueError('Source seal differs: ' + name)
    return value


def match_key(cell):
    return cell['world'], cell['variant'], cell['cue_state']


class Source:
    def __init__(self, archive, tok):
        archive = Path(archive)
        self.inputs = {SOURCE_ZIP: archive.read_bytes(),
                       SOURCE_LOG: archive.with_name(SOURCE_LOG).read_bytes(),
                       'SHA256SUMS': archive.with_name('SHA256SUMS').read_bytes()}
        if sha_bytes(self.inputs[SOURCE_ZIP]) != SOURCE_SHA256:
            raise ValueError('Source ZIP SHA256 differs')
        if sha_bytes(self.inputs[SOURCE_LOG]) != LOG_SHA256:
            raise ValueError('Source startup log SHA256 differs')
        checksums = dict(line.split(maxsplit=1)[::-1] for line in self.inputs['SHA256SUMS'].decode().splitlines() if line.strip())
        for name in (SOURCE_ZIP, SOURCE_LOG):
            if checksums.get(name) != sha_bytes(self.inputs[name]):
                raise ValueError('Source checksum inventory differs: ' + name)
        if self.inputs[SOURCE_LOG].splitlines()[0] != b'VLLM_USE_FLASHINFER_SAMPLER=0':
            raise ValueError('Missing archived sampler workaround evidence')
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(self.inputs[SOURCE_ZIP])) as z:
            names = z.namelist()
            if len(set(names)) != len(names) or any(n.startswith('/') or '..' in PurePosixPath(n).parts for n in names):
                raise ValueError('Unsafe or duplicate archive member')
            self.files = {n: z.read(n) for n in names}
        manifest = self.json('bundle-manifest.json')
        if set(self.files) != set(manifest['files']) | {'bundle-manifest.json'}:
            raise ValueError('Source manifest file population differs')
        for name, info in manifest['files'].items():
            data = self.files[name]
            if info != dict(bytes=len(data), sha256=sha_bytes(data)):
                raise ValueError('Source member checksum differs: ' + name)
        if checksums.get('analysis.json') != sha_bytes(self.files['analysis.json']):
            raise ValueError('Archived analysis bytes differ from published checksum')
        self.seals_checked = 0
        for name in self.files:
            if name.endswith('.json'):
                obj = self.json(name)
                if isinstance(obj, dict) and 'artifact_hash' in obj:
                    sealed(obj, name); self.seals_checked += 1
        self.plan = self.seal('plan.json')
        self.execution = self.seal('execution.json')
        self.locations = self.seal('locations.json')  # provenance only; do not open these paths
        if (self.plan['artifact_hash'] != SOURCE_PLAN or original_contract() != SOURCE_CONTRACT
                or self.plan['code_contract'] != SOURCE_CONTRACT or self.plan['kind'] != 'screen'):
            raise ValueError('Frozen source plan/code contract differs')
        if any(manifest.get(k) != self.plan.get(k if k != 'plan_hash' else 'artifact_hash')
               for k in ('protocol', 'code_contract', 'plan_hash')):
            raise ValueError('Source manifest binding differs')
        if (self.plan['model'] != MODEL or self.plan['model_revision'] != REVISION or self.plan['runtime'] != RUNTIME
                or self.plan['engine'] != ENGINE or self.plan['sampler'] != SAMPLER or self.plan['tokenizer'] != tok.identity):
            raise ValueError('Source model/runtime/tokenizer differs')
        design = sealed(self.plan['design'], 'embedded design')
        requests = self.plan['requests']
        if len(requests) != 384 or [r['cell'] for r in requests] != design['cells']:
            raise ValueError('Source request/design population differs')
        # Use saved cells, never regenerate worlds. Re-render their official requests.
        if any(r != original_request(r['cell'], tok, 4096) for r in requests):
            raise ValueError('Source rendered request differs from frozen cell')
        tables = {match_key(t): t for t in design['tables']}
        for r in requests:
            cell = r['cell']; table = tables[match_key(cell)]
            if any(cell.get(k) != v for k, v in table.items()) or table['table'] not in cell['prompt']:
                raise ValueError('Source table binding differs')
            target = [row for row in parse_table(table['table']) if row['plate'] == table['target_plate']]
            if len(target) != 1 or target[0]['label'] != cell['expected']:
                raise ValueError('Source actual recorded class differs')
        self.operations, self.scores = self.verify_operations('', self.plan, requests, tok)
        self.verify_smoke(tok)
        controls = [r for r in requests if r['cell']['wording'] == 'original']
        self.off = [r for r in controls if r['cell']['thinking'] is False]
        self.on = {match_key(r['cell']): r for r in controls if r['cell']['thinking'] is True}
        if len(self.off) != 96 or len(self.on) != 96 or len({match_key(r['cell']) for r in self.off}) != 96:
            raise ValueError('Expected exactly 96 OFF / 96 ON matched controls')
        if Counter(r['cell']['relation'] for r in self.off) != {'support': 48, 'conflict': 48}:
            raise ValueError('Source support/conflict population differs')
        worlds = Counter(r['cell']['world'] for r in self.off)
        if len(worlds) != 24 or set(worlds.values()) != {4}:
            raise ValueError('Source world population differs')
        for off in self.off:
            on = self.on[match_key(off['cell'])]
            if any(off['cell'][k] != on['cell'][k] for k in off['cell'] if k not in ('id', 'thinking')):
                raise ValueError('Controls are not matched')
        self.binding = dict(zip_sha256=SOURCE_SHA256, plan_hash=SOURCE_PLAN, code_contract=SOURCE_CONTRACT,
                            execution_hash=self.execution['artifact_hash'], backend_hash=self.execution['backend_hash'],
                            manifest_sha256=sha_bytes(self.files['bundle-manifest.json']),
                            checksum_file_sha256=sha_bytes(self.inputs['SHA256SUMS']),
                            startup_log=dict(sha256=LOG_SHA256, line_number=1, text='VLLM_USE_FLASHINFER_SAMPLER=0',
                                note='Separate log evidence; the historical backend identity did not record this environment variable.'),
                            smoke=self.smoke_binding)

    def json(self, name):
        return json.loads(self.files[name])

    def seal(self, name):
        return sealed(self.json(name), name)

    def verify_operations(self, prefix, plan, requests, tok):
        ex = self.seal(prefix + 'execution.json')
        binding = dict(protocol=SOURCE_VERSION, plan_hash=plan['artifact_hash'], code_contract=SOURCE_CONTRACT,
                       measurement_mode='LIVE_LOCAL')
        if (any(ex.get(k) != v for k, v in binding.items()) or ex['backend_hash'] != digest(ex['backend'])
                or ex['backend'] != self.execution['backend']):
            raise ValueError('Source execution/smoke backend differs')
        results = {}; scores = {}; expected_files = set(); expected_dispatches = set()
        for r in requests:
            q = r['request']; rh = digest(q)
            if rh != r['request_hash']:
                raise ValueError('Source request hash differs')
            oid = 'v5/' + SOURCE_VERSION + '/' + rh + '/attempt-1'
            folder = prefix + 'operations-v5/' + digest(oid) + '/'
            identity = dict(binding, id=oid, request=q, request_hash=rh, stage='current_native_generation')
            for filename, status in (('request', 'planned'), ('started', 'started'), ('returned', 'returned')):
                name = folder + filename + '.json'; expected_files.add(name)
                op = self.seal(name)
                if op['status'] != status or any(op.get(k) != v for k, v in identity.items()):
                    raise ValueError('Source operation binding differs: ' + name)
            dispatch_name = prefix + 'dispatches/' + digest(oid) + '.json'; expected_dispatches.add(dispatch_name)
            dispatch = self.seal(dispatch_name)
            start = self.seal(prefix + 'invocations/' + dispatch['invocation'] + '/started.json')
            end = self.seal(prefix + 'invocations/' + dispatch['invocation'] + '/finished.json')
            if (dispatch['request_hash'] != rh or dispatch['backend_hash'] != ex['backend_hash']
                    or any(start.get(k) != v or end.get(k) != v for k, v in binding.items())):
                raise ValueError('Source dispatch/invocation binding differs')
            raw = op['result']
            resolved = dict(ex['backend']['resolved_sampling_defaults'], seed=q['seed'], max_tokens=q['budget'])
            if metadata_errors(raw, q, tok, resolved):
                raise ValueError('Source raw return identity differs: ' + r['cell']['id'])
            score = historical_score(raw, q, tok)
            if not score['valid']:
                raise ValueError('Source historical parser or smoke no longer passes')
            results[r['cell']['id']] = op; scores[r['cell']['id']] = score
        if {n for n in self.files if n.startswith(prefix + 'operations-v5/')} != expected_files:
            raise ValueError('Source operation population differs')
        if {n for n in self.files if n.startswith(prefix + 'dispatches/')} != expected_dispatches:
            raise ValueError('Source dispatch population differs')
        return results, scores

    def verify_smoke(self, tok):
        p = self.seal('technical-smoke/plan.json')
        gate = self.seal('smoke-evidence.json')
        ex = self.seal('technical-smoke/execution.json')
        prefix = self.seal('technical-smoke/smoke-prefixes.json')
        if (p['artifact_hash'] != self.plan['smoke']['plan_hash'] or gate['plan_hash'] != p['artifact_hash']
                or gate['execution_hash'] != ex['artifact_hash'] or gate['backend_hash'] != self.execution['backend_hash']
                or prefix['plan_hash'] != p['artifact_hash']):
            raise ValueError('Smoke gate bindings differ')
        if p['requests'] != [original_request(c, tok, 256) for c in smoke_design()['cells']]:
            raise ValueError('Smoke base requests differ')
        reqs = p['requests'] + prefix['requests']
        if len(reqs) != 8:
            raise ValueError('Expected eight smoke records')
        ops, _ = self.verify_operations('technical-smoke/', p, reqs, tok)
        if gate['operations'] != {k: v['artifact_hash'] for k, v in ops.items()}:
            raise ValueError('Smoke gate operation hashes differ')
        expected_prefixes = []; source_ops = {}
        for base in p['requests']:
            op = ops[base['cell']['id']]; k = min(8, len(op['result']['tokens']) - 1)
            saved = op['result']['tokens'][:k]
            if k < 1 or any(i in tok.eos_ids for i in saved):
                raise ValueError('Invalid smoke prefix')
            cell = dict(base['cell'], id=base['cell']['id'] + '/saved-prefix')
            q = dict(base['request']); ids = q['input_ids'] + saved
            q.update(cell_id=cell['id'], input_ids=ids, input_hash=digest(ids), rendered_input=tok.decode_all(ids),
                     prefix_token_ids=saved, budget=q['budget']-k,
                     prefix_source=dict(operation_hash=op['artifact_hash'], original_request_hash=base['request_hash'], length=k))
            expected_prefixes.append(dict(cell=cell, request=q, request_hash=digest(q)))
            source_ops[base['cell']['id']] = op['artifact_hash']
        if prefix['requests'] != expected_prefixes or prefix['source_operations'] != source_ops:
            raise ValueError('Smoke exact supplied prefixes differ')
        self.smoke_binding = dict(plan_hash=p['artifact_hash'], execution_hash=ex['artifact_hash'],
                                  operations=gate['operations'], verified_passing_records=8, scheduled_new_records=0)

    def reference(self, r):
        op = self.operations[r['cell']['id']]
        return dict(cell_id=r['cell']['id'], request_hash=r['request_hash'], operation_id=op['id'],
                    operation_hash=op['artifact_hash'], source_plan_hash=SOURCE_PLAN, source_zip_sha256=SOURCE_SHA256,
                    source_member='operations-v5/' + digest(op['id']) + '/returned.json')
