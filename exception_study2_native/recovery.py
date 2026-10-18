"""Native-only atomic-write debris handling. Canonical historical readers remain unchanged."""
import os
import re
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze, sha
from exception_study2_v5.journal import operations

CANONICAL={'request.json','started.json','returned.json','failed.json'}
# tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp') uses eight [a-z0-9_] characters.
TEMP=re.compile(r'(request|started|returned|failed)\.json\.[a-z0-9_]{8}\.tmp\Z')
CONTROL_TEMP=re.compile(r'(manifest|completed)\.json\.[a-z0-9_]{8}\.tmp\Z')


def regular(path,directory=False):
    if path.is_symlink() or not (path.is_dir() if directory else path.is_file()):
        raise ValueError('Regular native journal path required: '+str(path))


def state(op):
    if op is None or op['status']=='planned':return 'never_started'
    return 'ambiguous' if op['status'] in ('started','recovery_ambiguous') else op['status']


def read_recoveries(c,known,binding):
    base=c.out/'journal-recovery';records=[];uncommitted=[];claimed=set()
    if not base.exists():return records,uncommitted,claimed
    regular(base,True)
    for folder in sorted(base.iterdir()):
        regular(folder,True)
        if not re.fullmatch('[a-f0-9]{64}',folder.name):raise ValueError('Unexpected recovery folder')
        for p in folder.iterdir():
            if p.name=='files':regular(p,True)
            elif p.name in ('manifest.json','completed.json') or CONTROL_TEMP.fullmatch(p.name):regular(p)
            else:raise ValueError('Unexpected recovery control file')
        path=folder/'manifest.json'
        if not path.exists():
            if (folder/'completed.json').exists() or (folder/'files').exists():raise ValueError('Recovery files without canonical manifest')
            uncommitted.append(str(folder.relative_to(c.out)));continue
        m=sealed_read(path)
        if m['artifact_hash']!=folder.name or m['binding']!=binding:raise ValueError('Recovery manifest identity differs')
        if not isinstance(m['reason'],str) or not m['reason'].strip():raise ValueError('Recovery requires explicit reason')
        expected=set();moves=[]
        for entry in m['entries']:
            oid=entry['operation_id'];opfolder=entry['folder']
            must_hold=not any(n in entry['canonical'] for n in ('returned.json','failed.json'))
            if entry.get('hold') is not must_hold:raise ValueError('Recovery ambiguity hold differs from canonical evidence')
            if opfolder not in known or known[opfolder]['id']!=oid:raise ValueError('Recovery operation identity differs')
            canonical=c.out/'operations-v5'/opfolder
            dispatch=c.out/'dispatches'/(opfolder+'.json')
            if entry.get('dispatch_hash') is not None and (not dispatch.is_file() or sha(dispatch)!=entry['dispatch_hash']):
                raise ValueError('Recovered dispatch evidence changed')
            for name,h in entry['canonical'].items():
                if name not in CANONICAL:raise ValueError('Unexpected canonical recovery record')
                regular(canonical/name)
                if sha(canonical/name)!=h:raise ValueError('Recovered canonical journal changed')
            present={p.name for p in canonical.iterdir() if p.name in CANONICAL} if canonical.exists() else set()
            if present!=set(entry['canonical']):raise ValueError('Canonical states added/removed after recovery; preserve the held attempt')
            for name,h in entry['temporary'].items():
                if not TEMP.fullmatch(name):raise ValueError('Unexpected quarantined filename')
                relative=opfolder+'/'+name
                if relative in claimed:raise ValueError('Recovery evidence claimed twice')
                claimed.add(relative);expected.add(relative)
                src=canonical/name;dst=folder/'files'/relative
                if src.exists()==dst.exists():raise ValueError('Recovery evidence missing or duplicated')
                actual=src if src.exists() else dst;regular(actual)
                if sha(actual)!=h:raise ValueError('Recovery evidence hash differs')
                if src.exists():moves.append(dict(source=src,destination=dst))
        files=folder/'files'
        if files.exists():
            for p in files.rglob('*'):
                if p.is_symlink():raise ValueError('Recovery symlinks forbidden')
                rel=str(p.relative_to(files))
                if p.is_dir():
                    if not any(n.startswith(rel+'/') for n in expected):raise ValueError('Unexpected recovery directory')
                elif not p.is_file() or rel not in expected:raise ValueError('Unexpected quarantine file')
        completed=folder/'completed.json'
        if completed.exists():
            value=sealed_read(completed)
            if moves or value.get('manifest_hash')!=m['artifact_hash']:raise ValueError('Recovery completion differs')
        records.append(dict(folder=folder,manifest=m,moves=moves,complete=completed.exists()))
    return records,uncommitted,claimed


