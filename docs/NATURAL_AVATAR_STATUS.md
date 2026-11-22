## 2026-10-31 — Yangilangan avatar MP4 vizual tekshirildi

- Brauzer boshqaruvi qayta ishladi. LOCAL_ID saqlangan qisqa inglizcha namunasidagi mavjud MaDiS harakati qayta ishlatildi; ushbu bosqichda upload, ASR yoki model inference qayta bajarilmadi.
- NaturalAvatarTimeline interfeysidan haqiqiy 54 PNG kadr/24 fps olindi. relaxed-idle-v3 bilan eksport tugadi; token LOCAL_ID. FFprobe: H.264/AAC, 1280×720, 24 fps, 2.239093 s, 84220 bayt. HTTP download 200.
- Brauzerda video oxirigacha ijro etildi. Yangilangan kutish holati va 0.65 s dagi faol harakat kadri vizual ko‘rildi. Qo‘llar kutishda keng A-pose ga qaytmaydi; faol kadrda ikkala qo‘l ko‘rinadi. Barmoqlar va ASL semantikasi ekspert tomonidan baholanmagan.
- Original/eksport dekodlangan audio korrelyatsiyasi 0.9999683951. Audio qayta AAC kodlangan; bitma-bit bir xil emas.
- Yangi fayl examples/rocketbox-final-34a74c7b.mp4; hisobot examples/final-avatar-report.json. Dalillar docs/final-avatar-browser-proof.png, docs/final-avatar-rest.png, docs/final-avatar-signing.png. Oldingi MP4 fayllari saqlangan.
- Chegara: bu faqat 2.24 s lik saqlangan namuna. Uzun mustaqil videolar, yangi transkript tahrir UI si, ko‘p bo‘lakli eksport va ASL tushunarliligi bo‘yicha keyingi sinovlar qoladi. Quyidagi brauzer bloklanganligi haqidagi yozuvlar oldingi bosqichlarni ifodalaydi.

## 2026-10-31 — Tabiiyroq kutish holati

- Muammo: harakat yo‘q paytda va video oxirida modelning keng ochilgan A-pose holati ko‘rinardi.
- Rocketbox uchun alohida, ishora hisoblanmaydigan kutish holati yaratildi: qo‘llar pastda, tana yonida, tirsaklar biroz bukilgan. Asl GLB va skin bind o‘zgartirilmadi.
- 0.24 s yumshoq o‘tish faqat harakatsiz intervallarda ishlaydi. Qisqa oraliqda oldingi oxirgi poza keyingi boshlang‘ich pozaga aralashadi. Faol ishora intervallari va manba kadrlariga tegilmaydi. Seek va eksport aynan bitta vaqt bo‘yicha hisoblash yo‘lini ishlatadi.
- `node scripts/check-rocketbox-motion.mjs`: real 28 kadr, 968 trek, suyak uzunliklari, qo‘llarning tana yoniga tushishi, faol kadrlarning oldingi natijaga tengligi, blending va seek/restoration tekshirildi.
- `node scripts/check-avatar-playback.mjs`, `node scripts/check-avatar-timeline.mjs`, frontend TypeScript/Vite build va 25 backend testi o‘tdi. Three.js chunk hajmi ogohlantirishi qoladi.
- Eksport versiyasi `relaxed-idle-v3`. Oldingi videolar o‘chirilmaydi; interfeys ularga qayta eksport kerakligini aytadi.
- Brauzer vositasi hali «Local browser use is disabled in Work settings» javobini berdi. Shu sabab ushbu kutish holati brauzerda vizual tekshirilmadi va yangi MP4 eksport qilinmadi. Rasmda ko‘rsatilgan oldingi MP4 o‘z-o‘zidan yangilanmaydi.
- Bu taqdimot holati ASL lug‘atiga qo‘shilmagan; barmoq shakli va ASL semantikasi bo‘yicha yangi lingvistik tasdiq yo‘q.

## 2026-10-31 — Qo‘l boshlang‘ich holatini moslash

- Rocketbox A-pose qo‘llari SMPL-X extended-arm bazasi bilan to‘g‘ridan-to‘g‘ri bir xil deb olingan edi. Yelka→tirsak, tirsak→bilak va kaft→o‘rta barmoq yo‘nalishlari endi manbaning yon tomonga ochilgan qo‘l bazasiga moslanadi. Skin bind, suyak uzunliklari va barmoqlarning o‘zaro rest holati saqlanadi.
- Kliplar o‘ynayotgan modeldan emas, o‘zgarmas yuklangan modeldan yaratiladi; bo‘lak/import almashishda oldingi poza yangi klipning bazasiga aylanmaydi.
- Yangi eksportlar `motion_revision=arm-reference-v2` bilan saqlanadi va MP4 metadata ichida ko‘rsatiladi. Eski MP4 o‘chirilmaydi; qayta eksport kerakligi interfeysda yoziladi.
- `node scripts/check-rocketbox-motion.mjs` o‘tdi: neytral qo‘l o‘qi, ikki tirsakning ko‘tarilishi, real MaDiS 28 kadrida 968 trek, o‘zgarmas suyak uzunliklari/lokal offsetlar, finite transformlar, bosh/pelvis balandligi va qayta ijro tekshirildi.
- `node scripts/check-avatar-timeline.mjs`, `npm.cmd run build` va 25 backend pytest o‘tdi. Build Three.js chunk hajmi haqida ogohlantiradi.
- Ushbu davom ettirishda brauzer vositasi Work sozlamalari o‘chirilganligini qaytardi. Tuzatilgan harakatning yakuniy vizual tekshiruvi va yangi MP4 eksporti bajarilmadi. Avvalgi Rocketbox MP4 yangi qo‘l tuzatishlarini o‘z ichiga olmaydi.
- Kaftning bo‘ylama burilishi, litsenziyalangan SMPL-X hand-mean, barmoqlarning lingvistik aniqligi va yuz grammatikasi hali tasdiqlanmagan. Bu geometrik tuzatish to‘g‘ri ASL kafolati emas.

