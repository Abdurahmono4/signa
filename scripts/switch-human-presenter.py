from pathlib import Path
p=Path(r'D:\SignBridge-UZ\frontend\src\main.tsx');s=p.read_text(encoding='utf-8')
def replace(a,b):
 global s
 assert a in s,a[:90]
 s=s.replace(a,b,1)
replace("...saved.settings,language:saved.language||s.language", "...saved.settings,engine:'human',language:saved.language||s.language")
start=s.index('<div className="output-choice">')
end=s.index('<div className="tabs">',start)
s=s[:start]+'''<div className="output-choice"><span className="pill">HAQIQIY INSON IJROSI</span><h2>Video yonida inson tarjimon</h2><p>How2Sign’dagi mos ASL iboralari haqiqiy inson videosi orqali ijro etiladi. Mos kelmagan gaplar subtitrda qoladi.</p><button onClick={()=>setPage('corpus')}>Tarjimon videolarini ko‘rish →</button></div>'''+s[end:]
replace("</div><button disabled={working} onClick={()=>{setDemo(!demo);setPlaying(false);media.current?.pause()}}>{demo?'Namunani to‘xtatish':'3D harakatni sinash (ASL namuna)'}</button>","</div>{page==='library'&&<button disabled={working} onClick={()=>{setDemo(!demo);setPlaying(false);media.current?.pause()}}>{demo?'Namunani to‘xtatish':'3D texnik namunani sinash'}</button>}")
start=s.index(" {page==='studio'&&mode!=='text'&&job?.translation&&settings.language==='en'&&")
end=s.index(" {page==='studio'&&settings.language==='en'&&",start)
s=s[:start]+s[end:]
# The status labels belonged to the removed experimental model control card.
start=s.index(' const phaseNames:')
end=s.index('\n',start)
s=s[:start]+s[end:]
replace('<h3>Natija tayyor</h3>',"<h3>{job.settings?.engine==='neural'?'Oldingi 3D natija':'Inson tarjimonli natija tayyor'}</h3>{job.settings?.engine==='neural'&&<p>Bu oldin yaratilgan 3D video. Inson tarjimonli yangi nusxa uchun «MP4 video yaratish» tugmasini bosing.</p>}")
replace("Avatar joylashuvi<select", "Tarjimon joylashuvi<select")
replace("Avatar kengligi: ", "Tarjimon kengligi: ")
replace('Avatar video ustida</option>', 'Tarjimon video ustida</option>')
replace("'Avatar kadrlari yuklanmoqda'", "'Tarjimon kadrlari yuklanmoqda'")
p.write_text(s,encoding='utf-8')
