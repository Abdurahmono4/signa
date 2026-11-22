from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8')
s=s.replace("import {HumanSigner} from './HumanSigner';", "import {HumanSigner} from './HumanSigner';\nimport {CorpusLibrary} from './CorpusLibrary';\nimport type {CorpusState} from './CorpusLibrary';")
s=s.replace("useState<{phase:string;metadata_ready:boolean;clips:{id:string;text:string;duration:number;video_url:string}[]}|null>(null)","useState<CorpusState|null>(null)")
s=s.replace("['library','▦','Ishoralar kutubxonasi']", "['corpus','▦','ASL video kutubxonasi'],['library','◇','Animatsiya importi']")
s=s.replace("{page==='settings'?<section", "{page==='corpus'?<CorpusLibrary dataset={dataset} onUse={c=>{setPage('studio');setMode('text');setText(c.text);setSequence(null);setTime(0);setPlaying(false)}}/>:page==='settings'?<section")
s=s.replace("dataset?.clips.map(c=><button", "dataset?.clips.slice(0,5).map(c=><button")
s=s.replace('<h2>How2Sign tadqiqot to‘plami</h2>', '<h2>How2Sign tadqiqot to‘plami</h2><button onClick={()=>setPage(\'corpus\')}>Barcha kliplar va qidiruv →</button>')
s=s.replace('Ushbu matn uchun tekshirilgan o‘zbek ishoralari yo‘q.', 'Ushbu matn uchun mos tarjimon ijrosi topilmadi.')
p.write_text(s,encoding='utf-8')
p=Path('frontend/src/style.css');p.write_text(p.read_text(encoding='utf-8')+'''
.corpus-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-bottom:24px}.corpus-stats>div{padding:20px;border:1px solid #303d5a;background:#151f36;border-radius:14px}.corpus-stats b{display:block;font-size:32px;color:#aebaff}.corpus-stats span{font-size:11px;color:#9daecc}.corpus-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,.8fr);gap:24px}.corpus-results{display:grid;gap:8px}.corpus-row{text-align:left;background:#101a2f;padding:15px}.corpus-row span,.corpus-row small{display:block}.corpus-row small{margin-top:7px}.corpus-row.selected{border-color:#8c8be6;background:#252b50}.corpus-preview{position:sticky;top:20px;align-self:start}.corpus-preview .human-signer{margin:auto;max-width:100%}.corpus-preview h3{margin-top:18px}.pagination{display:flex;justify-content:space-between;align-items:center;margin-top:18px;gap:12px}.pagination span{font-size:11px}.corpus-preview a{color:#b8c4ff}@media(max-width:800px){.corpus-layout{grid-template-columns:1fr}.corpus-preview{position:static;grid-row:1}.corpus-stats{gap:8px}.corpus-stats>div{padding:12px}.corpus-stats b{font-size:25px}}
''',encoding='utf-8')
