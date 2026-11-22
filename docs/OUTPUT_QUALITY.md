## 2026-11-02 keyingi tekshiruv

Brauzer sinovi endi bajarildi: 1397 real yuqori aniqlikdagi kadrdan uzun MP4 yaratildi, download va to‘liq decode tekshirildi. Tarmoqdagi ETIMEDOUT uchun keep-alive/retry va xato xabarini saqlash tuzatildi. Dalillar: CURRENT_STATUS.md eng yuqori qayd va examples/browser-test-results-20261102-001.json. Quyidagi oldingi browser sinovi qolgan degan qayd tarixiy.

# Avatar va MP4 sifati — 2026-11-02

Hozirgi qiyofa: Microsoft Rocketbox Female 01, MIT. Standart kadr: beldan yuqori, 4:3 kamera, qo‘llar ko‘rinadigan maydon. Qiyofa va harakat retargeti ushbu bosqichda almashtirilmagan.

## Yangi eksport

NaturalAvatarTimeline shaffof 1024×768 PNG oladi, 24 fps deterministic motion sampling ishlatadi. Render target va pixel buffer qayta ishlatiladi; qurilma ko‘targan MSAA 4 gacha. Backend capture_quality=high uchun aynan shu o‘lchamni tekshiradi. Standard 512×384 va legacy 384×512 eski mijozlar uchun qolgan. PNG limiti 1 MiB; rasm noto‘g‘ri/yirik bo‘lsa aniq xato qaytadi. 720p MP4 H.264 CRF18, AAC160k; bu yo‘qolishsiz nusxa emas. Vaqt yetmasa audio va video birga sekinlashtirilishi mumkin.

ASS: asosiy matn pastda, kichik tajribaviy ASL belgisi tepada. Unsupported interval alohida ko‘rsatiladi; general subtitles=false bo‘lsa ham o‘sha intervalning asl matni chiqariladi. Bu jim tushirib qoldirishdan saqlaydi. Kutubxonaga mos kelmagan harakat tasdiqlangan ishora deb ko‘rsatilmaydi.

## Saqlangan natijani yangilash

Oddiy sahifada Video tayyor yonidagi Qayta tayyorlash tugmasi avatar ko‘rigini ochadi; keyin MP4 tayyorlash bosiladi. Cached motion qayta ishlatiladi. Oldingi videoning aniq tokenli manzili saqlanadi; yangi kod allaqachon yozilgan eski MP4ni avtomatik o‘zgartirmaydi.

## Tekshiruv chegarasi

117 pytest, frontend build, flow guards va haqiqiy 7-motion/280-frame kamera geometriyasi tekshirildi. 1024×768 sintetik kadrlarda API/FFmpeg eksport sinovi o‘tdi. Bu browserdan yangi yuqori aniqlikdagi avatarning piksel sifati tasdig‘i emas.

examples/avatar-quality-review-20261101-001.mp4 yangi subtitr namunasidir: oldingi real 3D eksportdagi avatar tasviri original media bilan qayta kompozitsiya qilingan. Yangi browser avatar kadrlari yaratilmagan. docs/avatar-quality-review-20261101-001.png ko‘rib tekshirildi. FFprobe H.264/AAC va 2.239093 s ni tasdiqladi.

Yangi capture, Qayta tayyorlash klik oqimi va 58 soniyalik yangi 3D MP4 vizual testi CUA Local browser use disabled sabab hali bajarilmagan. ASL semantikasi, qo‘l shakli va yuz grammatikasi uchun kar foydalanuvchilar hamda ASL mutaxassisi bahosi zarur. 280 bo‘g‘im pozasi kadr ichida qolishi tarjima to‘g‘ri degani emas.

Dalil: examples/quality-readiness-20261102-001.json. Buyruqlar:

```powershell
Set-Location D:\SignBridge-UZ
.\.venv\Scripts\python.exe -m pytest backend/tests -q --tb=short
node scripts/check-flow-guards.mjs
node scripts/check-partial-motion.mjs LOCAL_ID
Set-Location frontend
npm.cmd run build
```
