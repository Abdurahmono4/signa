# Avatar va ASL harakatlar korpusi

## Ko‘rinish va harakat

Avatar qisqa to‘q soch, yumaloq ko‘zoynak, yangilangan yuz shakli va keng indigo kiyim bilan qayta bezatilgan. `frontend/src/interpreter.ts` manba model kloniga bezak beradi; `Avatar3D.tsx` yorug‘lik, kamera va ijroni boshqaradi. Manba modelning qo‘l/barmoq skeleti, harakat tracklari va yuz morph kanallari saqlanadi. Birinchi kalibrlash T-pose kadrini ko‘rsatmaslik uchun dam holati 1/30 soniyadan olinadi.

Skelet `frontend/public/avatar/galtis.glb` da, animatsiyalar `{id}.motion.json` aktivlarida. Yuz morph kanallari mavjudligi har bir klipda ASL uchun zarur barcha yuz ifodalari yozilganini anglatmaydi. Model bezagi lingvistik sifatni tasdiqlamaydi.

Kamera masofasi `framing.ts` orqali panel tomonlari nisbati va ko‘rish burchagiga moslashadi. Tor panelda qo‘l/barmoq uchlari, yuz va soch uchun zaxira saqlanadi. Kamera ishoralar orasida o‘zgarmaydi.

## Korpus va kelib chiqish

