## 2026-11-02 — Haqiqiy brauzer sinovi va uzun eksport tuzatishi

- 117 backend testi 41.17 s da o‘tdi; frontend build o‘tdi. Node playback/timeline/retarget/flow va yangi frame-upload tekshiruvlari o‘tdi.
- Brauzer boshqaruvi mavjud bo‘ldi. To‘xtagan xizmatlar start.ps1 bilan qayta ishga tushirildi. Qayta tayyorlash tugmasi amalda tekshirildi.
- Haqiqiy uzun eksport avval 390 va 327-kadrlarda Vite proxy connect ETIMEDOUT bilan uzildi. Proxy backend socketlarini keepAlive Agent orqali qayta ishlatadi. Frame PUT bir xil sessiya/index/body bilan vaqtinchalik network/408/429/5xx xatoda 4 urinishgacha takrorlanadi; 409/413/422 va cancellation takrorlanmaydi. Unit/Node testlar buni tekshirdi.
- Eksport xatosi parent status/autoPrepare o‘zgarganda load() bilan tozalanib ketayotgani tuzatildi: joriy ish yuklangan bo‘lsa qayta yuklash xabarni yo‘qotmaydi. Brauzerda aniq Kadr 328/1397 xabari saqlanib ko‘rsatildi.
- Eksport uchun mustaqil 4:3 kamera, skeleton refresh va bo‘sh avatar kadri himoyasi qo‘shildi. Shaffof PNG dastlab viewerda noto‘g‘ri talqin qilingan; RGBA piksel tahlili va FFmpeg RGB kadrida avatar normal ekani tasdiqlandi. Bu tasdiqlangan model kichrayishi xatosi deb hisoblanmaydi.
- Qisqa yangi real browser eksport: 54 kadr, token LOCAL_ID; 2.239093 s, 86544 bayt. examples/high-capture-browser-20261102-001.mp4.
- Yakuniy uzun real browser eksport: 1397 ta 1024×768 PNG, token LOCAL_ID; MP4 6037554 bayt, 58.073107 s, H.264/AAC. Download aynan lokal faylga teng; to‘liq video/audio decode xatosiz. Native video oqimi 57.6 s, audio metadata 58.1878 s; output video 57.666667 s, audio 58.073107 s. Bu bit-identical audio yoki sub-frame timing tengligi tasdig‘i emas.
- Ko‘rilgan real motion kadri docs/long-result-20261102-001.jpg. UI yakuniy Video tayyor holati va download linkni ko‘rsatdi. Dalil examples/browser-test-results-20261102-001.json; docs/browser-tested-20261102-001.png.
- ASL semantik aniqligi va yuz/qo‘l lingvistik tekshiruvi bajarilmagan. Avvalgi dataset yaxlitligi cheklovlari saqlanadi.

## 2026-11-02 — Avatar kadrlari va natija ko‘rinishi

- Rocketbox ayol modeli, kamera va qo‘l harakati o‘zgartirilmagan. Yangi eksport uchun shaffof kadr 1024×768 (oldin 512×384), qayta ishlatiladigan render target/pixel buffer va GPU imkoniyatiga ko‘ra 4× gacha MSAA qo‘shildi. H.264 CRF 18. Yangi browser capture yo‘li hali vizual sinovdan o‘tmagan: CUA mahalliy browser use disabled qaytardi.
- Subtitr ASS formatida pastda 32 px/720p, tadqiqot belgisi tepada 14 px. 1080p da o‘lchamlar proporsional. Matn ichidagi ASS buyruqlari literal ko‘rsatiladi. Subtitr o‘chirilsa ham unsupported intervaldagi nutq matni saqlanadi.
- Oddiy natijaga Qayta tayyorlash tugmasi qo‘shildi: oldingi MP4 ochiq qolish o‘rniga cached harakatni yuklab, yangi eksportni boshlash mumkin. Asl fayl/oldingi tokenli eksportlar saqlanadi. Tugma frontend builddan o‘tdi; brauzer klik sinovi qolgan.
- Haqiqiy 58.1878 s namunaning 7 motion / 280 kadrida bosh, qo‘l va barmoq bo‘g‘imlari kamera chegarasida; bu CPU geometriya tekshiruvi, tekstura/piksel yoki ASL tushunarlilik bahosi emas.
- 117 backend testi (14.04 s), frontend build va Node flow guards o‘tdi. Yuqori o‘lchamdagi sintetik PNG → API → FFmpeg testida haqiqiy H.264/AAC va davomiylik tekshirildi. Sintetik kadrlar avatar renderi deb berilmagan.
- examples/avatar-quality-review-20261101-001.mp4: oldingi haqiqiy avatar tasviri bilan original video qayta kompozitsiya qilindi, yangi subtitr ko‘rinishi tekshirildi; bu yangi 1024×768 avatar kadrlari emas. FFprobe: 2.239093 s, H.264/AAC. PNG vizual ko‘rildi. Aniq dalillar: examples/quality-readiness-20261102-001.json.
- Faol media/inference yo‘qligi tekshirilib serverlar qayta ishga tushirildi; frontend va health HTTP 200. Uzun yangi 3D MP4 browser testi va ASL mutaxassisi bahosi hali qolgan. Katta train arxivlaridagi oldindan aniqlangan buzilishlar bu bosqichda tiklanmagan.

## 2026-11-01 — Hisoblash va eksport resurslari bir xil chegaraga keltirildi

- Oldingi frontend chegarasi (30 motion / 10000 frame) og‘ir model tugagandan keyin tayyor natijani ochishni rad etishi mumkin edi. Backend endi compatible chunklar sonini worker ochilishidan oldin tekshiradi; plan API limits qaytaradi. Frontend shu budgetdan foydalanadi: 75 motion / 30000 generated frame. Bu 75 iboraning sifati yoki barcha 20 daqiqalik videolar bo‘yicha sinov tasdig‘i emas; chegaralar unit/Node testlarda tekshirilgan.
- Backend build_plan ham kadr/bo‘lak umumiy hajmini tekshiradi. Matn/subtitrni saqlash yo‘li qoladi; ko‘p iborali faylga oldindan aniq xabar beriladi. Avatar, sifat parametrlari va asl media o‘zgarmadi.
- Render start disk bo‘sh joyini tekshiradi: har PNG uchun maksimal 1 MiB, output soniyasi uchun 2 MiB kodlangan video zaxirasi va 512 MiB bo‘sh marja. Native inson renderida PNG hissasi yo‘q. Bu disk rezervatsiyasi emas, konservativ baho; boshqa jarayonlarning keyingi yozishlarini kafolatlamaydi.
- Disk yetishmasligi HTTP 507 qaytaradi; job holati, token va papkalar o‘zgarmaydi. Test chegarasi, bitta bayt kam holat, worker ochilmasligi, katta motion inputi va frontend noto‘g‘ri limits tekshirildi.
- 111 pytest, frontend build va Node flow guard/budget testlari o‘tdi. Serverlar faol ish yo‘qligi tekshirilgach qayta ishga tushdi. Haqiqiy 7-motion plan limits bilan HTTP 200; frontend/health 200. examples/resource-readiness-20261101-001.json.
- Ushbu bosqichda yangi browser render yoki 75 iborali model inference bajarilmadi. Oldingi uzun videoning 3D MP4 vizual sinovi browser use tool disabled sabab hali qolgan. ASL ekspert bahosi va buzilgan train arxivlarini tiklash ham alohida qoladi.

## 2026-11-01 — Tinish belgisi sababli xato rad etish tuzatildi

