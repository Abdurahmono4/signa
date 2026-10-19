# Signa tekshiruvlari

## 2026-10-19 — neyron ASL integratsiyasi

Asosiy sahifa endi MaDiS–How2Sign gap → harakat oqimiga ulangan. Quyidagi eski tezkor lug‘at va harflash kuzatuvlari tarixiy natijalar; ular neyron modelning sifatini tasdiqlamaydi.

CPU muhiti haqiqiy Qwen3 modelini yuklash bilan tekshirildi. `test-neural-motion.mjs` 40 bo‘g‘im tartibi, haqiqiy inverse-bind matritsalari, chap/o‘ng qo‘l va barmoqlar izolyatsiyasi, murakkab aylanishlar, seek/replay hamda manba o‘zgarmasligini tekshiradi. `test_neural.py` to‘liq kadr saqlanishi, vaqt chizig‘i, uzun matn bo‘linishi va revision keshi qoidalarini tekshiradi. Lifecycle/API sinovlari kichik test jarayonlari bilan bekor qilish, timeout, jarayonni yig‘ishtirish, to‘liq bo‘lmagan indeks va yo‘l/revision cheklovlarini tekshiradi; ular model chiqishi deb ko‘rsatilmaydi.

**Haqiqiy neyron inferensiya bajarildi.** Foydalanuvchining mavjud 21.104 soniyalik MP4 fayli mahalliy API orqali MaDiS modeliga yuborildi: uchta gap guruhi uchun 88, 56 va 16 kadr olindi. Xom tokenlar tekshiruvi yoqilgan qayta sinovda ham uchala tana/qo‘l oqimi bo‘sh emasligi tasdiqlandi. CPU’da oxirgi zanjir 98.469 soniya davom etdi; keyingi ijro keshdan boshlanadi. 160 haqiqiy kadrdagi 2.74 million deformed vertex namunasi chekli, 7 ekran nisbati va 3 burchakda qo‘l/yuz kamera ichida qoldi.

Yangi `education-demo.mp4` brauzer fayl tanlagichi orqali yuklandi va haqiqiy ASR → MaDiS zanjiri bajarildi. Dastlab 20 so‘zli, tinish belgilarisiz qo‘shilgan matnda upstream bo‘sh javobni `[0]` bilan almashtirib, 4 kadr bergani topildi. Runner endi bunday bo‘sh xom tokenlarni VAE dekodlashdan oldin rad etadi. Nutq pauzalari bo‘yicha uchta gapga ajratilgan qayta ishlashda 32, 36 va 40 haqiqiy kadr yaratildi. Matnning barcha so‘zlari saqlandi; harflab ijroga qaytilmadi.

**Haqiqiy brauzer eksporti bajarildi:** original MP4 + burchakdagi harakatli avatar + subtitr birlashtirilib, 7,606,427 baytli 720×1280 VP9/Opus WebM yuklab olindi. PyAV 518 video kadrni o‘qidi; ovoz RMS 0.182, jim emas. Bu dastlabki yozuvda 21.016 soniyalik manba ovozi 21.96 soniyaga cho‘zilgani aniqlandi. RAF soati kechiksa media orqaga seek qilishi tuzatildi: endi media.currentTime asosiy soat, alohida ishora pauzalari esa wall-clock bilan boshqariladi. 21.0155 soniya, 160 vaqt bo‘lagi va 350 ms kechikadigan RAF regressiyasida tuzatilgan hook 0 ta corrective seek bilan manba oxiriga yetdi. **Ushbu oxirgi vaqt tuzatishi va yangi yaqin kamera bilan qayta brauzer yozuvi hali tasdiqlanmagan**: vosita keyin “Local browser use is disabled in Work settings” deb qaytdi.

Yangi kamera yuz/qo‘lni taxminan 2× kattalashtiradi, butun tayyor ketma-ketlik uchun bir xil kadrni saqlaydi. To‘q kiyim qo‘lga nisbatan >5:1 yorug‘lik kontrasti beradi. Bu ko‘rinish va texnik ijro tekshiruvlari: ASL ma’nosi, barcha gapning to‘liq tarjimasi yoki tushunarliligi tasdiqlanmagan. Model qisqa harakat qaytarishi, SMPL-X qo‘lning bazaviy mean holati va yuz ifodalarining Galtisga mosligi asosiy ochiq cheklovlar.

