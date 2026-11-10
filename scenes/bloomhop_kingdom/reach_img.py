import sys, numpy as np
from PIL import Image
import vxlcore, check
from spec import SPEC
S,C=vxlcore.decode(open(sys.argv[1]+'/bloomhop_kingdom.vxl','rb').read())
st=check.stand_mask(S); top=np.argmax(S,axis=2)
cols=[[np.nonzero(st[x,y])[0].tolist() for y in range(512)] for x in range(512)]
bx,by=SPEC['bases'][0]
sx=[(x,y,top[x,y]) for x in range(bx-20,bx+21,4) for y in range(by-20,by+21,4)]
d=check.bfs(S,st,cols,sx,max_drop=19)
img=np.zeros((512,512,3),np.uint8)
gr=np.zeros((512,512),bool)
for (x,y,z) in d:
    if z==top[x,y]: gr[x,y]=True
standtop=st[np.arange(512)[:,None],np.arange(512)[None,:],top]
img[standtop&gr]=(90,200,90); img[standtop&~gr]=(220,60,60); img[~standtop]=(40,40,40)
img[~S[:,:,62]]=(60,120,220)
# underground reached
ug=np.zeros((512,512),bool)
for (x,y,z) in d:
    if z>top[x,y]: ug[x,y]=True
img[ug]=(240,220,80)
Image.fromarray(img.transpose(1,0,2)).resize((1024,1024),Image.NEAREST).save(sys.argv[1]+'/renders/reach.png')
print('top reachable share (land, standable):', (standtop&gr&S[:,:,62]).sum()/(standtop&S[:,:,62]).sum())
