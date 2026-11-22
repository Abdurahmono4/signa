## 2026-10-31 — Brauzer orqali yangi studiya va 3D eksport tasdiqlandi

- Yangi studiya brauzerda ochildi: 31 047 train holati, inson/ML tanlovi, train sinov ishi va natija download havolasi ko‘rildi.
- 3D sinovda React maximum update depth ogohlantirishi aniqlandi. Woman capture callbacki har bir time yangilanishida qayta ro‘yxatdan o‘tardi; joriy vaqt refga ko‘chirilib, capture callback barqarorlashtirildi. Qayta ijro 2.24 s oxirigacha bordi va yangi shunday ogohlantirish qaytmadi.
- Brauzerdagi MP4 tugmasi bilan 54 PNG/24 fps haqiqiy eksport bajarildi. Token LOCAL_ID; 84220 bayt, H.264/AAC, 2.239093 s. HTTP download lokal fayl baytlari bilan aynan teng. examples/studio-3d-export-001.mp4 va JSON hisobot saqlandi. Asosiy ish holati va download tokeni brauzerda yangilandi.
- Eski asl media ijrosi birinchi yuklanishda xato berdi; qayta yuklab ijro tekshiruvi o‘tdi. Bir navigatsiyada bootstrap modulining vaqtinchalik syntax xatosi ko‘rindi; lokal va HTTP modulda NUL yo‘q, sahifani reload qilish bilan tiklandi. Tuzatilgan frontend build o‘tdi; yangi yakuniy ijro/eksport davomida bu xatolar takrorlanmadi. React DevTools til aniqlash xabari ilova funksiyasidan tashqarida qoladi.
- 50 backend testi avvalgi yakuniy run’da o‘tgan; keyingi o‘zgarish frontend capture callbackiga tegishli. Model yangi train datasetida qayta o‘qitilgani yoki ASL aniqligi tasdiqlangani da’vo qilinmaydi.

# How2Sign train iboralarini ijro etish

Bu bosqich modelni qayta o‘qitmaydi. Original CSVdagi to‘liq inglizcha ibora mosligi orqali haqiqiy ASL yozuvi tanlanadi. Yaqin ma’noli gap avtomatik tarjima sifatida qabul qilinmaydi. Barcha yangi train yozuvlari `verified: false`, `split: train` bilan qaytadi; validation katalogi alohida qoladi. Train ma’lumotlari bilan olingan natija mustaqil test bahosi emas.

## Lokal fayllar

- `D:\SignBridge-UZ\datasets\how2sign\train_rgb_front_clips.zip`
- `D:\SignBridge-UZ\datasets\how2sign\how2sign_train.csv`

31 047 klip indekslangan. CSVdagi 118 nom arxivda yo‘q. ZIP to‘liq ochilmaydi: faqat tanlangan klip CRC tekshiruvi bilan keshga yoziladi va FFprobe orqali haqiqiy davomiyligi olinadi. CSV intervali video davomiyligi deb qabul qilinmaydi. Har klip 200 MB, bir indeks versiyasi keshi 2 GiB bilan cheklangan. To‘lgan keshda fayllar avtomatik o‘chirilmaydi.

## API

- `GET /api/how2sign/train/status` — indeks va kesh holati.
- `GET /api/how2sign/train/clips/{id}` — xavfsiz ID orqali tanlangan video.
- Mavjud inglizcha translate/transcribe oqimi exact phrase qidiruviga ulangan. Mos validation klipi bo‘lsa, avval undan foydalaniladi; mos kelmagan matn subtitr bo‘lib qoladi.
- Native FFmpeg eksporti validation va train kliplarini bir xil xavfsiz resolver orqali oladi.

Manba: https://how2sign.github.io/ . Metadata litsenziyasi: CC BY-NC 4.0. Ushbu dataset bilan natijalar tadqiqot namunalari sifatida belgilangan; startup uchun tijorat huquqlari alohida tekshirilishi kerak.

## 2026-10-31 haqiqiy smoke sinovi

Windows TTS orqali sun’iy inglizcha nutq yaratildi: “Everybody's eyes open and the game begins.” Bu tabiiy nutq korpusi bo‘yicha umumiy aniqlik bahosi emas.

1. MP4 HTTP orqali yuklandi; yangi ish: `LOCAL_ID`.
2. Faster-Whisper tiny CPU matnni aynan qaytardi, 7 so‘zning vaqt belgilari olindi.
3. Train klipi `eca2726e10ca557b32fb9ac8` tanlandi. 100% manba iborasi mosligi; lingvistik aniqlik bahosi emas.
4. Native MP4 tokeni `LOCAL_ID`; HTTP download 200, 197558 bayt, 4.048980 s, H.264/AAC, 720p.
5. Original va eksport audiosi 64784 tadan 16 kHz sample; korrelyatsiya 0.9999655704. AAC qayta kodlanadi.
6. `docs/train-retrieval-proof-001.png` kadr ko‘rib tekshirildi: inson videosi o‘ngda, subtitr pastda. Yangi frontend oqimi brauzer kliklari bilan tekshirilmagan; TypeScript/Vite build o‘tgan.

Dalillar: `examples/train-retrieval-smoke-001.json`, `examples/train-retrieval-export-001.json`, `examples/train-retrieval-audio-001.json`, `examples/train-retrieval-result-001.mp4`.

Backend sinovlari: 50 passed. Katta Three.js chunk ogohlantirishi qoladi; build xatosi yo‘q. Yangi train asosida neural model o‘qitilmadi va ASL mutaxassisi tasdig‘i olinmadi.