**Oxirgi qayta sinov:** xom token va matn lug‘ati himoyasi bilan 21.104 s video 54.234 s CPU vaqtida tayyorlandi, harflangan so‘z 0. 9.363 s ta’lim namunasida uchta tugallangan gap 48.187 s ichida 32/36/40 kadr qaytardi. Modelga uzatiladigan matnga yetishmagan yakuniy nuqta qo‘shildi; barcha so‘zlar va asl transkript saqlandi. Compact lug‘atga sig‘magan tokenlar endi PAD/EOS bilan jim almashtirilmaydi: faqat kichik harfga o‘tkazish to‘liq qamrov bersa shu variant ishlatiladi, aks holda aniq xato qaytariladi. 75 backend testi, production build, neural 40 bo‘g‘im retarget testi, media soati regressiyasi, 50 klip invariantligi va haqiqiy 160 kadrning yaqin kamera testi o‘tdi.

## Qayta qurilgan sahifa uchun avtomatik tekshiruv

Loyiha papkasidan:

```powershell
npm.cmd test
npm.cmd run build
node scripts/test-avatar.mjs
node scripts/test-interpreter.mjs
node scripts/test-playback.mjs
node scripts/test-playback-media.mjs
node scripts/test-framing.mjs
node scripts/test-composite-export.mjs
```

Standart tezkor so‘z rejimi qo‘shilgach backend to‘plamining 48 testi o‘tdi. Avatar bog‘lanishi va qayta bezatilgan avatarda yozilgan harakat/yuz kanallari saqlanishi sinovlari barcha 50 klip bilan o‘tdi. Qayta qurish jarayonida TypeScript/Vite production build, sof vaqt xaritasi va media/hook boshqaruv sinovlari ham muvaffaqiyatli o‘tdi. Korpus yoki kod keyin o‘zgarsa, shu buyruqlar qayta bajarilishi kerak. Testlar va manifest amaldagi versiya uchun asosiy manbadir.

- Backend testlari yuklash/API, vaqtli ASR pipeline, inson tekshiruvi qoidalari va yangi ijro rejasini tekshiradi. Model chaqiruvlari almashtirilgan; haqiqiy nutq aniqligini o‘lchamaydi.
- `test-avatar` aktivlar/tracklar bog‘lanishi va kadrlarning chekli matritsalarini tekshiradi.
- `test-interpreter` asl va qayta bezatilgan modeldagi qo‘l/barmoq koordinatalari, yuz morph kanallari va ularning vaqtini solishtiradi; soch/ko‘zoynak/kiyim biriktirmalarini ham tekshiradi.
- `test-playback` klip vaqti/tezligi xaritasi, media pauzalari, bosh/ichki/oxirgi bo‘shliqlar, noma’lum matn, aniq chegaralar, oldinga/orqaga seek va yakuniy vaqtni tekshiradi. Backend standartda avtomatik harflash o‘chiqligi, noma’lum so‘zning nol qo‘shimcha holdi, ixtiyoriy yoqish va 1.25×/kanonik window chegaralarini tekshiradi.
- `test-playback-media` hookni sun’iy media/RAF bilan ishga tushiradi: pauza, seek, reset, hold/resume, bufferingdan qaytish, avatar tayyorligini kutish, kechikkan/rad etilgan play, yakun va qayta ijro tekshiriladi. Bu haqiqiy brauzer sinovini almashtirmaydi.
- `test-framing` qayta bezatilgan 50 klipni 61 kadr, yetti panel nisbati va uch ko‘rish burchagida tekshirdi. Qo‘l/barmoq markazlari atrofida 5 sm zaxira, yuz va soch chegaralari kamera ichida qoldi; eng katta normallashgan proyeksiya x=0.865, y=0.858 bo‘ldi. Bu kadr chegarasini tekshiradi, ishora tushunarliligini emas.
- Haqiqiy PyAV bilan kodlangan MP3 va ID3 APIC muqova tasviri testida rasm `attached_pic` stream sifatida ko‘rindi. Yuklash hamda eski metadata javobi baribir audio turini qaytardi; haqiqiy video uchun video turi saqlandi.
- `test-composite-export` chiqish o‘lchami va avatar panelining chegaralarini, klikda audio faollashtirish/qayta ishlatishni va recorder hayot siklini mock obyektlar bilan tekshirdi. Boshlanishni kutish, umumiy soat muzlaganda pause/resume, intentional media hold, final chunk, capture/codec/draw xatolari, bekor qilish va ijro to‘xtashidagi resurs tozalash o‘tdi. Bu WebM kodlagichining haqiqiy brauzer natijasi o‘rnini bosmaydi.
- Ixtiyoriy `fingerspelling=true` integratsiya sinovi `ABCDEFGHIJKLMNOPQRSTUVWXYZ` ni bitta noma’lum so‘z sifatida rejaladi: 26 haqiqiy harf aktivi, ularning manba davomiyliklari, `spelled_words: 1`, `signed_words: 0`, `caption_words: 0` tekshirildi. Takror harflar, apostrof, noma’lum/non-Latin belgilar, yetishmagan harf, tasdiqlangan/manba rejimi hamda so‘z/harf/vaqt limitlari uchun alohida sinovlar mavjud. Sun’iy fixturelar lingvistik ekspert tasdig‘i emas.
- Build katta Three.js bundle haqida ogohlantirishi mumkin; ogohlantirish muvaffaqiyatli buildni bekor qilmaydi.

