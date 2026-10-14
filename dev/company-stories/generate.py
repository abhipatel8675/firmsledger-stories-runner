import json,sys,os,re,time,urllib.request
key=[l.split('=',1)[1].strip().strip('"') for l in open('.env.local') if l.startswith('NEMOTRON_KEY_2=')][0]
RULES="""You write a manufacturer's profile for a B2B sourcing directory, in the depth of a strong MFG.com profile, but as a story told by an independent editor (third person).
From the INPUT (our database row + text from the company's own web pages), produce JSON:
{
 "skip": bool,                      // true if fewer than 4 concrete facts about the company
 "about": "3-4 paragraphs, 180-280 words. Para 1 WHERE + WHEN + WHO: city/state, founding year, ownership (family/veteran/woman-owned), founders by name if stated, how it began. Para 2 WHAT: what they make or do, processes, scale (facility size, headcount, volumes, part numbers). Para 3 FOR WHOM: industries and customer types, with concrete examples from the input. Para 4 WHY: what the company says sets it apart or why it was started (only if stated).",
 "built_on": ["3-5 short bullets: concrete differentiators stated by the company, e.g. 'Same-day shipping on stocked parts'"],
 "capabilities": ["specific processes/services"],
 "industries": ["industries served"],
 "equipment": ["named machines or equipment lines, only if stated"],
 "certifications": ["exact standard names, e.g. ISO 9001:2015, AS9100D, ITAR"],
 "materials": ["materials they work with, e.g. Aluminum, 304 Stainless Steel, FR-4, PEEK"],
 "volume": "production volume range as stated, e.g. 'Prototype to 20,000 units' (empty if not stated)",
 "lead_time": "typical lead/turnaround time as stated, e.g. '7 days for small orders' (empty if not stated)",
 "tolerances": "precision/tolerances as stated, e.g. '±0.0005 in' (empty if not stated)",
 "details": {"company_type":"","founded":"","employees":"","ownership":"","headquarters":"city, state"},
 "facts_used": ["fact -> source page path or 'db'"]
}
Hard rules:
- Never derive a founding year from 'X years of experience'; use only an explicitly stated year.
- capabilities: deduplicated, no near-duplicates (e.g. keep one of 'PCBA'/'PCB Assembly'), max 24, specific processes only, no generic words like 'Production Equipment'.
- industries: all industries explicitly named, deduplicated.
- Use ONLY facts in the INPUT. Never invent founders, years, numbers, clients, certifications or equipment. Missing -> omit the sentence or leave the field empty.
- Rewrite in plain editorial voice; never copy the company's slogans or 'we/our' sentences verbatim.
- No street addresses, phone numbers, emails, ratings, 'verified', or superlatives (leading, best, premier, world-class, trusted).
- Ignore cookie banners, menus, blog teasers, and text about other companies.
- Output JSON only."""
import threading
_pace_lock=threading.Lock(); _pace_next=[0.0]
RPM=float(os.environ.get('GEN_RPM','36'))
def pace(extra=0):
  with _pace_lock:
    now=time.time(); t=max(now,_pace_next[0])+extra
    _pace_next[0]=t+60/RPM
  time.sleep(max(0,t-now))

def call(r):
  inp={k:v for k,v in r.items() if v and k not in('phone','address','contact_email')}
  body={"model":"nvidia/nemotron-3-ultra-550b-a55b","temperature":0.3,"max_tokens":6000,
        "messages":[{"role":"system","content":RULES},{"role":"user","content":"INPUT:\n"+json.dumps(inp)[:20000]}]}
  for i in range(4):
    try:
      pace()
      q=urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions",json.dumps(body).encode(),{"Authorization":"Bearer "+key,"Content-Type":"application/json"})
      t=json.load(urllib.request.urlopen(q,timeout=300))["choices"][0]["message"]["content"]
      return {"name":r["name"],"slug":r["slug"],"old_description":r.get("description"),**json.loads(re.search(r"\{.*\}",t,re.S).group(0))}
    except Exception as e: err=str(e)[:200]; print("RETRY",r["slug"],err[:80],flush=True); pace(30 if '429' in str(e) else 0); time.sleep(5*(i+1))
  return {"name":r["name"],"slug":r["slug"],"skip":True,"error":err}
def write(res,out):
  json.dump(res,open(out,'w'),indent=1)
  md=[]
  for o in res:
    md.append(f"# {o['name']}\n")
    if o.get('skip') or not o.get('about'): md.append(f"_skipped: {o.get('error','not enough facts')}_\n"); continue
    md.append(f"**Old description:** {o.get('old_description')}\n\n## About\n{o['about']}\n")
    for k,t in [('built_on','Known for'),('capabilities','Capabilities'),('industries','Industries'),('equipment','Equipment'),('certifications','Certifications')]:
      if o.get(k): md.append(f"## {t}\n"+"\n".join('- '+x for x in o[k])+"\n")
    d={k:v for k,v in (o.get('details') or {}).items() if v}
    if d: md.append("## Company details\n"+"\n".join(f"- **{k.replace('_',' ').title()}:** {v}" for k,v in d.items())+"\n")
    md.append("<details><summary>Sources</summary>\n\n"+"\n".join('- '+x for x in o.get('facts_used',[]))+"\n</details>\n\n---\n")
  open(out.replace('.json','.md'),'w').write("\n".join(md))

if __name__=='__main__':
  src,out=sys.argv[1:3]
  res=[]
  for r in json.load(open(src)):
    o=call(r); res.append(o); print(o['name'],'| skip' if o.get('skip') else '| ok',o.get('error',''),flush=True)
  write(res,out)
