"""Measure wall bands in the plan mask. probe.py H y x0 x1  |  probe.py V x y0 y1"""
import sys, numpy as np
from PIL import Image
im=np.asarray(Image.open(sys.argv[5] if len(sys.argv)>5 else "/home/user/blender-cli/linden/ref/floorplan.jpg").convert("RGB")).astype(int)
r,g,b=im[...,0],im[...,1],im[...,2]
mask=((r<70)&(g<70)&(b<70))|((r>190)&(g>60)&(g<140)&(b<90))
def band(line, c):
    # contiguous-ish band (gaps<=3) of mask around index c within +-12
    lo=max(0,c-14); seg=line[lo:c+15]
    idx=np.where(seg)[0]+lo
    if len(idx)==0: return None
    # cluster
    groups=[[idx[0]]]
    for i in idx[1:]:
        if i-groups[-1][-1]<=4: groups[-1].append(i)
        else: groups.append([i])
    gbest=min(groups,key=lambda g_:abs((g_[0]+g_[-1])/2-c))
    return gbest[0],gbest[-1]
ax=sys.argv[1]; c=int(sys.argv[2]); a0=int(sys.argv[3]); a1=int(sys.argv[4])
res=[]
for t in range(a0,a1+1,2):
    line = mask[:,t] if ax=="H" else mask[t,:]
    res.append((t,band(line,c)))
# report runs of presence along the wall
cur=None
for t,bnd in res+[(None,None)]:
    if bnd and cur is None: cur=[t,[bnd]]
    elif bnd and cur: cur[1].append(bnd)
    elif cur:
        lo=np.median([x[0] for x in cur[1]]); hi=np.median([x[1] for x in cur[1]])
        print(f"  along {cur[0]}..{cur[0]+2*(len(cur[1])-1)}  band {lo:.0f}-{hi:.0f}  centre {(lo+hi)/2:.1f} thick {hi-lo+1:.0f}")
        cur=None
