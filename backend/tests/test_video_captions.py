from backend.app.video_captions import make_ass,literal

def job():return {'duration':5,'segments':[{'start':0,'end':5,'text':'All original words are kept.'}],'settings':{'engine':'neural','subtitles':True},'render_unsupported_intervals':[{'start':2,'end':3}]}

def test_main_caption_and_research_label_use_separate_sizes_and_positions():
    text=make_ass(job(),1280,720)
    assert 'Style: Caption,Arial,32.0' in text and 'Style: Research,Arial,14.0' in text
    assert 'All original words are kept.' in text and 'Tajribaviy ASL' in text
    assert '0:00:02.00,0:00:03.00,Unsupported' in text
    assert ',3,3,0,2,60,60,25,1' in text # subtitle bottom center
    assert ',3,3,0,7,20,20,18,1' in text # small label top left

def test_1080p_styles_scale_and_timestamps_follow_paced_output():
    data=job();data.update(timing_scale=2,output_duration=10)
    text=make_ass(data,1920,1080)
    assert 'Style: Caption,Arial,48.0' in text
    assert '0:00:00.00,0:00:10.00,Caption' in text

def test_subtitle_toggle_keeps_unsupported_speech_and_required_label():
    data=job();data['settings']['subtitles']=False
    text=make_ass(data,1280,720)
    assert '0:00:02.00,0:00:03.00,Caption' in text and 'All original words' in text and 'Tajribaviy ASL' in text
    data['settings']['engine']='human'
    assert 'Dialogue:' not in make_ass(data,1280,720)

def test_unsupported_fallback_uses_paced_timestamps_and_only_overlaps():
    data=job();data.update(timing_scale=2,output_duration=10)
    data['settings']['subtitles']=False
    data['segments']=[{'start':0,'end':1,'text':'Signed words'},{'start':1,'end':2,'text':'Fallback words'}]
    text=make_ass(data,1280,720)
    assert 'Signed words' not in text and 'Fallback words' in text
    assert '0:00:02.00,0:00:03.00,Caption' in text

def test_override_like_transcript_is_display_text_not_ass_commands():
    assert literal(r'{\pos(1,1)}Hello')=='｛＼pos(1,1)｝Hello'
    assert literal('one\ntwo')==r'one\Ntwo'
