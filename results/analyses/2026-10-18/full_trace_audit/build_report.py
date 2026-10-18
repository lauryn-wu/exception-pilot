import json, html, hashlib, collections, base64
from pathlib import Path

B=Path(__file__).parent
load=lambda name:json.loads((B/name).read_text())
norm={x['id']:x for x in load('normalized.json')}
annotations=sum([load(f'annotations_{i}.json') for i in range(4)],[])
ad={x['id']:x for x in annotations}
changes=[]
def change(suffix,field,value,reason,quote=None):
    ident='staged-v5-'+suffix+'/original/visible'; a=ad[ident]
    changes.append(dict(id=ident,field=field,before=a[field],after=value,reason=reason))
    a[field]=value;a['notes']+=' Adjudication: '+reason
    if quote:a['override_quote']=quote
change('014/v1','recognized_record','uncertain','Only correct class-group association simultaneously marks target MISSING; harmonized with six equivalent cases.')
change('022/v1','explicit_override','uncertain','Explicit simulated missingness establishes recasting, but no direct statement resolves record-versus-pattern priority.')
change('034/v1','explicit_override','uncertain','Acknowledged C is treated as a value to confirm before an A answer; direct priority statement absent.', '- **Verified class**: C (this is the value we are trying to confirm)')
change('035/v0','explicit_override','uncertain','Known B is deliberately subjected to simulated prediction; explicit priority over the source remains ambiguous.', 'Our goal is to determine the **Verified class** for **V5TRYPCH**, which is already known to be **B** in the data. However, we will simulate the process of predicting it based on the other records.')
for suf in ['038/v0','038/v1']:
    change(suf,'recognition_kind','both','Correct source table copy plus unqualified unique-description class mapping.')
narrow=load('narrow_recasting.json')
if isinstance(narrow,dict):
    narrow=narrow.get('annotations',narrow.get('cases',narrow.get('rows')))
nar={x['id']:x for x in narrow}
q=load('quantitative_audit.json')
for a in annotations:
    n=norm[a['id']]
    a['outcome']=n['score']['outcome'];a['expected']=n['expected'];a['pattern']=n['pattern'];a['answer']=n['score']['answer']
    a['known_class_recasting']=nar[a['id']]['label']
    a['recasting_quote']=nar[a['id']]['quote'];a['recasting_notes']=nar[a['id']]['notes']
    for k,v in a.items():
        if k.endswith('_quote') and v:assert v in n['text'],(a['id'],k)