- D77 ishining In order to obtain that, iborasi v4 da so‘z yetishmasligi emas, model inputida vergulga nuqta qo‘shilib ,. tokeni hosil bo‘lgani sabab rad etilgani aniqlandi. Bu oldingi qisman sinov xulosasini aniqlashtiradi.
- Preflight va runner request bir xil model_caption qoidasi bilan tayyorlanadi: faqat terminal vergul/nuqtali vergul/ikki nuqta yakuniy nuqtaga aylantiriladi. Ichki tinish belgisi va so‘zlar o‘zgarmaydi. Original transcript/timestamps/subtitle matni tegilmagan. Cache v5; oldingi motion/MP4lar saqlangan.
- Haqiqiy 58.1878 s / 7 bo‘lakli ish yangi MaDiS inference bilan 7 generated, 0 unsupported, partial_motion=false qaytardi. Asl segment 2 hali vergul bilan tugaydi. examples/punctuation-inference-20261101-001.json.
- Xato yoki qisman natijada yopiq Nutq matnini tekshirish boshqaruvi qo‘shildi. U faqat so‘ralganda segment/revisionni oladi, mavjud tahrir API orqali asl vaqtlarni saqlagan holda ishlaydi. Saqlashga request deadline qo‘shildi; eski revision himoyasi saqlangan. Brauzerda klik sinovi hali bajarilmadi.
- 107 pytest, frontend build va Node flow guards o‘tdi. IAB boshqaruvini qayta ulashga qaramay tool Local browser use disabled javobini berdi; foydalanuvchi yoqdim deb bildirgan bo‘lsa ham yangi uzun 3D MP4 eksporti tasdiqlanmagan. 7/7 generatsiya ASL semantik aniqligini isbotlamaydi.
- Sayt/API HTTP 200. Avatar modeli va oddiy sahifa saqlangan. MODEL_TEXT_INPUT.md batafsil sabab/cheklovni tushuntiradi.

## 2026-11-01 — Qisman ML ijrosi, recovery va kadr validatsiyasi

- Bir tokenizer-unsupported ibora butun videoni to‘xtatmaydi: faqat mos chunklar runnerga yuboriladi, unsupported matn/vaqt klipsiz intervalda qoladi. Haqiqiy 58.1878 s / 7 bo‘lakli LOCAL_ID ishida 6 motion / 244 kadr yaratildi; 1 ibora 36.2–38.3 s da subtitrga qoldi. Transcript o‘zgartirilmadi. 18 pozada CPU Three.js retarget/finite track va timeline tekshirildi.
- Plan/holat restartdan so‘ng ham generated=6, unsupported=1 qaytardi. Cache versiyasi v4; oldingi MP4lar saqlangan va eski aniq-token download HTTP 200, 84220 bayt qaytdi. Yangi qisman 3D video browser eksporti Work browser use disabled sabab bajarilmadi. Sintetik kadrlarda haqiqiy FFmpeg testi partial izoh, original matn, H.264/AAC va davomiylikni tekshirdi; bu avatar renderi deb berilmaydi.
- Public previewda asl chunk matni va unsupported izoh ko‘rinadi; eksport intervalida ham izoh bor. Job report va saqlangan neural_summary generated/unsupported sonlarini ko‘rsatadi. Qamrov 0 (lingvistik tasdiq yo‘q), qisman natija to‘liq tarjima deb belgilanmaydi.
- UI failed/cancelled qayta ochilishida retry ko‘rsatadi; polling idle bo‘lsa to‘xtaydi. Request deadline, upload abort/timeout, bosqichga mos retry, eksport token ownership tekshiruvlari qo‘shildi. Ilova/avatarning hozirgi qiyofasi saqlangan.
- PNG signature bilan cheklanmaydi: chunk CRC/tartibi, exact frame o‘lcham, bounded zlib va scanline filter tekshiriladi. Haqiqiy HTTP smoke: 24 baytli buzilgan PNG 422, to‘liq PNG 200, QA sessiya bekor qilindi. examples/partial-recovery-20261101-001.json.
- 98 pytest, frontend build, Node flow guards va haqiqiy 6 motion retarget skripti o‘tdi. Katta Three.js bundle ogohlantirishi qoladi. Serverlar sog‘lom, yangi fit/training bajarilmagan; ASL lingvistik aniqligi tasdiqlanmagan. docs/PARTIAL_MOTION.md va README hozirgi inglizcha oqimga mos yangilandi.

## 2026-11-01 — Train yaxlitligi xatolari va model kirish preflight

- To‘liq train ZIP tekshiruvida frontal 31048 fayl entrysida 5 MP4 barqaror CRC xatosi, yon 31165 entryda 1 CRC xatosi aniqlandi. Birinchi urinishda boshqa frontal klip xato bergan, qayta ikki o‘qishda o‘tgan; sabab aniqlanmadi. Jami 6 kuzatilgan frontal klip ehtiyot chorasi bilan qidiruv/resolverdan chiqarildi. Asl fayllar o‘zgartirilmadi. Qidiruvdagi train yozuvlari 31041, CSVda yo‘q 118 klip alohida.
- Train 2D gzipda 7457472512 ochilgan baytdan so‘ng zlib invalid stored block lengths xatosi qayta tasdiqlandi. Butun train to‘plami sog‘lom yoki o‘qitishga tayyor deb belgilanmaydi. Katta arxiv qayta yuklanmadi. datasets/how2sign/train-integrity-final-001.json va docs/TRAIN_INTEGRITY.md.
- Tekshiruvchi CRC/zlib xatolarini hisobotga yozadi, ZIPlarda qolgan entrylarni tekshiradi va har arxivdan so‘ng progress saqlaydi. ZIP/gzip to‘liq tekshiruvi barcha videolarni dekodlash/JSON schema yoki ASL bahosi emas.
- Model matn tokenizer/compact lug‘ati orqali og‘ir inference oldidan tekshiriladi. Runtime AutoTokenizer bilan 4 matnda tokenlar aynan mosligi tekshirildi; vaznlar yuklanmagan. Unsupported 7 chunkli ishda chunk 2 mos kelmasligi 0.334 s HTTP 422 bilan qaytdi va yangi worker ochilmadi. Matn qisqartirilmadi/almashtirilmadi. Oldingi sog‘lom ibora cached plan bilan HTTP 200.
- Istisno ro‘yxati arxiv hajmi/mtime bilan bog‘langan; o‘zgarishda indeks cache yangilanadi. Unit tests bloklangan klip oldingi cached media orqali ham ochilmasligini resolver darajasida tekshiradi. Python obyekt yasash taqiqlangan data-only map parser qo‘llandi.
- 76 pytest va frontend build o‘tdi. Backend/frontend ishga tushirildi, health HTTP 200. Avatar va asosiy interfeys o‘zgartirilmadi. Model yangi datasetda o‘qitilmadi, ASL aniqligi tasdiqlanmadi. Tafsilot examples/preflight-integrity-20261101-001.json.

## 2026-11-01 — Eksport sessiyasi izolyatsiyasi va uzilgan jarayonni tiklash

- Export finish va cancel endi ixtiyoriy token qabul qiladi; frontend o‘z eksportining tokenini yuboradi. Eski oynaning cancel/finish so‘rovi boshqa sessiyani o‘zgartirmay 409 beradi. Eski API mijozlari uchun tokensiz chaqiruv saqlangan.
- Frame yuklash body kelgandan so‘ng sessiya qayta tekshiriladi. Finish statusini queued ga almashtirish atomar: ikki parallel finish bir marta submit qiladi. Render workerlar token bilan check/update/fail qiladi; avvalgi sessiyadan kechikkan worker yangi natijani buzmaydi. Qayta ASR render_token ni bekor qiladi.
- Bekor qilingan PNGlar darhol o‘chirilmaydi; kechikkan body yozuvi lock ostida rad etiladi. Mavjud worker o‘z folderini yakunda tozalaydi. Foydalanuvchi fayllari o‘chirilmagan.
- Public sahifa frames/rendering holatida ham Jarayonni bekor qilish boshqaruvini ko‘rsatadi; retry xatolari ushlanadi. Avatar modeli yoki asosiy sahifa ko‘rinishi almashtirilmadi.
- Haqiqiy recovery-check.mp4 kichik inglizcha fixture qayta upload/ASR qilindi. LOCAL_ID ishining birinchi frames sessiyasi API orqali cancel qilindi, native inson eksporti boshlandi; eski cancel va finish ikkalasi 409, yangi eksport done. MP4 HTTP 200, 72031 bayt, 2.239093 s. examples/session-recovery-result-20261101-001.json va MP4.
- Brauzerda uzilgan ish qayta ochilganda cancel tugmasi borligi ko‘rildi. Keyingi click Work settingsda browser use disabled bo‘lgani uchun bajarilmadi; recovery API bilan yakunlandi. Ushbu bosqichda yangi 3D brauzer eksporti bajarilmadi.
- Foydalanuvchining boshqa 58.1878 s / 7 segmentli ishini qayta ishga tushirish bilan uzmaslik uchun server restart kutildi. Uning MaDiS generatsiyasi lug‘atdagi qo‘llanmaydigan token sabab failed bo‘ldi. U qayta tahlil qilinmadi/o‘zgartirilmadi. Compact error ko‘rinishiga TXT/SRT havolalari qo‘shildi; qo‘llanmaydigan matn muvaffaqiyatli tarjima deb belgilanmaydi.
- 70 pytest va frontend build o‘tdi. Server yangi kod bilan qayta ishga tushirildi, faol jarayonlar yo‘qligi tekshirildi. Native recovery MP4 FFprobe tekshiruvidan o‘tdi. ASL to‘g‘riligi bu testlar bilan tasdiqlanmaydi.

