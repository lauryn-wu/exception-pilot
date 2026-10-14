"""Separable judge-only stages. Never imports or launches a model."""
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from .artifacts import Review,freeze
from .boundaries import statement_boundaries
from .decisions import validate_vote,resolve
from .editing import edit_view,align_edit,mechanical,verify_bundle
from .policy import DRAFT_SCHEMA,schema_check
from .journal import Journal


def vote(review,tid,judge,journal):
    path=review.case_path(tid,'detect-'+judge)
    if path.exists():
        # Re-enter the journal so cache hits are visible without new timing samples.
        saved=review.read_case(tid,'detect-'+judge)
    else: saved=None
    view=review.source.detector(tid)
    entry=journal.call(tid,judge,'adjudicate' if judge=='J3' else 'initial',0,view)
    if entry is None: return None
    parsed=entry['parsed']; binding=review.source.case_binding(tid)
    value=validate_vote(parsed.get('value'),view['detection_view'],binding['trajectory_hash'],entry['identity']['trajectory_hash'],parsed['valid'],parsed.get('reason'))
    result=freeze(path,dict(review.binding(),**binding,judge=judge,operation_key=entry['key'],vote=value))
    if saved is not None and result!=saved: raise ValueError('Cached vote changed')
    return value


def read_resolution(review,tid):
    votes={}
    for j in ('J1','J2','J3'):
        p=review.case_path(tid,'detect-'+j)
        votes[j]=review.read_case(tid,'detect-'+j)['vote'] if p.exists() else None
    resolution=resolve(votes)
    if resolution['state']=='TERMINAL':
        return freeze(review.case_path(tid,'resolution'),dict(review.source.case_binding(tid),**review.binding(),**resolution))
    return resolution


def initial(review,plan,journal):
    for tid in plan['case_ids']:
        for j in ('J1','J2'):
            if vote(review,tid,j,journal) is None: return


def adjudicate(review,plan,journal):
    for tid in plan['case_ids']:
        result=read_resolution(review,tid)
        if result['state']=='TERMINAL': continue
        if result['resolution_route']=='waiting_initial': continue
        if vote(review,tid,'J3',journal) is None: return
        read_resolution(review,tid)


def freeze_statements(review,plan):
    rows=[]
    for tid in plan['case_ids']:
        result=read_resolution(review,tid)
        if result['state']!='TERMINAL': raise ValueError('Review INCOMPLETE: pending requests are not unresolved decisions')
        span=result['span']; row=review.source.rows[tid]
        rows.append(dict(result,task_id=tid,world=row['task']['world'],statement=None if span is None else row['raw']['text'][span[0]:span[1]],boundaries=None if span is None else statement_boundaries(row,span)))
    return freeze(review.root/'manifests'/(plan['scope']+'-statements.json'),dict(**review.binding(),review_plan_hash=plan['artifact_hash'],case_ids=plan['case_ids'],rows=rows))


def statements(review,plan):
    data=sealed_read(review.root/'manifests'/(plan['scope']+'-statements.json'))
    if data['review_plan_hash']!=plan['artifact_hash'] or data['case_ids']!=plan['case_ids'] or any(data[k]!=v for k,v in review.binding().items()): raise ValueError('Stale statement manifest')
    return data


def eligible(statement):
    return statement['decision']=='present' and statement['boundaries']['after_statement']['eligible']


def result_edit(review,tid,**data):
    return freeze(review.case_path(tid,'edit-result'),dict(review.binding(),**review.source.case_binding(tid),**data))


def draft(review,statement,journal,version=0,previous=None,criticism=None):
    tid=statement['task_id']; row=review.source.rows[tid]; view=edit_view(row,statement)
    if version:
        view.update(fixed_edit_quote=previous['bundle']['edit_quote'],fixed_edit_span=previous['span'],previous_bundle=previous['bundle'],criticism=criticism)
    drafter=statement['agreeing_pair'][0]
    entry=journal.call(tid,drafter,'draft' if version==0 else 'revise',version,view)
    if entry is None: return None
    value=entry['parsed'].get('value'); attempt=dict(version=version,operation_key=entry['key'],bundle=value,span=None,mechanical=None,usable=False,error=None)
    if not entry['parsed']['valid']: attempt['error']='unusable_draft_response'
    else:
        try:
            schema_check(value,DRAFT_SCHEMA)
            span=align_edit(statement,value)
            if version and (value['edit_quote']!=previous['bundle']['edit_quote'] or span!=previous['span']): raise ValueError('revision_changed_fixed_edit_span')
            attempt.update(span=span,usable=True,mechanical=mechanical(view['original_prefix'],span,value['edit_quote'],value['replacements'],row['task']['expected']))
        except (ValueError,TypeError,KeyError) as exc: attempt['error']=str(exc)
    frozen=freeze(review.case_path(tid,'draft-'+str(version)),dict(review.binding(),**review.source.case_binding(tid),**attempt))
    if not attempt['usable']: result_edit(review,tid,state='EXCLUDED',reason=attempt['error'],attempt_version=version)
    return frozen


