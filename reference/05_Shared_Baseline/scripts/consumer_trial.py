"""Separate-process contract consumption rehearsal, NOT an independent agent build trial."""
from pathlib import Path
import json,yaml,sys
P=Path(__file__).resolve().parents[1]
def main():
 api=yaml.safe_load((P/'contracts/openapi.yaml').read_text());requests=[];issues=[]
 for path,methods in api['paths'].items():
  for method,op in methods.items():
   request_schema=op.get('requestBody',{}).get('content',{}).get('application/json',{}).get('schema',{}).get('$ref')
   payload=None
   if request_schema:
    name=request_schema.split('/')[-1];f=P/'contracts/examples'/(name+'.valid.json')
    if not f.exists():issues.append(op['operationId']+': missing request example')
    else:payload=json.loads(f.read_text())
   requests.append({'operation':op['operationId'],'method':method.upper(),'path_template':path,'required_headers':[p['name'] for p in op['parameters'] if p['in']=='header' and p.get('required')],'request_example_loaded':request_schema is None or payload is not None})
 report={'kind':'contract_consumer_rehearsal_only','operations_consumed':len(requests),'issues':issues,'passed':not issues,'independent_agent_build':False,'application_executed':False,'requests':requests,'remaining_questions':['Need actual implementation URL and disposable identities to test behavior.','Need Docker/Postgres/IdP/parser environment for integration evidence.','Independent implementation agent trial remains NOT RUN.']}
 (P/'evidence/contract-consumer-trial.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='requests'},indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