## 2026-11-01 — Validation/test arxivlari va markaziy audio eksport

- D diskdagi test_2D_keypoints.tar.gz, test_rgb_front_clips.zip, test_rgb_side_clips.zip, val_2D_keypoints.tar.gz, val_rgb_side_clips.zip dataset papkasiga ko‘chirildi. Oldingi val_rgb_front_clips.zip Downloadsdan nusxalandi, originali saqlandi. Tugallanmagan yuklamalarga tegilmadi.
- 6 CSV SHA-256 bo‘yicha D ildizidagi nusxalarga teng. Validation frontal 1739/1741 (2 yo‘q), yon 1741/1741; test frontal 2343/2357 (14 yo‘q), yon 2357/2357. Train/val/test manba-video va sentence-ID kesishmasi 0. metadata-audit-003.json.
- Barcha 6 validation/test arxivining payload yaxlitligi to‘liq o‘qilib tekshirildi: 4 ZIPda barcha entry CRC, 2 TAR.GZda gzip oqimi CRC o‘tdi. evaluation-integrity-001.json all_complete=true. Bu barcha videolarning dekodlanishi yoki barcha JSON schema tekshiruvi emas.
- 12 namuna MP4 to‘liq dekodlandi. Val 3 ibora/1885 2D kadr, test 3/554 kadrda parse xatosi 0; 6/6 frontal video kadr soni mos. 2 yon namunada uzunlik farqi bor. evaluation-inspection-002/report.json va docs/EVALUATION_DATA.md. Test split ibora qidiruvi yoki model fitga qo‘shilmadi.
- Audio MP4da avatar endi markazda; original video bilan eksportning chap-video/o‘ng-avatar ko‘rinishi saqlanadi. Native va PNG yo‘llari haqiqiy FFmpeg piksel testlarida tekshirildi, jumladan audio overlay/side_by_side va video side panel.
- Yangi audio MaDiS inference + brauzer eksporti LOCAL_ID da o‘tdi: token LOCAL_ID; H.264/AAC, 4.048980 s, 134790 bayt, timing_scale=1.0. Kadr ko‘rildi: avatar markazda, subtitrlar pastda. examples/audio-center-20261101-001.mp4 va JSON, docs/audio-center-20261101-001.png.
- 66 pytest va frontend build o‘tdi. Serverlar yangi audio kompozitsiya bilan ishlayapti. Datasetda model qayta o‘qitilmadi, ishora aniqligi yoki tushunarliligi bo‘yicha ekspert tasdig‘i olinmadi.

## 2026-11-01 — Qayta tahlil, sukunat va yangi to‘liq MP4 sinovi

- ASR navbati atomar qilindi: ikki oynaning bitta ishni bir vaqtda boshlashi bitta submit va bitta 409 bilan yakunlanadi. Qayta tahlilda segment/qamrov tozalanadi, revision oshadi, oldingi MP4 tokeni tarixda saqlanadi. Oldingi avatar hisoblashiga cancel yuboriladi.
- Har ASR urinishiga transcribe_token beriladi. Bekor qilingan eski worker yangi urinish boshlanganidan so‘ng natija yoki xato holatini yozolmaydi. Bekor qilish → darhol qayta boshlash poygasi alohida testdan o‘tdi.
- Bo‘sh/whitespace ASR natijasi failed / Nutq topilmadi bilan yakunlanadi. Haqiqiy 2 s raqamli sukunat small modelda oldin You deb gallyutsinatsiya qildi; endi audio bir marta 16 kHz dekodlanib, faqat exact-zero yoki bo‘sh samples modeldan oldin rad etiladi. Eng past nonzero sample ham saqlanishi unit testda tekshirildi. Bu umumiy shovqin/musiqa yoki barcha gallyutsinatsiyalar detektori emas.
- Public nutq modeli small / CPU int8 bo‘ldi; mavjud lokal kesh ishlatildi. Audio 7 so‘z va video 6 so‘zli ikkita qisqa TTS fixture HTTP orqali qayta yuklanib haqiqiy small inference bilan 0 substitution/deletion/insertion qaytdi. Bu tabiiy nutq yoki umumiy aniqlik bahosi emas. examples/small-asr-recovery-20261101-001.json.
- Yangi video LOCAL_ID uchun yangi MaDiS inference, compact preview va brauzerdagi MP4 tugmasi bajarildi. Token LOCAL_ID; 82875 bayt, H.264/AAC, 2.239093 s. examples/reliability-export-20261101-001.mp4. 0.6 s kadr docs/reliability-avatar-20261101-001.png orqali ko‘rib chiqildi; hozirgi model saqlangan. Ishora ma’nosi tasdiqlanmadi.
- Ovozsiz ish LOCAL_ID yangi kodda qayta tahlil qilindi: failed, segments=[], Nutq topilmadi. examples/reliability-20261101-001.json oldingi haqiqiy xato va tuzatishdan keyingi natijalarni bog‘laydi.
- UI qayta urinish so‘rovlari xatoni ushlab ko‘rsatadi; generatsiya/eksport progressi sodda foiz bilan beriladi. 61 pytest va frontend build o‘tdi. Model semantikasi va uzoq tabiiy videolar bo‘yicha mustaqil ekspert/benchmark bahosi hali kerak. Serverlar qayta ishga tushirildi va yangi API sinovlari o‘tdi.

## 2026-11-01 — Asosiy interfeys soddalashtirildi, avatar saqlandi

- Oddiy foydalanuvchi uchun video/audio yuklash, avatar ijrosi, MP4 tayyorlash va yagona natija pleyeri qoldi. Dataset paneli, 1739/31047 klip sonlari, CSV/ZIP holati, matn rejimi va tadqiqot boshqaruvlari asosiy interfeysdan yashirildi. Ichki vositalar tools=1 parametri bilan saqlangan; bu autentifikatsiya emas, interfeys rejimi.
- Dastlabki main komponenti DeveloperApp.tsx ga ko‘chirildi. Public holatda dataset katalogi va train statusi qayta-qayta yuklanmaydi. Tugallangan natija uchun bitta video va aynan shu eksport tokeniga MP4 download qaytadi. Oldingi ishlar va fayllar saqlangan.
- Rocketbox modeli, teksturalar, yuz, barmoqlar, kamera va harakat moslashtirish algoritmi almashtirilmadi. Compact ko‘rikda original video chapda va hozirgi avatar o‘ngda; yakuniy natija bitta videopleyerda. Asl MP4 kompozitsiya yo‘li o‘zgarmadi.
- Frontend build o‘tdi. check-rocketbox-motion.mjs: 80 bone, 30 finger joint, 52 face morph, 28 motion frame, 968 track, activeSignFramesPreserved=true, relaxedRest=true. Bu lingvistik tasdiq emas.
- Brauzerda mavjud 39710d... ishning e9f281... natijasi ochildi. DOM: videoPlayers=1, datasetPanel=false, clipCount=false, download oldingi to‘g‘ri token bilan. Audio yuklash tanlovi bosilib ko‘rildi. Yangi upload/ASR/model inference yoki MP4 qayta eksporti bu UI bosqichida bajarilmadi.
- Brauzer konsolida ilovaga tegishli yangi kritik xato ko‘rinmadi; alohida language detection xabari brauzer qatlamidan. Three.js katta chunk ogohlantirishi qoladi. Avatar hali tajribaviy va ASL mutaxassisi tasdig‘i talab etiladi.

## 2026-11-01 — Dataset yuklamalari holati

