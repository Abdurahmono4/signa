from pathlib import Path
p=Path(r'D:\SignBridge-UZ\frontend\src\main.tsx');s=p.read_text(encoding='utf-8')
a='<div className="broadcast-player">'
b='''<div className={`broadcast-player ${settings.layout==='overlay'?'preview-overlay':''} ${settings.position==='left'?'preview-left':''}`} style={{'--signer-size':`${settings.size*100}%`} as React.CSSProperties}>'''
assert a in s;s=s.replace(a,b,1);p.write_text(s,encoding='utf-8')
css=Path(r'D:\SignBridge-UZ\frontend\src\style.css')
css.write_text(css.read_text(encoding='utf-8')+'''\n/* Keep studio composition consistent with the chosen export layout and size. */
.broadcast-player{position:relative;grid-template-columns:minmax(0,calc(100% - var(--signer-size,30%))) minmax(0,var(--signer-size,30%))}
.broadcast-player.preview-overlay{display:block}
.preview-overlay>.broadcast-media{height:100%;width:100%}
.preview-overlay>.broadcast-interpreter{position:absolute;right:1.875%;bottom:3.333%;height:auto;width:var(--signer-size,30%);background:transparent}
.preview-overlay.preview-left>.broadcast-interpreter{left:1.875%;right:auto}
.preview-overlay .avatar-card,.preview-overlay .avatar-stage,.preview-overlay .human-signer{background:transparent}
''',encoding='utf-8')
