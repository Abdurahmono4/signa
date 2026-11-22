from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8')
s=s.replace(" const coverage=", " const phaseNames:Record<string,string>={idle:'Hali yaratilmagan',queued:'Navbatda',loading_model:'Model xotiraga yuklanmoqda',verifying_model:'Model fayllari tekshirilmoqda',generating_segment:'Gap uchun harakat yaratilmoqda',generating_motion:'Harakat yaratilmoqda',ready:'Tayyor',failed:'Xato',cancelled:'Bekor qilingan'};\n const coverage=")
s=s.replace("?'ML harakati yaratildi':neural.phase", "?'ML harakati yaratildi':phaseNames[neural.phase||'']||'ML hisoblanmoqda'")
p.write_text(s,encoding='utf-8')
