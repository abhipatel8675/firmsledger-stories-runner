import json,sys,os,re,glob,time,urllib.request,concurrent.futures as cf
sys.path.insert(0,os.path.dirname(__file__))
import fix

O=os.environ.get('OUT','docs/reports/stories/industry-top/')
key=[l.split('=',1)[1].strip().strip('"') for l in open('.env.local') if l.startswith('NEMOTRON_KEY_2=')][0]
CACHE=O+'verify-cache'; os.makedirs(CACHE,exist_ok=True)
RULES="""You are a careful fact-checker. SOURCE is a company's database row plus text from its own website. STORY was written from SOURCE.
For each sentence of STORY, decide if it is SUPPORTED: every fact in it (names, years, places, ownership type, customers, products, numbers) can be found in SOURCE, possibly worded differently. Reasonable paraphrase and summarising is supported. A sentence is UNSUPPORTED only if it states something that is absent from SOURCE or contradicts it (for example "family-owned" when SOURCE never says so, an invented founder, an unlisted customer).
Return the UNSUPPORTED sentences only, copied exactly. Most sentences in a good story are supported; do not flag a sentence just because it is long or general.
Set wrong_company=true only if SOURCE clearly describes a different business than the company name, or is an empty placeholder/template site.
Reply with JSON only: {"unsupported":["exact sentence", ...],"wrong_company":bool,"note":"short reason if wrong_company"}"""

import threading
_pace_lock=threading.Lock(); _pace_next=[0.0]
RPM=float(os.environ.get('VERIFY_RPM','36'))
def pace(extra=0):
  with _pace_lock:
    now=time.time(); t=max(now,_pace_next[0])+extra
    _pace_next[0]=t+60/RPM
  time.sleep(max(0,t-now))

def call(slug,story,source):
  c=f'{CACHE}/{slug}.json'
  if os.path.exists(c): return json.load(open(c))
  body={"model":os.environ.get("VERIFY_MODEL","nvidia/nemotron-3-super-120b-a12b"),"temperature":0,"max_tokens":16000,
        "messages":[{"role":"system","content":RULES},{"role":"user","content":"SOURCE:\n"+source[:30000]+"\n\nSTORY:\n"+story}]}
  for i in range(5):
    try:
      pace()
      q=urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions",json.dumps(body).encode(),{"Authorization":"Bearer "+key,"Content-Type":"application/json"})
      t=json.load(urllib.request.urlopen(q,timeout=300))["choices"][0]["message"]["content"]
      o=json.loads(re.search(r"\{.*\}",t,re.S).group(0)); json.dump(o,open(c,'w')); return o
    except Exception as e: print('RETRY',slug,str(e)[:60],flush=True); pace(30 if '429' in str(e) else 0); time.sleep(5*(i+1))
  return {"error":True}

src={r['slug']:r for f in glob.glob(O+'pages/*-deep.json') for r in json.load(open(f))}
rows=json.load(open(O+'final-stories.json'))
def run(o):
  r=src[o['slug']]; source=json.dumps({k:v for k,v in r.items() if k not in('phone','address','contact_email')})
  story=o['about']+'\n\nKnown for: '+'; '.join(o.get('built_on') or [])
  return o['slug'],call(o['slug'],story,source)
res={}
with cf.ThreadPoolExecutor(20) as ex:
  for slug,v in ex.map(run,rows):
    res[slug]=v; print('done',slug,len(v.get('unsupported',[])),'wrong' if v.get('wrong_company') else '',flush=True)
json.dump(res,open(O+'verify-results.json','w'),indent=1)
ve=sum(1 for v in res.values() if v.get('error'))
print('ALL-DONE errors',ve)
if res and ve/len(res)>0.3: sys.exit('Too many fact-check failures. Batch not marked done; will retry next run.')
