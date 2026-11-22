"""Readable subtitles and a small persistent research label, at output resolution."""
def stamp(seconds):
    centiseconds=max(0,round(seconds*100))
    return f'{centiseconds//360000}:{centiseconds//6000%60:02}:{centiseconds//100%60:02}.{centiseconds%100:02}'

def literal(text):
    # Keep transcript text from becoming an ASS override/drawing instruction.
    return str(text).replace('\\','＼').replace('{','｛').replace('}','｝').replace('\r','').replace('\n',r'\N')

def make_ass(job,width,height):
    scale=job.get('timing_scale',1);duration=job.get('output_duration',job['duration'])
    settings=job.get('settings',{});neural=settings.get('engine')=='neural';factor=height/720
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,{32*factor:.1f},&H00FFFFFF,&H00FFFFFF,&H80000000,&H80000000,0,0,0,0,100,100,0,0,3,3,0,2,{60*factor:.0f},{60*factor:.0f},{25*factor:.0f},1
Style: Research,Arial,{14*factor:.1f},&H00D9E3F0,&H00D9E3F0,&H80000000,&H80000000,0,0,0,0,100,100,0,0,3,3,0,7,{20*factor:.0f},{20*factor:.0f},{18*factor:.0f},1
Style: Unsupported,Arial,{17*factor:.1f},&H00D5E4F3,&H00D5E4F3,&H80000000,&H80000000,0,0,0,0,100,100,0,0,3,3,0,8,{40*factor:.0f},{40*factor:.0f},{45*factor:.0f},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[]
    def add(start,end,style,text):
        start=max(0,min(duration,start));end=max(start,min(duration,end))
        if end<=start or not str(text).strip():return
        events.append(f'Dialogue: 0,{stamp(start)},{stamp(end)},{style},,0,0,0,,{literal(text)}')
    subtitles=settings.get('subtitles',True)
    unsupported=job.get('render_unsupported_intervals',[]) if neural else []
    if subtitles:
        for segment in job.get('segments',[]):add(segment['start']*scale,segment['end']*scale,'Caption',segment['text'])
    else:
        # Unsupported signing must retain the speech text even when general
        # captions are disabled. Both intervals use the output video clock.
        for item in unsupported:
            for segment in job.get('segments',[]):
                start=max(item['start'],segment['start']*scale)
                end=min(item['end'],segment['end']*scale)
                if end>start:add(start,end,'Caption',segment['text'])
    if neural:
        add(0,duration,'Research','Tajribaviy ASL · tasdiqlanmagan')
        for item in unsupported:add(item['start'],item['end'],'Unsupported','Avatar ijrosi yo‘q — subtitr bilan beriladi')
    return header+'\n'.join(events)+'\n'
