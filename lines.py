# Finds long straight lines in a rasterised schematic.
# Method: binarise, then look for runs of black pixels per row resp.
# column and merge neighbouring rows/columns into one segment (the lines
# are several pixels thick).
from PIL import Image
import numpy as np, sys
Image.MAX_IMAGE_PIXELS=None

if len(sys.argv) < 6:
    sys.exit('usage: lines.py image.png x0 y0 x1 y1 [minimum length]\n'
             'Produce the image first with  pdftoppm -f N -l N -r 800 -png manual.pdf page')
IMAGE = sys.argv[1]
X0,Y0,X1,Y1 = [int(v) for v in sys.argv[2:6]]
MIN = int(sys.argv[6]) if len(sys.argv)>6 else 150

im = Image.open(IMAGE).convert('L').crop((X0,Y0,X1,Y1))
a = np.array(im) < 160          # True = black
H,W = a.shape

def runs(vec, minimum):
    """Start/end of every contiguous run of True at least that long"""
    out=[]; s=None
    for i,v in enumerate(vec):
        if v and s is None: s=i
        elif not v and s is not None:
            if i-s>=minimum: out.append((s,i-1))
            s=None
    if s is not None and len(vec)-s>=minimum: out.append((s,len(vec)-1))
    return out

def collect(axis):
    """axis 'h': horizontals per row; 'v': verticals per column"""
    raw=[]
    n = H if axis=='h' else W
    for k in range(n):
        vec = a[k,:] if axis=='h' else a[:,k]
        for s,e in runs(vec, MIN):
            raw.append((k,s,e))
    # merge neighbouring rows with an almost identical run
    seg=[]
    for k,s,e in raw:
        for g in seg:
            if abs(g['k1']-k)<=3 and s<=g['e']+8 and e>=g['s']-8:
                g['k1']=k; g['s']=min(g['s'],s); g['e']=max(g['e'],e); break
        else:
            seg.append({'k0':k,'k1':k,'s':s,'e':e})
    return [( (g['k0']+g['k1'])//2, g['s'], g['e']) for g in seg]

print('# coordinates are absolute in the source image')
print('horizontals (y, x_from, x_to):')
for y,s,e in sorted(collect('h')):
    print('  y=%5d  x %5d .. %5d   (%d)' % (y+Y0, s+X0, e+X0, e-s))
print('verticals (x, y_from, y_to):')
for x,s,e in sorted(collect('v')):
    print('  x=%5d  y %5d .. %5d   (%d)' % (x+X0, s+Y0, e+Y0, e-s))
