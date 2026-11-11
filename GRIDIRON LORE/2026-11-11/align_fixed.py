import subprocess,re,json,sys
sys.path.insert(0,'.')
SCRIPT=[l.strip() for l in open("guion.txt") if l.strip()]
mp3=sys.argv[1]
out=subprocess.run(["ffmpeg","-nostats","-i",mp3,"-af","silencedetect=noise=-35dB:d=0.15","-f","null","-"],capture_output=True,text=True).stderr
ev=re.findall(r"silence_(start|end): ([0-9.]+)",out)
dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",mp3]))
P=[];s=None
for k,v in ev:
    v=float(v)
    if k=="start": s=v
    elif s is not None: P.append((s,v)); s=None
start=0.0 if not P or P[0][0]>0.05 else P[0][1]
end=P[-1][0] if P and P[-1][1]>=dur-0.05 else dur
P=[p for p in P if p[0]>start+0.3 and p[1]<end-0.3]
L=[len(x) for x in SCRIPT]; tot=sum(L)
exp=[];acc=0
for l in L[:-1]:
    acc+=l; exp.append(start+(end-start)*acc/tot)
n=len(exp); m=len(P)
INF=1e9
import functools
@functools.lru_cache(None)
def f(i,j):
    if i==n: return 0.0
    if j==m: return INF
    best=f(i,j+1)
    mid=(P[j][0]+P[j][1])/2; d=P[j][1]-P[j][0]
    c=abs(mid-exp[i])*1.0 - d*6.0
    best=min(best,c+f(i+1,j+1))
    return best
res=[];i=j=0
while i<n:
    mid=(P[j][0]+P[j][1])/2; d=P[j][1]-P[j][0]
    c=abs(mid-exp[i])-d*6.0
    if abs(f(i,j)-(c+f(i+1,j+1)))<1e-9: res.append(P[j]); i+=1
    j+=1
times=json.load(open('times_fixed.json'))
# sub-frases dentro de cada frase
import re as _re
segs=[]
for (a,b),line in zip(times,SCRIPT):
    parts=[p for p in _re.split(r'(?<=[.?!])\s+',line) if p]
    inner=[p for p in P if p[0]>a+0.1 and p[1]<b-0.1]
    k=len(parts)-1
    if k==0 or not inner:
        segs.append([[a,b,line]]); continue
    Ls=[len(x) for x in parts]; T=sum(Ls); ex=[];acc=0
    for l in Ls[:-1]:
        acc+=l; ex.append(a+(b-a)*acc/T)
    # greedy: para cada limite esperado, la pausa mas cercana con bonus por duracion, en orden
    chosen=[];j0=0
    for e in ex:
        cands=[(abs((p[0]+p[1])/2-e)-(p[1]-p[0])*4,idx) for idx,p in enumerate(inner) if idx>=j0]
        if not cands: break
        _,idx=min(cands); chosen.append(inner[idx]); j0=idx+1
    if len(chosen)!=k:
        segs.append([[a,b,line]]); continue
    cur=a;row=[]
    for p,txt in zip(chosen,parts):
        row.append([round(cur,3),round(p[0],3),txt]); cur=p[1]
    row.append([round(cur,3),b,parts[-1]])
    segs.append(row)
json.dump(segs,open(sys.argv[2].replace('.json','_segs.json'),'w'),indent=0)
for r in segs:
    for x in r: print('   ',x[0],x[1],x[2][:40])