- Studiyaga yopiladigan «Dataset fayllari holati» paneli qo‘shildi. Train/validation/test CSV va frontal ZIP nom mosligi hamda tugallanmagan .crdownload/.part yuklamalar alohida ko‘rsatiladi. Yangi sahifa qo‘shilmadi.
- GET /api/how2sign/dataset/status — read-only. ZIPdan hech narsa ajratmaydi, faqat markaziy katalogni va CSV nomlarini solishtiradi; natija full CRC/decode yoki lingvistik tekshiruv deb belgilanmaydi. Fayl yo‘llari APIga chiqarilmaydi. Test split avtomatik o‘qitish/qidiruvga qo‘shilmaydi.
- Haqiqiy tekshiruv: train 31047/31165 (118 yo‘q), validation 1739/1741 (2 yo‘q), test CSV 2357; tugallangan frontal test ZIP tekshirilgan joylarda hali yo‘q. Yuklanayotgan fayllar ko‘chirilmagan yoki o‘zgartirilmagan.
- 55 pytest va frontend TypeScript/Vite build o‘tdi. Backend va frontend faol ishlar yo‘qligi tekshirilgach qayta ishga tushirildi; yangi endpoint HTTP 200. Dalil storage/runs/dataset-readiness-20261101-001.json.
- Brauzerga ulanish browser.user unavailable xatosi sabab bajarilmadi; yangi panel vizual/klik sinovi hali tasdiqlanmagan. Mavjud katta Three.js chunk ogohlantirishi qoladi.

## 2026-10-31 — Brauzer orqali yangi studiya va 3D eksport tasdiqlandi

- Yangi studiya brauzerda ochildi: 31 047 train holati, inson/ML tanlovi, train sinov ishi va natija download havolasi ko‘rildi.
- 3D sinovda React maximum update depth ogohlantirishi aniqlandi. Woman capture callbacki har bir time yangilanishida qayta ro‘yxatdan o‘tardi; joriy vaqt refga ko‘chirilib, capture callback barqarorlashtirildi. Qayta ijro 2.24 s oxirigacha bordi va yangi shunday ogohlantirish qaytmadi.
- Brauzerdagi MP4 tugmasi bilan 54 PNG/24 fps haqiqiy eksport bajarildi. Token LOCAL_ID; 84220 bayt, H.264/AAC, 2.239093 s. HTTP download lokal fayl baytlari bilan aynan teng. examples/studio-3d-export-001.mp4 va JSON hisobot saqlandi. Asosiy ish holati va download tokeni brauzerda yangilandi.
- Eski asl media ijrosi birinchi yuklanishda xato berdi; qayta yuklab ijro tekshiruvi o‘tdi. Bir navigatsiyada bootstrap modulining vaqtinchalik syntax xatosi ko‘rindi; lokal va HTTP modulda NUL yo‘q, sahifani reload qilish bilan tiklandi. Tuzatilgan frontend build o‘tdi; yangi yakuniy ijro/eksport davomida bu xatolar takrorlanmadi. React DevTools til aniqlash xabari ilova funksiyasidan tashqarida qoladi.
- 50 backend testi avvalgi yakuniy run’da o‘tgan; keyingi o‘zgarish frontend capture callbackiga tegishli. Model yangi train datasetida qayta o‘qitilgani yoki ASL aniqligi tasdiqlangani da’vo qilinmaydi.

## 2026-10-31 — Train qidiruvi va yagona studiya oqimi

- 31 047 frontal train yozuvi ibora qidiruviga ulandi, 118 CSV yozuvining videosi arxivda yo‘q. Tanlangan klipgina keshga ochiladi va davomiyligi FFprobe bilan tekshiriladi. Train/validation kelib chiqishi alohida ko‘rsatiladi; yangi model o‘qitilmadi.
- Studiya ichida inson videosi va tajribaviy 3D ML tanlovi bor. ASR tayyor bo‘lgach ML tayyorlash avtomatik boshlanadi; matn tahriri revisioni almashganda avatar yangilanadi. MP4 tugagach asosiy ish holati yangilanadi. Yangi sahifa qo‘shilmadi.
- Bir vaqtda ikki render sessiyasi ochilishi 409 bilan cheklangan. Server qayta ishga tushganda qolib ketgan frames ishlari failed bo‘ladi, mavjud fayllar saqlanadi.
- Yangi TTS inglizcha video HTTP upload → haqiqiy tiny ASR → train klipi → native MP4 sinovidan o‘tdi. Job LOCAL_ID; H.264/AAC 720p, 4.048980 s, 197558 bayt, audio korrelyatsiyasi 0.9999655704. Kadr vizual tekshirildi. Batafsil docs/TRAIN_RETRIEVAL.md.
- 50 pytest va frontend build o‘tdi. Frontend 5174/backend 8001 HTTP 200; MaDiS CPU readiness true. Yangi frontend klik sinovi bajarilmadi; Three.js chunk hajmi ogohlantirishi qoladi. Lingvistik aniqlik tasdiqlanmagan.
- Startup skriptlari qaysi server mavjudligini mustaqil tekshiradi; boshqa loyihaning port egalarini to‘xtatmaydi. Git ignore katta dataset, storage, muhit va generated media fayllarini chiqarib tashlaydi. Git repo yaratilmagan/push bajarilmagan.

## 2026-10-31 — CSV splitlari va haqiqiy vaqtli 2D featurelar

- 6 original/realigned CSV dataset papkasiga nusxalandi; bir xil mavjud CSVlar almashtirilmadi. 31165 train, 1741 val, 2357 test. Manba video nomlari/ibora IDlari splitlar orasida takrorlanmaydi. Train/val/test kataloglari birlashtirilmadi.
- Realigned train intervalining 25566 tasi original kesilgan klipdan tashqariga chiqadi; shu sabab mavjud videolar jim qayta belgilanmadi. metadata-audit-002.json va docs/TRAIN_KEYPOINTS.md tafsilotlarni saqlaydi.
- 5 frontal klip /1196 kadr uchun haqiqiy dekodlangan PTS koordinatalarga biriktirildi: train-timed-features-001. 24/60 FPS hisobga olindi, NPZ vaqtlarining o‘sishi va massivlarga teng uzunligi tekshirildi.
- 44 pytest o‘tdi. Modelning yangi o‘qitilishi yoki so‘z–ishora alignmenti tasdiqlanmadi. Test CSV topildi, test video ZIP D diskda topilmadi. Oldingi 1739 validation klipi va sayt ma’lumotlari saqlangan.

## 2026-10-31 — 31 GB frontal train tekshiruvi

- train_rgb_front_clips.zip dataset papkasiga ko‘chirildi: 33 033 658 988 bayt. 31 047 MP4 / 31 047 noyob nom; CSV bilan 31 047 mos. CSVdagi 118 nom arxivda yo‘q, ro‘yxat train-front-inspection.json da.
- 5 frontal namuna ZIP CRC, FFprobe va barcha 1196 kadr dekodlashdan o‘tdi. Koordinatalar bilan kadr soni 5/5 mos; 24 va 60 FPS manbalar bor. Birinchi namunaning 12-kadrida tana/qo‘l nuqtalari raw video ustida vizual solishtirildi.
- Dalil datasets/how2sign/train-front-inspection-001/frame-012-overlay.png, tafsilot docs/TRAIN_KEYPOINTS.md. To‘liq ZIP CRC/all-video decode tekshiruvi yoki ASL lingvistik tasdiq bajarilmadi. Train ma’lumotlari validation katalogiga aralashtirilmadi, model qayta o‘qitilmadi.

## 2026-10-31 — MP4 versiyalarining izchilligi

- Preview va MP4 download endi v=token bilan aniq bir tugallangan eksportga bog‘langan. Oldin v cache-buster bo‘lib, server uni e’tiborsiz qoldirardi; bu eski oynada yangi fayl qaytishiga olib kelishi mumkin edi.
- Yangi eksport oldidan oldingi tugallangan token/settings tarixga qo‘shiladi. Jarayon davomida yoki cancel bo‘lgach ham aniq oldingi havola ishlaydi. Hali tugallanmagan render_token outputiga ruxsat berilmaydi. Yo‘q fayl uchun aniq 404; javobda no-store va X-Export-Version bor.
- 40 pytest va frontend build o‘tdi. Mavjud haqiqiy Rocketbox eksporti uchun result/download javoblari va lokal MP4 baytlari tengligi HTTP orqali tekshirildi. Noto‘g‘ri token 404. Brauzer klik sinovi bu bosqichda bajarilmadi.
- Tayyor frontal train ZIP tekshirilgan joylarda topilmadi; yuklamalar ko‘chirilmagan/o‘zgartirilmagan. Modelni yangi o‘qitish yoki ASL lingvistik tasdiq bajarilmadi.

