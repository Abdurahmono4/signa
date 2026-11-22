# SignAvatars ulanishi

Repozitoriy: https://github.com/ZhengdiYu/SignAvatars

Mahalliy yo‘l: D:\SignBridge-UZ\third_party\SignAvatars

Tekshirilgan commit: bbfb35056aaad252ae67c60b44eb91618506d4a8.

Faqat README, requirements, visualizatsiya misollari, tegishli litsenziya fayllari va validation CSV sparse checkout orqali olindi. Barcha katta aktivlar yoki dataset yuklanmadi. Upstream Python kodi bajarilmadi va uning eski CUDA talab qiluvchi requirements fayli ishchi muhitga o‘rnatilmadi.

## Platformada foydalanilgan qismlar

- how2sign_realigned_val.csv yozuvlari sentence_name orqali mahalliy kliplarga bog‘landi: 1741 metadata qatori, 1739 mos video.
- Datasets/signavatars/manifest.json asl klip, ibora va realigned vaqtlarni alohida saqlaydi. Asl How2Sign katalogi va video fayllari almashtirilmadi. Qayta moslangan vaqtlar mavjud kesilgan kliplarga tekshiruvsiz tatbiq qilinmaydi.
- backend/app/signavatars_bridge.py hujjatlashtirilgan SMPL-X 182 kanalini mavjud 133 kanal oqimiga o‘tkazuvchi mustaqil adapterdir. Tana bo‘g‘imlari bo‘yicha neck, collars, head, shoulders, elbows va wrists tanlanadi; barmoqlar, jag‘ va expression kanallari saqlanadi.
- Kadr indekslari orasida uzilish bo‘lsa konvertor vaqtni jim siqib yuborish o‘rniga rad etadi. Cheksiz yoki NaN qiymatlar qabul qilinmaydi.
- GET /api/signavatars haqiqiy tayyorgarlik holatini qaytaradi.

## Buyruqlar

PowerShell, loyiha ildizidan:

```powershell
cd D:\SignBridge-UZ
.\.venv\Scripts\python.exe scripts\signavatars_bridge.py prepare
.\.venv\Scripts\python.exe scripts\signavatars_bridge.py convert-json --input "D:\path\annotation.json" --output "D:\path\motion-133.json" --fps 24
```

convert-json kirishi — ruxsatli manbadan JSON ko‘rinishida chiqarilgan obyekt: smplx maydonida N×182 sonli massiv va ixtiyoriy total_valid_index massivi. Hozir haqiqiy annotatsiya olinmagan; ikkinchi buyruq misol yo‘llaridan foydalanadi va hali haqiqiy annotatsiyada bajarilmadi. Konvertor pickle faylni ochmaydi yoki uning kodini bajarmaydi. Chiqishdagi verified va retarget_validated doim false.

## Nima hali yo‘q

1. Rasmiy dataset ruxsati va mos 3D annotatsiya fayllari. README orqali mualliflarning ariza shakliga murojaat qilinadi; ariza avtomatik yuborilmadi.
2. Ruxsatli SMPL-X/MANO model aktivlari va hand-mean moslashuvi.
3. Birinchi namunadagi kabi tabiiy ayol avatarining qiyofa, teri/ko‘z/soch materiali, kiyim, barmoq va yuz rigi. Ushbu GitHub repo bunday tayyor MetaHuman modelini o‘z ichiga olmaydi.
4. Yangi inson rigiga retarget va lingvistik tekshiruv. Hozirgi raqamli konversiya o‘zi to‘g‘ri ijro yoki tabiiy qiyofani isbotlamaydi.

Asosiy studiya haqiqiy inson videosida qoladi. Foydalanuvchi rad etgan Galtis texnik qiyofasi SignAvatars nomi bilan qayta taqdim etilmaydi.
