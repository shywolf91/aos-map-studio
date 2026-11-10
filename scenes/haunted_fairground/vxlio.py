import numpy as np, struct
W=H=512; D=64
def write(path,S,C):
    # exposed-voxel mask (vectorised): solid with any air 6-neighbour, or z==0
    air=~S; ex=np.zeros_like(S)
    ex[:,:,1:]|=air[:,:,:-1]; ex[:,:,:-1]|=air[:,:,1:]
    ex[1:]|=air[:-1]; ex[:-1]|=air[1:]; ex[:,1:]|=air[:,:-1]; ex[:,:-1]|=air[:,1:]
    ex[:,:,0]=True; ex&=S
    out=bytearray()
    for y in range(H):
        for x in range(W):
            col=S[x,y]; e_=ex[x,y]; zs=np.flatnonzero(col)
            br=np.flatnonzero(np.diff(zs)!=1)
            starts=np.r_[zs[0],zs[br+1]]; ends=np.r_[zs[br],zs[-1]]
            air=0
            for i,(a,b) in enumerate(zip(starts,ends)):
                last=i==len(starts)-1
                exz=np.flatnonzero(e_[a:b+1])
                e=a+(exz[-1] if len(exz) else 0)
                n=e-a+1
                out+=bytes([0 if last else n+1,a,e,air])
                for z in range(a,e+1): out+=struct.pack('<I',0x7F000000|int(C[x,y,z]))
                air=b+1
    open(path,'wb').write(out)