Bular muhandislik sinovlari. Ular ishoraning ma’nosi, ASL gap grammatikasi yoki kar ASL foydalanuvchilari tushunarliligini baholamaydi.

## Avatarli video eksporti — haqiqiy brauzer tekshiruvi hali o‘tkazilmagan

Yangi `compositeExport.ts` va interfeys integratsiyasi production builddan o‘tdi. `test-composite-export.mjs` mock hayot sikli sinovi, 50 klipning avatar kadrlariga oid sinovlar va media boshqaruvi sinovi ham o‘tdi. Bular haqiqiy MediaRecorder kodlagichini, ishlab chiqarilgan fayl ovozini yoki downloadni sinamaydi.

Shu sessiyadagi yakuniy brauzer urinishida vosita **“Local browser use is disabled in Work settings”** deb javob berdi. Shu sabab yangi eksport uchun quyidagilar **tasdiqlanmagan**: WebM haqiqatan yozilishi, original nutq ovozining borligi, media pauzalarida audio/avatar mosligi, bekor qilishdan keyingi qayta eksport, tayyor preview va yuklab olingan faylning mustaqil pleyerda ijrosi. Avvalgi media/harflash brauzer kuzatuvlari bu yangi eksport tekshiruvi o‘rnini bosmaydi.

Brauzer yoqilgach [UI_REDESIGN.md](UI_REDESIGN.md) ning eksport qadamlarini bajaring: mos ishorali video bilan original kadr, burchakdagi harakatli avatar, ovoz va subtitrni tekshiring; oldin mute qilingan previewdan ham ovozli eksport va avvalgi ovoz holatining tiklanishini tekshiring. Rejadagi holdlar davomida video/ovoz to‘xtab, ishora davom etishini kuzating. Tayyor WebM faylni qayta ochib, boshidan oxirigacha tekshiring. Natija va fayl xususiyatlari keyin shu qaydga qo‘shiladi.

Amaldagi chiqish faqat brauzerdagi **WebM** yozuvidir. **MP4 eksporti amalga oshirilmagan.** Umumiy ASL gap tarjimasi va lingvistik sifat tasdiqlangan deb olinmaydi.

## Standart tezkor so‘z rejimi — haqiqiy ish rejasi

