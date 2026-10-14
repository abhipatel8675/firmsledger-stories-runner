import json,glob,re,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import safeio
O=sys.argv[1]; per=int(sys.argv[2]) if len(sys.argv)>2 else 75
src={r['slug']:json.dumps(r).lower() for f in glob.glob(O+'pages/*-deep.json') for r in json.load(open(f))}
EM=re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}')
PH=re.compile(r'(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}')
cl=lambda v: PH.sub('',EM.sub('',v)) if isinstance(v,str) else [cl(x) for x in v] if isinstance(v,list) else v
C=['family-owned','veteran-owned','woman-owned','women-owned','minority-owned']
q=lambda s:"'"+s.replace("'","''")+"'"
arr=lambda a:"ARRAY["+",".join(q(x) for x in a)+"]::text[]"
st=[]
for o in [safeio.clean_model(x) for x in (safeio.load(O+'clean-stories.json') or [])]:
  bad=[c for c in C if c.split('-')[0] not in src.get(o['slug'],'')]
  about='\n\n'.join(' '.join(s for s in re.split(r'(?<=[.!?])\s+',p) if not any(b in s.lower() for b in bad)) for p in o['about'].split('\n\n')).strip()
  about=cl(about)
  if len(about.split())<80: continue
  tags=[t for t in (o.get('ownership_tags') or []) if t.split('-')[0].split()[0].lower() in src.get(o['slug'],'')]
  prof={k:cl(o.get(k)) for k in ['capabilities','industries','materials','equipment','volume','lead_time','tolerances','built_on','facts_used','company_type','makes_products','type_evidence','founded_year','employee_count','cage_code','min_order','export_compliance','languages','social_links']}
  prof['ownership_tags']=tags
  st.append(f"UPDATE companies SET description={q(about)}, certifications={arr(o.get('certifications') or [])}, profile={q(json.dumps(prof))}::jsonb, updated_at=now() WHERE slug={q(o['slug'])} AND approved AND profile IS NULL;\n")
os.makedirs(O+'sql',exist_ok=True)
n=-(-len(st)//per)
for i in range(n):
  part=st[i*per:(i+1)*per]
  open(f"{O}sql/part{i+1:02d}-of-{n:02d}.sql",'w').write(f"-- {len(part)} fact-checked company stories\nBEGIN;\n"+''.join(part)+"COMMIT;\nSELECT count(*) FROM companies WHERE profile IS NOT NULL;\n")
print('sql parts',n,'stories',len(st))