## 2026-10-31 — Rocketbox kadr xatosi va haqiqiy MP4 eksporti

- Root sabab: Rocketbox modelidagi oddiy Bip01 parent va pelvis translation inverse-bind rekonstruksiyasida ikki marta qo‘llangan. Rocketbox uchun modelning asl bind transformlari saqlandi; eski Galtis yo‘li o‘zgarmadi.
- Kamera instance barqaror, ko‘krak balandligiga yo‘naltirilgan. Oyna 4:3, yuqori gavda va qo‘llar ko‘rinadi. Brauzer screenshot bilan tekshirildi.
- Yangi avatar oynasiga tajribaviy MP4 eksport tugmasi, progress, cancel, preview va download qo‘shildi. 512×384 alpha PNG kadrlar WebGL render targetdan olinib FFmpegga uzatiladi; original audio va vaqtli subtitr saqlanadi.
- Sinov: LOCAL_ID, 27 kadr, natija 2.239093 s, H.264/AAC, download HTTP 200. Dekodlangan original va eksport audio korrelyatsiyasi 0.99997. Avatar hududidagi 0.1/0.8 s kadrlar o‘rtacha farqi 1.829: haqiqiy harakat mavjud.
- Namuna: examples/rocketbox-result-2026-10-31.mp4; kadr: docs/rocketbox-export-frame.png.
- 20 backend testi o‘tdi; frontend build o‘tdi. Rocketbox regression tekshiruvi endi bosh (1.3–1.8 m), pelvis (.85–1.05 m) va yangilangan skinned bounding boxni ham tekshiradi.
- Chegara: sinov qisqa inglizcha namunada bajarildi. Uzoq media, ko‘p bo‘lakli eksport va cancellation brauzerda stress sinovidan o‘tmagan. ASL semantikasi, bilak burchaklari, barmoq shakllari va yuz grammatikasi tasdiqlanmagan; o‘zbek imo-ishorasi yaratilgani da’vo qilinmaydi.

## 2026-10-30 — Ijroni barqarorlashtirish

- Yangi avatar uchun AnimationMixer action har kadrda qayta ishga tushirilmaydi. Mavjud action vaqt bo‘yicha namunalanadi; bo‘lak almashgandagina binding almashtiriladi.
- Tayyor ML harakatli ish avatar oynasida avtomatik yuklanadi. Hisoblash davom etayotgan bo‘lsa holat kuzatiladi.
- Harakatsiz oralig‘lar nutq pauzasi deb taxmin qilinmaydi: interfeys bu vaqt uchun harakat yo‘qligini ko‘rsatadi.
- Asosiy inson-video rejimida foydalanilmayotgan eski ML so‘rovlari to‘xtatildi. Sahifa manzili tanlangan bo‘limni saqlaydi.
- Tekshirildi: frontend TypeScript/Vite build; playback oldinga/orqaga seek, oxirgi kadr, replay, clip almashish va neytral holatni tiklash; real Rocketbox rigida 28 kadr/968 track bilan qayta ijro va barcha suyaklar holatini tiklash.
- API health 200, frontend 200, saqlangan namuna ML status ready. Serverlar qayta ishga tushirildi.
- Brauzerda ushbu o‘zgarishlarning vizual tekshiruvi bajarilmadi. Build 3D chunk hajmi haqida ogohlantiradi. Yangi avatar MP4 eksporti va lingvistik tasdiq hali bajarilmagan.

# Yangi teksturali ayol modeli

## To‘liq media timeline bosqichi

NaturalAvatarTimeline.tsx endi faqat birinchi bo‘lak o‘rniga tayyor rejadagi barcha harakat bo‘laklarini yuklaydi (sinov chegarasi 30 bo‘lak va jami 10 000 kadr; ortiqcha bo‘lsa ochiq xato). Asl audio/video ijro vaqti yagona master clock: currentTime × timing_scale. Har bir bo‘lak shu output vaqtiga nisbatan o‘z native motion vaqtiga o‘tkaziladi. Bo‘sh intervallarda eski poza davom ettirilmaydi. Slider, media controls, replay va oxirida to‘xtash media bilan birga ishlashi uchun kodlandi.