Mavjud `GXW.mp3` ishi fayl yoki tarixini o‘zgartirmasdan API orqali o‘qib tekshirildi: original media 13.770839 soniya, matnda beshta so‘z, lug‘atga mos ishora 0. Yangi standart `fingerspelling=false` rejasi ham aynan 13.770839 soniya: qo‘shimcha hold 0, harflangan so‘z 0. Noma’lum so‘zlar faqat o‘z vaqtida subtitrda ko‘rinadi. Oldingi avtomatik harflash sabab shu faylning 67.190839 soniyaga cho‘zilishi standart oqimdan olib tashlandi.

Foydalanuvchi ixtiyoriy `fingerspelling=true`ni yoqsa, shu matnning besh so‘zi uchun 67.190839 soniyalik to‘liq harflash rejasi saqlangan. Bu o‘qilgan reja tekshiruvi; barcha ijroni brauzerda kuzatish yoki ASL tushunarlilik natijasi emas. Standart oqimning tezlashishi noma’lum so‘zlarga yangi ASL ishora yaratilganini anglatmaydi: shu namunada besh so‘z ham subtitrdir.

**Amaldagi brauzer tekshiruvi:** shu GXW faylida asosiy tugma bosildi, ijro boshlandi va **Pauza** bilan to‘xtatildi. Joriy “If” so‘zi subtitrda, umumiy vaqt **00:13**, **Harflab ko‘rsatish** esa belgilanmagan edi. Belgini yoqish pauzadagi rejani **01:07** va “If · I”ga o‘zgartirdi. O‘chirish **00:13** tezkor rejimga qaytardi va harf ko‘rinishi yo‘qoldi. Joriy fayl saqlandi; rejim almashishi qo‘shimcha ASR boshlamadi. Subtitrda butun gap o‘rniga joriy so‘z ko‘rinishi ham tekshirildi.

Shu GXW audiosi avvalgi avtomatik harflash yoqilgan brauzer kuzatuvida ham audio sifatida ochilgan: beshta so‘z uchun 16 ta asl harf klipi va 67.190839 soniyalik reja yaratildi. **HARFLAB** holati/harakat kuzatilib, pauza bosilgan. Bu hozirgi ixtiyoriy rejimga tegishli dalil, yangi standart emas. Foydalanuvchining to‘liq nutq transkripti va media fayli manba ZIP paketiga kiritilmaydi; kuzatuv ASR matnining lingvistik to‘g‘riligini alohida tasdiqlamaydi.

## Avvalgi tabiiy tezlikdagi haqiqiy demo kuzatuvlari

Quyidagi davomiyliklar tezkor so‘z rejimi qo‘shilishidan oldin o‘lchangan. Ularni yangi standart 1.25× rejaning vaqti deb olmang. To‘liq tabiiy tezlik ixtiyoriy harflash rejimida saqlanadi.

**Namunani sinash** tugmasi `frontend/public/avatar/demo.wav` ni fayl sifatida haqiqiy yuklash va `balanced / small.en` transkripsiyasiga yubordi. Tayyor matn ASR o‘rniga qo‘yilmadi. Original sintetik audio 15.7 soniya; tabiiy ishora pauzalari bilan umumiy reja 24.88 soniya bo‘ldi. Tayyorlashdan keyin ijro avtomatik boshlandi va oxirida tugma **Qayta ijro etish**ga o‘tdi.

Matnning Hello, Please, Book, My Name Is va Bye qismlari mavjud manba animatsiyalari bilan ijro etildi. Bu manba yozuvlari mahalliy ASL mutaxassisi tasdig‘i degani emas. Noma’lum matn uchun yangi ishora yaratilmaydi.

Brauzerda pauza va slayder orqali seek tekshirildi. Umumiy vaqt 0.65 soniyaga qo‘yilganda manba audio `currentTime: 0.44`, `paused: true` holatida edi; avatar Hello klipini davom ettiradigan vaqtga qo‘yilgan. Bu kengaytirilgan vaqtdagi media pauzasi kuzatuvidir.