Amaldagi ro‘yxat — `frontend/public/avatar/corpus.json`; backend nusxasi `backend/app/assets/corpus.json`. Manifest ibora, manba URL, Git blob SHA, litsenziya, davomiylik va chiqarib tashlangan tracklarni qayd etadi. Manba — [Studio Galt Sign-Language-Mocap-Archive](https://github.com/StudioGalt/Sign-Language-Mocap-Archive), manifest litsenziyasi CC0-1.0.

Amaldagi to‘plamda 50 manba klip bor: 24 lug‘at klipi va A–Z ning 26 barmoq alifbosi yozuvi. Boshlang‘ich lug‘at: Hello, My, My Name Is, Please, Book, Brother, Brown, Bye, Child, Class, Coffee va Take. Keyin Bring, Busy, But, Any, Booklet, Bookstore, Both, Break Pause, Breakfast, Buy, Carefully va Turn Off qo‘shilgan. Yangi importlarning manba/GLB taqqoslashida tekshirilgan matritsa va yuz qiymatlarining maksimal farqi 0 bo‘ldi; hech bir motion track chiqarib tashlanmadi. Blue Color, Boat, Body va Check Please nomzodlari rig mos kelmagani sabab qo‘shilmadi. Keyingi o‘zgarishlarda aynan manifest yakuniy ro‘yxat hisoblanadi.

Harflar rasmiy arxivning `SG ASL Fingerspelling/Letters` bo‘limidagi 2024-yil 16–17-iyun yozuvlaridan olingan. Manifest ularni `kind: fingerspelling`, `letter: A`–`Z`, `status: source` bilan ajratadi. Davomiyliklar 2.367–4.533 soniya; J 3.917 va Z 4.100 soniyalik asl harakat yo‘li bilan saqlangan. Ular statik taxminiy pozalarga almashtirilmagan yoki o‘zboshimcha qisqartirilmagan. Bular manba yozuvlari; ekspert tasdiqlagan umumiy gap tarjima modeli emas.

`status: source` mahalliy ASL mutaxassisi tasdig‘i emas. Manba importi `draft` yaratadi. Tekshiruvchi ma’no, qo‘l shakli/yo‘nalishi, fazoviylik va yuz ifodasini ko‘rib, ism va izoh bilan tasdiqlashi yoki rad etishi kerak. Dastur kiritilgan ismning malakasini mustaqil tekshirmaydi. ASL foydalanuvchilari bilan tushunarlilik bahosi hali o‘tkazilmagan.

## Sahifadagi ijro

Fayl yuklanib **Imo-ishorada ijro etish** bosilgach, nutq aniqlanadi. Standart so‘rov `playback-plan?include_source=true&fingerspelling=false`: manba lug‘at kliplari ham olinadi, avtomatik harflash o‘chiq. `prepareMotions()` faqat rejaga zarur kliplarni oldindan yuklaydi. Bitta vaqt chizig‘i media va avatarni birga boshqaradi.

**Tezkor so‘z rejimi:** mavjud 24 so‘z/ibora klipi ko‘pi bilan 1.25× tezlikda ijro etiladi; manba harakati o‘zboshimcha kesilmaydi. Ishora nutqdagi vaqtdan uzun bo‘lsa, media so‘z oxirida pauza qiladi. Lug‘atda yo‘q so‘zlar so‘zma-so‘z subtitrda o‘z vaqtida ko‘rsatiladi, qo‘shimcha hold yaratilmaydi. Subtitrning o‘zi ASL tarjima emas.

**Ixtiyoriy harflash:** **Harflab ko‘rsatish** yoqilsa, lug‘atda yo‘q A–Z so‘zlar manba harf kliplari bilan 1.0× tabiiy tezlikda, to‘liq davomiylikda ijro etiladi. Ekranda **HARFLAB**, asl so‘z va joriy harf ko‘rinadi. Birinchi harfdan keyingi harflar davomida media so‘z oxirida turadi. Bu rejim umumiy ijroni nutqdan ancha uzaytirishi mumkin.

Apostrof chiqarilgach A–Z ga sig‘magan so‘z, raqam, yetishmagan harf yoki limitdan oshgan so‘z butunlay subtitrda qoladi. Limitlar: 30 harf/so‘z, 10 000 harf/reja, harflash sabab ko‘pi bilan 3600 soniya qo‘shimcha pauza. O‘ylab topilgan harakat berilmaydi; kliplararo yangi tabiiy o‘tish yoki ASL gap grammatikasi yaratilmaydi. Harflash inglizcha so‘zning yozilishini ko‘rsatadi, uning ma’nosini ASL gapiga tarjima qilmaydi.

Asosiy sahifada eski laboratoriya/korpus tekshirish panellari yo‘q; tekshiruv/import API da saqlangan. Eski `/sign-plan` 0.5–2 vaqt nisbati tekshiruvini saqlaydi. `/playback-plan` tezlikni 1.25× bilan chegaralaydi va zarur media pauzalarini qo‘shadi; `sync_status` avvalgi audit holatini saqlaydi. Amaldagi manifestda neytral bosh/oxirni kesish metama’lumoti yo‘q. Kelajakda faqat tekshirilgan kanonik `playback_window` ishlatilishi mumkin; hozir to‘liq yozuv saqlanadi.

1.25× — tezlikni cheklovchi muhandislik tanlovi; ASL foydalanuvchilari tushunarliligi uchun tasdiqlangan me’yor deb olinmaydi. Neytral bo‘laklarni ehtiyotkor tahlil qilishda harakatni saqlash sharti bilan xavfsiz kesiladigan oraliq topilmadi; kliplarga trim qo‘shilmadi.

## Rig, eksport va import

Manifestdagi `animation_asset` mosligi bilangina manba harakati ijro etiladi. Eski geometrik `keyframes` formati yangi avatar uchun `unsupported_rig`. `examples/calibration-motion.json` — ASL emas, faqat rig sinovi; tarjima sifatida tasdiqlanmaydi.

Boshlang‘ich Child, Class va Coffee yozuvlarida `dropped_tracks: 6` qayd etilgan. Eksportni asl yozuv bilan alohida solishtirish zarur. Bog‘lanmagan track yo‘qligi yoki matritsalarning chekli bo‘lishi ishora ma’nosini isbotlamaydi.

`scripts/import-corpus.mjs` rasmiy arxivdan tanlangan FBX aktivlarini tekshirish uchun qo‘shilgan. U Git blob SHA, litsenziya, skelet iyerarxiyasi, inverse-bind matritsalari, animatsiya kanallari va yuz morph nomlarini tekshiradi. Asl FBX va GLB da 21 vaqtdagi skin bo‘g‘imlari matritsalari va yuz morph qiymatlari solishtiriladi. Faqat dastlabki statik pozaning farqiga qarab qaror qilinmaydi: u yozuvning birinchi animatsiya kadri bo‘lishi mumkin. Mos kelmagan rig yoki kanallar rad etiladi; muvaffaqiyatsiz to‘plam manifestga chiqarilmaydi. `--write` texnik tekshiruvdan o‘tgan yozuvlarni qo‘shadi va ekspert tasdig‘i bermaydi. Taxminiy retargeting bilan ishora yaratilmaydi. Natija ish papkasidagi `validation.json` da saqlanadi.

## Texnik tekshiruv

```powershell
node scripts/test-avatar.mjs
node scripts/test-interpreter.mjs
node scripts/test-playback.mjs
node scripts/test-framing.mjs
```

`test-avatar` aktiv/track bog‘lanishi va matritsalarni tekshiradi. `test-interpreter` har klipning bir nechta vaqtidagi asl hamda qayta bezatilgan qo‘l/barmoq koordinatalari bir xil ekanini va yuz kanallari/vaqti saqlanganini tekshiradi. `test-playback` tezlik/klip oynasi xaritasi, media pauzalari, noma’lum matn, chegaralar va seekni tekshiradi. Bular ASL ekspert bahosi o‘rnini bosmaydi.

Manba bilan eksportni taqqoslash, tabiiy o‘tishlar, gap tarjimasi va tushunarlilik mezonlari [RESEARCH_PLAN.md](RESEARCH_PLAN.md) da.
