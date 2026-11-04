"""Deterministic independent acceptance oracles, not application implementations.
Production code MUST NOT import this module. Hidden evaluators need separate fixtures.
"""
import copy,csv,hashlib,io,json,math,random,re,zipfile
from decimal import Decimal,InvalidOperation

def canonical(value):
    # Bounded contract: JSON only, no NaN/Infinity, keys sorted, UTF-8, no whitespace.
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()

def redact(value):
    """Allowlisted metadata + explicit credential-key filtering; not a general PII detector."""
    forbidden={'api_key','authorization','access_token','refresh_token','password','client_secret','cookie','secret'}
    allowed={'operation_id','name','outcome','input_tokens','output_tokens','redacted','reason'}
    if not isinstance(value,dict):raise ValueError('metadata object required')
    out={}
    for k,v in value.items():
        if k.lower() in forbidden:continue
        if k not in allowed:continue
        if k=='reason':continue # Free text can contain content/credentials; metadata-only omits it.
        if isinstance(v,(dict,list)):raise ValueError('nested metadata forbidden')
        out[k]=v
    return out

class EventOracle:
    def __init__(self):self.ids={};self.seqs={}
    def batch(self,project,events):
        # Entire batch atomic. Contradictory event IDs or producer sequences -> 409, no writes.
        ids,seqs=copy.deepcopy(self.ids),copy.deepcopy(self.seqs);accepted=[];duplicates=[]
        for e in events:
            eid=(project,e['event_id']);seq=(project,e['run_id'],e['producer_id'],e['producer_seq']);h=digest(e)
            if eid in ids:
                if ids[eid]!=h:raise ValueError('event_conflict')
                duplicates.append(e['event_id']);continue
            if seq in seqs:raise ValueError('sequence_conflict')
            ids[eid]=h;seqs[seq]=e['event_id'];accepted.append(e['event_id'])
        self.ids,self.seqs=ids,seqs
        return {'accepted':accepted,'duplicates':duplicates}

def recorded_match(records,tool,contract_hash,args,ordinal):
    # Hashes equality alone is not authorization. Occurrence order is explicit.
    candidates=[r for r in records if r['tool']==tool and r['contract_hash']==contract_hash and r['ordinal']==ordinal and canonical(r['args'])==canonical(args)]
    if len(candidates)!=1:raise ValueError('fixture_mismatch')
    return copy.deepcopy(candidates[0]['output'])

def archive_entries(blob,max_expanded=104857600,max_files=2000):
    paths=set();total=0
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if len(z.infolist())>max_files:raise ValueError('entry_limit')
        for e in z.infolist():
            n=e.filename
            if '\\' in n or '\x00' in n or n.startswith('/') or re.match(r'^[A-Za-z]:',n):raise ValueError('unsafe_path')
            parts=n.rstrip('/').split('/')
            if any(p in ('','..','.') for p in parts):raise ValueError('unsafe_path')
            mode=(e.external_attr>>16)&0o170000
            if mode not in (0,0o100000,0o040000):raise ValueError('unsafe_entry_type')
            key='/'.join(parts)
            if key in paths:raise ValueError('duplicate_path')
            paths.add(key);total+=e.file_size
            if total>max_expanded:raise ValueError('expanded_limit')
            if e.file_size>1048576 and e.file_size/max(e.compress_size,1)>100:raise ValueError('compression_ratio')
            # Read at most declared cap to check actual decompression; never extract to disk.
            with z.open(e) as f:
                actual=0
                while True:
                    b=f.read(65536)
                    if not b:break
                    actual+=len(b)
                    if actual>e.file_size or actual>max_expanded:raise ValueError('size_mismatch')
        return sorted(paths)

