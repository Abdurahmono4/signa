from pathlib import Path
p=Path('frontend/src/interpreter.ts')
s=p.read_text(encoding='utf-8')
# Keep original helpers for now, but stop applying facial and procedural alterations.
s=s.replace('after.copy(before);sculptFace(after);','after.copy(before);')
s=s.replace('    sculptFace(delta);','')
s=s.replace("if(object.name==='Strand008')object.visible=false;\n   else restyleMesh(object);",'restyleMesh(object);')
s=s.replace("if(body instanceof THREE.SkinnedMesh)sweatshirt(body);",'// Preserve the original authored garment topology.')
s=s.replace(' if(head){',' if(head && false){').replace(' if(chest){',' if(chest && false){')
p.write_text(s,encoding='utf-8')
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8')
s=s.replace("useState({resolution:720", "useState({layout:'side_by_side',resolution:720")
a=s.index('<section className="card avatar-card">');b=s.index('</section></div>',a)+len('</section>');panel=s[a:b]
s=s[:a]+"{!(page==='studio'&&job&&mode!=='text')&&avatarPanel}"+s[b:]
pos=s.index(' const coverage=');s=s[:pos]+' const avatarPanel='+panel+';\n'+s[pos:]
s=s.replace("{job.kind==='video'?<video controls", "<div className=\"broadcast-player\"><div className=\"broadcast-media\">{job.kind==='video'?<video controls")
s=s.replace("onTimeUpdate={e=>setTime(e.currentTarget.currentTime)}/>}<p className=\"caption\">", "onTimeUpdate={e=>setTime(e.currentTarget.currentTime)}/>}</div><div className=\"broadcast-interpreter\">{avatarPanel}</div></div><p className=\"caption\">")
s=s.replace('<div className="workspace-grid">', '<div className={`workspace-grid ${page===\'studio\'&&job&&mode!==\'text\'?\'has-broadcast\':\'\'}`}>')
s=s.replace('<label>Avatar joylashuvi', '<label>Video ko‘rinishi<select value={settings.layout} onChange={e=>setSettings({...settings,layout:e.target.value})}><option value="side_by_side">Video chapda, tarjimon o‘ngda</option><option value="overlay">Avatar video ustida</option></select></label><label>Avatar joylashuvi')
p.write_text(s,encoding='utf-8')
p=Path('frontend/src/style.css');p.write_text(p.read_text(encoding='utf-8')+'''
.workspace-grid.has-broadcast{grid-template-columns:minmax(0,1fr)}
.broadcast-player{display:grid;grid-template-columns:minmax(0,7fr) minmax(150px,3fr);background:#000;align-items:center;aspect-ratio:16/9;overflow:hidden;border-radius:12px}
.broadcast-media{min-width:0;background:#000;display:flex;align-items:center;justify-content:center;height:100%}
.broadcast-media video{width:100%;height:100%;max-height:none;object-fit:contain;border-radius:0}
.broadcast-media audio{width:95%}
.broadcast-interpreter{height:100%;min-width:0;display:flex;align-items:center;background:#000;overflow:hidden}
.broadcast-interpreter .avatar-card{border:0;border-radius:0;padding:0;background:#000;box-shadow:none;width:100%;max-width:none}
.broadcast-interpreter .section-head,.broadcast-interpreter .avatar-tag,.broadcast-interpreter .avatar-card>button,.broadcast-interpreter .muted{display:none}
.broadcast-interpreter .avatar-stage{width:100%;max-width:none;background:#000;border-radius:0}
.broadcast-interpreter .avatar-canvas{width:100%;height:auto;aspect-ratio:3/4;left:auto;transform:none;position:relative}
@media(max-width:640px){.broadcast-player{grid-template-columns:minmax(0,7fr) minmax(90px,3fr)}}
''',encoding='utf-8')