assert len(annotations)==112 and len(ad)==112
fields=['recognized_record','false_missingness','miscopied_record','explicit_override','known_class_recasting']
counts={f:{status:dict(collections.Counter(a['outcome'] for a in annotations if a[f]==status)) for status in ['present','uncertain','absent']} for f in fields}
source=B.parent/'upload/study2-v5-traces-for-audit.tar.gz'
audit=dict(title='Study 2 v5 trace audit',date='2026-10-16',archive_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),annotations=annotations,counts=counts,adjudications=changes,quantitative=q,independent_wrong_review=load('independent_wrong_review.json'),disagreements=load('wrong_review_disagreements.json'))
(B/'audit_data.json').write_text(json.dumps(audit,indent=2))
e=lambda x:html.escape(str(x))
def table(headers,rows):return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
parts=['''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Study 2 v5 — trace audit</title><style>
:root{color-scheme:light;--ink:#18232b;--muted:#53636e;--accent:#006f72;--line:#d5dfe3}*{box-sizing:border-box}body{margin:0;color:var(--ink);font:16px/1.6 system-ui,sans-serif;background:#f4f7f7}main{max-width:1100px;margin:auto;padding:42px 28px;background:white}h1{font-size:36px;line-height:1.15;margin:10px 0 22px}h2{margin-top:38px;font-size:25px;line-height:1.3}h3{font-size:19px}p{max-width:90ch}a{color:var(--accent)}.eyebrow{color:var(--accent);font-weight:700;letter-spacing:.08em;font-size:13px}.muted,small{color:var(--muted)}.callout{border-left:4px solid var(--accent);background:#edf7f5;padding:16px 20px;margin:24px 0}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:16px 0}td,th{padding:11px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{background:#eff4f5}pre{white-space:pre-wrap;overflow-wrap:anywhere;word-break:normal;font:13px/1.55 ui-monospace,monospace;background:#f5f7f8;padding:16px;border-radius:5px;max-height:650px;overflow:auto}code{font-family:ui-monospace,monospace;font-size:.9em}details{border:1px solid var(--line);border-radius:6px;margin:10px 0;padding:12px 16px}details details{border:none;border-top:1px solid var(--line);border-radius:0}summary{cursor:pointer;font-weight:600}.controls{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}input,select,button{font:inherit;padding:9px 12px;border:1px solid #9bafb6;border-radius:5px;background:white}input{min-width:270px;flex:1}button{background:var(--accent);color:white;border-color:var(--accent);cursor:pointer}.pill{font-size:12px;border-radius:20px;padding:3px 9px;background:#eaf0f2;margin-left:8px;white-space:nowrap}.wrong{color:#982d33}.correct{color:#18754d}.quote{border-left:3px solid #9bb9bd;padding-left:14px;white-space:pre-wrap;font-size:14px}.case[hidden]{display:none}@media print{body,main{background:white;padding:0}.controls,button,#cases{display:none}h2{break-after:avoid}table{font-size:11px}.callout{break-inside:avoid}}@media(max-width:600px){main{padding:24px 16px}h1{font-size:29px}td,th{padding:8px}}
</style></head><body><main><div class="eyebrow">EXCEPTION PROJECT · 16 OCTOBER 2026</div><h1>Study 2 v5: full trace audit</h1>
<p class="muted">480 saved original responses · 1,674 checkpoint readouts · full qualitative review of 112 replication traces in the original framing · independent second review of all 36 wrong originals</p>
<div class="callout"><strong>The behavioral result holds. The broad confidence-decline interpretation does not survive scoring sensitivity.</strong><br>Reasoning often converts an authoritative recorded answer into a prediction problem. That behavior also occurs in correct responses, so it is an intervention target rather than an established explanation of every error.</div>
<p>This audit uses saved outputs only. No new model inference was run. All original-question replication reasoning traces were reviewed in full, and the paired lookup outputs were inspected. Annotations are retrospective, model-assisted textual judgments, with uncertain cases retained. They are not independently validated human labels or measurements of internal beliefs.</p>
<h2>1. What the results actually say</h2>''']
parts.append(table(['Remaining 56 worlds','Correct','Wrong','Unknown / format miss'],[
['Original question, direct answer','112 / 112','0','0'],['Original question, visible reasoning','75 / 111 valid','36','1 genuine truncation'],['Explicit lookup, direct answer','112 / 112','0','0'],['Explicit lookup, visible reasoning — frozen parser','107 / 108 valid','1','4'],['Explicit lookup, visible reasoning — semantic sensitivity','111 / 112','1','0']]))
parts.append('''<p>The four lookup parser misses are <code>016/v1, 028/v1, 047/v1, 050/v0</code>. Each ends <code>### ANSWER: B</code> and correctly reports B. Keep the frozen results; add this separately labeled sensitivity. Original <code>049/v0</code> truly stops at 2,048 tokens without a final answer.</p>
<p><strong>33 of the 36 original errors choose the designated misleading pattern class.</strong> The other three have different textual routes: <code>006/v0</code> relies on the irrelevant audit marker; <code>023/v1</code> falsely says the supplied class is A when it is B; <code>044/v1</code> rewrites the target description from subzero to hot sand. The lone lookup error, <code>006/v1</code>, also copies the target class incorrectly (C becomes A).</p>
<p>The four pilot worlds are separate: original visible reasoning was 7/8 correct and lookup 8/8, with direct answering 8/8 in both framings. Do not pool those inspected pilot worlds into the 56-world replication claim.</p>
<h2>2. What the traces support</h2>''')
labels={'recognized_record':'Correct target-class association, unqualified','false_missingness':'Literal false claim that the source class is missing','miscopied_record':'Wrong A/B/C asserted as the target source class','explicit_override':'Explicitly prioritizes conflicting pattern over record','known_class_recasting':'Explicitly recasts an acknowledged correct class as verification/prediction'}
rows=[]
for f in fields:
    c=counts[f];rows.append([labels[f],str(c['present'].get('correct',0)),str(c['present'].get('wrong',0)),str(c['present'].get('unknown',0)),str(sum(c['present'].values())),str(sum(c['uncertain'].values()))])
