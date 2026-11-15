import subprocess, re, json, sys
src, dst, txt, out, target = sys.argv[1:6]; target=float(target)
def sil(f, d=0.22, n='-38dB'):
    o = subprocess.run(['ffmpeg','-i',f,'-af',f'silencedetect=noise={n}:d={d}','-f','null','-'],capture_output=True,text=True).stderr
    s=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',o)]; e=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',o)]
    return list(zip(s,e))
dur=lambda f: float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]))
D=dur(src); S=sil(src)
# trim silences to 0.3s
keep=[]; cur=0.0
for a,b in S:
    if b-a>0.3:
        keep.append((cur,a+0.15)); cur=b-0.15
keep.append((cur,D))
filt=''.join(f'[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}];' for i,(a,b) in enumerate(keep))
filt+=''.join(f'[a{i}]' for i in range(len(keep)))+f'concat=n={len(keep)}:v=0:a=1[c]'
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',src,'-filter_complex',filt,'-map','[c]','_trim.wav'],check=True)
T=dur('_trim.wav'); tempo=max(1.0,T/target)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','_trim.wav','-af',f'atempo={tempo:.4f}','-b:a','192k',dst],check=True)
D2=dur(dst); S2=sil(dst,0.12)
print('raw',D,'trim',T,'tempo',tempo,'final',D2,'gaps',len(S2))
lines=[l.strip() for l in open(txt) if l.strip()]
# speech start/end
sp_start = S2[0][1] if S2 and S2[0][0]<0.05 else 0.0
sp_end = S2[-1][0] if S2 and S2[-1][1]>D2-0.05 else D2
gaps=[(a,b) for a,b in S2 if a>sp_start+0.1 and b<sp_end-0.05]
L=[len(l) for l in lines]; tot=sum(L); n=len(lines)
speech=sp_end-sp_start
# DP: choose n-1 gaps (in order) as sentence boundaries; cost = squared deviation of sentence speaking duration from expected
import math
G=len(gaps)
exp_rate = speech/tot
INF=1e18
best=[[INF]*(G+1) for _ in range(n)]; prev=[[None]*(G+1) for _ in range(n)]
# best[i][j]: sentences 0..i placed, sentence i ends at gap j (j index into gaps), j=G means end
def seg_cost(i,s,e):
    d=e-s; ex=L[i]*exp_rate; return ((d-ex)/ex)**2
for j in range(G):
    best[0][j]=seg_cost(0,sp_start,gaps[j][0])
for i in range(1,n):
    for j in range(G+1):
        if i==n-1 and j!=G: continue
        if i<n-1 and j==G: continue
        e = sp_end if j==G else gaps[j][0]
        for k in range(j):
            if best[i-1][k]>=INF: continue
            c=best[i-1][k]+seg_cost(i,gaps[k][1],e)
            if c<best[i][j]: best[i][j]=c; prev[i][j]=k
# backtrack
bounds=[]; j=G
for i in range(n-1,0,-1):
    k=prev[i][j]; bounds.append(k); j=k
bounds=bounds[::-1]
res=[]
for i,l in enumerate(lines):
    s = sp_start if i==0 else gaps[bounds[i-1]][1]
    e = sp_end if i==n-1 else gaps[bounds[i]][0]
    # internal gaps
    ig=[g for g in gaps if s<g[0] and g[1]<e]
    words=l.split()
    # distribute words over speech chunks between internal gaps, proportional to chars
    chunks=[]; cs=s
    for a,b in ig: chunks.append((cs,a)); cs=b
    chunks.append((cs,e))
    # map words to chunks by punctuation: assign proportional over total speech time excluding gaps
    spt=sum(b-a for a,b in chunks); wl=[len(w)+1 for w in words]; wt=sum(wl)
    def tmap(x):  # x in [0,spt] -> absolute time
        for a,b in chunks:
            if x<=b-a+1e-9: return a+x
            x-=b-a
        return chunks[-1][1]
    acc=0; ws=[]
    for w,wlen in zip(words,wl):
        st=tmap(acc*spt/wt); acc+=wlen; en=tmap(acc*spt/wt)
        # snap: if a word ends with punctuation and next gap starts close, fine
        ws.append({'w':w,'s':round(st,3),'e':round(en,3)})
    res.append({'text':l,'start':round(s,3),'end':round(e,3),'words':ws})
    print(f'{i:2d} {s:6.2f}-{e:6.2f} ({e-s:4.2f} vs {L[i]*exp_rate:4.2f}) {l[:50]}')
json.dump(res,open(out,'w'),indent=1)
