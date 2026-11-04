"""Black-box API security/contract acceptance. Requires a REAL IMPLEMENTATION.
No app is included. Missing URL fails, rather than being silently skipped.
This is a bounded smoke suite; full product journey/security/UX gates remain mandatory.
"""
import os,json,re,sys
from pathlib import Path
import httpx
P=Path(__file__).resolve().parents[1]
def main():
 base=os.getenv('BASELINE_URL')
 if not base:print('BLOCKED: BASELINE_URL must identify an implemented private test API.');return 2
 if not (base.startswith('http://127.0.0.1:') or base.startswith('http://localhost:') or base.startswith('https://')):print('Refusing insecure nonlocal URL');return 2
 pol=json.loads((P/'contracts/endpoint-policy.json').read_text());uid='00000000-0000-4000-8000-000000000001';results=[]
 with httpx.Client(base_url=base,timeout=10,follow_redirects=False,trust_env=False) as c:
  for op in pol:
   path=re.sub(r'{\w+}',uid,op['path']);body={}
   if op['request']:body=json.loads((P/'contracts/examples'/(op['request']+'.valid.json')).read_text())
   kwargs={'headers':{'Idempotency-Key':uid,'X-Project-ID':uid}}
   if op['operation']=='foundation_put_upload':kwargs['content']=b'synthetic'
   elif op['method'] in ('POST','PUT'):kwargs['json']=body
   response=c.request(op['method'],path,**kwargs)
   ok=response.status_code==401
   # Authentication precedes resource existence, schema internals and disabled-mode disclosure.
   results.append({'operation':op['operation'],'expected':401,'actual':response.status_code,'pass':ok})
 output={'kind':'unauthenticated_endpoint_smoke_only','url':base,'results':results,'passed':all(x['pass'] for x in results),'not_covered':['authenticated product journeys','cross-project role matrix','OIDC browser flow','UI','DB/job failures','runtime security']}
 (P/'evidence/product-smoke.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2));return 0 if output['passed'] else 1
if __name__=='__main__':sys.exit(main())