**A–Z harflashi qo‘shilishidan oldingi video kuzatuvi:** `examples/education-demo.mp4` haqiqiy fayl tanlagich orqali yuklandi. Asosiy tugma bilan haqiqiy ASR ishladi, Please va Book topildi. 9.363 soniyalik video uchun o‘sha lug‘at rejasi 13.96 soniya bo‘ldi; avtomatik boshlanish va oxiriga yetish kuzatildi. Bekor qilingan tayyorlashdan keyin qayta boshlash ham tekshirildi. Amaldagi harflash yoqilgan reja noma’lum so‘zlar uchun qo‘shimcha kliplar beradi; uning vaqti 13.96 soniya deb olinmaydi.

**Hozir ixtiyoriy bo‘lgan A–Z rejimi uchun haqiqiy brauzer kuzatuvi:** Windows SAPI orqali “Yes.” sintetik audiosi yaratilib, `ASL-alifbo-sinov.wav` sifatida yuklandi. Haqiqiy ASR “Yes”ni tanidi. 1.414376 soniya manbadan 11.53104265 soniyalik tabiiy ijro rejasi olindi: bitta harflangan so‘z, uchta Y–E–S harfi, lug‘at ishorasi 0, qolgan klipsiz so‘z 0. Tayyorlashdan keyin avtomatik ijro va yakun kuzatildi; tugma **Qayta ijro etish**ga o‘tdi. Qayta ijro bosilganda **HARFLAB**, “Yes · Y”, “Harflab ko‘rsatilmoqda: Yes” va **Pauza** ko‘rindi. Bu bitta qisqa sintetik namunada ishlaydigan harflash oqimini ko‘rsatadi; umumiy ASL gap tarjimasi sifatini o‘lchamaydi. Standart tezkor rejim ushbu noma’lum so‘zni avtomatik harflamaydi.

Sahifa yangilanganda shu sessiyadagi oxirgi ish/fayl tiklanishi va avtomatik ijro boshlanmasligi ham tekshirildi.

Takrorlash qadamlari [UI_REDESIGN.md](UI_REDESIGN.md) da. Ushbu demo bitta sintetik namuna; nutq aniqligi, tezlik yoki foydalanuvchi tajribasining umumiy benchmarki emas. ASL tushunarliligi bo‘yicha foydalanuvchi tajribasi hali o‘tkazilmagan.

## Avvalgi tekshiruv qaydi — yangi sahifa natijasi emas

Quyidagi qayd 2026-10-17 dagi avvalgi interfeys va `/sign-plan` vaqt chekloviga tegishli. Undagi 43% paneli, laboratoriya va alohida preview yangi asosiy sahifada ko‘rsatilmaydi. `/sign-plan` audit qoidalari API da saqlangan; yangi sahifa esa `/playback-plan` orqali ishorani tabiiy davomiylikda ijro qilib, media vaqtiga pauza qo‘shadi. Tarixiy 43% ni yangi ijro natijasi bilan tenglashtirmang.

### Haqiqiy small.en bilan yangi tekshiruv

**Namuna:** oldindan mavjud `frontend/public/avatar/demo.wav`, sintetik inglizcha nutq; API ga `ASL-pipeline-validation.wav` nomida yuklandi. **Profil:** balanced / small.en. **Media davomiyligi:** 15.7 soniya. **Kuzatilgan yakunlanish vaqti:** 8.08 soniya. Bu bitta qisqa lokal ishga tushirishning devor vaqti; umumiy tezlik benchmarki yoki foydalanuvchi tajribasi emas.

Natija matni:

```text
Hello.
Please.
Book.
My name is...
Bye.
```

7 ta normallashtirilgan so‘z, bitta audio bo‘lagi, 15.7 soniya tahlil, 0 qayta urinish, yakuniy shubhali oraliq yo‘q. Ushbu kuzatuv uchun mustaqil inson tayanch matni bilan WER hisoblanmagan. Shubhali oraliq yo‘qligi matnning to‘liqligi yoki aniqligini isbotlamaydi.

Manba preview rejimidagi lug‘at natijasi:

| Element | Nutqdagi vaqt | Holat |
|---|---|---|
| hello | 0.00–0.44 s | timing_review |
| please | 2.84–3.26 s | timing_review |
| book | 5.52–5.78 s | timing_review |
| my name is | 8.88–11.28 s | source_preview |
| bye | 12.24–12.44 s | timing_review |

