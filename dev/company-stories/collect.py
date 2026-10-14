import json,glob,sys
O=sys.argv[1]
rows=[o for f in sorted(glob.glob(O+'pages/*-profiles.json')) for o in json.load(open(f)) if not o.get('skip') and o.get('about')]
seen={}; [seen.setdefault(o['slug'],o) for o in rows]
json.dump(list(seen.values()),open(O+'final-stories.json','w'),indent=1)
print('collected',len(seen))
