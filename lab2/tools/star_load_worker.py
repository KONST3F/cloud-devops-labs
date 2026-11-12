import concurrent.futures, time, urllib.request
start=time.monotonic(); deadline=start+12

def worker(_):
 ok=err=0
 while time.monotonic()<deadline:
  try:
   with urllib.request.urlopen('http://backend-a:8000/api/health',timeout=3) as response:
    if response.status==200: ok+=1
    else: err+=1
  except Exception: err+=1
 return ok,err
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 results=list(pool.map(worker,range(8)))
print('seconds=%.1f workers=8 HTTP_200=%s errors=%s' % (time.monotonic()-start,sum(x[0] for x in results),sum(x[1] for x in results)))
