"""Local research report. Run review-avatar-rig.mjs first; needs moderngl, Pillow, numpy."""
from pathlib import Path
import csv, io, json, math, os, struct, subprocess as sp, tempfile
import numpy as np
import moderngl as gl
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/asl-comparison-10'
BAKE=Path(tempfile.gettempdir())/'signbridge-asl10-bones'
FF=next((ROOT/'tools/ffmpeg').rglob('ffmpeg.exe'))
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def run(*args): return sp.check_output([str(FF),'-v','error',*map(str,args)])
data=(ROOT/'assets/avatars/rocketbox-female-01/female.glb').read_bytes()
n=struct.unpack_from('<I',data,12)[0]; g=json.loads(data[20:20+n]); blob=memoryview(data)[28+n:]
def view(i):
    b=g['bufferViews'][i]; p=b.get('byteOffset',0);return blob[p:p+b['byteLength']]
def accessor(i):
    a=g['accessors'][i];dtype={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']]
    cols={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    step=np.dtype(dtype).itemsize
    return np.ndarray((a['count'],cols),dtype,buffer=view(a['bufferView']),offset=a.get('byteOffset',0),strides=(g['bufferViews'][a['bufferView']].get('byteStride',step*cols),step))
ctx=gl.create_standalone_context();w,h=480,360
fb=ctx.simple_framebuffer((w,h));fb.use();ctx.enable(gl.DEPTH_TEST)
pg=ctx.program(vertex_shader="""#version 330
in vec3 p; in vec2 uv; in vec4 j; in vec4 w; out vec2 t; out vec3 wp;
uniform mat4 bones[80];
void main(){mat4 skin=w.x*bones[int(j.x)]+w.y*bones[int(j.y)]+w.z*bones[int(j.z)]+w.w*bones[int(j.w)];
vec4 v=skin*vec4(p,1); wp=v.xyz;float d=2.06-v.z;
gl_Position=vec4(v.x/(0.249328*4./3.),(v.y-1.27)/0.249328,1.002002*d-0.2002002,d);t=uv;}""",fragment_shader="""#version 330
in vec2 t;in vec3 wp;out vec4 frag;uniform sampler2D tex;uniform int body;
void main(){vec4 c=texture(tex,t);if(c.a<0.49)discard;
vec3 k=pow(c.rgb,vec3(2.2));
if(body==1){float rose=smoothstep(-.008,.012,(k.b-k.g)/max(k.r,.001))*smoothstep(1.08,1.24,k.r/max(k.g,.001));
k=mix(k,dot(k,vec3(.2126,.7152,.0722))*vec3(.12,.28,.72),rose);}
vec3 norm=normalize(cross(dFdx(wp),dFdy(wp)));float lit=.83+.28*max(0.,dot(norm,normalize(vec3(-.3,.6,1.))));
frag=vec4(pow(k*lit,vec3(1./2.2)),1);}""")
parts=[]
for pr in g['meshes'][0]['primitives']:
    a=pr['attributes'];arr=np.concatenate([accessor(a[key]) for key in ['POSITION','TEXCOORD_0','JOINTS_0','WEIGHTS_0']],axis=1)
    buf=ctx.buffer(arr.astype('f4').tobytes());idx=ctx.buffer(accessor(pr['indices']).astype('u4').tobytes())
    parts.append((pr['material'],ctx.vertex_array(pg,[(buf,'3f 2f 4f 4f','p','uv','j','w')],idx,index_element_size=4)))
tex=[]
for mat in g['materials']:
    im=g['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
    im=Image.open(io.BytesIO(view(g['images'][im]['bufferView']))).convert('RGBA')
    tx=ctx.texture(im.size,4,im.tobytes());tx.build_mipmaps();tex.append(tx)
def avatar(bones):
    fb.clear(.066,.105,.16,1,depth=1);pg['bones'].write(bones.tobytes())
    for m,vao in parts:
        pg['body'].value=int(m==0);tex[m].use(0);vao.render()
    return Image.frombytes('RGB',(w,h),fb.read(components=3,alignment=1)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def font(size,bold=False):
    return ImageFont.truetype(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/('segoeuib.ttf' if bold else 'segoeui.ttf')),size)
F={s:font(s,s>=20) for s in (14,16,18,20,24,32)}
def label(d,x,y,t,s=16,color='#dce7f6'):d.text((x,y),t,font=F[s],fill=color)
def motion_speed(a):
    # Average shortest quaternion arc across 15 joints; radians per second.
    a=a.reshape(len(a),15,3);angle=np.linalg.norm(a,axis=2,keepdims=True)
    q=np.concatenate((a*np.sinc(angle/(2*np.pi))*.5,np.cos(angle*.5)),axis=2)
    step=2*np.arccos(np.clip(abs((q[1:]*q[:-1]).sum(axis=2)),0,1))
    return np.r_[0,step.mean(axis=1)*24]
def run_review():
    samples=load(OUT/'samples.json');reviews=[];thumbs=[];fps=24
    enc=sp.Popen([str(FF),'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x540','-r','24','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'taqqoslash.mp4')],stdin=sp.PIPE)
    offset=0
    for i,s in enumerate(samples):
        sid=s['id'];mot=load(OUT/'model'/f'{i:04}'/'motion.json');a=np.array(mot['features'])
        assert mot['text']==s['text'] and a.shape==(mot['frame_count'],133) and mot['fps']==fps and np.isfinite(a).all()
        rig=load(BAKE/(sid+'.json'));bones=np.fromfile(BAKE/(sid+'.bin'),dtype='f4').reshape(len(a),80,16)
        src=run('-i',OUT/'human'/(sid+'.mp4'),'-vf','fps=24,crop=min(iw\\,ih*4/3):ih,scale=480:360','-f','rawvideo','-pix_fmt','rgb24','pipe:1')
        human=np.frombuffer(src,np.uint8).reshape(-1,h,w,3); assert len(human)>0
        elapsed=s['end']-s['start'];md=len(a)/fps;wr=np.array(rig['wrist']);avg=[motion_speed(a[:,x:x+45]) for x in (30,75)]
        total=max(len(a),len(human))
        row=dict(id=sid,text=s['text'],video_start_s=round(offset/fps,3),human_s=round(elapsed,3),model_s=round(md,3),model_frames=len(a),gen_cpu_s=mot['generation_seconds'],left_wrist_travel_cm=round(100*np.linalg.norm(np.diff(wr[:,0],axis=0),axis=1).sum(),1),right_wrist_travel_cm=round(100*np.linalg.norm(np.diff(wr[:,1],axis=0),axis=1).sum(),1),face_tracks=rig['faceTracks'],expression_max_range=round(np.ptp(a[:,123:],axis=0).max(),4))
        reviews.append(row)
        for k in range(total+12):
            t=min(k,total-1);j=min(t,len(a)-1)
            canvas=Image.new('RGB',(1280,540),'#0b1523');d=ImageDraw.Draw(canvas)
            label(d,22,10,'SIGNBRIDGE  /  ASL HARAKAT SINOVI',14,'#8cbcab');label(d,22,31,f"{i+1:02d} / 10     {s['text']}",32)
            label(d,22,83,'01    Haqiqiy tarjimon',20);label(d,514,83,'02    Model chiqishi',20);label(d,782,83,'03    Avatar ijrosi',20)
            canvas.paste(Image.fromarray(human[min(t,len(human)-1)]),(20,117))
            if k==0 or j!=prior_j: displayed=avatar(bones[j])
            prior_j=j;canvas.paste(displayed,(780,117))
            label(d,514,136,'Barmoq bo‘g‘imlari',18);label(d,514,164,'O‘rtacha tezlik · rad/s',14,'#98a9ba')
            for si,(seq,y,col) in enumerate(zip(avg,[245,345],['#69d9ad','#9cb5ff'])):
                label(d,514,y-49,['Chap qo‘l','O‘ng qo‘l'][si],16,col)
                mx=max(1,max(v.max() for v in avg));xs=np.linspace(518,756,len(a));ys=y+30-55*seq/mx
                d.line([(518,y+30),(756,y+30)],fill='#384b60');d.line(list(zip(xs,ys)),fill=col,width=3);d.ellipse((xs[j]-4,ys[j]-4,xs[j]+4,ys[j]+4),fill='white')
            label(d,514,400,'Nuqta = joriy model kadri',14,'#9daebd')
            label(d,20,483,f"How2Sign  ·  {elapsed:.2f} s"+('   |   Lavha tugadi' if k>=len(human) else ''),16)
            label(d,780,483,f"Rocketbox  ·  {md:.2f} s"+('   |   Ijro tugadi' if k>=len(a) else ''),16)
            label(d,20,513,'Asl tezlik  /  Yakunlangan ijroning so‘nggi kadri ushlab turiladi.  /  ASL ma’nosi ekspert tomonidan baholanmagan.',14,'#99acbf')
            if k==len(a)//2:thumbs.append(canvas.resize((576,243)))
            enc.stdin.write(canvas.tobytes())
        offset+=total+12
    enc.stdin.close();assert enc.wait()==0
    with (OUT/'olchovlar.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,reviews[0]);writer.writeheader();writer.writerows(reviews)
    sheet=Image.new('RGB',(1152,1215));assert len(thumbs)==10
    for i,im in enumerate(thumbs):sheet.paste(im,((i%2)*576,(i//2)*243))
    sheet.save(OUT/'kadrlar.jpg',quality=93)

if __name__ == '__main__':
    run_review()
