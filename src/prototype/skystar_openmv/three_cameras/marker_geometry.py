# Pure MicroPython-compatible geometry; no hardware access.
import math

def cross(o,a,b):
    return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])

def hull(points):
    pts=sorted(set(points))
    if len(pts)<3:return []
    lo=[];hi=[]
    for p in pts:
        while len(lo)>1 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi)>1 and cross(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]

def classify(points,expected,pixel_count):
    poly=hull(points)
    if len(poly)<3:return None
    xs=[p[0] for p in poly];ys=[p[1] for p in poly]
    w=max(xs)-min(xs);h=max(ys)-min(ys)
    if min(w,h)<8:return None
    tolerance=math.sqrt(w*w+h*h)*0.025
    while len(poly)>3:
        distances=[]
        for i,b in enumerate(poly):
            a=poly[i-1];c=poly[(i+1)%len(poly)]
            length=math.sqrt((c[0]-a[0])**2+(c[1]-a[1])**2)
            distances.append(abs(cross(a,c,b))/max(length,1))
        d=min(distances)
        if d>tolerance:break
        poly.pop(distances.index(d))
    wanted=4 if expected=='square' else 3
    if len(poly)!=wanted:return None
    area2=0;cx=0;cy=0
    for i,a in enumerate(poly):
        b=poly[(i+1)%len(poly)];v=a[0]*b[1]-b[0]*a[1]
        area2+=v;cx+=(a[0]+b[0])*v;cy+=(a[1]+b[1])*v
    if abs(area2)<100:return None
    # Reject hollow/noisy blobs; pixel grid edges can add a small area surplus.
    fill=pixel_count/(abs(area2)*0.5)
    if not 0.70<=fill<=1.35:return None
    if expected=='square':
        edges=[]
        for i,b in enumerate(poly):
            a=poly[i-1];c=poly[(i+1)%4]
            u=(a[0]-b[0],a[1]-b[1]);v=(c[0]-b[0],c[1]-b[1])
            lu=math.sqrt(u[0]**2+u[1]**2);lv=math.sqrt(v[0]**2+v[1]**2)
            if abs(u[0]*v[0]+u[1]*v[1])>0.35*lu*lv:return None
            edges.append(lu)
        if max(edges)>1.5*min(edges):return None
    return (int(round(cx/(3*area2))),int(round(cy/(3*area2))),poly)

def select(candidates):
    # Similar-sized multiple matches are ambiguous: report invalid, never swap silently.
    candidates=sorted(candidates,key=lambda x:x[0],reverse=True)
    if not candidates:return None
    if len(candidates)>1 and candidates[1][0]>=0.7*candidates[0][0]:return None
    return candidates[0]

def errors(cx,cy,aim=(80,60)):
    return max(-80,min(79,cx-aim[0])),max(-59,min(60,aim[1]-cy))