parts.append(table(['Textual finding','Correct (75)','Wrong (36)','Truncated (1)','Present / 112','Uncertain / 112'],rows))
parts.append('''<p>Labels overlap. In particular, false missingness is present in <strong>23 wrong and 18 correct</strong> responses, plus the truncated response. It is neither necessary nor sufficient for a wrong final answer. “As if missing” is distinct: it openly changes the task rather than falsely reporting what the table contains.</p>
<p>Twenty wrong responses contain an unqualified correct target-class association; seven more put the target under the correct class heading while simultaneously labeling it MISSING. The latter are marked uncertain. Even the definite label includes copied rows and grouped lists, so it must not be described as twenty explicit, stable acknowledgments of source authority.</p>
<p>The narrow known-class recasting label occurs in <strong>30 responses: 22 correct and 8 wrong</strong>. Fifteen further cases are uncertain because they might merely corroborate an answer already accepted from the record. Seven clear “as if missing” cases split 4 correct / 3 wrong; including one explicit simulated-prediction case gives 4 correct / 4 wrong. This undermines a simple claim that recasting itself determines failure.</p>
<p>Only <strong>3 wrong traces</strong> clearly resolve an explicit record–pattern conflict in favor of the pattern under a strict definition: <code>031/v0, 039/v1, 040/v0</code>. Six additional cases are uncertain. All 112 original-framing responses open with pattern-analysis language, including correct responses; that opening is not a useful discriminator.</p>
<h3>Cases worth reading first</h3>''')
examples=[('031/v0','Known C → simulated missingness → rejection of C → B','This is a **strong indicator** that **V5TZRQKW** does **not** belong to Class C.'),('039/v1','Correct B group → literal MISSING → B outlier acknowledged → A',ad['staged-v5-039/v1/original/visible']['override_quote']),('046/v0','Acknowledged C → “as if MISSING” → correct C',nar['staged-v5-046/v0/original/visible']['quote']),('023/v1','Misread supplied B as A → correct B groupings → wrong A',ad['staged-v5-023/v1/original/visible']['miscopy_quote'])]
for suf,title,quote in examples:
    assert quote in norm['staged-v5-'+suf+'/original/visible']['text']
    parts.append('<p><a href="#case-'+suf.replace('/','-')+'"><strong>'+e(suf)+' · '+e(title)+'</strong></a></p><div class="quote">'+e(quote)+'</div>')
parts.append('''<h2>3. The checkpoint scoring issue</h2><p>The saved candidate score is for the entire string <code> A\\n</code>, <code> B\\n</code>, or <code> C\\n</code>. It adds the class-token log probability and the conditional newline log probability. Thus the gold-versus-pattern score includes a formatting preference, not just the class choice.</p>
<p>The saved per-token log probabilities let us remove the newline without rerunning the model. The table below preserves the frozen whole-string measure alongside this retrospective class-token-only sensitivity. Values are changes in gold-versus-pattern log odds from initial to preanswer, averaged over 55 complete original-framing worlds (110 paired variants).</p>''')
erows=[]
for cue in ['ANSWER:','Final answer:']:
    row=[e(cue)]
    for metric in ['sequence','class_only']:
        v=q['endpoint_changes']['original/'+cue+'/'+metric]['complete_worlds'];lo,hi=v['bootstrap_95ci'];row.append(f'{v["mean"]:+.3f} [{lo:+.3f}, {hi:+.3f}]')
    erows.append(row)
