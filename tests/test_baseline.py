from pathlib import Path
import json,copy,io,zipfile,random,hashlib,re
import pytest,yaml
from jsonschema import Draft202012Validator,FormatChecker
from referencing import Registry,Resource
from reference.oracles import *
P=Path(__file__).resolve().parents[1]
SC=P/'contracts/schemas'
SCHEMAS={f.stem:json.loads(f.read_text()) for f in SC.glob('*.json')}
REG=Registry().with_resources((s['$id'],Resource.from_contents(s)) for s in SCHEMAS.values())
def validator(name):return Draft202012Validator(SCHEMAS[name],registry=REG,format_checker=FormatChecker())
@pytest.mark.parametrize('name',sorted(SCHEMAS))
def test_schema_and_examples(name):
 Draft202012Validator.check_schema(SCHEMAS[name]);v=validator(name)
 v.validate(json.loads((P/'contracts/examples'/(name+'.valid.json')).read_text()))
 assert list(v.iter_errors(json.loads((P/'contracts/examples'/(name+'.invalid.json')).read_text())))

def test_openapi_references_and_policies():
 api=yaml.safe_load((P/'contracts/openapi.yaml').read_text());pol=json.loads((P/'contracts/endpoint-policy.json').read_text())
 ids=[]
 def walk(x):
  if isinstance(x,dict):
   if '$ref' in x:assert x['$ref'].split('/')[-1] in api['components']['schemas']
   for v in x.values():walk(v)
  if isinstance(x,list):
   for v in x:walk(v)
 walk(api)
 for path,methods in api['paths'].items():
  for method,op in methods.items():
   ids.append(op['operationId']);assert op['security'];assert op['x-required-role']
   if method in ('post','put','delete'):assert any(p['name']=='Idempotency-Key' and p['required'] for p in op['parameters'])
   assert set(re.findall(r'{(\w+)}',path))=={p['name'] for p in op['parameters'] if p['in']=='path'}
 assert len(set(ids))==len(ids)==len(pol)

def test_metadata_capture_drops_credentials_and_free_text():
 assert redact({'name':'tool','api_key':'CANARY','authorization':'Bearer CANARY','reason':'CANARY','client':{'api_key':'CANARY'}})=={'name':'tool'}
 with pytest.raises(ValueError):redact({'name':{'nested':'CANARY'}})

def example_event():return json.loads((P/'contracts/examples/Event.valid.json').read_text())
def test_ingest_atomic_idempotency_conflicts():
 e=example_event();o=EventOracle();assert len(o.batch('p',[e])['accepted'])==1
 assert o.batch('p',[e])['duplicates']==[e['event_id']]
 bad=copy.deepcopy(e);bad['payload']={'name':'changed'}
 with pytest.raises(ValueError):o.batch('p',[bad])
 e2=copy.deepcopy(e);e2['event_id']='00000000-0000-4000-8000-000000000002';e2['producer_seq']=1
 conflict=copy.deepcopy(e2);conflict['event_id']='00000000-0000-4000-8000-000000000003';conflict['producer_seq']=0
 with pytest.raises(ValueError):o.batch('p',[e2,conflict])
 assert ('p',e2['event_id']) not in o.ids
 assert len(o.batch('other',[e])['accepted'])==1

def test_recorded_matching_has_no_live_fallback():
 r=[{'tool':'fetch','contract_hash':'a'*64,'args':{'x':1},'ordinal':i,'output':i} for i in range(2)]
 assert recorded_match(r,'fetch','a'*64,{'x':1},1)==1
 with pytest.raises(ValueError):recorded_match(r,'fetch','a'*64,{'x':2},1)

def zipped(name,body=b'hi',mode=None):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:
  e=zipfile.ZipInfo(name)
  if mode:e.external_attr=mode<<16
  z.writestr(e,body)
 return b.getvalue()
@pytest.mark.parametrize('name',['../escape','/absolute','a/../escape','C:/windows','a\\b','a//b','./x'])
def test_archive_rejects_paths(name):
 with pytest.raises(ValueError):archive_entries(zipped(name))
def test_archive_rejects_symlink_and_quota():
 with pytest.raises(ValueError):archive_entries(zipped('link',mode=0o120777))
 with pytest.raises(ValueError):archive_entries(zipped('ok',b'a'*100),max_expanded=10)
 assert archive_entries(zipped('folder/ok'))==['folder/ok']

def paired_fixture():return json.loads((P/'fixtures/paired_trials.json').read_text())
def test_statistics_known_effect_deterministic_and_clustered():
 d=paired_fixture();a=task_analysis(d['trials'],d['task_ids'],3);b=task_analysis(d['trials'],d['task_ids'],3)
 assert a==b;assert a['delta']==0.5;assert a['missing_trials']==0
 assert a['ci_low']<=0.5<=a['ci_high'];assert a['bound_low']==a['bound_high']==.5
 assert a['n_tasks']==12 and a['n_complete_tasks']==12