Ish almashganda eski animatsiya, label va media tozalanadi; eskirgan async yuklashlar AbortController bilan bekor qilinadi. Model faqat kerakli paytda chiziladi (frameloop demand); qiyofa pauzada har bir freymni qayta render qilmaydi. Yangi ML so‘rovini tayyorlash va cancel tugmalari mavjud, frontend avtomatik katta dataset yuklamaydi yoki modelni qayta o‘qitmaydi. Serverning mavjud en-only/CPU/readiness tekshiruvlari saqlanadi. Studiyaga Yangi avatarda sinash tugmasi qo‘shildi.

node scripts/check-avatar-timeline.mjs pauza/gap, aniq interval chegaralari, native pacing va noto‘g‘ri/overlap vaqtlarni tekshiradi. node scripts/check-rocketbox-motion.mjs haqiqiy mavjud 28-kadrli model chiqishini tekshiradi. Backend 20 pytest o‘tdi; frontend TypeScript/Vite build o‘tdi. Ushbu yangi UI yo‘li brauzer vositasi disabled bo‘lgani sabab klik va vizual sinovdan hali o‘tkazilmadi. Yangi ML generation/cancel tugmalari real generatsiya bilan bu bosqichda qayta sinalmadi. Oldingi bo‘limlardagi faqat bitta bo‘lak haqidagi yozuv tarixiy holatdir.

## Keyingi harakat bosqichi

Rocketbox skeletiga 40 SMPL-X upper-body va barmoq kanal xaritasi qo‘shildi. Yangi qiyofa oynasi saqlangan ishning mavjud ML planidan birinchi harakat bo‘lagini yuklaydi. Ijro/pauza, boshidan va vaqt slayderi bor. Yangi MaDiS generatsiyasi avtomatik ishga tushmaydi; ushbu sinov tayyor harakat faylidan foydalanadi.

node scripts/check-rocketbox-motion.mjs haqiqiy mavjud 28-kadrli MaDiS chiqishi bilan 968 trek yaratdi, pozalar o‘zgarishi, transformlarning chekli qiymatlari, barmoq trek mavjudligi va tana masshtabi metrda qolishini tekshirdi. Bu vizual yoki lingvistik tekshiruv emas.

Foydalanish: /?view=avatar&job=LOCAL_ID → Saqlangan ML harakatini yuklash → Tajribaviy ijroni boshlash. Hozir birinchi bo‘lak alohida ko‘rsatiladi; to‘liq media sinxronligi yoki yangi avatar bilan MP4 eksporti qo‘shilmadi. Yuz ifodasi koeffitsiyentlari taxminan ijro etilmaydi; ular alohida moslashuv talab qiladi. Qo‘l mean/bind kalibrlashi, bilak o‘qlari va barmoqlar sifati brauzerda tekshirilishi kerak. Lokal brauzer vositasi disabled qaytargani uchun vizual sinov bajarilmadi.

Manba: https://github.com/microsoft/Microsoft-Rocketbox
Model: Assets/Avatars/Adults/Female_Adult_01/Export/Female_Adult_01_facial.fbx.
Ruxsat: model papkasida upstream MIT LICENSE.md saqlangan.

Original model va teksturalar assets/avatars/rocketbox-female-01 ichida. scripts/convert-rocketbox-glb.mjs original FBXni GLBga o‘tkazadi, original diffuse rasmlarni joylaydi, takroriy yuz tizimlaridan ARKit nomli 52 kanalni saqlaydi, santimetrdan metrga scale beradi. Original FBX o‘zgartirilmagan. Chiqish female.glb 34449988 bayt. 80 skin bone, ikkala qo‘lda 30 barmoq bo‘g‘imi, 52 yuz kanali, 3 embedded PNG. Bo‘yi 1.743 m. FBXda qo‘shimcha root Bone GLBda umumiy node bo‘lib qolgan.

frontend/src/NaturalAvatar.tsx GLTFLoader bilan asli teksturalangan modelni yuklaydi, beldan yuqori kamerani va qiyofa burish boshqaruvini beradi. Yangi ayol modeli menyusidan yoki /?view=avatar orqali ochiladi. Asosiy inson videoli studiya saqlangan.

node scripts/check-natural-avatar.mjs sonli va tuzilma auditidan o‘tdi. Frontend TypeScript/Vite build o‘tdi. GLB HTTP 200 bilan berilishi tekshirildi. 930 KB atrofidagi lazy Three.js chunk hajmi ogohlantirishi bor.

Brauzer boshqaruvi Work tomonidan disabled javobi sabab yangi model hali ekranda vizual tekshirilmadi. UI qiyofasi, UV yo‘nalishi, soch alpha va kamera tekshirilgan deb hisoblanmasin. Bu model hali studiya tarjimoni sifatida yoqilmagan.

Qo‘l harakatlari va yuzning lingvistik belgilarini SignAvatars 3D annotatsiyalaridan retarget qilish bajarilmagan. Modelning qiyofasi SignAvatar.org’dagi MetaHuman bilan bir xil deb va’da qilinmaydi. Texnik suyak va yuz kanallari mavjudligi ASL ijrosining to‘g‘riligini isbotlamaydi.
