import struct
def load(path):
    return load_bytes(open(path,'rb').read())
def load_bytes(d):
    t=struct.unpack('<I',d[16:20])[0]; tex=d[t:]
    u16=lambda o:struct.unpack('<H',tex[o:o+2])[0]
    u32=lambda o:struct.unpack('<I',tex[o:o+4])[0]
    def dict_(o):
        n=tex[o+1]
        dh=o+u16(o+6)
        esz=u16(dh); data=dh+4
        names_o=dh+u16(dh+2)
        return [(tex[names_o+16*i:names_o+16*i+16].rstrip(b'\0').decode('latin1'), tex[data+i*esz:data+(i+1)*esz]) for i in range(n)]
    info=dict(texInfo=u16(0x0E),texData=u32(0x14),cmp=u32(0x24),cmpInfo=u32(0x28),plInfo=u16(0x34),plData=u32(0x38))
    texs=[]
    for name,e in dict_(info['texInfo']):
        p=struct.unpack('<I',e[:4])[0]
        texs.append(dict(name=name,off=(p&0xFFFF)<<3,fmt=(p>>26)&7,w=8<<((p>>20)&7),h=8<<((p>>23)&7),c0=(p>>29)&1,param=p))
    pals=[(name,(struct.unpack('<H',e[:2])[0])<<3) for name,e in dict_(info['plInfo'])]
    return tex,info,texs,pals
def rgb(c): return ((c&31)*255//31,((c>>5)&31)*255//31,((c>>10)&31)*255//31)
def decode(tex,info,t,palOff):
    from struct import unpack
    w,h,f=t['w'],t['h'],t['fmt']
    pal=lambda i: rgb(unpack('<H',tex[info['plData']+palOff+2*i:info['plData']+palOff+2*i+2])[0])
    px=[[(0,0,0,0)]*w for _ in range(h)]
    base=info['texData']+t['off']
    if f in (2,3,4):
        bpp={2:2,3:4,4:8}[f]; per=8//bpp
        for y in range(h):
            for x in range(w):
                i=y*w+x; b=tex[base+i//per]; v=(b>>((i%per)*bpp))&((1<<bpp)-1)
                a=0 if (t['c0'] and v==0) else 255
                px[y][x]=pal(v)+(a,)
    elif f==1 or f==6:
        for y in range(h):
            for x in range(w):
                b=tex[base+y*w+x]
                if f==1: v=b&31; a=(b>>5)*255//7
                else: v=b&7; a=(b>>3)*255//31
                px[y][x]=pal(v)+(a,)
    elif f==7:
        for y in range(h):
            for x in range(w):
                c=unpack('<H',tex[base+2*(y*w+x):base+2*(y*w+x)+2])[0]
                px[y][x]=rgb(c)+(255 if c&0x8000 else 0,)
    elif f==5:
        cb=info['cmp']+t['off']; ib=info['cmpInfo']+t['off']//2
        bw=w//4
        for by in range(h//4):
            for bx in range(bw):
                k=by*bw+bx
                blk=unpack('<I',tex[cb+4*k:cb+4*k+4])[0]
                idx=unpack('<H',tex[ib+2*k:ib+2*k+2])[0]
                po=palOff+((idx&0x3FFF)<<2); mode=idx>>14
                c=[pal(0) if False else None]*4
                def P(i): return rgb(unpack('<H',tex[info['plData']+po+2*i:info['plData']+po+2*i+2])[0])
                c0,c1=P(0),P(1)
                if mode==0: cs=[c0,c1,P(2),None]
                elif mode==1: cs=[c0,c1,tuple((a+b)//2 for a,b in zip(c0,c1)),None]
                elif mode==2: cs=[c0,c1,P(2),P(3)]
                else: cs=[c0,c1,tuple((5*a+3*b)//8 for a,b in zip(c0,c1)),tuple((3*a+5*b)//8 for a,b in zip(c0,c1))]
                for yy in range(4):
                    for xx in range(4):
                        v=(blk>>(2*(yy*4+xx)))&3
                        col=cs[v]
                        px[by*4+yy][bx*4+xx]=(col+(255,)) if col else (0,0,0,0)
    return px
