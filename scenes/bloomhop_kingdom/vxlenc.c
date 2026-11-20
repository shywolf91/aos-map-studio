// VXL encoder (pyspades save_vxl algorithm). solid[x][y][z] uint8, col[x][y][z][3] RGB.
#include <stdint.h>
#include <stdlib.h>
#define MX 512
#define MY 512
#define MZ 64
static const uint8_t *S; static const uint8_t *C;
static inline int solid(int x,int y,int z){
  if(x<0||x>=MX||y<0||y>=MY||z>=MZ) return 1;
  if(z<0) return 0;
  return S[((size_t)x*MY+y)*MZ+z];
}
static inline int surf(int x,int y,int z){
  if(!solid(x,y,z)) return 0;
  if(z==0) return 1;
  return !solid(x-1,y,z)||!solid(x+1,y,z)||!solid(x,y-1,z)||!solid(x,y+1,z)||!solid(x,y,z-1)||!solid(x,y,z+1);
}
static inline void putc4(uint8_t *o,size_t *n,int x,int y,int z){
  const uint8_t *c=C+(((size_t)x*MY+y)*MZ+z)*3;
  o[(*n)++]=c[2];o[(*n)++]=c[1];o[(*n)++]=c[0];o[(*n)++]=0x80;
}
// returns bytes written into out (caller allocs 40MB)
size_t encode(const uint8_t *solid_, const uint8_t *col_, uint8_t *out){
  S=solid_;C=col_; size_t n=0;
  for(int y=0;y<MY;y++) for(int x=0;x<MX;x++){
    int k=0;
    while(k<MZ){
      int air=k; while(k<MZ && !solid(x,y,k)) k++;
      int ts=k; while(k<MZ && surf(x,y,k)) k++;
      int te=k;
      while(k<MZ && solid(x,y,k) && !surf(x,y,k)) k++;
      int bs=k; int z=k; while(z<MZ && surf(x,y,z)) z++;
      if(z!=MZ){ while(surf(x,y,k)) k++; }
      int be=k;
      int tl=te-ts, bl=be-bs;
      out[n++]= (k==MZ)?0:(uint8_t)(tl+bl+1);
      out[n++]=ts; out[n++]=te-1; out[n++]=air;
      for(int i=ts;i<te;i++) putc4(out,&n,x,y,i);
      for(int i=bs;i<be;i++) putc4(out,&n,x,y,i);
      if(k==MZ) break;
    }
  }
  return n;
}
