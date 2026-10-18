from pathlib import Path
import os
import sys
sys.path[:0]=['/workspace/sustainable_deps','/workspace/elevation/deps']
import numpy as np,cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from PIL import Image
z=np.load(str(Path(__file__).resolve().parent/'probe.npz'));g=z['gray'].astype('float32');S=3
sig=1.35
a=ndi.gaussian_filter(g,sig,order=(0,2))*S*S
b=ndi.gaussian_filter(g,sig,order=(1,1))*S*S
c=ndi.gaussian_filter(g,sig,order=(2,0))*S*S
v=(a+c+np.sqrt((a-c)**2+4*b*b))/2
# Eigenvector corresponding to largest Hessian eigenvalue.
theta=.5*np.arctan2(2*b,a-c);nx=np.cos(theta);ny=np.sin(theta)
y,x=np.indices(g.shape,dtype='float32')
p=ndi.map_coordinates(v,[y+ny,x+nx],order=1);m=ndi.map_coordinates(v,[y-ny,x-nx],order=1)
r=(v>=p)&(v>=m)&(v>4)&(g<245)
r=skeletonize(r)
np.save(str(Path(__file__).resolve().parent/'ridge.npy'),r)
Image.fromarray((~r*255).astype('uint8')).resize((1774,887)).save('/tmp/ridge.png')
print(r.sum())
