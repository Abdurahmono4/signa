> 2026-11-01 yangilanish: kichik namunalar o‘tgan bo‘lsa ham, to‘liq train 2D gzipda dekompressiya xatosi topildi. Train RGB ZIPlarda ham CRC xatolari bor. Hozirgi xulosa va istisnolar uchun docs/TRAIN_INTEGRITY.md ga qarang.

# How2Sign train: mahalliy namuna

## Barcha CSVlar va vaqtli featurelar

Original hamda realigned train/val/test CSVlari D diskdan nusxalandi. Mavjud bir xil train/val fayllari SHA-256 bilan tekshirilib, ustiga yozilmadi. Audit buyruği:

```powershell
.\.venv\Scripts\python.exe scripts/audit_how2sign_metadata.py --output datasets/how2sign/metadata-audit-new.json
.\.venv\Scripts\python.exe scripts/attach_pose_timing.py --output datasets/how2sign/train-timed-features-new
```

Natija: 31 165 train, 1741 val, 2357 test qator. Interval/noyob ID xatolari topilmadi; original/realigned matnlar bir xil. Splitlar orasida SENTENCE_NAME yoki VIDEO_NAME takrori 0. Bu semantic duplicate tekshiruvi emas. Original train/frontend katalog yo‘llari o‘zgarmadi.

Train 27 361, val 1649, test 2187 interval qayta moslangan. Train 25 566, val 1577, test 2070 interval original klipdan tashqariga chiqadi. Shuning uchun realigned CSV mavjud kesilgan videolarga jim almashtirilmadi. To‘liq manba video bo‘lmasdan tashqaridagi kadrlar qayta yaratilmaydi. Hisobot metadata-audit-001.json (birinchi audit), metadata-audit-002.json (archive mavjudligi faqat dataset papkasiga tegishli ekanini aniqlashtiradi).

`train-timed-features-001` da avval tekshirilgan 5 klip / 1196 kadrga haqiqiy frontal MP4 dekodlangan PTS vaqtlari qo‘shildi (`time_seconds`). 4 klip 24 FPS, 1 klip 60 FPS. Kadr soni va indekslar tekshirildi. Vaqt birinchi video kadridan boshlanadi, boshqa original massivlar saqlandi. Bu so‘z–ishora alignmenti emas; training_ready=false qoladi. Avvalgi fps:null manifestlar o‘zgartirilmadi.

44 backend testi o‘tdi. D diskda test original/realigned CSV bor, lekin test video ZIP aniqlanmadi; CSVning o‘zi yakuniy media testi uchun yetmaydi. Validationning avvaldan chiqarilgan 1739 manba klipi saqlangan; ZIP dataset papkasida yo‘qligi bu kliplar yo‘q degani emas.

## Frontal train RGB arxivi tekshirildi

2026-10-31: `D:/train_rgb_front_clips.zip` → `datasets/how2sign/train_rgb_front_clips.zip`, 33 033 658 988 bayt. ZIP katalogida 31 047 noyob MP4. CSVdagi 31 165 qatorning 31 047 tasi nom bo‘yicha mos, 118 yozuvning MP4si bu arxivda yo‘q. Begona nomlar va xavfli relative yo‘llar topilmadi. 118 nom `train-front-inspection.json` ichida to‘liq saqlangan; buning o‘zi yuklama buzilganini anglatmaydi. Butun 31 GB ZIP CRCsi tekshirilmadi.

`train-front-inspection-001` ga oldingi 5 keypoint namunasining frontal MP4lari ajratildi. Shu beshta faylda ZIP CRC/FFprobe va to‘liq PyAV dekodlash bajarildi: jami 1196 kadr. PTSlar har birida o‘sib boradi; kadr sonlari keypoint namunalari bilan teng.

| Ibora | Frontal FPS | Dekodlangan/koordinata kadr |
|---|---:|---:|
| anxhVQxvPGs_21-5 | 24 | 174/174 |
| BbM3wYI7H8U_4-8 | 24 | 24/24 |
| FStKSCmBx00_14-4 | 24 | 239/239 |
| aibMW4Xt7wA_4-4 | 24 | 169/169 |
| 3CrOUbBvRkQ_25-5 | 60 | 590/590 |

Birinchi videoning 12-kadriga aynan 12-raqamli raw frontal keypointlar qo‘yildi (`frame-012-overlay.png`), tana va qo‘llar ko‘rinadigan gavda/qo‘llar bilan fazoviy mosligi vizual ko‘rildi. Bu faqat bir kadrning vizual tekshiruvi; barcha kliplarda pixel/time alignment va til semantikasi tasdiqlangani emas. Oldingi feature manifestidagi `fps:null` qiymatlari jim o‘zgartirilmadi; tekshirilgan media faktlari alohida hisobotda turibdi. Rasmiy matn-imo vaqt mosligi mustaqil baholanishi kerak.

