"""Trusted-maintainer same-host receipts; not hostile same-UID secrecy attestation."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

if __package__:
    from . import trial_admission as ad, trial_reservation as reservation, promotion as gate
else:
    import trial_admission as ad, trial_reservation as reservation, promotion as gate
ev, p = ad.ev, ad.p
require, same = ad.require, ad.same


class Unavailable(ValueError):
    pass


def _closed(value, fields):
    require(ev.keys(value, fields), 'heldout_schema')


def _read(guard, path, digest=None):
    value = guard.json(path, private=True)
    require(digest is None or ev.sha(digest) and guard.files[Path(path)][0] == digest, 'heldout_changed')
    return value


def _stamp(value):
    require(isinstance(value,str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',value), 'heldout_time')
    datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ')
    return value


def _comment(ref):
    """One fixed bounded GitHub GET; no caller command, host, login or publication."""
    executable = shutil.which('gh')
    if executable is None: raise Unavailable('anchor_unavailable')
    env = dict(os.environ, GH_DEBUG='', GH_PROMPT_DISABLED='1', GH_NO_UPDATE_NOTIFIER='1', GH_PAGER='')
    argv = [executable,'api','--hostname','github.com','--method','GET',
            f"repos/{ref['repository']}/issues/comments/{ref['comment_id']}"]
    try: result = ad.nt.bounded(argv,5,limit=65536,env=env)
    except (OSError,subprocess.SubprocessError): raise Unavailable('anchor_unavailable') from None
    if result['exit'] or result['stop_reason'] or result['stderr']: raise Unavailable('anchor_unavailable')
    try: return json.loads(result['stdout'],object_pairs_hook=ev.no_duplicates)
    except (ValueError,TypeError): raise Unavailable('anchor_unavailable') from None


def _anchor(ref, payload):
    _closed(ref,'repository issue_number comment_id created_at body_sha256')
    require(isinstance(ref['repository'],str) and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',ref['repository'])
            and ev.integer(ref['issue_number'],1) and ev.integer(ref['comment_id'],1), 'heldout_anchor')
    created = _stamp(ref['created_at']); body = ev.encoded(payload).decode()
    require(hashlib.sha256(body.encode()).hexdigest() == ref['body_sha256'], 'heldout_anchor')
    value = _comment(ref)
    if not (isinstance(value,dict) and type(value.get('id')) is int and value['id'] == ref['comment_id']
        and value.get('issue_url') == f"https://api.github.com/repos/{ref['repository']}/issues/{ref['issue_number']}"
        and value.get('created_at') == value.get('updated_at') == created and value.get('body') == body):
        raise Unavailable('heldout_anchor_changed')
    return {k:value[k] for k in ('id','created_at','updated_at','body','issue_url')}


def preparation_message(pack_id, pack_path, requirements, behavior_categories):
    return 'Prepare a fresh held-out pack from these requirements and behavior categories only. Do not inspect candidate patches or author history. Keep cases and answers private; return only pack_id, pack_digest, grader_digest and schedule_digest.\n' + ev.encoded(dict(pack_id=pack_id,pack_path=pack_path,requirements=requirements,behavior_categories=behavior_categories)).decode()


def _prepare(path, source=None):
    guard = ad.Guard(); helper = guard.read(Path(__file__).resolve(),retain=False)[1]
    path = p.absolute(str(path),'heldout_path'); guard.directory(path.parent)
    m = _read(guard,path)
    _closed(m,'schema_version kind pack_id repository content source experiment contexts exposure preflight freeze record_digest')
    require(type(m['schema_version']) is int and m['schema_version']==1 and m['kind']=='same_host_heldout_evidence_v1'
        and ev.token(m['pack_id']) and m['record_digest']==ev.digest({k:v for k,v in m.items() if k!='record_digest'}), 'heldout_record')
    _closed(m['content'],'path sha256 pack_digest'); _closed(m['experiment'],'experiment_path spec_path context_path report_path attempts')
    _closed(m['contexts'],'author preparation tasks'); _closed(m['exposure'],'path'); _closed(m['preflight'],'path')
    x = m['experiment']; experiment = _read(guard,x['experiment_path']); spec = _read(guard,x['spec_path'])
    ctx = ad.load_context(experiment,spec,x['context_path']); pack = _read(guard,m['content']['path'],m['content']['sha256'])
    _closed(pack,'cases checks')
    require(same(pack,{k:spec[k] for k in ('cases','checks')}) and ev.digest(pack)==m['content']['pack_digest']
        and same(spec.get('evaluation_scope'),dict(kind='same_host_heldout',pack_digest=ev.digest(pack))), 'heldout_pack')
    if source is None:
        source = gate.verify_source(ctx,repository=m['repository'],**{k:m['source'][k] for k in ('baseline_commit','candidate_commit','component_roots')})
    require(same(source,m['source']), 'heldout_source')
    authors, author_hashes = [], []
    known_exposed = False
    require(isinstance(m['contexts']['author'],list) and 1<=len(m['contexts']['author'])<=8, 'heldout_authors')
    for ref in m['contexts']['author']:
        _closed(ref,'context_id input_evidence_path sha256'); value = _read(guard,ref['input_evidence_path'],ref['sha256'])
        _closed(value,'schema_version kind context_id workspace candidate_commit materials')
        require(type(value['schema_version']) is int and value['schema_version']==1 and value['kind']=='candidate_author_inputs_v1'
            and value['context_id']==ref['context_id'] and ev.text(ref['context_id'],256)
            and value['candidate_commit']==source['candidate_commit']
            and not p.absolute(m['content']['path'],'pack_path').resolve(strict=True).is_relative_to(p.absolute(value['workspace'],'workspace').resolve(strict=True))
            and isinstance(value['materials'],list) and len(value['materials'])<=64, 'heldout_author')
        for material in value['materials']:
            _closed(material,'kind path sha256')
            material_path = p.absolute(material['path'],'heldout_author')
            require(material['kind'] in ('requirements','development','source')
                and guard.read(material_path,p.MAX_FILE_BYTES,private=True,retain=False)[1]==material['sha256'], 'heldout_author')
            if (material_path.resolve(strict=True)==Path(m['content']['path']).resolve(strict=True)
                    or material['sha256']==m['content']['sha256']):
                known_exposed = True
        authors.append(ref['context_id']);author_hashes.append(ref['sha256'])
    require(len(authors)==len(set(authors)), 'heldout_authors')
    ref = m['contexts']['preparation'];_closed(ref,'context_id input_evidence_path sha256')
    d = _read(guard,ref['input_evidence_path'],ref['sha256'])
    _closed(d,'schema_version kind purpose source input dispatch returned output chronology receipt_digest')
    require(type(d['schema_version']) is int and d['schema_version']==1 and d['kind']=='same_host_fork_none_dispatch_v1'
        and d['purpose']=='heldout_preparation' and d['receipt_digest']==ev.digest({k:v for k,v in d.items() if k!='receipt_digest'}), 'heldout_dispatch')
    require(same(d['source'],dict(envelope_version='requirements-only-v1',helper_sha256=helper)), 'heldout_producer')
    inp,out,chron = d['input'],d['output'],d['chronology']
    _closed(inp,'requirements behavior_categories message_sha256 tool_call_evidence_path tool_call_evidence_sha256')
    _closed(out,'pack_id pack_digest grader_digest schedule_digest metadata_evidence_path metadata_evidence_sha256')
    _closed(chron,'candidate_freeze_anchor pack_creation_evidence_path pack_creation_evidence_sha256')
    _closed(d['returned'],'agent_id tool_result_evidence_path tool_result_evidence_sha256')
    require(same(d['dispatch'],dict(tool='collaboration.spawn_agent',task_name=d['dispatch']['task_name'],fork_turns='none'))
        and re.fullmatch(r'[a-z0-9_]{1,64}',d['dispatch']['task_name']), 'heldout_dispatch')
    texts = {}
    for kind in ('requirements','behavior_categories'):
        require(isinstance(inp[kind],list) and 1<=len(inp[kind])<=8, 'heldout_inputs');texts[kind]=[]
        for item in inp[kind]:
            _closed(item,'path sha256');raw,digest = guard.read(Path(item['path']),8192,private=True)
            require(digest==item['sha256'], 'heldout_inputs');texts[kind].append(raw.decode('utf-8'))
    message = preparation_message(m['pack_id'],m['content']['path'],**texts)
    require(hashlib.sha256(message.encode()).hexdigest()==inp['message_sha256'], 'heldout_message')
    call = _read(guard,inp['tool_call_evidence_path'],inp['tool_call_evidence_sha256'])
    returned = _read(guard,d['returned']['tool_result_evidence_path'],d['returned']['tool_result_evidence_sha256'])
    created = _read(guard,chron['pack_creation_evidence_path'],chron['pack_creation_evidence_sha256'])
    _closed(call,'tool arguments observed_at');_closed(returned,'tool agent_id task_name observed_at');_closed(created,'agent_id pack_id pack_digest observed_at')
    require(call['tool']=='collaboration.spawn_agent' and same(call['arguments'],dict(task_name=d['dispatch']['task_name'],fork_turns='none',message=message))
        and returned['tool']==call['tool'] and returned['task_name']==d['dispatch']['task_name']
        and returned['agent_id']==d['returned']['agent_id']==created['agent_id']==ref['context_id']
        and ev.text(ref['context_id'],256) and ref['context_id'] not in authors, 'heldout_fresh_context')
    expected = dict(pack_id=m['pack_id'],pack_digest=ev.digest(pack),grader_digest=spec['identities']['grader'],schedule_digest=ev.digest(experiment['trials']))
    require(same({k:out[k] for k in expected},expected)
        and same(_read(guard,out['metadata_evidence_path'],out['metadata_evidence_sha256']),expected)
        and created['pack_id']==m['pack_id'] and created['pack_digest']==ev.digest(pack), 'heldout_metadata_only')
    candidate_payload = dict(kind='committed_candidate_freeze_v1',source=source)
    candidate = _anchor(chron['candidate_freeze_anchor'],candidate_payload)
    require(_stamp(call['observed_at']) <= _stamp(created['observed_at']) <= _stamp(returned['observed_at']), 'heldout_chronology')
    if not candidate['created_at'] < call['observed_at']:raise Unavailable('heldout_anchor_order')
    payload = dict(kind='same_host_heldout_freeze_v1',**expected,experiment_digest=experiment['experiment_digest'],context_digest=ctx.digest,
        source=source,dispatch_receipt_digest=d['receipt_digest'],author_receipt_digests=author_hashes)
    anchor = _anchor(m['freeze'],payload)
    if not returned['observed_at'] <= anchor['created_at']:raise Unavailable('heldout_anchor_order')
    refs = x['attempts'];require(isinstance(refs,list) and len(refs)==len(experiment['trials'])<=64, 'heldout_tasks')
    for trial,ref in zip(experiment['trials'],refs):
        _closed(ref,'trial_id attempt_id attempt_path')
        require(ref['trial_id']==trial['trial_id'] and ev.token(ref['attempt_id'])
            and p.absolute(ref['attempt_path'],'attempt_path')==Path(ctx.data['execution_root'])/trial['trial_id']/ref['attempt_id'], 'heldout_tasks')
    expected_tasks = [{'trial_id':t['trial_id'],'attempt_id':r['attempt_id']} for t,r in zip(experiment['trials'],refs)]
    require(same(m['contexts']['tasks'],expected_tasks) and len({r['attempt_path'] for r in refs})==len(refs), 'heldout_tasks')
    require(not path.parent.is_relative_to(Path(ctx.data['execution_root']))
        and p.absolute(m['preflight']['path'],'preflight_path').parent==path.parent
        and p.absolute(m['exposure']['path'],'exposure_path').parent==path.parent, 'heldout_area')
    return m,ctx,guard,helper,[(chron['candidate_freeze_anchor'],candidate_payload,candidate),(m['freeze'],payload,anchor)],authors,known_exposed


def _preflight_value(m, ctx, helper, anchor, header):
    return dict(schema_version=1,kind='same_host_preflight_v1',record_digest=m['record_digest'],helper_digest=helper,
        anchor_digest=ev.digest(anchor),header_digest=ev.digest(header),reserved_initial_turns=0)


def assess(path, development, development_report, source):
    """Verify selected receipts and actual typed records; unknown FS reads stay separate."""
    batch = None
    result = dict(status='inconclusive',reasons=['heldout_unavailable'],claim=None,
        filesystem_access='unrestricted_or_unknown',unobserved_filesystem_reads='unknown',
        trust_boundary='selected_trusted_maintainer_receipts',future_classification='same_host_heldout')
    try:
        m,ctx,guard,helper,anchors,authors,known_exposed = _prepare(path,source)
        require(same(ctx.spec['identities'],development.context.spec['identities']) and same(ctx.spec['runtime'],development.context.spec['runtime'])
            and all(same(ctx.spec[k],development.context.spec[k]) for k in ('primary_metric','regression_margin','promotion_rule'))
            and ctx.data.get('execution_root')!=development.context.data.get('execution_root'), 'heldout_comparison_binding')
        require('evaluation_scope' not in development.context.spec
            and development_report.get('classification')=='development'
            and development_report.get('evidence_kind')=='native_artifact_development_comparison', 'development_scope_required')
        # Stable category IDs may repeat; an already-visible task may not.
        def contents(spec):
            return {ev.digest(part['inputs']) for case in spec['cases'] for part in (case,case['counterpart'])}
        require(not contents(ctx.spec).intersection(contents(development.context.spec)), 'heldout_cases_overlap')
        batch = ad.read_attempts(ctx,m['experiment']['attempts'])
        report = ev.compare(ctx.experiment,[],ctx.spec,native=batch)
        require(same(_read(guard,m['experiment']['report_path']),report), 'heldout_report')
        require(batch.execution_lease is not None, 'heldout_reservation')
        header = batch.execution_lease.header
        require(same(_read(guard,m['preflight']['path']),_preflight_value(m,ctx,helper,anchors[-1][2],header)), 'heldout_preflight')
        exposure = _read(guard,m['exposure']['path']);_closed(exposure,'schema_version kind events')
        require(type(exposure['schema_version']) is int and exposure['schema_version']==1 and exposure['kind']=='same_host_exposure_v1'
            and isinstance(exposure['events'],list) and len(exposure['events'])<=256, 'heldout_exposure')
        exposed,unknown = known_exposed,False
        for event in exposure['events']:
            _closed(event,'context_id material phase')
            require(ev.text(event['context_id'],256) and event['material'] in ('pack','case','answer','pack_read','aggregate_feedback','candidate_edit','unknown_delivery')
                and event['phase'] in ('before_comparison','during_comparison','after_comparison'), 'heldout_exposure')
            if event['material']=='candidate_edit': raise ev.Invalid('heldout_candidate_edited')
            if event['context_id'] in authors:
                result['future_classification']='development_regression'
                if event['phase'] in ('before_comparison','during_comparison'):
                    unknown |= event['material']=='unknown_delivery';exposed |= event['material']!='unknown_delivery'
        metrics = gate.evaluate_rule(ctx.experiment,report);metrics['scope']='source_guarded_same_host_heldout_rule_diagnostic'
        allowed = {'diagnostic_only','same_host_heldout_unimplemented','same_host_heldout_unverified'}
        blockers = sorted((set(report['blockers'])-allowed) | (set(development_report['blockers'])-{'diagnostic_only','same_host_heldout_unimplemented'}))
        require(guard.check() and ctx.guard.check() and batch.guard.check(), 'heldout_changed')
        for ref,payload,value in anchors:
            if not same(_anchor(ref,payload),value):raise Unavailable('heldout_anchor_changed')
        require(guard.check() and ctx.guard.check() and batch.guard.check(), 'heldout_changed')
        if not batch.valid(ctx.experiment,ctx.spec) or not development.valid(development.context.experiment,development.context.spec):
            blockers.append('heldout_native_unavailable')
        if not batch.observed_models_complete() or not development.observed_models_complete():blockers.append('heldout_model_unavailable')
        if batch.execution is None or batch.execution.get('status')!='complete' or development.execution is None or development.execution.get('status')!='complete':blockers.append('heldout_reservation_incomplete')
        result.update(rule_result=metrics,report_digest=report['report_digest'],record_digest=m['record_digest'],reasons=sorted(set(blockers)))
        if exposed:result.update(status='exposed',reasons=['heldout_exposed'])
        elif unknown:result.update(status='inconclusive',reasons=['heldout_delivery_unknown'])
        elif blockers:result['status']='inconclusive'
        else:result.update(status='verified',claim='not_supplied_to_recorded_author_context_during_comparison')
        require(guard.check() and ctx.guard.check() and batch.guard.check(), 'heldout_changed')
        if known_exposed:result['future_classification']='development_regression'
    except Unavailable as error:
        reason = str(error) if str(error) in ('anchor_unavailable','heldout_anchor_changed','heldout_anchor_order') else 'heldout_unavailable'
        result.update(status='inconclusive',reasons=[reason])
    except OSError:pass
    except (ValueError,TypeError,KeyError,RecursionError) as error:
        reason = str(error) if str(error) in ('heldout_cases_overlap','development_scope_required') else 'invalid_heldout_evidence'
        result.update(status='invalid',reasons=[reason],claim=None)
    finally:
        if batch is not None:batch.close()
    return result


def run_next(record_path, plan_path, auth_source):
    """Preflight under existing lease, then delegate ONLY to the fixed serial gate."""
    m,ctx,guard,helper,anchors,_,known_exposed = _prepare(record_path)
    require(not known_exposed, 'heldout_exposed')
    require(ctx.qualification_error is None, 'qualification_unavailable')
    path = Path(m['preflight']['path']);lease = reservation.Lease(ctx)
    try:
        summary,records,_ = reservation.audit(lease)
        expected = _preflight_value(m,ctx,helper,anchors[-1][2],lease.header)
        if not path.exists():
            require(summary['reserved_initial_turns']==0 and summary['status']=='ready', 'heldout_preflight_late')
            require(lease.check() and records.check() and guard.check(), 'heldout_changed')
            ad.nt.private_write(path,ev.encoded(expected))
        require(same(_read(guard,path),expected) and lease.check() and guard.check(), 'heldout_preflight')
    finally:lease.close()
    for ref,payload,value in anchors:
        if not same(_anchor(ref,payload),value):raise Unavailable('heldout_anchor_changed')
    require(guard.check() and ctx.guard.check(), 'heldout_changed')
    return reservation.run_next(ctx.data['execution_root'],ctx.experiment,ctx.spec,m['experiment']['context_path'],plan_path,auth_source)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('run-next',))
    parser.add_argument('--record',required=True);parser.add_argument('--plan',required=True);parser.add_argument('--auth-source',required=True)
    args=parser.parse_args()
    try:
        result=run_next(args.record,args.plan,Path(args.auth_source));print(ev.encoded(result).decode(),end='');return 0
    except (OSError,ValueError,KeyError,TypeError,RecursionError,subprocess.SubprocessError):
        print('{"status":"refused","reason":"heldout_preflight_unavailable"}');return 2


if __name__=='__main__':raise SystemExit(main())