## 2026-10-31 — Noutbukda haqiqiy kichik ML tajribasi

- CPU PCA modeli 3 train namunasida o‘rgandi, boshqa video validation/test sifatida ajratildi. 582/24/590 kadr. 64 rank validation qo‘l xatosi bo‘yicha tanlandi. Bu matn→ASL yoki 3D model emas.
- Fit 0.0283 s; peak working set 40.71 MiB; model 120214 bayt. Test qo‘l RMSE 0.03008 baseline ga qarshi 0.03565: 18.49% yomonroq. Model mahsulotga ulanmagan.
- docs/CPU_ML_EXPERIMENT.md va storage/experiments/pose-cpu-001/report.json haqiqiy natija/chegaralarni saqlaydi. NPZdan qayta yuklangan model chiqishi saqlangan chiqishga mosligi tekshirildi. 39 pytest o‘tdi.
- Katta model o‘qitilishi boshlanmadi. Datasetlarning yangi yuklamalariga va mavjud avatar/MP4 yo‘liga tegilmadi.

## 2026-10-31 — Ikkinchi train ZIP tekshirildi

- train_rgb_side_clips.zip D diskdan datasets/how2sign ga ko‘chirildi. 23 273 015 704 bayt, 31 165 yon ko‘rinish MP4, CSV bilan nom bo‘yicha 31 165/31 165 mos.
- 5 kichik namuna ajratilib ZIP CRC, FFprobe va bitta kadr ko‘rigi bajarildi. 24 FPS va 60 FPS videolar bor. Ikki namunada frontal keypoint va yon video kadr soni farq qiladi; frontal FPS avtomatik taxmin qilinmadi.
- Batafsil docs/TRAIN_KEYPOINTS.md, datasets/how2sign/train-side-inspection.json. To‘liq ZIP ochilmadi/to‘liq CRC tekshirilmadi, model o‘qitilmadi. Ishlayotgan platforma yo‘li o‘zgartirilmadi.

## 2026-10-31 — Matn va SRT yuklab olish

- Studiya va avatar ijrosi ichiga TXT/SRT download havolalari qo‘shildi. Yangi sahifa yo‘q. GET /api/jobs/{id}/transcript/download?format=txt yoki srt joriy matnni beradi.
- SRT original media soati bo‘yicha; sekinlashtirilgan MP4 soati sifatida belgilangan emas. Vaqtlar millisekundda, oxiri original davomiylikdan oshmaydi. Bo‘sh/nol davomiylikli cue chiqarilmaydi. UTF-8 BOM va attachment filename, no-store, revision header bor.
- 38 pytest va frontend build o‘tdi. Mavjud QA ishida haqiqiy HTTP 200 TXT va SRT yuklandi: examples/qa-transcript.txt va examples/qa-transcript.srt; matn va 0–1.600 s vaqt tekshirildi. Brauzer link klik sinovi bajarilmadi. Dataset yuklamalariga tegilmadi.

## 2026-10-31 — Yangi fayl bilan ASR/tahrir/native MP4 oqimi

- Yangi QA ish LOCAL_ID HTTP upload orqali mavjud qisqa inglizcha test mediasidan yaratildi. Whisper tiny haqiqiy qayta ishga tushdi: at least in a physical way. Bir segment va so‘z vaqt belgilari qaytdi; manba ibora mosligi 100%. Bu faqat ushbu sinov uchun qamrov, ASL aniqligi bahosi emas.
- Transcript API da expected_revision bilan eski oynaning keyingi tahrirni bosishidan himoya qo‘shildi; save paytida revision/segments/status qayta tekshiriladi. Frontend tahrir formasida revision yuboriladi. Ikkita tahrirni ketma-ket sinash, eskisini rad etish va original matnni qaytarish HTTP orqali o‘tdi.
- Native How2Sign inson eksporti yangi ishda bajarildi: full kadr, original yashil fon, 720p, subtitr. examples/qa-human-workflow.mp4: 94960 bayt, H.264/AAC, 2.239093 s, HTTP download 200. Audio korrelyatsiyasi 0.9999683951. docs/qa-human-workflow-frame.png kadr vizual ko‘rildi. Hisobot examples/qa-human-workflow-report.json.
- 37 pytest va frontend build o‘tdi. Three.js lazy chunk hajmi ogohlantirishi qoladi. Brauzer boshqaruvi shu davom ettirishda disabled javob berdi; tahrir UI klik sinovi bajarilmadi. Saytning yangi yuklanayotgan train arxiviga tegilmadi. Lingvistik tasdiq qo‘shilmadi.

## 2026-10-31 — Maskalangan 2D ML formati

- 5 ibora / 1196 kadr 120 nuqtali, gavda markazi va yelka masshtabiga mos 2D formatga o‘tkazildi. Asl detector ballari, valid maskalar va ketma-ket kadrlar uchun delta saqlandi. Yo‘q nuqta yoki frame gap ustidan interpolatsiya bajarilmaydi.
- datasets/how2sign/train-features-001; docs/TRAIN_KEYPOINTS.md da format va qayta ishga tushirish bayoni bor. 36 backend testi va barcha haqiqiy output NPZ fayllarining shakli/maska tekshiruvi o‘tdi.
- FPS va alignment hali tasdiqlanmagan. Model o‘qitilmadi, yangi yuklanayotgan arxivga tegilmadi, 2D format 3D avatarga avtomatik aylantirilgani da’vo qilinmaydi.

## 2026-10-31 — Train 2D namunalari tayyorlandi

- 21.1 GiB train_2D_keypoints.tar.gz va 31 165 qatorli CSV lokal dataset papkasida. 5 ibora / 1196 kadr cheklangan oqim o‘qish bilan NPZ formatida ajratildi; to‘liq arxiv ochilmadi.
- Kadr tartibi, matnga mosligi va detector score sifati tekshirildi. 2D skelet chizmasi ko‘rildi. Batafsil: docs/TRAIN_KEYPOINTS.md; yakuniy namuna datasets/how2sign/train-sample-002.
- 33 backend testi o‘tdi. Model o‘qitilmadi, 2D koordinatalar 3D avatarga ulanmagan. FPS va 3D moslash alohida tekshirishni talab qiladi. Saytning mavjud MaDiS/MP4 oqimi o‘zgartirilmadi.

## 2026-10-31 — Yangilangan avatar MP4 vizual tekshirildi

- Brauzer boshqaruvi qayta ishladi. LOCAL_ID saqlangan qisqa inglizcha namunasidagi mavjud MaDiS harakati qayta ishlatildi; ushbu bosqichda upload, ASR yoki model inference qayta bajarilmadi.
- NaturalAvatarTimeline interfeysidan haqiqiy 54 PNG kadr/24 fps olindi. relaxed-idle-v3 bilan eksport tugadi; token LOCAL_ID. FFprobe: H.264/AAC, 1280×720, 24 fps, 2.239093 s, 84220 bayt. HTTP download 200.
- Brauzerda video oxirigacha ijro etildi. Yangilangan kutish holati va 0.65 s dagi faol harakat kadri vizual ko‘rildi. Qo‘llar kutishda keng A-pose ga qaytmaydi; faol kadrda ikkala qo‘l ko‘rinadi. Barmoqlar va ASL semantikasi ekspert tomonidan baholanmagan.
- Original/eksport dekodlangan audio korrelyatsiyasi 0.9999683951. Audio qayta AAC kodlangan; bitma-bit bir xil emas.
- Yangi fayl examples/rocketbox-final-34a74c7b.mp4; hisobot examples/final-avatar-report.json. Dalillar docs/final-avatar-browser-proof.png, docs/final-avatar-rest.png, docs/final-avatar-signing.png. Oldingi MP4 fayllari saqlangan.
- Chegara: bu faqat 2.24 s lik saqlangan namuna. Uzun mustaqil videolar, yangi transkript tahrir UI si, ko‘p bo‘lakli eksport va ASL tushunarliligi bo‘yicha keyingi sinovlar qoladi. Quyidagi brauzer bloklanganligi haqidagi yozuvlar oldingi bosqichlarni ifodalaydi.

