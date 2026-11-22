from pathlib import Path
p=Path(r'D:\SignBridge-UZ\frontend\src\main.tsx');s=p.read_text(encoding='utf-8')
start=s.index(' const avatarPanel=')
end=s.index('\n useEffect(',start)
s=s[:start]+''' const avatarPanel=page==='library'?<section className="card"><h2>Tabiiy 3D tarjimon modeli kutilmoqda</h2><p>Oldingi texnik qiyofa foydalanishdan chiqarildi. Import qilingan harakatni yangi inson modelida tekshirish uchun mos barmoq va yuz rigi talab qilinadi.</p><button onClick={()=>setPage('corpus')}>Haqiqiy inson ijrolarini ko‘rish →</button></section>:<section className="card avatar-card"><div className="section-head"><h2>Inson tarjimon videosi</h2><span className="pill">{ready?'IJRO TAYYOR':'YUKLANMOQDA'}</span></div><div className="avatar-stage"><HumanSigner cropMode={settings.cropMode} removeGreen={settings.removeGreen} time={time} items={items} playing={playing} onReady={onReady} onError={onError}/><div className="avatar-tag">{current?.supported?current.text:'Mos ibora topilganda inson ijrosi ko‘rsatiladi'}</div></div><p className="muted">How2Sign haqiqiy inson videosi · ASL · tadqiqot namunasi.</p></section>;'''+s[end:]
s=s.replace("const Avatar=lazy(()=>import('./Avatar').then(m=>({default:m.Avatar})));\n",'')
s=s.replace('useCallback,lazy,Suspense','useCallback')
p.write_text(s,encoding='utf-8')
