from pathlib import Path
import json,uuid,copy
P=Path(__file__).resolve().parents[1];SC=P/'contracts/schemas'
uid='00000000-0000-4000-8000-000000000001';sha='a'*64

def sample(s):
 if '$ref' in s:return sample(json.loads((SC/s['$ref']).read_text()))
 if 'const' in s:return s['const']
 if 'enum' in s:return s['enum'][0]
 if 'anyOf' in s:return sample(s['anyOf'][0])
 t=s.get('type');t=t[0] if isinstance(t,list) else t
 if t=='object':return {k:sample(s['properties'][k]) for k in s.get('required',[])}
 if t=='array':return [sample(s['items']) for _ in range(s.get('minItems',0))]
 if t=='boolean':return False
 if t in ('number','integer'):return s.get('minimum',0)
 if t=='null':return None
 if t=='string':
  if s.get('format')=='uuid':return uid
  if s.get('format')=='date-time':return '2026-11-03T12:00:00Z'
  if s.get('format')=='date':return '2026-10-31'
  if s.get('format')=='uri':return 'https://baseline.invalid/problems/invalid'
  pattern=s.get('pattern','')
  if '[a-f0-9]{64}' in pattern:return sha
  if '[a-f0-9]{40}' in pattern:return 'b'*40
  if '[A-Z]{3}' in pattern:return 'EUR'
  if pattern.startswith('^-?'):return '0'
  if pattern.startswith('^/api'):return '/api/v1/uploads/'+uid+'/bytes'
  return 'x'*max(1,s.get('minLength',1))
 raise ValueError(s)
for f in SC.glob('*.json'):
 value=sample(json.loads(f.read_text()));(P/'contracts/examples'/(f.stem+'.valid.json')).write_text(json.dumps(value,indent=2))
 invalid=copy.deepcopy(value);invalid['undeclared_field']='must be rejected'
 (P/'contracts/examples'/(f.stem+'.invalid.json')).write_text(json.dumps(invalid,indent=2))
trials=[];tasks=['task-%02d'%i for i in range(12)]
for i,t in enumerate(tasks):
 for r in range(3):
  for arm in ['baseline','treatment']:
   passed=(i%2==0) or arm=='treatment'
   trials.append({'task_id':t,'repeat':r,'arm':arm,'outcome':'pass' if passed else 'fail','cost':'0','currency':'EUR','attempt':1})
(P/'fixtures/paired_trials.json').write_text(json.dumps({'task_ids':tasks,'repetitions':3,'trials':trials,'expected_delta':0.5,'expected_missing':0,'rights':'Synthetic authored fixture; no personal or third-party data.'},indent=2))
# A tiny valid synthetic PDF, authored here with no third-party document rights.
text='Synthetic annual report FY 2025 | Entity: Example Labs | Revenue: 1,234 | Assets: 5,678 | Currency EUR; units 1000'
stream=('BT /F1 12 Tf 50 740 Td ('+text.replace('(','\\(').replace(')','\\)')+') Tj ET').encode()
objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
pdf=b'%PDF-1.4\n';offsets=[0]
for i,o in enumerate(objects,1):offsets.append(len(pdf));pdf+=f'{i} 0 obj\n'.encode()+o+b'\nendobj\n'
xref=len(pdf);pdf+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{n:010} 00000 n \n'.encode() for n in offsets[1:]);pdf+=f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
(P/'fixtures/synthetic-report.pdf').write_bytes(pdf)
region={'page_ordinal':1,'x0':0.1,'y0':0.1,'x1':0.9,'y1':0.2}
import hashlib
source={'document_id':uid,'sha256':hashlib.sha256(pdf).hexdigest(),'page_count':1}
parse={'id':uid,'elements':{'e1':{'page_ordinal':1,'region':region,'text':text}}}
evidence={'document_id':uid,'source_sha256':source['sha256'],'parse_id':uid,'element_id':'e1','region':region,'quote':'Revenue: 1,234','method':'digital_text','support':'supported_exact'}
(P/'fixtures/document-evidence.json').write_text(json.dumps({'source':source,'parse':parse,'evidence':evidence,'rights':'Synthetic document authored for this baseline. No real issuer or personal data.','note':'Regions are synthetic acceptance-fixture metadata, NOT actual Docling extraction output.'},indent=2))
print('Generated schema examples, 72 paired trials and synthetic source evidence')

# Structurally and semantically safe extraction sample: explicit unsupported absence per key.
f=P/'contracts/examples/Extraction.valid.json'
x=json.loads(f.read_text())
keys=['entity','period_end','currency','scale','revenue_current','revenue_prior','assets_current','assets_prior']
for field,key in zip(x['fields'],keys):
 field.update(key=key,raw=None,value=None,currency=None,scale=None,period_end=None,missing_reason='unsupported',evidence=[],review_state='needs_review',risk_flags=[])
f.write_text(json.dumps(x,indent=2))
