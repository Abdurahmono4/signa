import unittest
import json
from pathlib import Path
from unittest.mock import patch
import test_api
from app import signs


def clip(purpose='sign'):
    return {'purpose':purpose,'phrase':'A test phrase.','source':'Synthetic API fixture, not real ASL',
            'license':'CC0','duration':2,'keyframes':[{'time':0,'rotations':{'head':[0,0,0]}},
                                                     {'time':2,'rotations':{'head':[0,0,0]}}]}


def alphabet_fixture(letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ',duration=1):
    return [{'id':f'asl-letter-{letter.lower()}','animation_asset':f'asl-letter-{letter.lower()}',
             'phrase':letter,'letter':letter,'kind':'fingerspelling','purpose':'sign','language':'ASL',
             'source':'Synthetic scheduler fixture, not real ASL','license':'CC0','status':'source',
             'duration':duration,'keyframes':[]} for letter in letters]


class SignsTest(unittest.TestCase):
    setUp = test_api.APITest.setUp
    tearDown = test_api.APITest.tearDown
    # Reuse the isolated database setup without approving anything in user data.
    def test_draft_cannot_be_used_for_translation(self):
        result=self.client.post('/api/signs',json=clip())
        self.assertEqual(result.status_code,201)
        segment={'start':0,'end':2,'text':'A test phrase.'}
        self.assertEqual(signs.plan([segment])['matched'],0)
        review={'reviewer':'Test fixture','decision':'approved','notes':'Synthetic test, no real linguistic validation.'}
        self.assertEqual(self.client.post(f"/api/signs/{result.json()['id']}/review",json=review).status_code,200)
        self.assertEqual(signs.plan([segment])['items'][0]['status'],'unsupported_rig')
        self.assertEqual(signs.plan([{**segment,'text':'A test'}])['matched'],0)
        self.assertEqual(signs.plan([{**segment,'end':.1}])['items'][0]['status'],'unsupported_rig')

    def test_source_motion_is_not_automatically_approved(self):
        assets=self.client.get('/api/signs/corpus').json()
        frontend_assets=Path(__file__).resolve().parents[2]/'frontend'/'public'/'avatar'
        self.assertEqual(assets,json.loads((frontend_assets/'corpus.json').read_text(encoding='utf-8')))
        self.assertGreaterEqual(len(assets),12)
        self.assertEqual(len({asset['id'] for asset in assets}),len(assets))
        for asset in assets:
            self.assertTrue((frontend_assets/f"{asset['id']}.motion.json").is_file())
            self.assertEqual(asset['status'],'source')
            self.assertEqual(asset['license'],'CC0-1.0')
        item=next(c for c in assets if c['id']=='hello')
        segment={'start':0,'end':item['duration'],'text':'Hello!'}
        self.assertEqual(signs.plan([segment])['matched'],0)
        preview=signs.plan([segment],include_source=True)
        self.assertEqual(preview['items'][0]['status'],'source_preview')
        result=self.client.post('/api/signs/corpus/hello/import')
        self.assertEqual(result.status_code,201)
        self.assertEqual(result.json()['status'],'draft')
        review={'reviewer':'Test fixture','decision':'approved','notes':'Automated fixture, not linguistic certification.'}
        self.client.post(f"/api/signs/{result.json()['id']}/review",json=review)
        self.assertEqual(signs.plan([segment])['matched'],1)
        self.assertEqual(signs.plan([{**segment,'end':.1}])['items'][0]['status'],'timing_review')
        self.assertEqual(signs.plan([{**segment,'text':'Hello everyone'}])['matched'],0)
        self.assertEqual(self.client.post('/api/signs/corpus/missing/import').status_code,404)

    def test_motion_asset_cannot_reference_arbitrary_files(self):
        data={**clip(),'keyframes':[],'animation_asset':'../../private'}
        self.assertEqual(self.client.post('/api/signs',json=data).status_code,422)
        data['animation_asset']='hello'
        self.assertEqual(self.client.post('/api/signs',json=data).status_code,422)

    def test_every_corpus_phrase_is_playable_at_its_recorded_duration(self):
        for asset in signs.corpus():
            with self.subTest(asset=asset['id']):
                segment={'start':0,'end':.25,'text':asset['phrase']}
                result=signs.playback_plan([segment],.25,include_source=True,fingerspelling=True)
                self.assertEqual(result['playable_signs'],1)
                self.assertEqual(result['missing_words'],[])
                self.assertFalse(result['complete_translation'])
                motion=result['items'][0]
                self.assertEqual(motion['status'],'source_preview')
                self.assertEqual(motion['clip']['animation_asset'],asset['id'])
                self.assertAlmostEqual(motion['duration'],asset['duration'])
                self.assertAlmostEqual(result['playback_duration'],max(.25,asset['duration']))
                self.assertEqual(signs.playback_plan([segment],.25)['playable_signs'],0)

    def test_invalid_motion_and_calibration_not_approved(self):
        bad=clip();bad['keyframes'][0]['rotations']={'unknown':[0,0,0]}
        self.assertEqual(self.client.post('/api/signs',json=bad).status_code,422)
        bad=clip();bad['keyframes'][1]['time']=0
        self.assertEqual(self.client.post('/api/signs',json=bad).status_code,422)
        result=self.client.post('/api/signs',json=clip('calibration')).json()
        review={'reviewer':'Test fixture','decision':'approved','notes':'Synthetic test, no linguistic validation.'}
        self.assertEqual(self.client.post(f"/api/signs/{result['id']}/review",json=review).status_code,422)

    def test_dictionary_uses_longest_phrase_and_preserves_unknown_words(self):
        segment={'start':0,'end':8,'text':'My name is Alex. Hello, please!'}
        result=signs.lexical_plan([segment],include_source=True)
        self.assertEqual(result['mode'],'dictionary_assistance')
        self.assertEqual([item['text'] for item in result['items']],['my name is','alex','hello','please'])
        self.assertEqual(result['source_previews'],3)
        self.assertEqual(result['missing_words'],['alex'])
        self.assertEqual(result['missing'],1)
        self.assertEqual(result['total_words'],6)
        self.assertEqual(result['covered_words'],5)
        self.assertEqual(result['coverage'],83)
        self.assertTrue(all(item['timing']=='estimated' for item in result['items']))
        self.assertEqual(result['items'][0]['start'],0)
        self.assertEqual(result['items'][-1]['end'],8)

    def test_unicode_unknown_words_and_punctuation_are_preserved(self):
        segment={'start':0,'end':12,'text':"My 你好, café—book; O’Neil can't."}
        result=signs.lexical_plan([segment],include_source=True)
        self.assertEqual([item['text'] for item in result['items']],
                         ['my','你好','café','book',"o'neil","can't"])
        self.assertEqual(result['total_words'],6)
        self.assertEqual(result['covered_words'],2)
        self.assertEqual(result['coverage'],33)
        self.assertEqual(result['missing_words'],['你好','café',"o'neil","can't"])
        self.assertEqual(signs.normalized('hello-world,HELLO/world'),'hello world hello world')
        self.assertEqual(signs.normalized("Ｈｅｌｌｏ Cafe\u0301 l’amour 'quote'"),"hello café l'amour quote")
        self.assertEqual(signs.normalized('नाम १२३'),'नाम १२३')

    def test_dictionary_keeps_alignment_and_blocks_extreme_playback_speed(self):
        segment={'start':2,'end':9,'text':'Hello book','words':[
            {'word':' Hello','start':2,'end':4.2},
            {'word':' book','start':4.2,'end':4.3}]}
        result=signs.lexical_plan([segment],include_source=True)
        self.assertEqual([item['status'] for item in result['items']],['source_preview','timing_review'])
        self.assertTrue(all(item['timing']=='aligned' for item in result['items']))
        self.assertEqual((result['items'][1]['start'],result['items'][1]['end']),(4.2,4.3))
        self.assertEqual(result['timing_review'],1)
        self.assertEqual(result['covered_words'],1)
        self.assertEqual(result['coverage'],50)
        self.assertEqual(result['missing_words'],[])

    def test_dictionary_reports_legacy_rig_instead_of_omitting_it(self):
        imported=self.client.post('/api/signs',json=clip()).json()
        segment={'start':0,'end':2,'text':'A test phrase.'}
        self.assertEqual(signs.lexical_plan([segment])['missing'],3)
        review={'reviewer':'Test fixture','decision':'approved','notes':'Synthetic test, no linguistic validation.'}
        self.client.post(f"/api/signs/{imported['id']}/review",json=review)
        result=signs.lexical_plan([segment])
        self.assertEqual(result['unsupported_rig'],1)
        self.assertEqual(result['items'][0]['status'],'unsupported_rig')
        self.assertEqual(result['items'][0]['clip']['id'],imported['id'])
        self.assertEqual(result['total_words'],3)
        self.assertEqual(result['covered_words'],0)
        self.assertEqual(result['missing_words'],[])

    def test_legacy_approved_calibration_is_excluded_from_both_planners(self):
        imported=self.client.post('/api/signs',json=clip('calibration')).json()
        # Simulate an older database whose calibration row was already approved.
        with signs.connection() as db:
            db.execute("UPDATE signs SET status='approved' WHERE id=?",(imported['id'],))
        segment={'start':0,'end':2,'text':'A test phrase.'}
        self.assertEqual(signs.plan([segment])['items'][0]['status'],'missing')
        result=signs.lexical_plan([segment])
        self.assertEqual(result['missing'],3)
        self.assertTrue(all(item['clip'] is None for item in result['items']))

    def test_edited_transcript_ignores_stale_word_alignment(self):
        segment={'start':0,'end':4,'text':'My book','edited':True,'words':[
            {'word':' My','start':0,'end':.1},
            {'word':' book','start':.1,'end':.2}]}
        result=signs.lexical_plan([segment],include_source=True)
        self.assertEqual([(item['start'],item['end']) for item in result['items']],[(0,2),(2,4)])
        self.assertTrue(all(item['timing']=='estimated' for item in result['items']))
        self.assertEqual(result['source_previews'],2)

    def test_sign_plan_endpoint_requires_ready_job_and_respects_review(self):
        upload=self.client.post('/api/jobs',files={'file':('sample.wav',test_api.wav_bytes(),'audio/wav')})
        self.assertEqual(upload.status_code,201)
        url=f"/api/jobs/{upload.json()['id']}"
        self.assertEqual(self.client.get(url+'/sign-plan').status_code,409)
        edited=self.client.put(url+'/transcript',json={'revision':0,'segments':[
            {'start':0,'end':.9,'text':'My'}]})
        self.assertEqual(edited.status_code,200)
        self.assertEqual(self.client.get(url+'/sign-plan').json()['missing'],1)
        preview=self.client.get(url+'/sign-plan?include_source=true').json()
        self.assertEqual(preview['source_previews'],1)
        self.assertEqual(preview['matched'],0)
        self.assertEqual(preview['coverage'],100)
        imported=self.client.post('/api/signs/corpus/my/import').json()
        self.assertEqual(self.client.get(url+'/sign-plan').json()['matched'],0)
        review={'reviewer':'Test fixture','decision':'approved','notes':'Automated fixture, not linguistic certification.'}
        self.client.post(f"/api/signs/{imported['id']}/review",json=review)
        approved=self.client.get(url+'/sign-plan').json()
        self.assertEqual(approved['matched'],1)
        self.assertEqual(approved['source_previews'],0)
        self.assertEqual(approved['items'][0]['status'],'matched')

    def test_paced_plan_plays_fast_speech_clips_naturally_and_preserves_gaps(self):
        segments=[{'start':1,'end':1.2,'text':'Hello'},
                  {'start':3,'end':4,'text':'Unknown'}]
        with patch.object(signs,'fingerspelling_alphabet',return_value={}):
            result=signs.playback_plan(segments,5,include_source=True)
        self.assertEqual(result['mode'],'dictionary_assistance')
        self.assertEqual(result['playback'],'paced')
        self.assertFalse(result['complete_translation'])
        self.assertEqual([item['status'] for item in result['items']],
                         ['gap','source_preview','gap','missing','gap'])
        motion=result['items'][1]
        self.assertEqual(motion['sync_status'],'timing_review')
        self.assertEqual((motion['start'],motion['end']),(1,1.2))
        self.assertEqual((motion['media_start'],motion['media_end']),(1,1.2))
        self.assertAlmostEqual(motion['duration'],motion['clip']['duration']/1.25)
        self.assertEqual(motion['playback_rate'],1.25)
        self.assertAlmostEqual(motion['hold_duration'],motion['duration']-.2)
        self.assertAlmostEqual(result['playback_duration'],5+motion['hold_duration'])
        self.assertEqual(result['missing_words'],['unknown'])
        self.assertEqual(result['items'][3]['clip'],None)
        self.assertEqual(result['playable_signs'],1)
        self.assertEqual(motion['clip']['keyframes'],[])
        self.assertNotIn('download',motion['clip'])
        self.assertTrue(result['limitations'])

    def test_spelling_keeps_dictionary_priority_and_alphabet_out_of_lexical_plan(self):
        hello=next(asset for asset in signs.corpus() if asset['id']=='hello')
        with patch.object(signs,'corpus',return_value=[hello]+alphabet_fixture()):
            segments=[{'start':0,'end':1,'text':'Hello A'}]
            lexical=signs.lexical_plan(segments,include_source=True)
            self.assertEqual([item['status'] for item in lexical['items']],['timing_review','missing'])
            result=signs.playback_plan(segments,1,include_source=True,fingerspelling=True)
            self.assertEqual([item['rendering'] for item in result['items']],['sign','fingerspelling'])
            self.assertEqual(result['items'][0]['clip']['id'],'hello')
            self.assertEqual(result['items'][1]['letter'],'A')
            self.assertEqual(result['signed_words'],1)
            self.assertEqual(result['spelled_words'],1)
            self.assertEqual(result['missing_words'],[])
            self.assertEqual(result['dictionary_missing_words'],['a'])
            self.assertFalse(result['complete_translation'])

    def test_unknown_latin_word_uses_complete_natural_letter_sequence_and_media_hold(self):
        with patch.object(signs,'corpus',return_value=alphabet_fixture()):
            result=signs.playback_plan([{'start':.2,'end':.5,'text':'Eva'}],1,include_source=True,fingerspelling=True)
        letters=[item for item in result['items'] if item['rendering']=='fingerspelling']
        self.assertEqual([item['letter'] for item in letters],list('EVA'))
        self.assertEqual([item['clip']['animation_asset'] for item in letters],['asl-letter-e','asl-letter-v','asl-letter-a'])
        self.assertTrue(all(item['word_text']=='Eva' for item in letters))
        self.assertEqual([item['word_count'] for item in letters],[1,0,0])
        self.assertEqual([(item['media_play_start'],item['media_play_end']) for item in letters],[(.2,.5),(.5,.5),(.5,.5)])
        self.assertEqual([item['duration'] for item in letters],[1,1,1])
        self.assertEqual([item['rendering'] for item in result['items']],['gap','fingerspelling','fingerspelling','fingerspelling','gap'])
        for previous,current in zip(result['items'],result['items'][1:]):
            self.assertAlmostEqual(previous['playback_end'],current['playback_start'])
            self.assertLessEqual(previous['media_play_end'],current['media_play_start'])
        self.assertAlmostEqual(result['hold_duration'],2.7)
        self.assertAlmostEqual(result['playback_duration'],3.7)
        self.assertAlmostEqual(sum(item['media_play_end']-item['media_play_start'] for item in result['items']),1)
        self.assertEqual((result['total_words'],result['signed_words'],result['spelled_words'],result['caption_words']),(1,0,1,0))
        self.assertEqual(result['fingerspelling_letters'],3)

    def test_installed_complete_alphabet_plays_all_26_authentic_assets(self):
        alphabet=signs.fingerspelling_alphabet(include_source=True)
        self.assertEqual(set(alphabet),set('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        result=signs.playback_plan([{'start':0,'end':1,'text':'ABCDEFGHIJKLMNOPQRSTUVWXYZ'}],1,include_source=True,fingerspelling=True)
        letters=[item for item in result['items'] if item['rendering']=='fingerspelling']
        self.assertEqual(''.join(item['letter'] for item in letters),'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self.assertEqual(result['spelled_words'],1)
        self.assertEqual(result['signed_words'],0)
        self.assertEqual(result['caption_words'],0)
        self.assertEqual(result['missing_words'],[])
        self.assertAlmostEqual(result['playback_duration'],sum(alphabet[letter]['duration'] for letter in alphabet))
        for item in letters:
            self.assertEqual(item['clip']['animation_asset'],f"asl-letter-{item['letter'].lower()}")
            self.assertEqual(item['duration'],alphabet[item['letter']]['duration'])
            self.assertEqual(item['clip']['kind'],'fingerspelling')
            self.assertEqual(item['clip']['status'],'source')

    def test_default_quick_word_mode_never_automatically_spells_unknown_words(self):
        self.assertEqual(len(signs.fingerspelling_alphabet(include_source=True)),26)
        segments=[{'start':.2,'end':1.8,'text':'Every sentence contains several unsupported words'}]
        result=signs.playback_plan(segments,2,include_source=True)
        self.assertFalse(result['fingerspelling_enabled'])
        self.assertEqual(result['presentation'],'words')
        self.assertEqual(result['spelled_words'],0)
        self.assertEqual(result['fingerspelling_letters'],0)
        self.assertEqual(result['hold_duration'],0)
        self.assertEqual(result['playback_duration'],2,'Unknown words must not lengthen quick playback')
        self.assertEqual(result['caption_words'],6)
        self.assertTrue(all(item['rendering'] in {'caption','gap'} for item in result['items']))
        optional=signs.playback_plan(segments,2,include_source=True,fingerspelling=True)
        self.assertTrue(optional['fingerspelling_enabled'])
        self.assertEqual(optional['presentation'],'fingerspelling')
        self.assertEqual(optional['spelled_words'],6)
        self.assertGreater(optional['playback_duration'],2)

    def test_quick_word_timing_only_uses_verified_canonical_motion_windows(self):
        asset={'id':'fixture-hello','animation_asset':'fixture-hello','phrase':'Hello','purpose':'sign',
               'language':'ASL','status':'source','source':'Synthetic timing fixture, not real ASL',
               'license':'CC0','duration':4,'keyframes':[],
               'playback_window':{'start':.5,'end':3.5,'verified':True}}
        segments=[{'start':0,'end':.25,'text':'Hello'}]
        with patch.object(signs,'corpus',return_value=[asset]):
            result=signs.playback_plan(segments,.25,include_source=True)
            motion=result['items'][0]
            self.assertEqual((motion['clip_start'],motion['clip_end'],motion['playback_rate']),(.5,3.5,1.25))
            self.assertAlmostEqual(motion['duration'],2.4)
            self.assertEqual(motion['clip']['duration'],4,'Recorded source duration remains intact')
            natural=signs.playback_plan(segments,.25,include_source=True,fingerspelling=True)['items'][0]
            self.assertEqual((natural['clip_start'],natural['clip_end'],natural['playback_rate']),(0,4,1))
            self.assertEqual(natural['duration'],4)
        for window in [{'start':.5,'end':3.5,'verified':False},{'start':-.5,'end':3.5,'verified':True},
                       {'start':.5,'end':4.5,'verified':True},{'start':3.5,'end':.5,'verified':True}]:
            with self.subTest(window=window),patch.object(signs,'corpus',return_value=[{**asset,'playback_window':window}]):
                motion=signs.playback_plan(segments,.25,include_source=True)['items'][0]
                self.assertEqual((motion['clip_start'],motion['clip_end']),(0,4))
                self.assertAlmostEqual(motion['duration'],3.2)

    def test_spelling_apostrophes_and_unsupported_characters_are_explicit(self):
        with patch.object(signs,'corpus',return_value=alphabet_fixture()):
            result=signs.playback_plan([{'start':0,'end':2,'text':"Don't O’Neil café 你好 123 Straße"}],2,include_source=True,fingerspelling=True)
        letters=[item['letter'] for item in result['items'] if item['rendering']=='fingerspelling']
        self.assertEqual(''.join(letters),'DONTONEIL')
        self.assertEqual(result['spelled_words'],2)
        self.assertEqual(result['caption_words'],4)
        self.assertEqual(result['missing_words'],['café','你好','123','strasse'])
        captions=[item for item in result['items'] if item['rendering']=='caption']
        self.assertEqual(captions[-1]['word_text'],'Straße','Casefold must not turn a non-ASCII source word into eligible Latin spelling')
        self.assertTrue(all(item['clip'] is None for item in captions))

    def test_missing_letter_never_silently_spells_a_partial_word(self):
        with patch.object(signs,'corpus',return_value=alphabet_fixture('ABC')):
            result=signs.playback_plan([{'start':0,'end':1,'text':'CAB ZAP'}],1,include_source=True,fingerspelling=True)
        self.assertEqual(''.join(item['letter'] or '' for item in result['items']),'CAB')
        self.assertEqual(result['spelled_words'],1)
        self.assertEqual(result['missing_words'],['zap'])
        self.assertEqual(result['items'][-1]['rendering'],'caption')
        self.assertEqual(result['items'][-1]['word_text'],'ZAP')

    def test_overlapping_words_and_zero_media_letter_slots_never_replay_audio(self):
        segment={'start':0,'end':.2,'text':'AB CD','words':[
            {'word':' AB','start':.1,'end':.2},{'word':' CD','start':.1,'end':.2}]}
        with patch.object(signs,'corpus',return_value=alphabet_fixture()):
            result=signs.playback_plan([segment],1,include_source=True,fingerspelling=True)
        letters=[item for item in result['items'] if item['rendering']=='fingerspelling']
        self.assertEqual(''.join(item['letter'] for item in letters),'ABCD')
        self.assertEqual([(item['media_play_start'],item['media_play_end']) for item in letters],[(.1,.2),(.2,.2),(.2,.2),(.2,.2)])
        self.assertTrue(all(item['slot_duration']==1 for item in letters))
        self.assertEqual(result['spelled_words'],2)
        self.assertAlmostEqual(sum(item['media_play_end']-item['media_play_start'] for item in result['items']),1)
        self.assertAlmostEqual(result['playback_duration'],1+result['hold_duration'])

    def test_spelling_limits_preserve_whole_words_and_bounded_duration(self):
        with patch.object(signs,'corpus',return_value=alphabet_fixture()),patch.object(signs,'MAX_SPELLING_WORD_LENGTH',3):
            result=signs.playback_plan([{'start':0,'end':1,'text':'ABCD'}],1,include_source=True,fingerspelling=True)
        self.assertEqual(result['spelling_limits']['limit_reasons'],{'abcd':'word_length'})
        self.assertEqual(result['spelled_words'],0)
        self.assertEqual(result['playback_duration'],1)
        with patch.object(signs,'corpus',return_value=alphabet_fixture()),patch.object(signs,'MAX_SPELLING_LETTERS',3):
            result=signs.playback_plan([{'start':0,'end':1,'text':'AB CD'}],1,include_source=True,fingerspelling=True)
        self.assertEqual(result['spelled_words'],1)
        self.assertEqual(result['fingerspelling_letters'],2)
        self.assertEqual(result['spelling_limits']['limit_reasons'],{'cd':'letter_budget'})
        with patch.object(signs,'corpus',return_value=alphabet_fixture()),patch.object(signs,'MAX_SPELLING_HOLD_SECONDS',2):
            result=signs.playback_plan([{'start':0,'end':.5,'text':'AB CD'}],.5,include_source=True,fingerspelling=True)
        self.assertEqual(result['spelled_words'],1)
        self.assertEqual(result['spelling_limits']['limit_reasons'],{'cd':'duration_budget'})
        self.assertLessEqual(result['hold_duration'],2)
        self.assertEqual(result['missing_words'],['cd'])

    def test_legacy_imported_alphabet_cannot_masquerade_as_dictionary_word(self):
        asset=alphabet_fixture('A')[0]
        legacy={key:value for key,value in asset.items() if key not in {'id','status','kind','letter'}}
        with signs.connection() as db:
            db.execute("INSERT INTO signs (id,clip,status) VALUES (?,?,'approved')",('legacy-a',json.dumps(legacy)))
        with patch.object(signs,'corpus',return_value=[asset]):
            self.assertEqual(signs.lexical_plan([{'start':0,'end':1,'text':'A'}])['items'][0]['status'],'missing')
            result=signs.playback_plan([{'start':0,'end':1,'text':'A'}],1,fingerspelling=True)
            self.assertEqual(result['items'][0]['rendering'],'fingerspelling')
            self.assertEqual(result['items'][0]['letter'],'A')
            self.assertEqual(result['signed_words'],0)
            self.assertEqual(result['spelled_words'],1)

    def test_spelling_endpoint_opt_in_and_alphabet_import_metadata(self):
        upload=self.client.post('/api/jobs',files={'file':('sample.wav',test_api.wav_bytes(),'audio/wav')}).json()
        url=f"/api/jobs/{upload['id']}"
        self.client.put(url+'/transcript',json={'revision':0,'segments':[{'start':0,'end':.9,'text':'Eva'}]})
        with patch.object(signs,'corpus',return_value=alphabet_fixture()):
            self.assertEqual(self.client.get(url+'/playback-plan').json()['spelled_words'],0)
            quick=self.client.get(url+'/playback-plan?include_source=true').json()
            self.assertFalse(quick['fingerspelling_enabled'])
            self.assertEqual(quick['presentation'],'words')
            self.assertEqual(quick['playback_duration'],1)
            self.assertEqual(quick['hold_duration'],0)
            result=self.client.get(url+'/playback-plan?include_source=true&fingerspelling=true').json()
            self.assertEqual(result['spelled_words'],1)
            self.assertEqual([item['letter'] for item in result['items'] if item['clip']],list('EVA'))
            imported=self.client.post('/api/signs/corpus/asl-letter-a/import').json()
            saved=next(item for item in self.client.get('/api/signs').json() if item['id']==imported['id'])
            self.assertEqual((saved['kind'],saved['letter']),('fingerspelling','A'))

    def test_paced_plan_partitions_overlapping_alignment_without_media_replay(self):
        segment={'start':0,'end':.3,'text':'Hello my','words':[
            {'word':' Hello','start':0,'end':.2},
            {'word':' my','start':.1,'end':.3}]}
        result=signs.playback_plan([segment],1,include_source=True)
        first,second,trailing=result['items']
        self.assertEqual(second['media_start'],.1)
        self.assertEqual(second['media_play_start'],.2)
        self.assertEqual(second['media_play_end'],.3)
        self.assertEqual(second['playback_start'],first['playback_end'])
        self.assertEqual(second['timing'],'aligned')
        self.assertEqual(trailing['status'],'gap')
        self.assertAlmostEqual(sum(item['media_play_end']-item['media_play_start'] for item in result['items']),1)
        self.assertAlmostEqual(result['playback_duration'],1+result['hold_duration'])

    def test_paced_plan_never_invents_unknown_or_unsupported_motion(self):
        imported=self.client.post('/api/signs',json=clip()).json()
        review={'reviewer':'Test fixture','decision':'approved','notes':'Synthetic test, no linguistic validation.'}
        self.client.post(f"/api/signs/{imported['id']}/review",json=review)
        result=signs.playback_plan([{'start':0,'end':2,'text':'A test phrase.'},
                                    {'start':2,'end':3,'text':'你好'}],4)
        self.assertEqual([item['status'] for item in result['items']],['unsupported_rig','missing','gap'])
        self.assertTrue(all(item['clip'] is None for item in result['items']))
        self.assertEqual(result['playable_signs'],0)
        self.assertEqual(result['total_words'],4)
        self.assertEqual(result['hold_duration'],0)
        self.assertEqual(result['playback_duration'],4)
        self.assertEqual(signs.playback_plan([],3)['items'][0]['status'],'gap')

    def test_paced_endpoint_ready_state_opt_in_and_backward_compatibility(self):
        upload=self.client.post('/api/jobs',files={'file':('sample.wav',test_api.wav_bytes(),'audio/wav')})
        self.assertEqual(upload.status_code,201)
        job_id=upload.json()['id']
        url=f'/api/jobs/{job_id}'
        self.assertEqual(self.client.get(url+'/playback-plan').status_code,409)
        self.assertEqual(self.client.get('/api/jobs/missing/playback-plan').status_code,404)
        self.client.put(url+'/transcript',json={'revision':0,'segments':[
            {'start':.1,'end':.2,'text':'Hello'}]})
        hidden=self.client.get(url+'/playback-plan').json()
        self.assertEqual(hidden['playable_signs'],0)
        self.assertFalse(hidden['source_preview_enabled'])
        result=self.client.get(url+'/playback-plan?include_source=true')
        self.assertEqual(result.status_code,200,result.text)
        result=result.json()
        self.assertEqual(result['job_id'],job_id)
        self.assertEqual(result['revision'],1)
        self.assertEqual(result['source_previews'],1)
        self.assertEqual(result['items'][1]['status'],'source_preview')
        self.assertEqual(result['items'][1]['timing'],'estimated')
        self.assertEqual(self.client.get(url+'/sign-plan?include_source=true').json()['items'][0]['status'],'timing_review')
