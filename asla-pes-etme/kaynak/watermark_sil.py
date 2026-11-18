import cv2, numpy as np, glob, os, sys
S=sys.argv[1]
fs=sorted(glob.glob(S+'/v2/fr/*.png'))
# static watermark: build mask from temporal median of bright pixels in box
x0,y0,x1,y1=255,352,465,400
stack=np.stack([cv2.imread(f)[y0:y1,x0:x1] for f in fs[::10]])
g=stack.mean(-1)
white=(g>200).mean(0)>0.8
m=np.zeros(cv2.imread(fs[0]).shape[:2],np.uint8)
m[y0:y1,x0:x1][white]=255
m=cv2.dilate(m,np.ones((7,7),np.uint8),iterations=1)
cv2.imwrite(S+'/v2/mask.png',m)
for f in fs:
    im=cv2.imread(f)
    out=cv2.inpaint(im,m,6,cv2.INPAINT_TELEA)
    cv2.imwrite(S+'/v2/clean/'+os.path.basename(f),out)
print(white.sum())
