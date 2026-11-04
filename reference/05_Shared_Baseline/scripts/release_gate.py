"""Fail closed: a green contract suite is NOT production release authorization."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
REQUIRED=['contract_suite','postgres_migrations','application_e2e','authorization_matrix','oidc_integration','docling_integration','executor_boundary','backup_restore','load_chaos','accessibility_manual','domain_holdout','statistical_review','independent_security_review','clean_room_agent_trial','release_images_sbom','operator_signoff']
def evaluate(path):
 data=json.loads(Path(path).read_text());checks=data.get('checks',{})
 blocking=[k for k in REQUIRED if checks.get(k,{}).get('status')!='passed' or not checks.get(k,{}).get('evidence')]
 return {'ready':not blocking,'blocking':blocking,'warning':'Evidence claims require independent review; this script cannot verify human truthfulness.'}
if __name__=='__main__':
 r=evaluate(ROOT/'evidence/release-status.json');print(json.dumps(r,indent=2));sys.exit(0 if r['ready'] else 1)