def test_statistics_missing_is_not_pass_or_silent_exclusion():
 d=paired_fixture();d['trials'][0]['outcome']='infra_error'
 a=task_analysis(d['trials'],d['task_ids'],3)
 assert a['status']=='partial';assert a['missing_trials']==1;assert a['bound_low']<a['bound_high'];assert a['n_complete_tasks']==11
 with pytest.raises(ValueError):task_analysis(d['trials']+[d['trials'][0]],d['task_ids'],3)

def test_statistics_tiny_no_inferential_claim():
 a=task_analysis([],['one'],3);assert a['status']=='insufficient';assert a['delta'] is None;assert a['ci_low'] is None;assert a['bound_low']==-1 and a['bound_high']==1

@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_geometry_roundtrip_and_orientation(rotation):
 crop=(-10,20,190,420);rng=random.Random(3)
 for _ in range(100):
  x=-10+rng.random()*200;y=20+rng.random()*400
  u,v=pdf_point(x,y,crop,rotation);xx,yy=inverse_pdf_point(u,v,crop,rotation)
  assert abs(xx-x)<1e-10 and abs(yy-y)<1e-10
 corners={0:(0,0),90:(1,0),180:(1,1),270:(0,1)}
 assert pdf_point(-10,420,crop,rotation)==corners[rotation]
 with pytest.raises(ValueError):pdf_point(-11,420,crop,rotation)

@pytest.mark.parametrize('raw,locale,scale,value',[('1,234','en','1000','1234000'),('(1,234.50)','en','1','-1234.50'),('1.234,50','de','1','1234.50'),('0','en','1','0')])
def test_number_semantics(raw,locale,scale,value):assert normalize_number(raw,locale,scale)['value']==value
@pytest.mark.parametrize('raw',['1,23','12x','1e5','NaN','(−3)','(+1)'])
def test_ambiguous_numbers_rejected(raw):
 with pytest.raises(ValueError):normalize_number(raw)
def test_dash_is_not_zero():assert normalize_number('—')['value'] is None

def test_source_evidence_real_and_tampered():
 d=json.loads((P/'fixtures/document-evidence.json').read_text());assert validate_evidence(d['evidence'],d['source'],d['parse'])
 assert hashlib.sha256((P/'fixtures/synthetic-report.pdf').read_bytes()).hexdigest()==d['source']['sha256']
 e=copy.deepcopy(d['evidence']);e['quote']='invented number'
 with pytest.raises(ValueError):validate_evidence(e,d['source'],d['parse'])
 e=copy.deepcopy(d['evidence']);e['region']['page_ordinal']=99
 with pytest.raises(ValueError):validate_evidence(e,d['source'],d['parse'])
 e=copy.deepcopy(d['evidence']);e['source_sha256']='0'*64
 with pytest.raises(ValueError):validate_evidence(e,d['source'],d['parse'])

@pytest.mark.parametrize('value',['=SUM(A1)',' @cmd','+1','-3','\t=1'])
def test_csv_formula_mitigation(value):assert csv_safe(value).startswith("'")

def test_runtime_profile_is_fail_closed():
 p=yaml.safe_load((P/'infra/runtime-policy.yaml').read_text())
 assert p['live_model_calls'] is False and p['untrusted_code_execution'] is False
 assert p['public_uploads'] is False and p['provider_credentials'] is False

def test_release_gate_refuses_unimplemented():
 from scripts.release_gate import evaluate
 result=evaluate(P/'evidence/release-status.json')
 assert result['ready'] is False
 assert 'application_e2e' in result['blocking'] and 'independent_security_review' in result['blocking']

def test_postgresql_syntax_only():
 from pglast import parse_sql
 for file in sorted((P/'database/migrations').glob('*.sql')):
  assert parse_sql(file.read_text())
 # Parsing is not applying migration or proving RLS/FK/transaction behavior.

def test_ui_operations_reference_api():
 ui=yaml.safe_load((P/'contracts/ui-workflows.yaml').read_text());ops={x['operation'] for x in json.loads((P/'contracts/endpoint-policy.json').read_text())}
 for s in ui['screens']:
  assert {'loading','empty','ready','denied','error','conflict','offline','partial'} <= set(s['states'])
  for a in s['actions']:assert a['operation_id'] in ops or a['operation_id']=='local_fixture'

def test_extraction_example_unique_keys():
 e=json.loads((P/'contracts/examples/Extraction.valid.json').read_text())
 assert len(set(f['key'] for f in e['fields']))==8
 assert all(f['value'] is None and f['missing_reason']=='unsupported' for f in e['fields'])
