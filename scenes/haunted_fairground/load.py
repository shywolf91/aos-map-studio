import numpy as np
def load(path):
  d=open(path,'rb').read(); W=H=512
  S=np.zeros((W,H,64),bool); C=np.zeros((W,H,64),np.uint32); p=0
  for y in range(H):
    for x in range(W):
      while True:
        N,s,e,a=d[p:p+4]
        for i,z in enumerate(range(s,e+1)): C[x,y,z]=int.from_bytes(d[p+4+4*i:p+8+4*i],'little')&0xFFFFFF
        if N==0: S[x,y,s:]=True; p+=4*(e-s+2); break
        k=N-1-(e-s+1); nxt=p+4*N; na=d[nxt+3]; S[x,y,s:na]=True
        for i in range(k): C[x,y,na-k+i]=int.from_bytes(d[p+4*(2+e-s+i):p+4*(3+e-s+i)],'little')&0xFFFFFF
        p=nxt
  assert p==len(d); return S,C
