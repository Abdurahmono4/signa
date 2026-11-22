from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8')
s=s.replace("disabled={working||settings.language!=='en'||!modelReady}", "disabled={working||mode==='text'||settings.language!=='en'||!modelReady}")
s=s.replace("onClick={()=>{setMode(key);setPlaying(false);", "onClick={()=>{setMode(key);if(key==='text')setSettings(s=>({...s,engine:'human'}));setPlaying(false);")
s=s.replace("{page==='studio'&&job?.translation&&settings.language==='en'", "{page==='studio'&&mode!=='text'&&job?.translation&&settings.language==='en'")
p.write_text(s,encoding='utf-8')
