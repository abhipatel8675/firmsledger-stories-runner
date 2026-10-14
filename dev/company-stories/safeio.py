import json,os
def save(obj,path):
  tmp=path+'.tmp'
  with open(tmp,'w') as f: json.dump(obj,f,indent=1)
  os.replace(tmp,path)
def load(path,default=None):
  try:
    with open(path) as f: return json.load(f)
  except Exception: return default
def strs(v):
  if v is None: return []
  if isinstance(v,(str,int,float)): return [str(v)] if str(v).strip() else []
  if isinstance(v,list): return [x if isinstance(x,str) else json.dumps(x) if isinstance(x,(dict,list)) else str(x) for x in v if x not in (None,'')]
  return [str(v)]
def text(v):
  if v is None: return ''
  return v if isinstance(v,str) else ', '.join(strs(v))
LISTS=['built_on','capabilities','industries','materials','equipment','certifications','facts_used','ownership_tags','export_compliance','languages','social_links']
TEXTS=['about','volume','lead_time','tolerances','company_type','makes_products','type_evidence','founded_year','employee_count','cage_code','min_order']
def clean_model(o):
  for k in LISTS:
    if k in o: o[k]=strs(o[k])
  for k in TEXTS:
    if k in o: o[k]=text(o[k])
  if not isinstance(o.get('details'),dict): o['details']={}
  return o
