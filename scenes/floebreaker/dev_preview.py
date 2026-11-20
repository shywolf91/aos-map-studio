import sys, time
sys.path.insert(0,'../..'); sys.path.insert(0,'.')
import numpy as np
from fb_core import *
import fb_build
from aosmap.vxl import VoxelMap, surface_mask
from aosmap import render
t=time.time()
W=fb_build.build()
print('build',round(time.time()-t,1),W.stats)
pal={1:(200,210,222),2:(120,170,210),3:(70,130,200),4:(100,100,110),5:(190,200,210),
 6:(176,44,44),7:(36,40,48),8:(120,128,138),9:(110,116,124),10:(206,210,214),11:(150,156,166),12:(60,64,74),
 13:(230,120,40),14:(230,190,40),16:(150,110,70),17:(100,70,50),18:(230,120,40),19:(60,140,70),20:(60,90,170),
 21:(190,50,50),22:(50,80,180),23:(206,198,176),24:(170,50,50),25:(50,140,70),26:(50,90,170),27:(220,180,50),
 29:(150,206,232),30:(112,176,220),31:(176,226,238),33:(255,175,95),34:(95,255,255),35:(95,255,95)}
solid=W.m>0; solid[:,:,63]=True
col=np.zeros(W.m.shape+(3,),np.uint8)
for k,v in pal.items(): col[W.m==k]=v
vm=VoxelMap(solid=solid)
c=(np.uint32(0x80)<<24)|(col[...,0].astype(np.uint32)<<16)|(col[...,1].astype(np.uint32)<<8)|col[...,2].astype(np.uint32)
vm.color=c; vm.colored=surface_mask(solid)
vm.color[:,:,63][~W.land]=(0x80<<24)|(30<<16)|(80<<8)|140
P='../../work/arctic_icebreaker/preview/'
render.top_down(vm).save(P+'dev_top.png')
render.isometric(vm,s=1).save(P+'dev_iso.png')
render.isometric(vm,crop=(200,40,312,200),s=4,view=0).save(P+'dev_ship.png')
np.save('../../work/arctic_icebreaker/dev_m.npy',W.m)
print(time.time()-t)
