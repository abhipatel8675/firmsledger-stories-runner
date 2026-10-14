import json,sys,os,re,glob,time,html,subprocess,urllib.request,concurrent.futures as cf
from html.parser import HTMLParser
sys.path.insert(0,os.path.dirname(__file__))
import generate, safeio

PAGES=sys.argv[1] if len(sys.argv)>1 else 'docs/reports/stories/industry-top/pages'
PATHS=['','/about-us','/about','/services','/capabilities','/quality']
FETCH_WORKERS,GEN_WORKERS=20,60
CACHE=f'{PAGES}/cache'; os.makedirs(CACHE,exist_ok=True)

class Text(HTMLParser):
  def __init__(s): super().__init__(); s.out=[]; s.skip=0
  def handle_starttag(s,t,a):
    if t in('script','style','noscript','svg','nav','footer','header'): s.skip+=1
  def handle_endtag(s,t):
    if t in('script','style','noscript','svg','nav','footer','header') and s.skip: s.skip-=1
  def handle_data(s,d):
    if not s.skip and d.strip(): s.out.append(d.strip())

def direct(u):
  r=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36'})
  with urllib.request.urlopen(r,timeout=15) as f:
    if 'html' not in (f.headers.get('Content-Type') or ''): return None
    p=Text(); p.feed(f.read(2_000_000).decode('utf-8','ignore')); t=html.unescape('\n'.join(p.out))
    return t if len(t)>300 else None

def jina(u):
  try:
    r=urllib.request.Request('https://r.jina.ai/'+u,headers={'X-Return-Format':'text'})
    t=urllib.request.urlopen(r,timeout=40).read().decode()
    return t if len(t)>300 else None
  except Exception: return None

def fetch_company(r):
  w=(r.get('website') or '').rstrip('/'); pages={}; seen=set()
  if not w.startswith('http'): w='https://'+w if w else ''
  for p in PATHS if w else []:
    try: t=direct(w+p)
    except Exception as e: t=None if '404' in str(e) else (jina(w+p) if p=='' else None)
    if t and t[:400] not in seen: seen.add(t[:400]); pages[p or '/']=t[:7000]
  if not pages and w:
    t=jina(w)
    if t: pages['/']=t[:7000]
  return {**r,'pages':pages}

def load(path):
  pass

def finished(f):
  rows=safeio.load(f.replace('-raw','-profiles'))
  return isinstance(rows,list) and not any(o.get('error') for o in rows)
allraws=sorted(glob.glob(f'{PAGES}/*-raw.json'))
with cf.ThreadPoolExecutor(FETCH_WORKERS) as ex:
  for f in allraws:
    d=f.replace('-raw','-deep')
    if finished(f) and not os.path.exists(d):
      rows=list(ex.map(fetch_company,json.load(open(f)))); safeio.save(rows,d)
      print('refetched site text for',os.path.basename(f),flush=True)
raws=[f for f in allraws if not finished(f)]
done={}
def cached(r):
  c=f"{CACHE}/{r['slug']}.json"
  o=safeio.load(c)
  if isinstance(o,dict) and o.get('slug'): return safeio.clean_model(o)
  o=generate.call(r)
  if not o.get('error'): safeio.save(o,c)
  return o
def finish(f,i,o):
  try: _finish(f,i,o)
  except Exception as e: print('PAGE ERROR',os.path.basename(f),repr(e)[:200],flush=True)
def _finish(f,i,o):
  done[f][i]=o
  print(('skip ' if o.get('skip') else 'ok   ')+o['name'],o.get('error',''),flush=True)
  if all(done[f]):
    out=f.replace('-raw','-profiles'); generate.write(done[f],out); load(out)
    print('PAGE DONE',os.path.basename(out),flush=True)
gen=cf.ThreadPoolExecutor(GEN_WORKERS); futs=[]
with cf.ThreadPoolExecutor(FETCH_WORKERS) as ex:
  for f in raws:
    d=f.replace('-raw','-deep')
    rows=safeio.load(d)
    if not isinstance(rows,list):
      rows=list(ex.map(fetch_company,json.load(open(f))))
      safeio.save(rows,d)
      print('fetched',os.path.basename(f),sum(bool(x['pages']) for x in rows),'/',len(rows),flush=True)
    done[f]=[None]*len(rows)
    for i,r in enumerate(rows):
      futs.append(gen.submit(lambda f=f,i=i,r=r: finish(f,i,cached(r))))
cf.wait(futs); gen.shutdown()
errs=sum(1 for v in done.values() for o in v if o and o.get('error'))
tot=sum(len(v) for v in done.values())
print('ALL-DONE errors',errs,'of',tot)
if tot and errs/tot>0.3: print('Too many API failures (key, credits or rate limit). Batch not marked done; will retry next run.'); sys.exit(3)
missing=[os.path.basename(f) for f in done if not finished(f) and not any(o and o.get('error') for o in done[f])]
if missing: print('Pages not saved:',missing); sys.exit(2)