5 elementdan 0 tasi ekspert tasdiqlagan `matched`, 1 tasi manba preview, 4 tasi vaqt tekshiruviga tushdi, yo‘q klip 0. Sinxron ijro qamrovi **3 / 7 so‘z = 43%**. To‘rtta alohida so‘zning ASR vaqti manba ishora davomiyligiga juda qisqa kelgani uchun ijro bloklandi. Bu natija vaqt moslashtirish hali muammo ekanini ko‘rsatadi. 0.5–2 nisbati muhandislik chegarasi; ASL tabiiyligi bo‘yicha tasdiqlangan standart emas.

Brauzerda 43% paneli, Hello uchun tabiiy davomiylikdagi alohida preview, pauza va 0.5× tezlik boshqaruvlari tekshirildi. “Tekshirish kerak” filtri to‘rtta `timing_review` elementini ko‘rsatdi. Manba previewlari o‘chirilganda reja 0 / 7 ijro qamrovi va 7 ta klipsiz so‘zni qaytardi; qayta yoqilganda 3 / 7 va 43% bo‘ldi. Preview ochilganda manba media pauzada bo‘ladi. Bu alohida ko‘rish sinxron tarjimani tayyor qilib qo‘ymaydi va ekspert tasdig‘i bermaydi.

Xom API natijalari shu hujjat bilan birga saqlangan: [2026-10-17-demo-validation.json](evidence/2026-10-17-demo-validation.json). Yangi korpus yozuvi yoki haqiqiy lingvistik tasdiq yaratilmagan.

### Avvalgi medium.en o‘lchovlari — qayta bajarilmagan yozuv

Quyidagi raqamlar loyiha hujjatining avvalgi versiyasidan saqlandi. Ushbu yangilashda qayta o‘lchanmadi. Avvalgi muhit yozuvi: CPU INT8, AMD Ryzen 9 5900HX, 6 hisoblash oqimi. Har bir o‘lchovning to‘liq buyruq/logi, normallashtirish kodi va muhit manifesti loyiha bilan bog‘langan xom dalil sifatida saqlanmagan; shu sabab raqamlar magistrlik ishida mustaqil yakuniy benchmark sifatida ishlatilishidan oldin qayta tekshirilishi kerak.

| Namuna | Avval yozilgan kuzatuv |
|---|---|
| Sintetik inglizcha nutq, 94.673 soniya | 170 tayanch so‘z, 170 aniqlangan, normallashtirilgan WER 0; 70.97 soniya hisoblash |
| 124.121 soniyalik foydalanuvchi musiqali audiosi | Oldingi 36 so‘zdan 145 so‘zga; so‘nggi so‘z vaqti 70.24 dan 118.64 soniyaga |
| 21.104 soniyalik inglizcha video | Oldingi va yangi natijada 43 tadan so‘z |

Avvalgi izohga ko‘ra, sintetik namunada olti bo‘lim, uch soniyalik tanaffuslar, to‘rtinchi bo‘limda 10 baravar pasaytirilgan ovoz bor; o‘rta va oxirgi nazorat iboralari topilgan. WAV va tayanch matn `examples/long-speech-demo.*` da mavjud.

Musiqali namuna uchun avvalgi yozuv barcha olti bo‘lak tahlili va to‘rtta qayta urinishni qayd etgan. 70.4–95.4, 97.4–102.5 va 118.9–123.2 soniyalardagi faol oraliqlar tinglash uchun qolgan; ular instrumental musiqa bo‘lishi ham mumkin. Inson tayanch matni yo‘qligi sabab bu namuna uchun WER hisoblanmagan.

So‘z sonining oshishi aniqlik oshganini isbotlamaydi. Bitta sintetik namunadagi 0 WER real odam nutqi, aksent, shovqin yoki qo‘shiq uchun kafolat emas. Hozircha foydalanuvchilar bilan ASL tushunarlilik bahosi va keng ekspert tasdiqlagan gap korpusi yo‘q. Yakuniy tadqiqot protokoli va qabul mezonlari [RESEARCH_PLAN.md](RESEARCH_PLAN.md) da.