Arxiv to‘liq ochilmadi. Yangi 31 047 klip hozirgi 1739 validation kutubxonasiga avtomatik aralashtirilmadi; model qayta o‘qitilmadi. Manba videolar va oldingi ishlar saqlandi.

## Ikkinchi arxiv: yon ko‘rinish videolari

2026-10-31 da `D:/train_rgb_side_clips.zip` tekshirilib, shu diskdagi `datasets/how2sign/train_rgb_side_clips.zip` ga ko‘chirildi. Hajmi 23 273 015 704 bayt. ZIP markaziy katalogida 31 165 MP4; CSVdagi 31 165 SENTENCE_NAME ga `-rgb_front` → `-rgb_side` nom almashtirish bilan to‘liq mos keldi. Nomi bo‘yicha moslik vaqt yoki ma’no aniqligini isbotlamaydi.

`train-side-inspection-001` ga oldingi 5 koordinata namunasining yon videolari ajratildi. ZIP read/CRC va FFprobe shu 5 faylda o‘tdi; birinchi video kadri vizual ko‘rildi. Butun ZIP CRCsi yoki barcha videolarning dekodlanishi tekshirilmadi. Hisobot `train-side-inspection.json`.

| Ibora | Yon video FPS | Yon video kadr | Frontal koordinata kadr |
|---|---:|---:|---:|
| anxhVQxvPGs_21-5 | 24 | 130 | 174 |
| BbM3wYI7H8U_4-8 | 24 | 24 | 24 |
| FStKSCmBx00_14-4 | 24 | 239 | 239 |
| aibMW4Xt7wA_4-4 | 24 | 169 | 169 |
| 3CrOUbBvRkQ_25-5 | 60 | 443 | 590 |

Koordinatalarning frontal FPS qiymati yon video FPS qiymatidan avtomatik olinmadi. Camera view va ayrim kadr sonlari farqli. Shu sabab 2D koordinatalarni yon videoga pixel sifatida qo‘yish yoki shu asosda 3D rekonstruksiya qilingan deb hisobot qilish mumkin emas. Model o‘qitilishi boshlanmadi, yon videolar mahsulotning frontal tarjimon kutubxonasiga avtomatik qo‘shilmadi. Frontal train RGB kliplari mavjudligi hali tasdiqlanmagan.

## Keyingi bosqich — maskalangan ML xususiyatlari

`backend/app/keypoint_features.py` va `scripts/build_keypoint_features.py` qo‘shildi. `datasets/how2sign/train-features-001` da 5 ibora / 1196 kadr, har bir kadr uchun 120 nuqta bor: yuqori tana 8, qo‘llar 21+21, yuz 70. Bu 3D avatar animatsiyasi emas.

- `xy`: T×120×2, klipning ishonchli bo‘yin nuqtalari medianasi markaz, ishonchli yelka kengligi medianasi masshtab sifatida ishlatiladi. Rasm x-o‘qi o‘ngga, y-o‘qi pastga. Chap/o‘ng qo‘l va tana egilishi saqlanadi.
- `valid`: T×120 maska; detector score >=0.2. Ishonchsiz nuqtada xy=0 va maska=false. Bu nol haqiqiy nuqta sifatida ishlatilmasligi kerak.
- `scores`: asl detector ballari, jumladan 1 dan katta qiymatlar saqlanadi.
- `delta_xy_per_frame`, `delta_valid`: o‘zgarish faqat ikkala kadrda ham nuqta ishonchli va kadr raqamlari ketma-ket bo‘lsa olinadi. Bu sekundga nisbatan tezlik emas; FPS tasdiqlanmagan.
- `origin_xy`, `scale_px`, `frame_numbers`, `point_names` bilan tekshirish va valid nuqtalarni pixel koordinatalariga qaytarish mumkin. Interpolatsiya va vaqt bo‘yicha resampling bajarilmaydi.

```powershell
.\.venv\Scripts\python.exe scripts/build_keypoint_features.py --source datasets/how2sign/train-sample-002 --output datasets/how2sign/train-features-002
```

Output papkasi yangi bo‘lishi kerak. Buyruq faqat train manifestini qabul qiladi; validation/test bu buyruqda aralashtirilmaydi. 36 backend testi o‘tdi: masshtab/ko‘chirishga invariantlik, valid nuqtalarni qaytarish, frame gaplar va yetishmayotgan nuqtalarni maskalash, ishonchli markaz bo‘lmasa rad etish tekshirildi.