def drafting(review,plan,journal):
    for statement in statements(review,plan)['rows']:
        tid=statement['task_id']
        if not eligible(statement) or review.case_path(tid,'edit-result').exists(): continue
        if draft(review,statement,journal) is None: return


def verification(review,plan,journal):
    for statement in statements(review,plan)['rows']:
        tid=statement['task_id']
        if not eligible(statement) or review.case_path(tid,'edit-result').exists(): continue
        p=review.case_path(tid,'draft-0')
        if not p.exists(): continue
        previous=review.read_case(tid,'draft-0'); criticism=None
        for version in (0,1):
            attempt=previous if version==0 else draft(review,statement,journal,1,previous,criticism)
            if attempt is None: return
            if not attempt['usable']: break
            checks=attempt['mechanical']
            if checks['passed']:
                view=edit_view(review.source.rows[tid],statement)
                view.update(proposed_bundle=attempt['bundle'],edit_span=attempt['span'],proposed_prefixes=checks['texts'])
                entry=journal.call(tid,statement['agreeing_pair'][1],'verify' if version==0 else 'reverify',version,view)
                if entry is None: return
                response=entry['parsed'].get('value')
                try:
                    if not entry['parsed']['valid']: raise ValueError('unusable_verifier_response')
                    checks=verify_bundle(response)
                except (ValueError,TypeError,KeyError) as exc:
                    freeze(review.case_path(tid,'verify-'+str(version)),dict(review.binding(),**review.source.case_binding(tid),operation_key=entry['key'],usable=False,response=response,error=str(exc)))
                    result_edit(review,tid,state='EXCLUDED',reason='unusable_verifier_response',attempt_version=version); break
                freeze(review.case_path(tid,'verify-'+str(version)),dict(review.binding(),**review.source.case_binding(tid),operation_key=entry['key'],usable=True,response=response,checks=checks))
                if response['source_assertion_concern'] is not None:
                    result_edit(review,tid,state='EXCLUDED',reason='source_assertion_concern',concern=response['source_assertion_concern'],attempt_version=version); break
            if checks['passed']:
                result_edit(review,tid,state='SEMANTIC_ACCEPTED',reason=None,attempt_version=version,span=attempt['span'],bundle=attempt['bundle'],texts=attempt['mechanical']['texts'],initial_agreement=statement['initial_agreement']); break
            criticism=checks['reasons']
            if version==1: result_edit(review,tid,state='EXCLUDED',reason='edit_checks_failed',criticism=criticism,attempt_version=1)


def run(output,stage='all',scope='full',live=False,transport=None,max_calls=None,wall_seconds=None,clock=None):
    # Judge locks/journals do not touch source locks or model operations.
    with run_lock(str(output)+'/locks'):
        review=Review(output); plan=review.plan(scope); journal=Journal(review,live,transport,max_calls,wall_seconds,clock)
        try:
            if stage in ('initial','all'): initial(review,plan,journal)
            if stage in ('adjudicate','all') and not journal.metrics['stop_reason']: adjudicate(review,plan,journal)
            if stage in ('freeze-statements','all') and not journal.metrics['stop_reason']: freeze_statements(review,plan)
            if stage in ('draft','all') and not journal.metrics['stop_reason']: drafting(review,plan,journal)
            if stage in ('verify','all') and not journal.metrics['stop_reason']: verification(review,plan,journal)
            if stage not in ('initial','adjudicate','freeze-statements','draft','verify','all'): raise ValueError('Unknown stage')
        finally:
            journal.finish(stage,scope)
            from .reporting import report
            report(output,scope)
    return journal.metrics


def freeze_policy_lock(output):
    review=Review(output); plan=review.plan('full'); statements(review,plan)
    if review.source.plan['phase']!='selection': raise ValueError('Policy must be locked on selection')
    return freeze(review.root/'policy-lock.json',dict(**review.binding(),selection_collection_hash=review.source.collection['artifact_hash'],no_2a_selection=True))
