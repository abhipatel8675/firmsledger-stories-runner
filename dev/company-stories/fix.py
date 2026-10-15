import json,re,sys,glob,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import safeio
sys.path.insert(0,os.path.dirname(__file__))
import generate

ADJ=r'\b(leading|world-class|trusted|premier|renowned|top-tier|industry-leading)\s+'
ADDR=r',?\s*(?:at|from|on)?\s*\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Drive|Dr|Way|Lane|Ln|Parkway|Pkwy|Highway|Hwy)\b\.?,?'

def norm(s): return s.lower().replace('\\u00a0',' ').replace(',','')

def num_ok(n,src):
  n=n.rstrip('.').replace(',','')
  forms={n,n.replace(':','-'),n.replace(':',' ')}
  if n.isdigit() and len(n)>=4 and n.endswith('000'): forms|={n[:-3]+'k',n[:-3]+' k',n[:-3]+'k+'}
  if re.fullmatch(r'\d+\.\d+',n): forms.add(n.lstrip('0'))
  return any(f in src for f in forms)

def cert_ok(c,src):
  toks=[t for t in re.findall(r'[a-z0-9]+',c.lower()) if len(t)>2 or t.isdigit()]
  return all(t in src for t in toks)

def sentences(t): return re.split(r'(?<=[.!?])\s+',t)

def clean_text(t,bad):
  out=[]
  for para in t.split('\n\n'):
    keep=[s for s in sentences(para) if not any(b in s for b in bad)]
    if keep: out.append(' '.join(keep))
  return '\n\n'.join(out)

def fix(o,src,site=None):
  o=safeio.clean_model(o)
  if o.get('skip') or not o.get('about'): return o,[]
  log=[]
  certs=o.get('certifications') or []
  badc=[c for c in certs if not cert_ok(c,src if site is None else site)]
  o['certifications']=[c for c in certs if c not in badc]
  fields=o['about']+' '+' '.join(o.get('built_on') or [])+' '+' '.join(str(o.get(k) or '') for k in ['volume','lead_time','tolerances'])
  badn=[n for n in set(re.findall(r'\d[\d,.:]*\d|\d{2,}',fields)) if not num_ok(n,src)]
  bad=badn+badc
  o['about']=re.sub(ADDR,'',o['about'])
  o['about']=re.sub(ADJ,'',o['about'],flags=re.I)
  o['about']=clean_text(o['about'],bad+[' best ',' best-',' circa '])
  o['built_on']=[x for x in o.get('built_on') or [] if not any(b in x for b in bad) and not re.search(r'\bbest\b',x,re.I)]
  for k in ['volume','lead_time','tolerances']:
    if o.get(k) and any(b in str(o[k]) for b in badn): o[k]=''
  if badn: log.append(f'nums {badn}')
  if badc: log.append(f'certs {badc}')
  return o,log

if __name__=='__main__':
  for f in sorted(glob.glob(sys.argv[1]+'/*-profiles.json')):
    deep=json.load(open(f.replace('-profiles','-deep')))
    src={r['slug']:norm(json.dumps(r)) for r in deep}
    site={r['slug']:norm(json.dumps(r.get('pages') or {})) for r in deep}
    rows=json.load(open(f)); changed=False
    for i,o in enumerate(rows):
      before=json.dumps(o)
      rows[i],log=fix(o,src.get(o['slug'],''),site.get(o['slug'],''))
      if json.dumps(rows[i])!=before:
        changed=True; print(o['slug'],'|',' ; '.join(log) or 'wording/address')
    if changed: generate.write(rows,f)
