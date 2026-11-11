import subprocess,re,json
src="voz_raw.mp3"; maxgap=0.3; tempo=1.03
out=subprocess.run(["ffmpeg","-nostats","-i",src,"-af","silencedetect=noise=-38dB:d=0.2","-f","null","-"],capture_output=True,text=True).stderr
ev=re.findall(r"silence_(start|end): ([0-9.]+)",out)
dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",src]))
S=[];s=None
for k,v in ev:
    v=float(v)
    if k=="start": s=v
    elif s is not None: S.append((s,v)); s=None
keep=[];cur=0.0
for a,b in S:
    if b-a>maxgap:
        keep.append((cur,a+maxgap/2)); cur=b-maxgap/2
keep.append((cur,dur))
def m(t):
    acc=0
    for a,b in keep:
        if t<a: return acc/tempo
        if t<=b: return (acc+t-a)/tempo
        acc+=b-a
    return acc/tempo
T=json.load(open('times_fixed.json')); Sg=json.load(open('times_raw_segs.json'))
json.dump([[round(m(a),3),round(m(b),3)] for a,b in T],open('times.json','w'))
json.dump([[[round(m(a),3),round(m(b),3),x] for a,b,x in r] for r in Sg],open('times_segs.json','w'))
print(json.load(open('times.json')))
