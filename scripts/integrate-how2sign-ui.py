from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8')
s=s.replace("import {Avatar} from './Avatar';", "import {Avatar} from './Avatar';\nimport {HumanSigner} from './HumanSigner';")
s=s.replace("model:'small'", "model:'tiny',language:'en'")
s=s.replace(" const avatar=useRef", " const [dataset,setDataset]=useState<{phase:string;metadata_ready:boolean;clips:{id:string;text:string;duration:number;video_url:string}[]}|null>(null);\n useEffect(()=>{const load=()=>api<any>('/how2sign').then(setDataset).catch(()=>{});load();const timer=setInterval(load,10000);return()=>clearInterval(timer)},[]);\n const avatar=useRef")
s=s.replace('model:settings.model}', 'model:settings.model,language:settings.language}')
s=s.replace('json({text})','json({text,language:settings.language})')
s=s.replace('<Avatar time={time} items={items} demo={demo} onReady={onReady} onError={onError}/>', "{settings.language==='en'&&!demo&&page==='studio'?<HumanSigner time={time} items={items} playing={playing} onReady={onReady} onError={onError}/>:<Avatar time={time} items={items} demo={demo} onReady={onReady} onError={onError}/>}")
s=s.replace('<h2>3D tarjimon</h2>',"<h2>{settings.language==='en'&&!demo?'ASL tarjimon videosi':'3D tarjimon'}</h2>")
s=s.replace('O‘zbekcha nutq, vaqtli subtitr va tekshirilgan imo-ishoralar — bir maydonda.', 'Inglizcha nutq, How2Sign manba videolari va vaqtli subtitr — bir maydonda.')
s=s.replace('<h2>Ijro va eksport sozlamalari</h2>', '<h2>Ijro va eksport sozlamalari</h2><label>Nutq va ishora yo‘nalishi<select value={settings.language} onChange={e=>setSettings({...settings,language:e.target.value})}><option value="en">Inglizcha → ASL manba videolari</option><option value="uz">O‘zbekcha → tekshirilgan mahalliy ishoralar</option></select></label>')
s=s.replace('O‘zbekcha matn', 'Kirish matni').replace('MP4 da original audio, subtitr va neytral avatar bo‘ladi; bu imo-ishora tarjimasi hisoblanmaydi.', 'MP4 da original audio va subtitr saqlanadi. Mos tarjimon videosi yo‘q bo‘laklar tarjima qilingan deb belgilanmaydi.')
s=s.replace('{page===\'studio\'&&coverage&&', '''{page==='studio'&&settings.language==='en'&&<section className="card coverage"><div className="section-head"><h2>How2Sign tadqiqot to‘plami</h2><span>{dataset?.clips.length||0} klip</span></div><p>{dataset?.phase||'To‘plam tekshirilmoqda'} · {dataset?.metadata_ready?'Matn metadata tayyor':'Metadata kutilmoqda'}</p><p>ZIP ni datasets/how2sign yoki Downloads papkasida saqlang. ASL manba kliplari mustaqil lingvistik tekshiruvdan o‘tmagan. CC BY-NC 4.0 · tadqiqot uchun.</p><div className="segments">{dataset?.clips.map(c=><button key={c.id} onClick={()=>{setMode('text');setText(c.text);setSequence(null);setTime(0);setPlaying(false)}}>{c.text}<small>{c.duration.toFixed(1)} soniya · matn rejimida sinash</small></button>)}</div></section>}
 {page==='studio'&&coverage&&''')
p.write_text(s,encoding='utf-8')
p=Path('frontend/src/style.css');p.write_text(p.read_text(encoding='utf-8')+'''
.human-signer{width:384px;max-width:100%;aspect-ratio:3/4;position:relative;background:#000;color:#dce2f4}
.human-signer video{width:100%;height:100%;object-fit:contain;display:block}
.signer-placeholder{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;text-align:center}
.signer-placeholder>span{font-size:32px;color:#8099e4;margin-bottom:20px}.signer-placeholder p{font-size:11px;margin-top:12px}
.broadcast-interpreter .human-signer{width:100%}
''',encoding='utf-8')