def scan(c,known,binding):
    """Read-only view: validate canonical files, report debris, conservatively hold orphans."""
    records,uncommitted,claimed=read_recoveries(c,known,binding)
    base=c.out/'operations-v5';inventories={}
    if base.exists():
        regular(base,True)
        for folder in sorted(base.iterdir()):
            regular(folder,True)
            if folder.name not in known:raise ValueError('Unknown/orphan operation folder outside frozen native requests')
            canonical={};temporary={}
            for p in folder.iterdir():
                regular(p)
                if p.name in CANONICAL:canonical[p.name]=sha(p)
                elif TEMP.fullmatch(p.name):temporary[p.name]=sha(p)
                else:raise ValueError('Unexpected operation journal file')
            if 'request.json' not in canonical and canonical:
                raise ValueError('Orphan canonical states without request; explicit forensic review required')
            inventories[folder.name]=dict(folder=folder.name,operation_id=known[folder.name]['id'],canonical=canonical,temporary=temporary)
    for folder in known:
        dispatch=c.out/'dispatches'/(folder+'.json')
        if dispatch.exists():
            regular(dispatch)
            inventories.setdefault(folder,dict(folder=folder,operation_id=known[folder]['id'],canonical={},temporary={}))
            inventories[folder]['dispatch_hash']=sha(dispatch)
    saved=operations(c.out)  # unchanged canonical state/identity/hash validation
    holds={};pending=[]
    for rec in records:
        for item in rec['manifest']['entries']:
            if item['hold']:holds[item['operation_id']]=item
    for folder,item in inventories.items():
        oid=item['operation_id'];op=saved.get(oid)
        unclaimed={n:h for n,h in item['temporary'].items() if folder+'/'+n not in claimed}
        # A canonical request alone is normally never-started. Debris/orphans need explicit review.
        orphan=(not item['canonical'] or state(op)=='never_started' and 'dispatch_hash' in item) and oid not in holds
        if not unclaimed and not orphan:continue
        entry=dict(item,temporary=unclaimed,hold=state(op) not in ('returned','failed'))
        entry['classification']=('dispatch_without_canonical_start' if state(op)=='never_started' and 'dispatch_hash' in item else
            'orphan_request_or_empty_folder' if not item['canonical'] else
            'completed_canonical_with_debris' if state(op)=='returned' else
            'failed_canonical_with_debris' if state(op)=='failed' else
            'interrupted_return_or_failure_write' if any(n.startswith(('returned.','failed.')) for n in unclaimed) else
            'interrupted_start_write' if any(n.startswith('started.') for n in unclaimed) else 'interrupted_request_write')
        if oid in holds:raise ValueError('New debris on a previously held attempt; preserve for explicit forensic review')
        pending.append(entry)
        if entry['hold']:holds[oid]=entry
    for oid,item in holds.items():
        op=saved.get(oid)
        if state(op) in ('returned','failed'):raise ValueError('Held recovery attempt acquired a terminal state')
        # A virtual view, never a synthetic canonical request/start/return on disk.
        original=op or dict(known[digest(oid)]['identity'],status='absent')
        view=dict(original,canonical_artifact_hash=original.get('artifact_hash'),canonical_status=original['status'],
                  status='recovery_ambiguous',recovery_evidence=item)
        view.pop('artifact_hash',None);view['artifact_hash']=digest(view);saved[oid]=view
    c.recovery=dict(pending=pending,records=records,uncommitted=uncommitted)
    return saved


def summary(c):
    r=c.recovery
    return dict(pending_entries=r['pending'],held_attempts=[x['operation_id'] for x in r['pending'] if x['hold']],
        recoveries=[dict(manifest_hash=x['manifest']['artifact_hash'],complete=x['complete'],moves_remaining=len(x['moves']),
                         held_attempts=[i['operation_id'] for i in x['manifest']['entries'] if i['hold']]) for x in r['records']],
        uncommitted_recovery_intents=r['uncommitted'],
        action='inspect is read-only. Use recover with an explicit reason to quarantine recognized atomic-write debris; then explicit retry for held attempts. Temporary returns are never promoted.')


def needs_recovery(c):
    return bool(c.recovery['pending'] or any(not x['complete'] for x in c.recovery['records']))


def quarantine(c,binding,reason):
    """Caller holds the run lock. Freeze intent BEFORE moving bytes; resume interrupted moves."""
    if not isinstance(reason,str) or not reason.strip():raise ValueError('Explicit recovery reason required')
    records=list(c.recovery['records'])
    if c.recovery['pending']:
        value=dict(binding=binding,reason=reason,entries=c.recovery['pending'],policy='native-atomic-quarantine-v1')
        folder=c.out/'journal-recovery'/digest(value)
        m=freeze(folder/'manifest.json',value)
        records.append(dict(folder=folder,manifest=m,complete=False,moves=[
            dict(source=c.out/'operations-v5'/x['folder']/name,destination=folder/'files'/x['folder']/name)
            for x in value['entries'] for name in x['temporary']]))
    moved=0
    for rec in records:
        if rec['complete']:continue
        for move in rec['moves']:
            move['destination'].parent.mkdir(parents=True,exist_ok=True)
            if move['destination'].exists():raise ValueError('Refusing to overwrite quarantine evidence')
            os.replace(move['source'],move['destination']);moved+=1
        freeze(rec['folder']/'completed.json',dict(manifest_hash=rec['manifest']['artifact_hash']))
    return dict(quarantined_files=moved,model_loads=0,new_calls=0)
