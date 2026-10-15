"""Optional, bounded judge-only stages; no model loader or intervention execution."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5 import PROTOCOL
from exception_study2_v5.core import source_hash
from exception_study2_v5.runner import Source, bound_source
from exception_study2_v5.review.workflow import blinded_view, validate_decisions
from .policy import EVENTS, PROMPTS, SCHEMAS, freeze_policy
from .decisions import validate_vote, resolve, nonpresent


def target_metadata(task):
    """Index 9 is the tenth vehicle, NOT the ninth vehicle or a Markdown line."""
    lines = task['table'].splitlines()
    index = task['target_row_position']
    if (type(index) is not int or not 0 <= index < len(lines) - 2 or
            lines[index + 2] != task['target_row'] or
            task['target_row_values'] != lines[index + 2].strip('| ').split(' | ') or
            task['target_row_values'][0] != task['target_plate'] or
            task['target_row_values'][-1] != task['expected']):
        raise ValueError('Target row identity/index convention mismatch')
    return dict(plate=task['target_plate'], row=task['target_row'], verified_class=task['expected'],
                target_row_position=index, target_row_index_base=0,
                target_row_index_counts='vehicle data rows only; excludes header and separator',
                target_row_number_one_based=index + 1,
                table_line_index_zero_based=index + 2)


def view_for(row, family):
    view = blinded_view(row)
    view.pop('rubric')  # The two separately frozen family prompts are authoritative.
    view.update(family=family, target=target_metadata(row['task']))
    return view


def _views(source):
    return {f: {tid: view_for(row, f) for tid, row in source.rows.items() if row['task']['arm'] == 'visible'} for f in EVENTS}


def _separate(source, out):
    if source.root == out or source.root in out.parents or out in source.root.parents:
        raise ValueError('Judge output must be separate from the original source directory')


def prepare(source_path, output, config, scope='pilot'):
    src = Source(source_path, scope=scope); out = Path(output).resolve()
    _separate(src, out)
    policy = freeze_policy(config)
    views = _views(src)
    if out.exists() and any(out.iterdir()) and not (out/'judge-plan-v5.json').exists():
        raise ValueError('Fresh judge directory required')
    with run_lock(out/'locks'):
        if (out/'judge-plan-v5.json').exists():
            review = Review(out)
            if review.source_original.binding != src.binding or review.policy != policy:
                raise ValueError('Existing judge plan differs')
            return review.plan
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1],
                                  text=True, capture_output=True, check=True).stdout.strip()
        count = len(views['M'])
        freeze(out/'policy.json', policy)
        return freeze(out/'judge-plan-v5.json', dict(protocol=PROTOCOL, source=src.binding_at(out),
            scientific_source_hash=source_hash(), policy_hash=policy['policy_hash'], code_revision=revision,
            views=views, case_ids=list(views['M']), initial_request_ceiling=count*4,
            total_request_ceiling=count*6, concurrency=1, scope=scope,
            source_measurement=src.execution['mode'],
            blinding='Original prompt/table and pre-answer text only; no scores, final answers, readouts or intervention outcomes'))


class Review:
    def __init__(self, output):
        self.root = Path(output).resolve()
        self.plan = sealed_read(self.root/'judge-plan-v5.json')
        saved = sealed_read(self.root/'policy.json')
        self.policy = freeze_policy(saved['config'])
        if self.policy != {k:v for k,v in saved.items() if k != 'artifact_hash'}:
            raise ValueError('Frozen judge code/prompt/schema/provider configuration changed')
        self.source_original = bound_source(self.plan['source'], self.root)
        _separate(self.source_original, self.root)
        if (self.plan['protocol'] != PROTOCOL or self.plan['scientific_source_hash'] != source_hash() or
                self.plan['policy_hash'] != self.policy['policy_hash'] or
                self.plan['views'] != _views(self.source_original) or
                self.plan['case_ids'] != list(self.plan['views']['M'])):
            raise ValueError('Frozen judge source/view/population identity changed')
        # Shared Journal needs only case_binding. Family names separate immutable slots,
        # while both journals share one root, total spend ledger and invocation budget.
        self.source = SimpleNamespace(case_binding=self.case_binding)

    def case_binding(self, key):
        family, tid = key.split(':', 1)
        view = self.plan['views'][family][tid]
        return dict(task_id=key, original_task_id=tid, family=family,
                    source_hash=self.source_original.hash, trajectory_hash=view['source_row_hash'],
                    view_hash=digest(view), review_plan_hash=self.plan['artifact_hash'])

    def path(self, family, tid, name):
        return self.root/'cases'/family/digest(tid)/(name+'.json')

    def vote(self, family, tid, judge, journal):
        key = family + ':' + tid
        entry = journal.call(key, judge, 'adjudicate' if judge == 'J3' else 'initial', 0, self.plan['views'][family][tid])
        if entry is None:
            return None
        identity = entry['identity']
        if any(identity.get(k) != v for k,v in self.case_binding(key).items()):
            raise ValueError('Judge operation source identity mismatch')
        value = validate_vote(family, entry['parsed'].get('value'), self.plan['views'][family][tid],
                              entry['parsed']['valid'], entry['parsed'].get('reason'))
        return freeze(self.path(family, tid, judge), dict(operation_key=entry['key'],
                      operation_hash=entry['artifact_hash'], vote=value))['vote']


def _journals(review, live, transport, max_calls, wall_seconds, clock):
    from .family_m.journal import Journal as MJournal
    from .family_o.journal import Journal as OJournal
    if live and review.source_original.execution['mode'] != 'LIVE_LOCAL':
        raise ValueError('Paid judging requires a real-model source, never a synthetic fixture')
    journals = {f: cls(review, live, transport, max_calls, wall_seconds, clock)
                for f, cls in (('M', MJournal), ('O', OJournal))}
    # Both unchanged journal implementations enforce a single aggregate invocation
    # budget through shared metrics; entries()/spend already read the same ledger.
    journals['O'].metrics = journals['M'].metrics
    journals['O'].started = journals['M'].started
    journals['O'].clock = journals['M'].clock
    return journals


def _family_resolution(review, family, tid, journal, allow_j3):
    view = review.plan['views'][family][tid]
    if not view['original_available']:
        return dict(state='TERMINAL', needs_j3=False, events={e:nonpresent('invalid', 'Original unavailable; no judge request') for e in EVENTS[family]},
                    pairs={e:None for e in EVENTS[family]}, initial_agreement={e:False for e in EVENTS[family]},
                    unavailable_original=True)
    votes = {}
    for judge in ('J1', 'J2'):
        votes[judge] = review.vote(family, tid, judge, journal)
        if votes[judge] is None:
            return resolve(family, votes)
    resolution = resolve(family, votes)
    if resolution['state'] != 'TERMINAL' and allow_j3:
        votes['J3'] = review.vote(family, tid, 'J3', journal)
        resolution = resolve(family, votes)
    return dict(resolution, votes=votes)


def run(output, live=False, transport=None, max_calls=None, wall_seconds=None, clock=None, stage='all'):
    if stage not in ('initial', 'all'):
        raise ValueError('Choose initial or all (all adds only conditional J3)')
    with run_lock(Path(output)/'locks'):
        review = Review(output)
        journals = _journals(review, live, transport, max_calls, wall_seconds, clock)
        report = dict(review_plan_hash=review.plan['artifact_hash'], families={}, complete=False)
        try:
            # All J1/J2 calls precede J3, so an initial-only pass is independently auditable.
            for adjudicate in ([False, True] if stage == 'all' else [False]):
                for family, journal in journals.items():
                    for tid in review.plan['case_ids']:
                        result = _family_resolution(review, family, tid, journal, adjudicate)
                        if result['state'] == 'TERMINAL':
                            freeze(review.path(family, tid, 'resolution'), result)
                        report['families'].setdefault(family, {})[tid] = result
                        if journal.metrics['stop_reason']:
                            return journal.metrics
            report['complete'] = all(report['families'].get(f, {}).get(t, {}).get('state') == 'TERMINAL'
                                     for f in EVENTS for t in review.plan['case_ids'])
        finally:
            metrics = journals['M'].finish(stage, review.plan['scope'])
            freeze(review.root/'reports'/(metrics['id']+'.json'), dict(report, metrics=metrics))
    return metrics


def export(output):
    """Explicit offline export; requires terminal, revalidated journals for all cases.

    Exported certificates are the agreeing judges' explicit assertions, not proof.
    No intervention verification fields are created or accepted here.
    """
    with run_lock(Path(output)/'locks'):
        review = Review(output)
        journals = _journals(review, False, None, 0, None, None)
        cases = {}; provenance = {}; disagreements = []
        try:
            for tid in review.plan['case_ids']:
                results = {f: _family_resolution(review, f, tid, journals[f], True) for f in EVENTS}
                if any(r['state'] != 'TERMINAL' for r in results.values()):
                    raise ValueError('Review incomplete: finish pending requests before export; no calls made')
                # Terminal resolutions must already have been frozen by run().
                for f, r in results.items():
                    if sealed_read(review.path(f, tid, 'resolution')) != dict(r, artifact_hash=digest(r)):
                        raise ValueError('Frozen resolution differs from journal-derived decisions')
                events = {e:d for r in results.values() for e,d in r['events'].items()}
                validate_decisions(blinded_view(review.source_original.rows[tid]), events)
                m, o = events['erasure'], events['override']
                stratum = None
                if o['status'] == 'present':
                    stratum = ('mixed' if m['status'] == 'present' and m['span'][0] < o['span'][0] else
                               'clean' if m['status'] == 'absent' or (m['status'] == 'present' and m['span'][0] >= o['span'][0]) else
                               'unknown_erasure_history')
                agreed = all(all(r['initial_agreement'].values()) for r in results.values())
                if not agreed:
                    disagreements.append(tid)
                row = review.source_original.rows[tid]
                cases[tid] = dict(world=row['task']['world'], events=events, initial_agreement=agreed,
                                  override_stratum=stratum, source_row_hash=row['artifact_hash'])
                provenance[tid] = {f: sealed_read(review.path(f, tid, 'resolution')) for f in EVENTS}
            return freeze(review.root/'annotation-manifest-v5.json', dict(protocol=PROTOCOL,
                source=review.source_original.binding_at(review.root), code_hash=source_hash(),
                review_plan_hash=review.plan['artifact_hash'], cases=cases, disagreements=disagreements,
                method='automated-independent-family-detection', policy_hash=review.policy['policy_hash'],
                judge_code_hash=review.policy['code_hash'], reviews=provenance, adjudication='conditional independent J3',
                semantic_certification='Explicit agreeing-judge assertions only; JSON/alignment do not prove semantics. Independent intervention verification still required.',
                blinding=review.plan['blinding']))
        finally:
            journals['M'].finish('export', review.plan['scope'])
