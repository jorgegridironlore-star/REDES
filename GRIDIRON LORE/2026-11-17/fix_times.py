import json,re
L=[l.strip() for l in open('gridiron_lore_09_guion.txt') if l.strip()]
# [start,end] por frase y cortes entre sub-frases (inicio,fin) segun silencios del audio crudo
R=[[(0.0,3.73),(4.37,6.71)],[(7.29,9.74),(10.19,12.02)],[(12.52,13.41),(13.87,15.48)],[(15.92,18.72),(19.13,21.14)],
[(21.53,22.85),(23.18,25.19),(25.61,26.56)],[(26.95,30.60)],[(31.03,34.10)],[(34.44,36.50),(36.96,37.42)],
[(37.77,40.30)],[(40.65,43.70)],[(44.06,48.07)],[(48.53,49.18)],[(49.69,50.61),(51.11,54.83)],
[(55.37,58.31)],[(58.66,60.40),(60.78,61.45)],[(61.86,64.02)],[(64.57,68.24)],
[(68.72,72.95)],[(73.45,76.70)],[(77.27,78.08),(78.50,79.46)]]
T=[];S=[]
for line,r in zip(L,R):
    parts=[p for p in re.split(r'(?<=[.?!])\s+',line) if p]
    if len(parts)!=len(r): parts=[line]; r=[(r[0][0],r[-1][1])]
    T.append([r[0][0]-0.05 if r[0][0]>0 else 0.0, r[-1][1]+0.05])
    S.append([[a,b,p] for (a,b),p in zip(r,parts)])
json.dump(T,open('times_fixed.json','w')); json.dump(S,open('times_raw_segs.json','w'))
for s in S: print(s)