## 2026-10-31 — Inglizcha asosiy oqim va nutqni tuzatish

- Studiya ichida nutq matnini tahrirlash qo‘shildi. PUT /api/jobs/{id}/transcript original segment soni va vaqtlarini saqlaydi. O‘zgargan matnning eskirgan word timestampslari olib tashlanadi, qamrov qayta hisoblanadi va avvalgi ML request bekor qilinadi. Matn o‘zgargani sabab mavjud content-based ML kaliti ham o‘zgaradi.
- Oldingi MP4 fayllari va original media o‘chirilmaydi. Eski eksport tokeni previous_results ga saqlanadi; yangi matn uchun status ready bo‘lib, yangi harakat/eksport talab qilinadi. O‘zgarmagan matnni qayta saqlash natijani bekor qilmaydi.
- Eksport kadrlarini olish paytida transkripsiyani qayta boshlash bloklandi. Tahrir faol ishlov paytida ham bloklanadi. UI da inglizcha → ASL yo‘nalishi qoldirildi; eski o‘zbekcha backend ma’lumotlari o‘chirilmagan.
- 31 pytest va frontend build o‘tdi. Yangi testlar matn/qamrov, ML kaliti, vaqtlarni saqlash, eski word timestamps, media va oldingi natija saqlanishi, bo‘sh matn hamda faol eksportni tekshiradi.
- Bu bosqichda brauzerdagi tahrir UI klik sinovi va yangi avatar MP4ning vizual tekshiruvi bajarilmadi. ASL lingvistik tasdiq va yangi datasetda modelni o‘qitish bajarilmadi.

## 2026-10-31 — Mavjud ASL yozuvlarini tanlashni tuzatish

- Bir xil matnli kliplar bir-birini bosmaydi. Nutq oralig‘iga tezligi mos keladigan yozuv tanlanadi; tasdiqlangan yozuvga ustunlik beriladi. Uzun mos ibora juda sekin bo‘lsa, uning ichidagi qisqaroq to‘liq manba iborasi ham tekshiriladi. Rad etilgan va texnik yaroqsiz klip ishlatilmaydi. Taxminiy/fuzzy gap video tarjimasi deb belgilanmaydi.
- Katalog diskdan har so‘rovda qayta JSON parse qilinmaydi; faylning yo‘li, mtime va hajmi o‘zgarsa kesh yangilanadi. Ekspert qarorlari har safar yangidan olinadi; kesh tasdiqni muzlatmaydi. Normalizatsiyalangan iboralar ham keshlandi.
- 29 pytest o‘tdi, jumladan dublikat ibora, mos kelmagan uzun klip, rad etish va katalog keshini yangilash. Lokal katalog 1739 klip; mavjud namuna iborasi 100% manba mosligini saqladi. Bu lingvistik aniqlik bahosi emas.
- MaDiS pretrained CPU modeli ishlatiladi. Foydalanuvchi yuklagan validation videolarida qayta o‘qitish bajarilmadi. Videolar tashqi xizmatga yuborilmadi.

## 2026-10-31 — Eksport ravonligi va tayyorlik

- Rocketbox PNG eksporti 12 fps dan 24 fps ga o‘tdi. Kadr soni, sessiya javobi va FFmpeg kirish tezligi bitta saqlangan `render_fps` qiymatidan foydalanadi. Avvalgi sessiyalar va legacy avatar uchun 12 fps fallback saqlanadi.
- Model/kadr olish funksiyasi tayyor bo‘lmaguncha MP4 tugmasi faollashmaydi. Har bir kadr olingach ko‘rik pozasi tiklanadi; eksport oxirgi pozani ekranda qoldirmaydi.
- `pytest backend/tests -q`: 26 passed. Rocketbox 512×384 PNG, 24 fps, 2× timing bilan haqiqiy H.264/AAC MP4 yaratish, davomiylik va 440 Hz audio pitch sinovi o‘tdi. Bu shaffof texnik PNG fixture; haqiqiy avatar renderi yoki ASL tekshiruvi emas.
- Frontend build va uchta Node sinovi (Rocketbox, playback, timeline) o‘tdi. 3D chunk hajmi ogohlantirishi qoladi.
- Brauzer boshqaruvi disabled javobi sabab yangi avatar MP4ning vizual tekshiruvi bajarilmadi. Oldingi foydalanuvchi MP4 fayllari saqlandi.

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

## 2026-10-31 — To‘rtta GitHub manbasi bilan amaliy ulanish

- `docs/RESEARCH_SOURCES.md`: har bir repo, commit, litsenziya, foydalanilgan qism va yetishmayotgan aktivlar.
- Yangi avatar oynasida GitHub/tadqiqot bo‘limi, JSON import, qamrov auditi va GBNF download mavjud.
- MIT grammatika generatori litsenziyasi bilan ishlatiladi. SignAvatars 182 va Dong 53×6 formatlari uchun mustaqil adapterlar mavjud. Sign-Kit boshqaruv g‘oyasi mustaqil yozildi; ISL ishoralari va litsenziyasi noma’lum model ko‘chirilmagan.
- 25 test, frontend build, haqiqiy katalog grammatikasi, brauzer auditi va sonli import/ijro sinovi o‘tdi. Tafsilot: docs/RESEARCH_TEST_RESULTS_2026-10-31.md.
- Dong/SignAvatars aktivlari bilan haqiqiy ML inference hali yo‘q. Asosiy MaDiS va inson-video yo‘llari saqlangan. Lingvistik tasdiq berilmagan.

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

# Haqiqiy tekshiruv natijalari — 2026-10-24

**Oxirgi natija:** 16 test o‘tdi, frontend build muvaffaqiyatli. Avtomatik yuklash → ASR → ML → brauzer kadrlaridan MP4 oqimi sinovdan o‘tdi; `examples/madis-auto-result.mp4` va hisoboti saqlandi. Ishchi ma’lumotlarga testlar tegmasligi alohida test bilan tekshiriladi. [Yakuniy hisobot](CURRENT_STATUS.md).

**Yakuniy texnik kengaytma:** 15 pytest testi va TypeScript/Vite build o‘tdi. Tabiiy timing, pitch saqlanishi, ekspert qarorlari tarixi, rad etilgan klipdan himoya, ishlar tarixi va hisobot tekshirildi. Ikkinchi haqiqiy ML harakati MP4 eksporti `examples/madis-unseen-result.mp4` da saqlandi. To‘liq ma’lumot [CURRENT_STATUS.md](CURRENT_STATUS.md) boshida.

**2026-10-28:** keyingi to‘liq corpus va ML tekshiruvi [CURRENT_STATUS.md](CURRENT_STATUS.md) da. Backend 11 test, frontend build, 1739 klip FFprobe tekshiruvi, haqiqiy MaDiS inference va uning browser PNG → MP4 eksporti o‘tdi. Quyidagi yozuvlar dastlabki 2026-10-24 holatiga tegishli.

## O‘tdi

- Mavjud Python 3.11.9 `.venv` qayta ishlatildi. `main.py`, `transcribe.py` va foydalanuvchi audio fayllari o‘zgartirilmadi.
- Backend 8001 va frontend 5174 portlarda ishga tushdi. Startup script HTTP health va frontend 200 javobini tekshirdi.
- `python -m pytest backend/tests -q`: **7 passed**. Unicode/o‘zbek apostroflari, tekshirilmagan/ASL ishoralarni chiqarib tashlash, to‘liq ibora mosligi, juda tez ishorani rad qilish, upload formati, noto‘g‘ri media, yo‘l IDlari, import validatsiyasi, kadr sessiyasi, bekor qilish, haqiqiy subtitrli MP4 testi.
- `npm.cmd run build`: TypeScript va Vite muvaffaqiyatli. JS bundle 1.18 MB atrofida; 500 kB chunk ogohlantirishi mavjud, build xatosi emas.
- `node scripts/check-avatar.mjs`: 340 barmoq nomli rig suyaklari, 1249 animatsiya treki; uch vaqt nuqtasida finite transformlar va pozalar o‘zgarishi tekshirildi. Bu **brauzer vizual tekshiruvi emas**.
- Multilingual Whisper tiny modeli lokal CPU INT8 da ochildi. Sukutli 2 soniyali fayllar ASR oqimidan o‘tdi. Bu o‘zbekcha nutq aniqligi testi emas.
- `python scripts/smoke_pipeline.py`: real HTTP audio/video upload → tiny ASR → structured unsupported natija → PNG upload → FFmpeg → download. Ikki real 720p MP4 fayl yaratildi, har biri 2.000 soniya, H.264 + AAC. `storage/integration-evidence/results.json` da dalillar.
- MP4 testida 440 Hz sintetik manba audio yaratildi, eksportdan dekodlangan audiodagi dominant chastota 440 Hz ga 3 Hz ichida mos keldi. O‘zbekcha texnik subtitrning tasvirga yozilgani piksel tekshiruvida tasdiqlandi.

