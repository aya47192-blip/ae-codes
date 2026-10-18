from pathlib import Path
import os
import sys
sys.path[:0]=['/workspace/sustainable_deps','/workspace/elevation/deps']
import cv2,numpy as np
from skimage.morphology import skeletonize
from PIL import Image
im=cv2.imread(os.environ.get('FACADE_SOURCE',str(Path(__file__).resolve().parents[3]/'IMG_3106.PNG')));g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
g=cv2.resize(g,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
hi=cv2.dilate(g,np.ones((19,19),np.uint8));lo=cv2.erode(g,np.ones((19,19),np.uint8))
t=(hi.astype(float)+lo)/2
bw=(g<t)&(g<244)&((hi.astype(int)-lo)>14)
sk=skeletonize(bw)
np.savez_compressed(str(Path(__file__).resolve().parent/'probe.npz'),gray=g,binary=bw,skeleton=sk)
Image.fromarray((255*(~sk)).astype('uint8')).save('/tmp/sk.png')
small=cv2.resize((255*(~sk)).astype('uint8'),(1774,887),interpolation=cv2.INTER_AREA)
Image.fromarray(small).save('/tmp/sk_small.png')
print('pixels',bw.sum(),sk.sum())
