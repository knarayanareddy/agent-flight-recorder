from pathlib import Path
import json,hashlib,sys
P=Path(__file__).resolve().parents[1]
def main():
 f=P/'contracts/baseline-manifest.json'
 if not f.exists():print('Missing reviewed baseline manifest');return 1
 d=json.loads(f.read_text());bad=[]
 for name,expected in d['files'].items():
  file=P/name
  if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:bad.append(name)
 print(json.dumps({'valid':not bad,'protected_files':len(d['files']),'changed_or_missing':bad,'note':'Integrity only; authenticity requires signed source/reviewer trust.'},indent=2));return 0 if not bad else 1
if __name__=='__main__':sys.exit(main())