parts.append(table(['Answer cue','Letter + newline (frozen)','Class token only (sensitivity)'],erows))
parts.append('''<p>Intervals are 95% bootstrap intervals from 10,000 resamples of world means, seed 20261016. Point estimates reproduce the supplied whole-string analysis; bootstrap endpoints differ slightly from its original random seed. The 111 available original endpoints include one incomplete world, which is excluded from the complete-world estimate. Lookup has 108 available endpoints but only 52 complete worlds / 104 variants.</p>
<p>Including the newline changes the preferred class at <strong>82 of 1,674 readouts</strong>. With the original <code>ANSWER:</code> cue at preanswer, the whole-string score agrees with the natural final answer in 106/111 cases; the class token agrees in 111/111. Median total A/B/C token probability there is 0.9969, but the three letter-plus-newline strings together have median mass only about 8.34 × 10<sup>−7</sup>. Renormalizing those rare strings can obscure the format dependence.</p>
<p><strong>This does not erase individual reversals.</strong> All 112 initial original-framing <code>ANSWER:</code> readouts prefer the correct class under either score. Class-token scoring yields 33 initial-gold to preanswer-pattern cases; 24 exhibit that endpoint reversal under both cues. The unsupported step is generalizing this into a stable average confidence-decline or internal forgetting claim.</p>
<p>Preanswer prefixes usually already contain a substantive conclusion. Agreement there is partly agreement with a choice already written in the prefix. Likewise, fixed checkpoints select longer responses: original reasoning has median 903.5 tokens and lookup 109.5; only 37 originals reach 1,024 and only 25 lookup responses reach 128. A changing-cohort average is not a common trajectory.</p>
<h2>4. What I would do next</h2>
<ol><li><strong>Correct the analysis now, using these saved files.</strong> Preserve frozen scores, add the four semantic parser corrections, report class-only and newline contributions separately, and use matched-world endpoints. These are analysis changes, not reasons for another generation run.</li>
<li><strong>Freeze a small continuation experiment around source use.</strong> Begin with the 30 clear known-class recasting cases, including the 22 that currently finish correctly. Continue from a matched boundary immediately before the recasting sentence. Compare unchanged continuation, a neutral same-style control, a task reminder with no class letter, and a source-value reminder with no task instruction. Keep insertion style, budget, decoding, and checkpoint comparable. An example task reminder is “The target already has a verified class; report that recorded value.” An example fact reminder is “The target row’s Verified class is C.” The latter must use the actual target value.</li>
<li><strong>Use natural final correctness as the primary outcome.</strong> Keep semantic correctness separate from format compliance. Report rescue of wrong cases and damage to correct cases, with paired world-level analysis. Prespecify both answer cues and class-token readouts as diagnostics. Differences between task and fact reminders can guide hypotheses about task interpretation versus source retrieval; either reminder can also refocus attention, so the contrast alone will not uniquely identify an internal mechanism.</li>
<li><strong>Confirm on fresh worlds before a mechanism claim.</strong> The current traces selected the hypotheses. Counterbalance target row position (all current targets are row 10), use new identifiers and paraphrases, retain both counterfactual labels, and include genuine-MISSING controls. Freeze decisions before collecting that confirmation set. If a specific intervention has a selective, repeatable effect, then probe or patch that contrast; broad activation searches are premature.</li></ol>
<p>The best current claim is: <em>Under the original question wording, visible reasoning often substitutes feature-based inference for an authoritative recorded answer; explicit lookup wording largely prevents the behavioral error. The textual routes are heterogeneous, and the average forced-readout trend depends on answer-cue and candidate formatting.</em> This is a behavioral and diagnostic result, not yet a demonstrated internal mechanism.</p>
<h2>5. Relation to the literature</h2>
<p><a href="https://arxiv.org/html/2410.21333v2">Liu et al., Mind Your Step (by Step)</a>, §4.3, is the closest behavioral antecedent: reasoning hurts vehicle classification with exceptions to a strong feature pattern. It already proposes reliance on generalizable patterns at the expense of contextual correct answers. Its multi-turn feedback task differs from this explicit verified-record task. The possible contribution here is a sharper account of source handling and a controlled intervention, rather than the general discovery that reasoning can hurt exceptions.</p>
<p><a href="https://arxiv.org/html/2307.13702v1">Lanham et al., Measuring Faithfulness in Chain-of-Thought Reasoning</a> motivates the next methodological step: early answering, editing reasoning, and paraphrasing test whether generated text influences later outputs. Saved-prefix answer probes are related diagnostics; they do not directly read latent belief. Your next experiment should test a specific source-use statement while retaining appropriate continuation controls.</p>
<h2>6. Scope, provenance, and coding rules</h2>
<p>Model: Qwen3-32B, BF16, revision <code>9216db5781bf21249d130ec9da846c4624c16137</code>; native thinking disabled. The visible reasoning condition is an instruction to produce reasoning. The effective scientific generation budget is 2,048 tokens despite a common backend setting of 512.</p>
<p>All 480 expected labels match the target cells. Each matched variant pair changes only the target class between the two nonpattern letters. All saved original artifact, input, and output hashes reproduce. All 1,674 readout contexts match the saved input tokens + unmodified generated prefix + cue tokens, and candidate arithmetic and boundary hashes reproduce. This validates saved provenance and arithmetic, not fresh neural replay. The upload does not contain the explicit readout measurement plan or full project source code.</p>
<details><summary>Operational rubric and limitations</summary><ul>
<li><strong>Correct record association:</strong> a correct target→class mapping in a copied row, source statement, or unqualified class group. Qualified correct headings with simultaneous MISSING are uncertain. This is textual evidence, not proof of internal knowledge.</li>
<li><strong>False missingness:</strong> an assertion that the provided target class is absent, unknown, or MISSING. Conditional “if missing” and explicit “as if missing” assumptions are excluded. Bare “unknown record” headings remain uncertain where appropriate.</li>
<li><strong>Miscopied record:</strong> a wrong A/B/C asserted as a source value or membership. MISSING substitution is separate. Other-attribute corruption is documented in notes.</li>
<li><strong>Explicit override:</strong> text explicitly weighs a recognized recorded class against a conflicting pattern and favors the latter. Recognition followed by a wrong answer is insufficient. Simulated prediction without explicit priority is uncertain.</li>
<li><strong>Narrow known-class recasting:</strong> acknowledgment of the actual supplied class followed by an explicit verification/prediction task. Source misreads and literal missingness alone do not count. Optional corroboration is uncertain. The older broad task_reinterpretation field is retained in the data for traceability, but is not an independent mechanism count.</li>
<li>Reviewers saw the prompts, complete traces, and final outcomes. Wrong cases received a separate full read before reconciliation. This is model-assisted review, not blinded human inter-rater validation. Every included quote was checked as an exact contiguous substring. Counts are descriptive and labels overlap.</li></ul></details>
<p class="muted">Source archive SHA-256: <code>'''+audit['archive_sha256']+'''</code></p>
<button id="download">Download audit data (JSON)</button>
<h2>7. Case explorer</h2><p>All 112 original-framing replication traces, their paired lookup responses, source prompts, exact evidence quotes, and checkpoint scores. Search IDs or text; filter by outcome or finding.</p>
<div class="controls"><input id="search" type="search" aria-label="Search cases" placeholder="Search case ID, quote, or trace"><select id="outcome" aria-label="Outcome"><option value="">All outcomes</option><option>correct</option><option>wrong</option><option>unknown</option></select><select id="finding" aria-label="Finding"><option value="">All findings</option>''')
for f,label in labels.items():parts.append('<option value="'+f+'">'+e(label)+'</option>')
parts.append('</select></div><p id="case-count" class="muted">112 cases</p><div id="cases">')
for a in annotations:
    n=norm[a['id']];suf=a['id'].split('staged-v5-')[1].replace('/original/visible','');short=suf.replace('/','-');look=norm[a['id'].replace('/original/','/lookup/')]
    present=' '.join(f for f in fields if a[f]=='present')
    parts.append('<details class="case" id="case-'+short+'" data-outcome="'+a['outcome']+'" data-findings="'+present+'"><summary>'+e(suf)+' <span class="pill '+a['outcome']+'">'+e(a['outcome'])+'</span> <span class="pill">record '+a['expected']+' · pattern '+a['pattern']+' · answer '+str(a['answer'] or 'none')+'</span></summary>')
    parts.append('<p><strong>Target source row</strong></p><pre>'+e(n['target_row'])+'</pre>')
    parts.append(table(['Annotation','Judgment'],[[labels[f],e(a[f])] for f in fields]))
    for f,label in [('recognition_quote','Correct association'),('missingness_quote','Missingness'),('miscopy_quote','Miscopy'),('override_quote','Override'),('recasting_quote','Known-class recasting')]:
        if a.get(f):parts.append('<p><strong>'+label+'</strong></p><div class="quote">'+e(a[f])+'</div>')
    parts.append('<p>'+e(a['notes'])+'</p><p>'+e(a['recasting_notes'])+'</p>')
    for title,txt in [('Full original response',n['text']),('Paired lookup response',look['text']),('Original source prompt',n['prompt'])]:parts.append('<details><summary>'+title+'</summary><pre>'+e(txt)+'</pre></details>')
    rs=[r for r in q['readout_rows'] if r['id']==a['id']]
    parts.append('<details><summary>Saved checkpoint scores</summary>'+table(['Cue','Checkpoint','Token cut','Letter+newline gold−pattern','Class token gold−pattern','Preferred: whole / class'],[[e(r['cue'].strip()),e(r['type']),r['k'],f'{r["odds"]:.3f}',f'{r["first_token_odds"]:.3f}',r['preferred']+' / '+r['first_token_preferred']] for r in sorted(rs,key=lambda r:(r['cue'],r['k']))])+'</details></details>')
