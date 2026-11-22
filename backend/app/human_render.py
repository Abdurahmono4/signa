"""Compose original signer recordings directly, without browser PNG sampling."""
import math,re,subprocess
from .core import STORE,binary,probe
from . import how2sign

def native_items(job):
    items=[]
    for item in (job.get('translation') or {}).get('items',[]):
        if not item.get('supported') or not item.get('video_url'):continue
        ident=item.get('sign_id','')
        if not re.fullmatch('[a-f0-9]{24}',ident):
            raise ValueError('Tarjimon manba klipi katalogda topilmadi.')
        record=how2sign.resolve_record(ident)
        source=how2sign.resolve_clip(ident)
        start,end=float(item['start']),float(item['end'])
        duration=float(record['duration'])
        if not all(math.isfinite(v) for v in [start,end,duration]) or not 0<=start<end<=job['duration']+.05 or duration<=0:
            raise ValueError('Tarjimon vaqtlari yaroqsiz.')
        if not .5<=duration/(end-start)<=2:raise ValueError('Tarjimon ijro tezligi yaroqsiz.')
        if not source.is_file():raise ValueError('Tarjimon klipi fayli yo‘q.')
        items.append((source,start,end,duration))
    return items

def compose(job,check,progress):
    settings=job['settings'];folder=STORE/job['id']/job['render_token']
    duration=job['duration'];height=settings['resolution'];width=height*16//9
    aw=round(width*settings['size']/2)*2;ah=min(height,round(aw*4/3/2)*2)
    args=[binary('ffmpeg'),'-y','-hide_banner','-loglevel','error','-i',str(STORE/job['id']/f"input{job['ext']}")]
    if job['kind']=='audio':
        args+=['-f','lavfi','-i',f'color=c=0x101629:s={width}x{height}:r=24']
    base='1:v' if job['kind']=='audio' else '0:v'
    offset=2 if job['kind']=='audio' else 1
    items=native_items(job)
    for source,_,_,_ in items:args+=['-i',str(source)]
    audio_only=job['kind']=='audio'
    panel=settings.get('layout')=='side_by_side' and not audio_only;main_width=width-aw if panel else width
    source_padding='' if audio_only else f',tpad=stop_mode=clone:stop_duration={duration:.10f}'
    graph=[f'[{base}]setpts=PTS-STARTPTS{source_padding},scale={main_width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:'+
           f'({main_width}-iw)/2'+':(oh-ih)/2:color=black,setsar=1[bg0]']
    for n,(_,start,end,native_duration) in enumerate(items):
        chain=f'[{offset+n}:v]trim=duration={native_duration:.8f},setpts=(PTS-STARTPTS)*{(end-start)/native_duration:.10f}+{start:.8f}/TB'
        if settings['cropMode']=='center':
            chain+=",crop=w='min(iw,ih*3/4)':h=ih:x=(iw-ow)/2:y=0"
        chain+=',format=rgba'
        chain+=f',scale={aw}:{ah}:force_original_aspect_ratio=decrease'
        if settings['removeGreen']:
            # Match HumanSigner.tsx rather than assuming a pure #00FF00 cloth.
            green='g(X,Y)-max(r(X,Y),b(X,Y))'
            alpha=f'if(gt(g(X,Y),60)*gt({green},8),255*max(0,1-({green}-8)/12),255)'
            chain+=f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{alpha}'"
        chain+=f',pad={aw}:{ah}:(ow-iw)/2:(oh-ih)/2:color=black@0[sign{n}]'
        graph.append(chain)
        x='(W-w)/2' if audio_only else str(main_width) if panel else ('W-w-24' if settings['position']=='right' else '24')
        y='(H-h)/2' if panel or audio_only else 'H-h-24'
        graph.append(f'[bg{n}][sign{n}]overlay=x={x}:y={y}:eof_action=pass:repeatlast=0:enable=\'gte(t,{start:.8f})*lt(t,{end:.8f})\'[bg{n+1}]')
    tail=f'[bg{len(items)}]'
    if settings['subtitles'] and job['segments']:
        from .main import timestamp
        srt='\n\n'.join(f"{i+1}\n{timestamp(s['start'])} --> {timestamp(s['end'])}\n{s['text'].replace(chr(10),' ')}" for i,s in enumerate(job['segments']))
        (folder/'captions.srt').write_text(srt,encoding='utf-8')
        tail+="subtitles=captions.srt:force_style='FontName=Arial,FontSize=20,Outline=2,MarginV=18'"
    else:tail+='null'
    graph.append(tail+'[out]')
    args+=['-filter_complex_threads','1','-filter_complex',';'.join(graph),'-map','[out]','-map','0:a:0',
           '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-r','24','-c:a','aac','-b:a','160k',
           '-t',str(duration),'-movflags','+faststart','-metadata','title=SignBridge UZ research result',
           '-metadata','comment=ASL recordings: How2Sign, Amanda Duarte et al., CVPR 2021; https://how2sign.github.io/ ; CC-BY-NC-4.0. Changes: crop, green key, temporal alignment and composition. Native clip rendering, 24 fps; linguistic validation separate.',
           '-progress','pipe:1',str(folder/'result.mp4')]
    proc=None
    try:
        check(job['id'])
        with (folder/'ffmpeg.log').open('w') as log:
            proc=subprocess.Popen(args,cwd=folder,stdout=subprocess.PIPE,stderr=log,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for line in proc.stdout:
                check(job['id'])
                if line.startswith('out_time_us='):
                    try:progress(min(99,max(1,int(100*int(line.split('=')[1])/1e6/duration))))
                    except ValueError:pass
            if proc.wait()!=0:raise RuntimeError('Inson tarjimon eksporti bajarilmadi. FFmpeg jurnalini tekshiring.')
        check(job['id']);info=probe(folder/'result.mp4')
        from .export_validation import validate_export
        return validate_export(info,duration,width,height,probe(STORE/job['id']/f"input{job['ext']}"))
    finally:
        if proc and proc.poll() is None:proc.kill();proc.wait()