## Topilgan va tuzatilgan xato

Avatar yuklashidagi `TypeError: this is not a constructor`: `AnimationClip.parse` promise callback sifatida kontekstsiz berilgan. `data => THREE.AnimationClip.parse(data)` bilan tuzatildi. Offline parser/animatsiya testi va build o‘tdi; brauzerda qayta tasdiqlanmadi.

## Hali tekshirilmagan / to‘siqlar

- Brauzer boshqaruv vositasi `Local browser use is disabled in Work settings` qaytardi. Foydalanuvchi yoqilganini bildirgach qayta urinish ham xuddi shu javobni berdi. Siyosatni aylanib o‘tish qilinmadi.
- Avatar vizual renderi, tugmadagi harakat, barcha PNG kadrlarning aynan brauzerdan chiqishi va yakuniy avatarli MP4 ko‘rinishi **hali tasdiqlanmadi**. Integratsiya smoke testidagi PNG lar shaffof texnik fixture; ular avatar o‘rniga taqdim etilmaydi.
- `audio` ichida hali faqat `Altare – bye (slowed).mp3` bor. Foydalanuvchi o‘zbekcha namuna qo‘shishini bildirdi. O‘zbekcha real audio ASR, WER/CER va vaqt mosligi tekshirilmagan.
- 0 ta tasdiqlangan `uz_sign` animatsiya. Bitta manbasi bor ASL Hello demo kutubxonada tekshirilmagan sifatida saqlanadi va o‘zbek tarjimaga kirmaydi.
- 1080p, 20 daqiqali yuklama, mobil ekran, barcha brauzerlar, mutaxassis bilan lingvistik tekshiruv hali o‘tkazilmagan.
- Smooth animation blending va boshqariladigan grammatika qoidalari to‘liq amalga oshirilmagan. Hozir deterministik ibora klipi sampling; tezlik 0.5–2× diapazondan tashqarida bo‘lsa subtitr fallback.

## Takrorlash

```powershell
cd D:\SignBridge-UZ
.\.venv\Scripts\python.exe -m pytest backend\tests -q
node scripts\check-avatar.mjs
.\.venv\Scripts\python.exe scripts\smoke_pipeline.py
cd frontend
npm.cmd run build
```

Smoke HTTP testi ishlayotgan lokal serverni talab qiladi. U faqat o‘zi yaratgan sintetik media va alohida ish yozuvlari bilan ishlaydi. Test MP4 lar `storage/integration-evidence` ichida. Original foydalanuvchi fayllari o‘chirilmagan.

## 2026-11-09 — Ulanish va tayyor natijani ochish

Ushbu bo‘lim avvalgi sinovlar tarixiga qo‘shimcha. Joriy mahsulot inglizcha nutq va tajribaviy ASL bilan ishlaydi.

- `node scripts/check-read-json.mjs`: PASS. Network/503/timeoutdan tiklanish, faqat GET so‘rovlarini cheklangan qayta urinish, 401/403/404/409/422 xatolarini takrorlamaslik, HTML va buzilgan JSON javoblarini aniqlash, kutish va so‘rovni bekor qilish.
- `node scripts/check-job-polling.mjs`: PASS. Parallel ustma-ust so‘rovlar yo‘q, kechikkan eski javob rad etiladi, bekor qilish va aloqadan tiklanish.
- `node scripts/check-flow-guards.mjs`: PASS. Eksport tokeni, request deadline, motion limits.
- `npm.cmd run build --prefix frontend`: PASS. Vite katta avatar JS chunk haqida ogohlantiradi; build xatosi yo‘q.
- Lokal frontend HTTP 200; backend health `ok=true`, `ffmpeg=true`, `device=cpu`, `verified_signs=0`.
- Saqlangan `LOCAL_ID` ish `done`. Uning real MP4 fayli Range so‘roviga HTTP 206, `video/mp4`, dastlabki 1024 bayt bilan javob berdi.
- MP4 finish so‘rovi yuborilgandan keyin holatni olishdagi aloqa xatosi server eksportini avtomatik bekor qilmaydi. Foydalanuvchining explicit cancel amali saqlangan.
- Natija playeriga qayta ochish va media xatosi xabari qo‘shildi. Qayta ochish yangi generatsiya boshlamaydi.
- Ushbu iteratsiyada yangi MP4 generatsiyasi va brauzer playerining vizual sinovi bajarilmadi. Mahalliy brauzer boshqaruvi avvalgi tekshiruvda o‘chirilgan. ASL lingvistik aniqligi ushbu texnik testlar bilan tasdiqlanmaydi.

## 2026-11-09 — Harakatlarni parallel yuklash va yuklangan ishni tiklash

- `node scripts/check-motion-loading.mjs`: PASS. Ko‘pi bilan 3 ta faol so‘rov, tartib va ma’lumot saqlanishi, xatoda qo‘shni yuklashlarni bekor qilish, foydalanuvchi bekor qilishi, yaroqsiz chegaralar.
- `node scripts/check-transcription-request.mjs`: PASS. POST javobi yo‘qolganda holat/revision orqali qabul qilingan ishni topish; POST takrorlanmaydi; boshqa ish yoki eski revision muvaffaqiyat deb qabul qilinmaydi.
- `node scripts/check-read-json.mjs`: PASS. Tarmoq tiklanishi va so‘rovlarni bekor qilish.
- `npm.cmd run build --prefix frontend`: PASS; katta avatar bundle ogohlantirishi saqlanadi.
- Real lokal `LOCAL_ID` motion plan: 7 asset, 280 kadr. Bir martalik o‘lchov: ketma-ket 105 ms, concurrency=3 bilan 58 ms. Ikkala natijaning JSON SHA256 qiymati bir xil: cacf3ff2983482a54444f5f3ff081bc4a367ffa2c53107294bf36052bf895b08.
- Bu o‘lchov faqat tayyor motion JSON yuklashni qamraydi; ASR, ML generatsiyasi yoki MP4 renderi tezligi haqida xulosa emas. Kesh va lokal tarmoq natijaga ta’sir qilishi mumkin.
- UI yuklangan harakatlar sonini ko‘rsatadi. `uploaded` holatida transkripsiyani faylni qayta yuklamasdan boshlash tugmasi mavjud.
- Boshlang‘ich saqlangan ish so‘rovi yangi upload boshlanganda bekor qilinadi; kechikkan eski javob yangi ishni almashtirmaydi.
- Ushbu iteratsiyada brauzer vizual sinovi va yangi MP4 eksporti bajarilmadi. Avatar modeli, kamera va harakat qiymatlari o‘zgartirilmadi.

## 2026-11-09 — MP4 yo‘laklari va oxirgi kadrlar to‘liqligi

