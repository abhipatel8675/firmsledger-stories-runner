import json,re,sys,os
O=sys.argv[1] if len(sys.argv)>1 else 'docs/reports/stories/industry-top/'
rows=json.load(open(O+'final-stories.json'))
ver=json.load(open(O+'verify-results.json'))
clean,wrong,errors,removed=[],[],[],0
norm=lambda s:re.sub(r'\s+',' ',s).strip().lower()
for o in rows:
  v=ver.get(o['slug'],{})
  if v.get('error'): errors.append(o['slug']); continue
  if v.get('wrong_company'): wrong.append((o['slug'],v.get('note',''))); continue
  bad={norm(s) for s in v.get('unsupported',[])}
  paras=[]
  for p in o['about'].split('\n\n'):
    keep=[s for s in re.split(r'(?<=[.!?])\s+',p) if norm(s) not in bad and not any(b and b in norm(s) for b in bad)]
    removed+=len(re.split(r'(?<=[.!?])\s+',p))-len(keep)
    if keep: paras.append(' '.join(keep))
  o['about']='\n\n'.join(paras)
  o['built_on']=[x for x in o.get('built_on') or [] if not any(b and (b in norm(x) or norm(x) in b) for b in bad)]
  if len(o['about'].split())<80: wrong.append((o['slug'],f"too short after fact-check ({len(o['about'].split())} words)")); continue
  clean.append(o)
json.dump(clean,open(O+'clean-stories.json','w'),indent=1)
json.dump(wrong,open(O+'needs-review.json','w'),indent=1)
print('clean',len(clean),'| sentences removed',removed,'| needs review',len(wrong),'| check errors',len(errors))
for w in wrong: print('REVIEW',*w)
for e in errors: print('ERROR',e)
