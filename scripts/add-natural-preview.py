from pathlib import Path
p=Path(r'D:\SignBridge-UZ\frontend\src\main.tsx');s=p.read_text(encoding='utf-8')
s=s.replace("useCallback} from 'react'","useCallback,lazy,Suspense} from 'react'",1)
s=s.replace("import './style.css';","import './style.css';\nconst NaturalAvatar=lazy(()=>import('./NaturalAvatar'));",1)
a="const avatarPanel=page==='library'?<section"
assert a in s
start=s.index(' const avatarPanel=');end=s.index(':<section className="card avatar-card">',start)
s=s[:start]+" const avatarPanel=page==='library'?<Suspense fallback={<p>Yangi model yuklanmoqda…</p>}><NaturalAvatar/></Suspense>"+s[end:]
s=s.replace("['library','◇','Animatsiya importi']","['library','◇','Yangi ayol modeli']")
p.write_text(s,encoding='utf-8')