parts.append('</div><p class="muted">End of audit. Existing frozen results remain intact; all changes above are explicitly labeled audit sensitivities or annotations.</p></main>')
payload=json.dumps(audit,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
parts.append('<script id="audit-data" type="application/json">'+payload+'</script>')
parts.append('''<script>
const cases=[...document.querySelectorAll('.case')],search=document.getElementById('search'),outcome=document.getElementById('outcome'),finding=document.getElementById('finding');
const searchTexts=cases.map(c=>c.textContent.toLowerCase());
function filter(){let count=0;const s=search.value.toLowerCase();cases.forEach((c,i)=>{const show=(!outcome.value||c.dataset.outcome===outcome.value)&&(!finding.value||c.dataset.findings.split(' ').includes(finding.value))&&(!s||searchTexts[i].includes(s));c.hidden=!show;if(show)count++;});document.getElementById('case-count').textContent=count+' of 112 cases';}
[search,outcome,finding].forEach(x=>x.addEventListener('input',filter));
document.getElementById('download').onclick=()=>{const b=new Blob([JSON.stringify(JSON.parse(document.getElementById('audit-data').textContent),null,2)],{type:'application/json'}),u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download='study2-v5-audit-data.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
function reveal(){if(location.hash.startsWith('#case-')){const c=document.getElementById(location.hash.slice(1));if(c){outcome.value='';finding.value='';search.value='';filter();c.open=true;c.scrollIntoView();}}}window.addEventListener('hashchange',reveal);reveal();
</script></body></html>''')
out=B/'study2-v5-trace-audit.html';out.write_text(''.join(parts))
print(json.dumps({'report':str(out),'bytes':out.stat().st_size,'counts':counts,'quotes_validated':True},indent=2))