- `python -m pytest backend/tests -q`: 137 passed in 32.56s (eksport validator va FFmpeg o‘zgarishlari bilan).
- Keyingi kesh tekshiruvi o‘zgarishidan so‘ng `python -m pytest backend/tests/test_export_speed.py backend/tests/test_export_validation.py -q`: 19 passed in 4.76s.
- FFmpeg bilan real fixture sinovlari: 1 soniyalik ko‘k video + 3 soniyalik sinus audio. Native va PNG eksport yo‘llarida video oxirgi kadrni ushlab 3 soniyagacha davom etadi. Tayyor MP4 to‘liq dekodlandi, HTTP Range 206 tekshirildi. Rangli fixturelar avatar/ASL sifati dalili emas.
- Yangi `export_validation.py`: video/audio yo‘laklarini alohida tekshiradi, H.264/AAC, tanlangan o‘lcham, yuv420p, 24 fps, kadrlar soni va davomiyliklarni tasdiqlaydi. Asl audio metadata davomiyligi bo‘lmasa faqat yuqori chegara tekshiriladi va bu `audio_duration_reference` orqali belgilanadi.
- Saqlangan qisqa natija `LOCAL_ID`: yangi tekshiruvdan o‘tdi; 1920x1080, 24 fps, 53 kadr, video 2.208333 s, audio 2.239093 s.
- Saqlangan uzun natija `LOCAL_ID`: yangi tekshiruvdan o‘tmadi. Asl video yo‘lagi 57.6 s, audio 58.1878 s; eski natijadagi video 57.666667 s (1384 kadr), audio 58.073107 s. Avvalgi container-only .5 s tekshiruvi buni ushlamagan. Yangi source-frame padding va stream validation shu xatoni bartaraf etishga qaratilgan.
- Eski uzun MP4 qayta generatsiya qilinmadi va o‘zgartirilmadi. Yangilangan kod bilan qayta eksport talab etiladi. Brauzer/avatar vizual tekshiruvi ushbu iteratsiyada bajarilmagan.
- Tezkor export keshiga faqat `probe.validation=streams-v1` yozuvlari olinadi. Yangi qoida asosida tekshirilmagan eski natija avtomatik qayta ishlatilmaydi.
- Faol transkripsiya/eksport yo‘qligi va backend process ownership tekshirilib, faqat loyiha backend jarayoni qayta ishga tushirildi. start.ps1 health tekshiruvlari muvaffaqiyatli; frontend saqlandi.

## 2026-11-11 — Uzun videoning haqiqiy 3D brauzer eksporti

- Backend va frontend to‘xtagan edi; `scripts/start.ps1` orqali ishga tushirilib health tekshirildi.
- IAB orqali `LOCAL_ID` ishida “Qayta tayyorlash” va “MP4 tayyorlash” bajarildi. Haqiqiy GLB/R3F kadrlaridan yangi eksport yaratildi; texnik PNG fixture ishlatilmadi.
- Natija tokeni: `LOCAL_ID`. Fayl: `storage/LOCAL_ID/LOCAL_ID/result.mp4`.
- FFprobe: 1920x1080 H.264, AAC, 24 fps, 1397 video kadr, video 58.208333 s, audio 58.073107 s. `validation=streams-v1`.
- `ffmpeg -v error -xerror -i result.mp4 -f null -`: exit 0, stderr bo‘sh. Fayl to‘liq dekodlandi.
- Brauzer native video player: 58.208333 s, `MediaError=null`, ijro ishladi. 44-soniya atrofida qo‘l harakati ko‘rindi, screenshot `docs/avatar-export-2026-11-11.jpg` saqlandi.
- Brauzer logida “Could not establish connection. Receiving end does not exist” va “language detection is not supported for this tab” yozuvlari bor. Ularning kelib chiqishi aniqlanmagan; konsol butunlay toza deb da’vo qilinmaydi. Playerda media xatosi kuzatilmadi.
- Bu eski fayl inglizcha ASR/ASL aniqligi benchmarki emas: faqat uzoq video, avatar renderi va eksport davomiyligini tekshirish uchun ishlatildi. ASL lingvistik tasdig‘i yo‘q.
- Muvaffaqiyatli renderdan keyin eski “Bekor qilindi” error saqlanib qolishi topildi. Yangi render boshlanishi/yakunida error tozalanadi; UI xato matnini faqat failed/cancelled holatida ko‘rsatadi.
- Terminal ishga tokensiz kechikkan cancel so‘rovi endi 409 qaytaradi va tayyor natijani cancelled holatiga o‘zgartirmaydi. Oldingi natija nusxalari saqlanadi.
- `pytest backend/tests/test_export_recovery.py backend/tests/test_export_versions.py backend/tests/test_transcription_recovery.py -q`: 14 passed in 4.05s.
- `npm.cmd run build --prefix frontend`: PASS; katta avatar chunk ogohlantirishi mavjud.
- Qo‘shimcha tuzatishlar backend qayta ishga tushirilgach faollashtirildi. Lokal manzil http://127.0.0.1:5174/ . Ommaviy hosting/deploy bu iteratsiyada bajarilmadi.

## 2026-11-11 — Qo‘l harakati va takrorlanish auditi

- 7 ta saqlangan motion bo‘lagi turli qiymatlarga ega. Byte farqi ASL mazmuni to‘g‘ri ekanini isbotlamaydi.
- Ayrim 2 s harakatlar 5.6 s nutq oralig‘iga cho‘zilgan (0.357×). `bounded-cadence-v4` ijroni kamida 0.85× bilan cheklaydi, qolgan vaqt silliq neytral tanaffus; harakat qayta aylantirilmaydi. Bu evristik taqdimot sozlamasi, ASL tezligi standarti emas.
- Source motion qiymatlari, nutq boshlanishi, audio va subtitr vaqtlari o‘zgarmadi. Motion yakuni va tanaffusdagi fade yangi faol oynaga moslandi. Oldingi MP4 keshidan avtomatik foydalanish revision bilan cheklangan.
- Timeline regression: PASS (final frames, no loop, gap, seek/boundaries). Rocketbox geometry regression: PASS. 7 bo‘lak/280 kadrda bosh va qo‘l bo‘g‘imlari kamera chegarasida. Bu mesh collision yoki lingvistik test emas.
- Backend export-speed: 2 passed. Frontend build: PASS; katta JS chunk ogohlantirishi saqlanadi.
- `At least in a physical way.` uchun How2Sign val front `-f1_kdl050s_25-1-rgb_front.mp4` arxivdan alohida nusxaga olindi. Original timestamp metadata manual review talab qiladi.
- `docs/motion-review-2026-11-11/reference-before.jpg` va `avatar-before.jpg`: oldingi MP4 va haqiqiy tarjimon kadrlarida qo‘l holatlari farq qiladi. Bu farqning o‘zi tarjima noto‘g‘riligini isbotlamaydi (variantlar/alignment), ammo to‘g‘ri ASL deb tasdiqlashga asos yo‘q. Mutaxassis bahosi zarur.
- Yangi brauzer vizual testi va MP4 eksporti yakunlanmadi: CUA navigatsiya paytida “Local browser use is disabled” qaytardi. Yangi kodning vizual sifati tasdiqlanmadi; eski videolar o‘zgartirilmagan.
- Keyingi sifat darvozasi: bir xil matn uchun haqiqiy tarjimon/model videolarini ASL mutaxassisi bilan baholash (qo‘l shakli, kaft yo‘nalishi, joylashuv, harakat, yuz ifodasi, ma’no). Hozir learned hand-mean/palm roll va yuz semantikasi tekshirilmagan.

## 2026-11-13 — Inglizcha Ethernet videosi: tezlik va uzilgan eksport

- Ikki daqiqalik yozuvning 29 segmentida How2Sign ibora moslashtirish natijasi barcha maydonlari bilan aynan bir xil qoldi. Yangi Python jarayonidagi birinchi chaqiruv: 7.04 → 4.56 s; uch takrorning medianasi: 0.622 → 0.166 s. Bu nutq, ML yoki to‘liq eksport tezligi emas.
- Brauzerda 2881 kadrli eksport uzildi. Backend qayta ochilgach `/render/resume` 1632 PNGni tekshirib, navbatdagi indeks 1632 ni qaytardi. Eskirgan sessiyaning yozish va bekor qilish so‘rovlari rad etilishi testdan o‘tdi. Qolgan 1249 kadr va ikki daqiqalik yakuniy MP4 bu sinovda chiqarilmagan.
- Dastlabki 240 haqiqiy WebGL kadri va shu vaqt oralig‘idagi manba media bilan alohida `docs/ethernet-preview-20261113/first-10-seconds.mp4` tayyorlandi: 1920×1080, H.264/AAC, 24 fps, video va audio 10.00 s. FFprobe va to‘liq FFmpeg dekodlash o‘tdi. `frame.jpg` videoning 2-soniyasidan. Bu ASL lingvistik tasdig‘i emas.
- Backend: 144 test o‘tdi. Frontend build o‘tdi (avatar JS hajmi uchun ogohlantirish mavjud).
