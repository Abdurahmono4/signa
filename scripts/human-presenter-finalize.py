from pathlib import Path
p=Path(r'D:\SignBridge-UZ\frontend\src\main.tsx')
s=p.read_text(encoding='utf-8')
s=s.replace("settings.language==='en'&&settings.engine==='human'&&!demo&&page==='studio'?<HumanSigner", "page==='studio'&&!demo?<HumanSigner")
s=s.replace("settings.engine==='neural'?'Tajribaviy ML avatari':settings.language==='en'&&!demo?'ASL tarjimon videosi':'3D tarjimon'", "page==='studio'?'Inson tarjimon videosi':'3D animatsiya ko‘rigi'")
s=s.replace("<button onClick={()=>setPage('corpus')}>Tarjimon videolarini ko‘rish", "<button disabled={working} onClick={()=>setPage('corpus')}>Tarjimon videolarini ko‘rish")
p.write_text(s,encoding='utf-8')
