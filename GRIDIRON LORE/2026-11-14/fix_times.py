import json,re
L=[l.strip() for l in open('gridiron_lore_06_guion.txt') if l.strip()]
# [start,end] por frase y cortes entre sub-frases (inicio,fin) segun silencios del audio crudo
R=[[(0.0,3.685),(4.246,5.277)],[(6.033,7.855),(8.346,9.935)],[(10.434,11.923)],[(12.289,14.562),(15.068,17.388)],
[(17.967,22.034)],[(22.547,24.088),(24.486,25.843)],[(26.252,28.478)],[(28.938,30.621),(31.069,32.58)],
[(32.986,34.329),(34.865,36.045)],[(36.483,38.264)],[(38.769,44.707)],[(45.175,47.49)],[(47.864,49.433)],
[(49.836,53.669)],[(54.142,55.903),(56.294,59.604)],[(60.023,61.909),(62.383,65.002)],[(65.446,68.418)],
[(68.891,72.804)],[(73.258,77.657)],[(78.424,79.294),(79.729,80.692)]]
T=[];S=[]
for line,r in zip(L,R):
    parts=[p for p in re.split(r'(?<=[.?!])\s+',line) if p]
    if len(parts)!=len(r): parts=[line]; r=[(r[0][0],r[-1][1])]
    T.append([r[0][0]-0.05 if r[0][0]>0 else 0.0, r[-1][1]+0.05])
    S.append([[a,b,p] for (a,b),p in zip(r,parts)])
json.dump(T,open('times_fixed.json','w')); json.dump(S,open('times_raw_segs.json','w'))
for s in S: print(s)
