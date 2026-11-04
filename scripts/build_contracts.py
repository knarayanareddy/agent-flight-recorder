"""Generate normative v0.2 contracts. Regenerate with: python scripts/build_contracts.py."""
from pathlib import Path
import json, yaml
P=Path(__file__).resolve().parents[1]
SC=P/'contracts/schemas'
def obj(props,required=None,**extra):return {'type':'object','properties':props,'required':list(props) if required is None else required,'additionalProperties':False,**extra}
def arr(items,**kw):return {'type':'array','items':items,**kw}
def enum(*v):return {'type':'string','enum':list(v)}
def st(**kw):return {'type':'string',**kw}
def ref(n):return {'$ref':n+'.json'}
UUID=st(format='uuid');TIME=st(format='date-time');HASH=st(pattern='^[a-f0-9]{64}$');DEC=st(pattern=r'^-?(0|[1-9][0-9]*)(\.[0-9]+)?$');N={'type':'integer','minimum':0};POS={'type':'integer','minimum':1};BOOL={'type':'boolean'}
S={}
S['Problem']=obj({'type':st(format='uri'),'title':st(),'status':{'type':'integer','minimum':400,'maximum':599},'code':enum('invalid','unauthenticated','forbidden','not_found','conflict','precondition_failed','too_large','unsupported_media','quota','unavailable','mode_disabled'),'detail':st(maxLength=1000),'request_id':UUID,'field_errors':arr(obj({'path':st(),'code':st()}))},['type','title','status','code','detail','request_id'])
S['Empty']=obj({})
S['PageQuery']=obj({'limit':{'type':'integer','minimum':1,'maximum':100},'cursor':st(maxLength=2048)},[])
S['Actor']=obj({'user_id':UUID,'organization_id':UUID,'roles':arr(enum('viewer','analyst','operator','maintainer','admin'),minItems=1,uniqueItems=True)})
S['ProjectCreate']=obj({'name':st(minLength=1,maxLength=120),'content_capture':enum('metadata_only','redacted'),'external_transfer':BOOL})
S['Project']=obj({'id':UUID,'name':st(),'content_capture':enum('metadata_only','redacted'),'external_transfer':BOOL,'revision':POS,'created_at':TIME})
S['UploadCreate']=obj({'filename':st(minLength=1,maxLength=200),'media_type':enum('application/pdf','application/json','application/zip','text/plain'),'byte_size':{'type':'integer','minimum':1,'maximum':104857600},'sha256':HASH,'classification':enum('synthetic','public_authorized','sensitive')})
S['Upload']=obj({'id':UUID,'artifact_id':UUID,'put_path':st(pattern='^/api/v1/'),'expires_at':TIME,'maximum_bytes':POS})
S['UploadFinalize']=obj({'sha256':HASH,'byte_size':POS})
S['Artifact']=obj({'id':UUID,'project_id':UUID,'sha256':HASH,'byte_size':POS,'media_type':st(),'status':enum('pending','ready','quarantined','deleting','deleted'),'classification':enum('synthetic','public_authorized','sensitive'),'created_at':TIME})
S['Job']=obj({'id':UUID,'project_id':UUID,'kind':st(),'state':enum('queued','leased','running','cancel_requested','succeeded','failed','timed_out','cancelled','failed_unknown_effect'),'attempt':N,'revision':POS,'created_at':TIME,'result_id':{'type':['string','null'],'format':'uuid'},'error_code':{'type':['string','null']}})
S['Deletion']=obj({'id':UUID,'state':enum('requested','revoked','purging','complete','failed'),'revoked_at':TIME,'purge_deadline':TIME,'affected_artifacts':N})
S['EventPayload']=obj({'operation_id':UUID,'name':st(maxLength=120),'outcome':enum('success','failure','unknown'),'input_tokens':N,'output_tokens':N,'content_artifact_id':UUID,'redacted':BOOL,'reason':st(maxLength=500),'missing_sequence_start':N,'missing_sequence_end':N},[])
S['Event']=obj({'schema_version':{'const':'afr-event/1'},'event_id':UUID,'run_id':UUID,'producer_id':st(minLength=1,maxLength=100),'producer_seq':N,'event_type':enum('run.started','run.finished','model.requested','model.responded','tool.requested','tool.responded','tool.failed','capture.dropped','approval.decided'),'observed_at':TIME,'capture_policy_id':UUID,'parent_event_id':{'type':['string','null'],'format':'uuid'},'payload':ref('EventPayload')},['schema_version','event_id','run_id','producer_id','producer_seq','event_type','observed_at','capture_policy_id','payload'])
S['EventBatch']=obj({'events':arr(ref('Event'),minItems=1,maxItems=500)})
S['BatchReceipt']=obj({'accepted':arr(UUID),'duplicates':arr(UUID),'request_id':UUID})
S['Run']=obj({'id':UUID,'project_id':UUID,'state':enum('recording','completed','failed','abandoned'),'revision':POS,'event_count':N,'completeness':arr(enum('sequence_gap','missing_terminal','orphan','content_not_captured','truncated'),uniqueItems=True),'verified_outcome':enum('unscored','pass','fail','error'),'created_at':TIME})
S['Check']=obj({'kind':enum('json_equals','forbidden_tool','mock_state_equals'),'path':st(maxLength=200),'expected':{'type':['string','number','boolean','object','array','null']}},['kind','path','expected'])
S['CaseCreate']=obj({'run_id':UUID,'run_revision':POS,'name':st(minLength=1,maxLength=120),'mode':enum('visual','recorded'),'checks':arr(ref('Check'),minItems=1,maxItems=100),'fixture_artifact_ids':arr(UUID,maxItems=100)})
S['Case']=obj({'id':UUID,'project_id':UUID,'schema_version':{'const':'afr-case/1'},'version':POS,'manifest_sha256':HASH,'definition':ref('CaseCreate'),'created_at':TIME})
S['ReplayCreate']=obj({'case_id':UUID,'case_version':POS,'mode':enum('visual','recorded'),'maximum_seconds':{'type':'integer','minimum':1,'maximum':300}})
S['ReplayResult']=obj({'id':UUID,'job_id':UUID,'case_id':UUID,'state':enum('pass','fail','error','unscored'),'network_calls':{'const':0},'checks':arr(obj({'index':N,'outcome':enum('pass','fail','error'),'reason':st(maxLength=500)})),'manifest_sha256':HASH})
S['PackageCreate']=obj({'artifact_id':UUID,'name':st(minLength=1,maxLength=120),'source_commit':st(pattern='^[a-f0-9]{40}$'),'license_expression':st(maxLength=200)},['artifact_id','name'])
S['Package']=obj({'id':UUID,'project_id':UUID,'artifact_id':UUID,'sha256':HASH,'state':enum('quarantined','inspected','approved','rejected'),'execution_profile':{'const':'fixture_only'},'revision':POS})
S['PackageReview']=obj({'decision':enum('approved','rejected'),'package_sha256':HASH,'reason':st(minLength=5,maxLength=1000)})
S['Task']=obj({'id':st(minLength=1,maxLength=100),'category':st(maxLength=100),'input_artifact_id':UUID,'split':enum('development','validation','holdout'),'scorer_id':st(minLength=1,maxLength=100)})
S['SuiteCreate']=obj({'name':st(minLength=1,maxLength=120),'tasks':arr(ref('Task'),minItems=1,maxItems=1000),'rights_manifest_artifact_id':UUID})
S['Suite']=obj({'id':UUID,'project_id':UUID,'sha256':HASH,'version':POS,'task_count':POS,'created_at':TIME})
S['PlanCreate']=obj({'package_id':UUID,'package_sha256':HASH,'suite_id':UUID,'suite_sha256':HASH,'harness':{'const':'fixture/1'},'model':{'const':'recorded/1'},'repetitions':{'type':'integer','minimum':1,'maximum':20},'seed':N,'bootstrap_iterations':{'type':'integer','minimum':100,'maximum':10000},'practical_margin':{'type':'number','minimum':0,'maximum':1},'primary_metric':{'const':'task_mean_success_delta'},'missing_rule':{'const':'report_bounds_no_silent_drop'},'mode':{'const':'fixture_only'}})
S['Plan']=obj({'id':UUID,'project_id':UUID,'sha256':HASH,'state':enum('draft','preregistered'),'revision':POS,'definition':ref('PlanCreate'),'created_at':TIME})
S['Trial']=obj({'task_id':st(),'repeat':N,'arm':enum('baseline','treatment'),'outcome':enum('pass','fail','infra_error','policy_block','activation_failed','cancelled'),'cost':{'anyOf':[DEC,{'type':'null'}]},'currency':{'const':'EUR'},'attempt':POS,'trace_artifact_id':UUID},['task_id','repeat','arm','outcome','cost','currency','attempt'])
S['ExperimentCreate']=obj({'plan_id':UUID,'plan_sha256':HASH})
S['Experiment']=obj({'id':UUID,'project_id':UUID,'plan_id':UUID,'plan_sha256':HASH,'state':enum('queued','running','completed','stopped','failed'),'job_id':UUID,'created_at':TIME})
S['Analysis']=obj({'id':UUID,'experiment_id':UUID,'analysis_version':{'const':'paired-task-bootstrap/1'},'input_sha256':HASH,'status':enum('valid','partial','insufficient'),'n_tasks':N,'n_complete_tasks':N,'delta':{'type':['number','null'],'minimum':-1,'maximum':1},'ci_low':{'type':['number','null'],'minimum':-1,'maximum':1},'ci_high':{'type':['number','null'],'minimum':-1,'maximum':1},'bound_low':{'type':['number','null'],'minimum':-1,'maximum':1},'bound_high':{'type':['number','null'],'minimum':-1,'maximum':1},'interpretation':{'const':'descriptive_no_certification'},'missing_trials':N})
S['DocumentCreate']=obj({'artifact_id':UUID,'title':st(minLength=1,maxLength=200)})
S['Document']=obj({'id':UUID,'project_id':UUID,'version':POS,'source_sha256':HASH,'source_artifact_id':UUID,'title':st(),'state':enum('quarantined','accepted','parsing','parsed','partial','failed','deleting'),'page_count':{'type':['integer','null'],'minimum':1,'maximum':100},'created_at':TIME})
S['ParseCreate']=obj({'profile':enum('fixture/1','docling_local/1'),'source_sha256':HASH})
S['Parse']=obj({'id':UUID,'document_id':UUID,'source_sha256':HASH,'profile':enum('fixture/1','docling_local/1'),'profile_sha256':HASH,'state':enum('queued','running','parsed','partial','failed'),'job_id':UUID,'page_count':N,'created_at':TIME})
S['Region']=obj({'page_ordinal':POS,'page_label':st(maxLength=50),'x0':{'type':'number','minimum':0,'maximum':1},'y0':{'type':'number','minimum':0,'maximum':1},'x1':{'type':'number','minimum':0,'maximum':1},'y1':{'type':'number','minimum':0,'maximum':1}},['page_ordinal','x0','y0','x1','y1'])
S['Evidence']=obj({'document_id':UUID,'source_sha256':HASH,'parse_id':UUID,'element_id':st(minLength=1,maxLength=100),'region':ref('Region'),'quote':st(maxLength=10000),'method':enum('digital_text','ocr_text','manual_image'),'support':enum('supported_exact','supported_normalized','ambiguous','unsupported','source_unavailable')})
S['Field']=obj({'key':enum('entity','period_end','currency','scale','revenue_current','revenue_prior','assets_current','assets_prior'),'raw':{'type':['string','null']},'value':{'type':['string','null']},'currency':{'type':['string','null'],'pattern':'^[A-Z]{3}$'},'scale':{'enum':['1','1000','1000000',None]},'period_end':{'type':['string','null'],'format':'date'},'missing_reason':{'enum':['not_present','unreadable','ambiguous','unsupported','parse_failed',None]},'evidence':arr(ref('Evidence'),maxItems=20),'review_state':enum('unreviewed','accepted','corrected','rejected','needs_review'),'risk_flags':arr(enum('unit_ambiguous','period_ambiguous','support_mismatch','arithmetic_discrepancy','wrong_row','parse_warning'),uniqueItems=True)})
S['ExtractionCreate']=obj({'schema_version':{'const':'annual-report-8/1'},'method':enum('fixture','deterministic'),'parse_id':UUID})
S['Extraction']=obj({'id':UUID,'project_id':UUID,'parse_id':UUID,'schema_version':{'const':'annual-report-8/1'},'revision':POS,'fields':arr(ref('Field'),minItems=8,maxItems=8),'created_at':TIME})
S['ReviewPatch']=obj({'key':st(),'action':enum('accept','correct','reject'),'value':{'type':['string','null']},'currency':{'type':['string','null']},'scale':{'type':['string','null']},'period_end':{'type':['string','null']},'evidence':arr(ref('Evidence')),'reason':st(minLength=5,maxLength=1000)},['key','action','reason'])
S['ReviewCreate']=obj({'base_revision':POS,'patches':arr(ref('ReviewPatch'),minItems=1,maxItems=8)})
S['Review']=obj({'id':UUID,'extraction_id':UUID,'revision':POS,'base_revision':POS,'actor_id':UUID,'created_at':TIME,'patches':arr(ref('ReviewPatch'))})
S['ExportCreate']=obj({'review_revision':POS,'format':enum('json','csv'),'allow_incomplete':BOOL})
S['Export']=obj({'id':UUID,'project_id':UUID,'extraction_id':UUID,'review_revision':POS,'artifact_id':UUID,'manifest_sha256':HASH,'incomplete':BOOL,'warnings':arr(st(maxLength=500)),'created_at':TIME})
for name,s in S.items():
    full={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://baseline.invalid/schemas/'+name+'.json','title':name,**s}
    (SC/(name+'.json')).write_text(json.dumps(full,indent=2)+'\n')
# OpenAPI uses these exact JSON Schema definitions. Generated clients must not replace objects with any.
def api_schema(x):
    if isinstance(x,dict):
        return {k:('#/components/schemas/'+v[:-5] if k=='$ref' and v.endswith('.json') else api_schema(v)) for k,v in x.items()}
    if isinstance(x,list):return [api_schema(v) for v in x]
    return x
components={n:api_schema(s) for n,s in S.items()}
for n in ['Project','Artifact','Run','Event','Case','Package','Suite','Plan','Experiment','Trial','Document','Parse','Extraction','Review','Export']:
    components[n+'Page']=obj({'items':arr({'$ref':'#/components/schemas/'+n},maxItems=100),'next_cursor':{'type':['string','null']}})
paths={};policy=[]
def endpoint(method,path,operation,request,response,role='viewer',status=200,conditional=False,binary=False):
    params=[]
    if path != '/api/v1/projects' and '{project_id}' not in path:
        params.append({'name':'X-Project-ID','in':'header','required':True,'schema':UUID})
    for key in __import__('re').findall(r'{(\w+)}',path):params.append({'name':key,'in':'path','required':True,'schema':UUID})
    if method=='get' and response.endswith('Page'):
        params += [{'name':'limit','in':'query','schema':{'type':'integer','default':50,'minimum':1,'maximum':100}},{'name':'cursor','in':'query','schema':st(maxLength=2048)}]
    if method in ['post','put','delete']:
        params.append({'name':'Idempotency-Key','in':'header','required':True,'schema':UUID})
    if conditional:params.append({'name':'If-Match','in':'header','required':True,'schema':st(pattern='^"[1-9][0-9]*"$')})
    content={'application/json':{'schema':{'$ref':'#/components/schemas/'+response}}}
    if binary:content={'application/octet-stream':{'schema':{'type':'string','format':'binary'}}}
    responses={str(status):{'description':'Successful operation. ETag on revisioned resources.','headers':{'X-Request-ID':{'schema':UUID},'ETag':{'schema':st()}},'content':content}}
    for code in [400,401,403,404,409,412,413,415,422,428,429,503]:responses[str(code)]={'description':'See Problem.code and normative behavior matrix.','content':{'application/problem+json':{'schema':{'$ref':'#/components/schemas/Problem'}}}}
    op={'operationId':operation,'tags':[operation.split('_')[0]],'security':[{'sessionCookie':[]},{'apiKey':[]}],'parameters':params,'responses':responses,'x-required-role':role,'x-project-authorization':'resolve parent resource on every call','x-content-access':role!='viewer'}
    if request:op['requestBody']={'required':True,'content':{'application/json':{'schema':{'$ref':'#/components/schemas/'+request}}}}
    paths.setdefault(path,{})[method]=op;policy.append({'operation':operation,'method':method.upper(),'path':path,'role':role,'if_match':conditional,'request':request,'response':response,'success':status})
B='/api/v1';PR=B+'/projects/{project_id}'
endpoint('post',B+'/projects','foundation_create_project','ProjectCreate','Project','admin',201)
endpoint('get',B+'/projects','foundation_list_projects',None,'ProjectPage')
endpoint('post',PR+'/uploads','foundation_create_upload','UploadCreate','Upload','analyst',201)
# Upload bytes is a separate endpoint, no JSON request schema.
endpoint('put',B+'/uploads/{upload_id}/bytes','foundation_put_upload',None,'Empty','analyst')
paths[B+'/uploads/{upload_id}/bytes']['put']['requestBody']={'required':True,'content':{'application/octet-stream':{'schema':{'type':'string','format':'binary'}}}}
endpoint('post',B+'/uploads/{upload_id}:finalize','foundation_finalize_upload','UploadFinalize','Artifact','analyst')
endpoint('get',B+'/artifacts/{artifact_id}','foundation_get_artifact',None,'Artifact','analyst')
endpoint('get',B+'/artifacts/{artifact_id}/bytes','foundation_download_artifact',None,'Artifact','analyst',binary=True)
endpoint('get',B+'/jobs/{job_id}','foundation_get_job',None,'Job')
endpoint('post',B+'/jobs/{job_id}:cancel','foundation_cancel_job','Empty','Job','operator',202)
endpoint('post',PR+'/afr/events:batch','afr_ingest_events','EventBatch','BatchReceipt','operator',202)
endpoint('get',PR+'/afr/runs','afr_list_runs',None,'RunPage')
endpoint('get',B+'/afr/runs/{run_id}','afr_get_run',None,'Run')
endpoint('get',B+'/afr/runs/{run_id}/events','afr_list_events',None,'EventPage','analyst')
endpoint('post',PR+'/afr/cases','afr_create_case','CaseCreate','Case','analyst',201)
endpoint('get',B+'/afr/cases/{case_id}','afr_get_case',None,'Case','analyst')
endpoint('post',PR+'/afr/replays','afr_create_replay','ReplayCreate','Job','operator',202)
endpoint('get',B+'/afr/replays/{replay_id}','afr_get_replay',None,'ReplayResult','analyst')
endpoint('post',PR+'/skb/packages','skb_create_package','PackageCreate','Package','analyst',201)
endpoint('get',B+'/skb/packages/{package_id}','skb_get_package',None,'Package','analyst')
endpoint('post',B+'/skb/packages/{package_id}:inspect','skb_inspect_package','Empty','Job','operator',202)
endpoint('post',B+'/skb/packages/{package_id}/reviews','skb_review_package','PackageReview','Package','maintainer',200,True)
endpoint('post',PR+'/skb/suites','skb_create_suite','SuiteCreate','Suite','maintainer',201)
endpoint('get',B+'/skb/suites/{suite_id}','skb_get_suite',None,'Suite','analyst')
endpoint('post',PR+'/skb/plans','skb_create_plan','PlanCreate','Plan','analyst',201)
endpoint('get',B+'/skb/plans/{plan_id}','skb_get_plan',None,'Plan','analyst')
endpoint('post',B+'/skb/plans/{plan_id}:preregister','skb_preregister','Empty','Plan','maintainer',200,True)
endpoint('post',PR+'/skb/experiments','skb_create_experiment','ExperimentCreate','Experiment','operator',202)
endpoint('get',B+'/skb/experiments/{experiment_id}','skb_get_experiment',None,'Experiment')
endpoint('get',B+'/skb/experiments/{experiment_id}/trials','skb_list_trials',None,'TrialPage','analyst')
endpoint('post',B+'/skb/experiments/{experiment_id}/analyses','skb_create_analysis','Empty','Analysis','analyst',201)
endpoint('get',B+'/skb/analyses/{analysis_id}','skb_get_analysis',None,'Analysis','analyst')
endpoint('post',PR+'/evf/documents','evf_create_document','DocumentCreate','Document','analyst',201)
endpoint('get',PR+'/evf/documents','evf_list_documents',None,'DocumentPage')
endpoint('get',B+'/evf/documents/{document_id}','evf_get_document',None,'Document','analyst')
endpoint('post',B+'/evf/documents/{document_id}/parses','evf_create_parse','ParseCreate','Parse','operator',202)
endpoint('get',B+'/evf/parses/{parse_id}','evf_get_parse',None,'Parse','analyst')
endpoint('post',PR+'/evf/extractions','evf_create_extraction','ExtractionCreate','Extraction','analyst',201)
endpoint('get',B+'/evf/extractions/{extraction_id}','evf_get_extraction',None,'Extraction','analyst')
endpoint('post',B+'/evf/extractions/{extraction_id}/reviews','evf_create_review','ReviewCreate','Review','analyst',201,True)
endpoint('get',B+'/evf/extractions/{extraction_id}/reviews','evf_list_reviews',None,'ReviewPage','analyst')
endpoint('post',B+'/evf/extractions/{extraction_id}/exports','evf_create_export','ExportCreate','Export','analyst',201)
endpoint('get',B+'/evf/exports/{export_id}','evf_get_export',None,'Export','analyst')
endpoint('delete',B+'/evf/documents/{document_id}','evf_delete_document',None,'Deletion','maintainer',202)
endpoint('get',PR+'/afr/cases','afr_list_cases',None,'CasePage','analyst')
endpoint('get',PR+'/skb/packages','skb_list_packages',None,'PackagePage','analyst')
endpoint('get',PR+'/skb/suites','skb_list_suites',None,'SuitePage','analyst')
endpoint('get',PR+'/skb/plans','skb_list_plans',None,'PlanPage','analyst')
endpoint('get',PR+'/skb/experiments','skb_list_experiments',None,'ExperimentPage')
api={'openapi':'3.1.0','info':{'title':'Three-product bounded baseline','version':'0.2.0','description':'Normative bounded release. Products are NOT implemented. Live arbitrary code/models disabled.'},'servers':[{'url':'/'}],'paths':paths,'components':{'securitySchemes':{'sessionCookie':{'type':'apiKey','in':'cookie','name':'__Host-baseline-session'},'apiKey':{'type':'apiKey','in':'header','name':'X-API-Key'}},'schemas':components}}
(P/'contracts/openapi.yaml').write_text(yaml.safe_dump(api,sort_keys=False))
(P/'contracts/endpoint-policy.json').write_text(json.dumps(policy,indent=2))
(P/'contracts/schema-index.json').write_text(json.dumps(sorted(S),indent=2))
print(len(S),'schemas;',len(policy),'API operations')
