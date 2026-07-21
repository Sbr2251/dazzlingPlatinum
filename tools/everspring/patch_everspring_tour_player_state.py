#!/usr/bin/env python3
"""Synchronize both Platinum save partitions for deterministic Everspring tests."""
import argparse,json,struct
from pathlib import Path
PS=0x40000; GS=0xCF2C; FS=0x14; SIG=0x20060623; STATE=0x1280; TABLE=0x2858; OS=0x50; ON=64
u16=lambda d,o:struct.unpack_from("<H",d,o)[0]
u32=lambda d,o:struct.unpack_from("<I",d,o)[0]
def crc(d):
 t=b=255
 for v in d:
  x=v^t;x^=x>>4;t=(b^(x>>3)^((x<<4)&255))&255;b=(x^((x<<5)&255))&255
 return t<<8|b
def valid(d,base):
 f=base+GS-FS
 return u32(d,f+8)==GS and u32(d,f+12)==SIG and d[f+16]==0 and u16(d,f+18)==crc(d[base:f])
def pobj(d,base):
 m=[]
 for i in range(ON):
  o=base+TABLE+i*OS
  if u32(d,o)&1 and d[o+8]==255 and d[o+9]==1:m.append(o)
 if len(m)!=1:raise AssertionError(f"partition {base//PS}: expected one active player object, found {len(m)}")
 return m[0]
def patch(d,p,a):
 base=p*PS
 if not valid(d,base):raise AssertionError(f"partition {p}: invalid CRC before patch")
 s=base+STATE; before=struct.unpack_from("<iiiii",d,s); field=(before[0] if a.map_id is None else a.map_id,before[1] if a.warp_id is None else a.warp_id,a.x,a.z,a.face);struct.pack_into("<iiiii",d,s,*field)
 o=pobj(d,base); coords=(a.x,a.y,a.z,a.x,a.y,a.z); h=(a.y<<3)<<12
 struct.pack_into("<bbb",d,o+12,a.face,a.face,a.face);struct.pack_into("<hhhhhh",d,o+32,*coords);struct.pack_into("<i",d,o+44,h)
 f=base+GS-FS;struct.pack_into("<H",d,f+18,crc(d[base:f]))
 assert struct.unpack_from("<iiiii",d,s)==field and struct.unpack_from("<hhhhhh",d,o+32)==coords and struct.unpack_from("<i",d,o+44)[0]==h and valid(d,base)
 return {"partition":p,"field_after":field,"coordinates_after":coords,"height_fx32_after":h,"crc_valid":True}
def main():
 q=argparse.ArgumentParser();q.add_argument("source",type=Path);q.add_argument("output",type=Path)
 for n in("x","y","z","face"):q.add_argument(f"--{n}",type=int,required=True)
 q.add_argument("--map-id",type=int);q.add_argument("--warp-id",type=int);a=q.parse_args()
 if any(not -32768<=getattr(a,n)<=32767 for n in("x","y","z")) or not -128<=a.face<=127:raise ValueError("coordinate or face is outside persisted integer range")
 p=a.source.read_bytes()
 if len(p) not in(0x80000,0x80000+122):raise SystemExit(f"unexpected save size: {len(p)}")
 d=bytearray(p[:0x80000]);out=[patch(d,i,a) for i in(0,1)];payload=bytes(d)+p[0x80000:];a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(payload)
 if a.output.read_bytes()!=payload:raise AssertionError("written save differs from verified payload")
 print(json.dumps({"output":str(a.output),"partitions":out},indent=2))
if __name__=="__main__":main()