Rasmiy sahifa qayta tekshirildi: https://how2sign.github.io/ . Original klip vaqtlarining ASL matniga nomukammal mosligi (Green Screen RGB clips izohi) qayd etilgan. Shu sabab CSV davomiyligi/kadr sonidan aniq FPS yoki lingvistik alignment deb xulosa chiqarilmadi. Hozirgi manifestlarda training_started=false va training_ready=false. Yangi yuklanayotgan train arxiviga tegilmadi.

2026-10-31. Arxiv `datasets/how2sign/train_2D_keypoints.tar.gz` (22 619 897 332 bayt) RGB video emas, OpenPose 2D JSON yozuvlarini saqlaydi. `how2sign_train.csv` 31 165 qator. Metadata `SENTENCE_NAME` bilan arxivdagi klip papkasi bog‘lanadi.

## Bajarilgan ish

`scripts/prepare_keypoint_sample.py` arxivni oqim sifatida o‘qiydi; barcha fayllarni diskka ochmaydi. A’zolar soni, JSON hajmi va skan qilingan tar offseti cheklangan. Fayl yo‘llari to‘g‘ridan-to‘g‘ri extract qilinmaydi. Mavjud output papkasi ustiga yozilmaydi.

Yakuniy namuna `datasets/how2sign/train-sample-002` da: 5 ibora, 1196 kadr, 4 144 138 bayt JSON, parse xatolari 0. Kadrlar fayl tartibida emas, raqam bo‘yicha saralandi. Olingan diapazonlarda kadr raqamlari uzilishi va ko‘p/bo‘sh odam holatlari 0. To‘liq arxiv skan qilinmagani sabab bir klipning barcha yozuvlari topilgani kafolatlanmaydi.

Har bir NPZ ichida `frame_numbers`, `person_counts`, tana (25×3), chap/o‘ng qo‘l (21×3), yuz (70×3) massivlari bor. Ustunlar x, y, detector confidence. `np.load(..., allow_pickle=False)` bilan o‘qiladi. Ko‘p odam topilsa bittasi taxminan tanlanmaydi: kadr yetishmayotgan deb belgilanadi. Asl raw qiymatlar mavjud.

`manifest.json` matn, manba video nomi, CSV intervallari, kadr statistikasi va confidence threshold qamrovini saqlaydi. Score >1 holatlari asl ma’lumotda bor (masalan, 1.01007); parser musbat chekli qiymatlarni saqlaydi va bunday nuqtalar sonini hisobot qiladi. Bu ball yoki threshold qamrovi tarjima aniqligi emas.

`contact-sheet.png`: har bir qator bitta ibora, 8 ta bir tekis tanlangan kadr. Ko‘k — tana, yashil — chap qo‘l, sariq — o‘ng qo‘l, kulrang — yuz. Chizma faqat confidence >0.2 nuqtalarni ko‘rsatadi. `first-clip.png` birinchi iboraning ko‘rigi.

`train-sample-001` dastlabki, score >1 ni qat’iy rad etgan tekshiruv natijasidir; o‘qitish uchun ishlatilmasin. Yakuniy ko‘rik `train-sample-002` dan olinadi. Original arxiv o‘zgartirilmadi.

## Qayta ishga tushirish

Loyiha papkasidan, yangi output nomi bilan:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_keypoint_sample.py --output datasets/how2sign/train-sample-003 --clips 5
.\.venv\Scripts\python.exe -m pytest backend/tests/test_keypoint_sample.py -q
```

## Ochiq chegaralar

- FPS tasdiqlanmagan; CSV vaqtlaridan ishonchli FPS deb xulosa chiqarilmaydi. Manifestda `fps: null`.
- 2D x/y koordinatalar chuqurlik yoki SMPL-X/GLB suyak aylanishlarini bermaydi. Mavjud MaDiS modeli 133 kanalli 3D aylanish chiqishini ishlatadi; ushbu NPZ to‘g‘ridan-to‘g‘ri uning o‘qitish ma’lumoti sifatida ulanmagan.
- Model o‘qitilmadi. Manifestda `training_ready: false`, `verified: false`.
- Keyingi ish: FPS va media alignmentni tekshirish, yetishmayotgan nuqtalar uchun maskalar/normalizatsiya, tanlangan 2D yoki 3D o‘qitish vazifasiga mos format, mustaqil baholash to‘plami.
- How2Sign manbasi: https://how2sign.github.io/ . Mahalliy manba metadatasi CC-BY-NC-4.0 deb belgilangan; yangi tijoriy foydalanish huquqlari bu ish bilan tasdiqlanmagan.

33 backend testi o‘tdi. Ular orasida detector score saqlanishi, ambiguous odamlar, tartibsiz kadrlarni saralash, CSV bilan moslash, NPZ o‘qish, xavfsiz qayta ishga tushirish bor. Chizmalar vizual tekshirildi; ASL semantikasi ekspert tomonidan tasdiqlanmagan.
