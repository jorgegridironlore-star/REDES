import subprocess,re,sys
src,dst,maxgap,tempo=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4])
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
        mid=(a+b)/2
        keep.append((cur,a+maxgap/2)); cur=b-maxgap/2
keep.append((cur,dur))
# trim leading/trailing silence
f=";".join(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[s{i}]" for i,(a,b) in enumerate(keep))
f+=";"+"".join(f"[s{i}]" for i in range(len(keep)))+f"concat=n={len(keep)}:v=0:a=1[c];[c]atempo={tempo}[o]"
subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-filter_complex",f,"-map","[o]","-b:a","192k",dst],check=True)
print(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",dst]).decode())
