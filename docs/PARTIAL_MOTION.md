## 2026-11-01 — Tinish belgisi sababli xato rad etish tuzatildi

- D77 ishining In order to obtain that, iborasi v4 da so‘z yetishmasligi emas, model inputida vergulga nuqta qo‘shilib ,. tokeni hosil bo‘lgani sabab rad etilgani aniqlandi. Bu oldingi qisman sinov xulosasini aniqlashtiradi.
- Preflight va runner request bir xil model_caption qoidasi bilan tayyorlanadi: faqat terminal vergul/nuqtali vergul/ikki nuqta yakuniy nuqtaga aylantiriladi. Ichki tinish belgisi va so‘zlar o‘zgarmaydi. Original transcript/timestamps/subtitle matni tegilmagan. Cache v5; oldingi motion/MP4lar saqlangan.
- Haqiqiy 58.1878 s / 7 bo‘lakli ish yangi MaDiS inference bilan 7 generated, 0 unsupported, partial_motion=false qaytardi. Asl segment 2 hali vergul bilan tugaydi. examples/punctuation-inference-20261101-001.json.
- Xato yoki qisman natijada yopiq Nutq matnini tekshirish boshqaruvi qo‘shildi. U faqat so‘ralganda segment/revisionni oladi, mavjud tahrir API orqali asl vaqtlarni saqlagan holda ishlaydi. Saqlashga request deadline qo‘shildi; eski revision himoyasi saqlangan. Brauzerda klik sinovi hali bajarilmadi.
- 107 pytest, frontend build va Node flow guards o‘tdi. IAB boshqaruvini qayta ulashga qaramay tool Local browser use disabled javobini berdi; foydalanuvchi yoqdim deb bildirgan bo‘lsa ham yangi uzun 3D MP4 eksporti tasdiqlanmagan. 7/7 generatsiya ASL semantik aniqligini isbotlamaydi.
- Sayt/API HTTP 200. Avatar modeli va oddiy sahifa saqlangan. MODEL_TEXT_INPUT.md batafsil sabab/cheklovni tushuntiradi.

# Qisman avatar ijrosi va tiklanish

2026-11-01 holati: foydalanuvchi inglizcha audio/video yuklaydi. Faster-Whisper small/CPU matn va so‘z vaqtlarini oladi. Pretrained MaDiS modeli mos matndan tajribaviy 3D harakat yaratadi. Yangi datasetlarda model qayta o‘qitilmagan.

## Model bir iborani qabul qilmasa

Tokenizer tekshiruvi gapni qisqartirmaydi yoki so‘zlarni tashlab yubormaydi. Mos chunklar runnerga o‘z identifikatori va matni bilan yuboriladi. Mos kelmagan chunk `unsupported`, `clip: null` bo‘ladi; matni va original vaqt oralig‘i rejada qoladi. Avatar shu bo‘lakda yangi ishora ijro etmaydi. Ko‘rik matni va eksport subtitri davom etadi; MP4da ushbu oralig‘ida alohida izoh bor. Barcha chunklar mos kelmasa, model ishga tushmaydi: aniq xabar va TXT/SRT havolalari beriladi.

Bu haqiqiy qisman natija. Qamrov yoki ASL aniqligi 100% deb ko‘rsatilmaydi. `coverage: 0` lingvistik tasdiq yo‘qligini saqlaydi; `generated_phrases`, `unsupported_phrases`, `caption_words` texnik hisobotga kiradi. Tokenizer mos kelgan chunkda model yaroqsiz chiqish bersa, bu boshqa xato sifatida to‘xtaydi; bunday chiqish jim yo‘qolmaydi.

## Haqiqiy sinov

Oldin lug‘at sabab to‘xtagan `LOCAL_ID` videosida qayta MaDiS inference bajarildi. Asl 7 transkript bo‘lagi o‘zgartirilmadi. 6 chunk uchun 244 harakat kadri yaratildi; bitta 5 so‘zli ibora 36.2–38.3 s oralig‘ida subtitrga qoldi. Reja davomiyligi 58.1878 s, timing_scale=1. Natija server restartidan so‘ng ham diskdan topildi. Eski tayyor MP4 fayllari saqlangan; motion cache versiyasi v4 bo‘ldi.

Node/Three.js tekshiruvi shu haqiqiy 6 motion assetni API orqali o‘qib, 18 pozada finite matritsalar va tracks, 133 kanal formati, interval va caption-only bo‘lakning markazida faol motion yo‘qligini tekshirdi. Avatar: 80 bone, 30 finger joint, 52 face morph. Bu vizual yoki ASL ekspert bahosi emas.

```powershell
Set-Location D:\SignBridge-UZ
node scripts\check-partial-motion.mjs LOCAL_ID
node --experimental-strip-types scripts\check-flow-guards.mjs
```

Brauzer ko‘rigi bu davom ettirishda boshlangan, keyin Work settingsdagi mahalliy browser use disabled bo‘lgani uchun yangi qisman 3D MP4 browser eksporti tugatilmagan. Shu uzun ishga yangi tayyor video deb havola berilmaydi. Alohida haqiqiy FFmpeg integratsiya testi sintetik shaffof kadrlar bilan qisman subtitr, H.264/AAC, original transkript va davomiylikni tekshiradi; u avatar renderi sifatida ko‘rsatilmaydi.

## Jarayon tiklanishi

- `idle` qaytgan model polling cheksiz kutmaydi; failed/cancelled holati qayta ochilganda retry va TXT/SRT boshqaruvlari bor.
- Har request bekor qilish signali va deadline bilan ishlaydi. Upload deadline 5 daqiqa. Model inference o‘z timeoutiga ega.
- Eksport progress/result faqat o‘z tokeniga tegishli bo‘lsa qabul qilinadi. Eski oynaning cancel/finish so‘rovi yangi eksportni to‘xtatmaydi.
- Qayta urinish xato bosqichiga mos: yuklash, model yoki eksport.
- PNG kadrlar endi faqat signature/o‘lcham bilan qabul qilinmaydi: chunk CRC/tartibi, bounded zlib stream, scanline hajmi va filtrlar tekshiriladi. Buzilgan yoki kesilgan PNG serverga yozilmaydi.

Dalillar: `examples/partial-plan-20261101-001.json`, `examples/partial-recovery-20261101-001.json`. Yakuniy tekshiruv: 98 pytest, frontend build va Node flow guards o‘tgan. Three.js katta bundle ogohlantirishi qoladi.
