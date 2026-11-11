import subprocess, re, json, numpy as np, wave
SR=44100
raw=subprocess.run(['ffmpeg','-v','error','-i','assets/voz_raw.mp3','-ac','1','-ar',str(SR),'-f','s16le','-'],capture_output=True).stdout
x=np.frombuffer(raw,np.int16).astype(np.float32)
log=subprocess.run(['ffmpeg','-hide_banner','-i','assets/voz_raw.mp3','-af','silencedetect=noise=-38dB:d=0.25','-f','null','-'],capture_output=True,text=True).stderr
st=[float(v) for v in re.findall(r'silence_start: ([\d.]+)',log)]
en=[float(v) for v in re.findall(r'silence_end: ([\d.]+)',log)]
dur=len(x)/SR
# speech units in original time
units=[]; prev=0.0
for s,e in zip(st,en):
    units.append((prev,s)); prev=e
units.append((prev,dur))
# trim leading silence of first unit / trailing of last
KEEP=0.15
out=[]; newunits=[]; t=0.0
# leading
lead=min(units[0][0],0.1)
pieces=[]
pieces.append((units[0][0]-lead, units[0][1]+KEEP))
for i in range(1,len(units)):
    pieces.append((units[i][0]-KEEP, units[i][1]+ (KEEP if i<len(units)-1 else 0.3)))
for i,(a,b) in enumerate(pieces):
    a=max(a,0); b=min(b,dur)
    seg=x[int(a*SR):int(b*SR)]
    us,ue=units[i]
    newunits.append((t+(us-a), t+(ue-a)))
    out.append(seg); t+=len(seg)/SR
y=np.concatenate(out)
TEMPO=1.04
newunits=[(a/TEMPO,b/TEMPO) for a,b in newunits]
with wave.open('assets/tmp.wav','wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(y.astype(np.int16).tobytes())
subprocess.run(['ffmpeg','-v','error','-y','-i','assets/tmp.wav','-af',f'atempo={TEMPO}','-ar','44100','assets/voz.wav'],check=True)
d=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0','assets/voz.wav'],capture_output=True,text=True).stdout)
print(len(units),'units; new dur',d)
json.dump({'units':newunits,'dur':d},open('times.json','w'),indent=1)
for i,u in enumerate(newunits): print(i+1, round(u[0],2), round(u[1],2))