def task_analysis(trials,task_ids,repetitions,seed=17,iterations=2000):
    """Intention-to-evaluate bounds, task-level paired bootstrap on complete tasks only.
    Pass=1, fail/policy/activation=0; infra/cancel/absent=unknown. No efficacy/equivalence label.
    PRNG random.Random seed; percentiles linear interpolation (type 7). Min 10 complete tasks.
    """
    if not task_ids or repetitions<1 or iterations<100:raise ValueError('invalid_analysis')
    if len(set(task_ids))!=len(task_ids):raise ValueError('duplicate_task')
    idx={}
    for r in trials:
        key=(r['task_id'],r['repeat'],r['arm'])
        if r['task_id'] not in task_ids or not 0<=r['repeat']<repetitions:raise ValueError('unknown_trial')
        if r['arm'] not in ('baseline','treatment') or key in idx:raise ValueError('duplicate_or_invalid_arm')
        if r['outcome'] not in ('pass','fail','activation_failed','policy_block','infra_error','cancelled'):raise ValueError('unknown_outcome')
        idx[key]=r
    deltas=[];lo=[];hi=[];missing=0
    for t in sorted(task_ids):
        vals={a:[] for a in ('baseline','treatment')}
        for a in vals:
            for rep in range(repetitions):
                r=idx.get((t,rep,a));o=r['outcome'] if r else None
                v=1 if o=='pass' else 0 if o in ('fail','activation_failed','policy_block') else None
                vals[a].append(v)
                missing+=v is None
        b,tv=vals['baseline'],vals['treatment']
        lower=lambda v:sum(x or 0 for x in v)/repetitions
        upper=lambda v:sum(1 if x is None else x for x in v)/repetitions
        lo.append(lower(tv)-upper(b));hi.append(upper(tv)-lower(b))
        if None not in b and None not in tv:deltas.append(sum(tv)/repetitions-sum(b)/repetitions)
    n=len(task_ids);nc=len(deltas)
    out={'analysis_version':'paired-task-bootstrap/1','status':'valid' if nc==n and nc>=10 else 'partial' if nc>=10 else 'insufficient','n_tasks':n,'n_complete_tasks':nc,'delta':sum(deltas)/nc if nc else None,'ci_low':None,'ci_high':None,'bound_low':sum(lo)/n,'bound_high':sum(hi)/n,'interpretation':'descriptive_no_certification','missing_trials':missing}
    if nc>=10:
        rng=random.Random(seed);bs=sorted(sum(deltas[rng.randrange(nc)] for _ in range(nc))/nc for _ in range(iterations))
        def q(p):
            v=(len(bs)-1)*p;i=math.floor(v);j=math.ceil(v);return bs[i]+(bs[j]-bs[i])*(v-i)
        out['ci_low'],out['ci_high']=q(.025),q(.975)
    return out

def pdf_point(x,y,crop,rotation):
    """PDF bottom-left point -> top-left [0,1] after clockwise intrinsic rotation.
    crop=(x0,y0,x1,y1); valid points only, no silent clamping.
    """
    x0,y0,x1,y1=crop
    if rotation not in (0,90,180,270) or x1<=x0 or y1<=y0:raise ValueError('invalid_geometry')
    u=(x-x0)/(x1-x0);v=(y1-y)/(y1-y0)
    if not (0<=u<=1 and 0<=v<=1):raise ValueError('outside_crop')
    return {0:(u,v),90:(1-v,u),180:(1-u,1-v),270:(v,1-u)}[rotation]

def inverse_pdf_point(u,v,crop,rotation):
    if not (0<=u<=1 and 0<=v<=1):raise ValueError('outside_render')
    x0,y0,x1,y1=crop
    if rotation not in (0,90,180,270) or x1<=x0 or y1<=y0:raise ValueError('invalid_geometry')
    a,b={0:(u,v),90:(v,1-u),180:(1-u,1-v),270:(1-v,u)}[rotation]
    return x0+a*(x1-x0),y1-b*(y1-y0)

def normalize_number(raw,locale='en',scale='1'):
    if scale not in ('1','1000','1000000'):raise ValueError('invalid_scale')
    if locale not in ('en','de'):raise ValueError('unsupported_locale')
    s=raw.strip()
    if s in ('—','–','-','N/A',''):return {'value':None,'missing_reason':'ambiguous' if s in ('—','–','-') else 'not_present'}
    negative=s.startswith('(') and s.endswith(')')
    if negative:s=s[1:-1]
    pattern=r'[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?' if locale=='en' else r'[-+]?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?'
    if not re.fullmatch(pattern,s) or (negative and s.startswith(('-','+'))):raise ValueError('ambiguous_number')
    s=s.replace(',','') if locale=='en' else s.replace('.','').replace(',','.')
    v=Decimal(s)*Decimal(scale)
    if negative:v=-v
    return {'value':format(v,'f'),'missing_reason':None}

def validate_evidence(e,source,parse):
    if e['source_sha256']!=source['sha256'] or e['parse_id']!=parse['id'] or e['document_id']!=source['document_id']:raise ValueError('source_mismatch')
    region=e['region'];p=region['page_ordinal'];element=parse['elements'].get(e['element_id'])
    if not element or element['page_ordinal']!=p or p<1 or p>source['page_count']:raise ValueError('missing_source')
    if not (0<=region['x0']<region['x1']<=1 and 0<=region['y0']<region['y1']<=1):raise ValueError('invalid_region')
    if region!=element['region']:raise ValueError('region_mismatch')
    if e['method']!='manual_image' and e['quote'] not in element['text']:raise ValueError('quote_mismatch')
    if e['method']=='manual_image' and e['quote']:raise ValueError('manual_image_not_text')
    return True

def csv_safe(value):
    # RFC4180 escaping is performed by csv.writer separately; mitigate spreadsheet formulas.
    s='' if value is None else str(value)
    return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else s
