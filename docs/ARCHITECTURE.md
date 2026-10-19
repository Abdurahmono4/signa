# Signa arxitekturasi

Kirish — inglizcha nutqli audio/video; chiqish — vaqtli subtitr va MaDiS–How2Sign modeli yaratgan uzluksiz harakatni ko‘rsatuvchi avatar. Asosiy sahifa neyron modeldan foydalanadi; oldingi lug‘at/harflash API yo‘llari saqlangan. `complete_translation: false` lingvistik sifat tasdiqlanmaganini bildiradi. `/api/health` dagi `asl_ready` esa model fayllari va CPU muhiti o‘rnatilganini bildiradi, ASL sifat bahosi emas.

## Asosiy oqim

```text
Yagona React / TypeScript sahifasi
  → fayl tanlash / tashlash, mahalliy media preview
  → POST /api/jobs: format, hajm, davomiylik tekshiruvi; SQLite
  → “Imo-ishorada ijro etish”
  → POST /api/jobs/{id}/transcribe: balanced / small.en, speech
  → holat: queued → processing → ready / failed / cancelled
  → POST /api/jobs/{id}/neural; GET /api/jobs/{id}/neural bilan holat
  → alohida Python CPU jarayonida MaDiS: gap → 133 o‘lchamli harakat, 24 fps
  → GET /api/jobs/{id}/neural/plan va /neural/motions/{id}
  → Galtis skeletiga aylanishlarni ko‘chirish, animatsiyalarni oldindan yuklash
  → bitta virtual vaqt chizig‘i: media + subtitr + Three.js avatar
  → ixtiyoriy canvas kompozit yozuvi: media + burchakdagi avatar → WebM
```

`main.tsx` yuklash, tayyorlash va boshqaruvlarni birlashtiradi. Yangi operatsiya avvalgi so‘rovni bekor qiladi; operatsiya identifikatori kech kelgan natijaning boshqa faylni ishga tushirishini cheklaydi. Laboratoriya, kutubxona, qamrov va tahrir panellari asosiy sahifaga ulanmagan; ularning API imkoniyatlari saqlangan.

Fayl yuklangach media oynasi asosiy maydonni egallaydi, avatar uning burchagida turadi. Chiqish videoda ham original kadr ustiga shu turdagi avatar paneli chiziladi.

Oxirgi ish identifikatori `sessionStorage` da saqlanadi. Shu tab yangilanganda job va serverdagi media manzili tiklanadi; ijro avtomatik boshlanmaydi. Bu sessiya qulayligi, foydalanuvchi hisobi emas. Yo‘q ish uchun 404 qaytsa, eskirgan identifikator chiqariladi; boshqa aloqa xatolari foydalanuvchiga ko‘rsatiladi.

PyAV ovozni dekodlaydi; faster-whisper CPU INT8 bilan nutqni aniqlaydi. Media, baza va model kompyuterda saqlanadi. Brauzer avatarni GLB va animatsiya JSON aktivlaridan chizadi. Transkripsiya tashqi AI xizmatiga yuborilmaydi.

MP3 dagi albom muqovasi FFmpeg orqali video stream sifatida ko‘rinsa ham, `attached_pic` haqiqiy video hisoblanmaydi. Audio kengaytmalari audio pleyerda qoladi; eski ishlarning API javobidagi noto‘g‘ri tur ham fayl yoki bazani o‘zgartirmasdan tuzatiladi.

## Nutq va ma’lumotlar

Audio 16 kHz mono formatga o‘tkaziladi, taqdimot vaqtlaridagi uzilishlar saqlanadi. Butun vaqt chizig‘i 24 soniyalik asosiy bo‘laklarga bo‘linadi; ikki tomondan 3 soniyagacha kontekst qo‘shiladi. So‘z vaqtining o‘rtasi qaysi asosiy bo‘lakda bo‘lsa, natija o‘sha bo‘lakka tegishli. Ustma-ust farazlar birlashtiriladi; haqiqiy takrorlar saqlanadi.

VAD oldindan audio qismlarini kesmaydi; yakuniy audit matnsiz faol oraliqlarni izlaydi. Cheklangan qayta tahlil va audit API da qoladi. Sahifa `balanced` / `small.en` profilini tanlaydi; `accurate` / `medium.en` API da mavjud. Bitta model xotirada saqlanadi. Bir vaqtda bitta transkripsiya qabul qilinadi; bekor qilish bo‘laklar orasida tekshiriladi. Server qayta ishga tushganda tugallanmagan ishlar `failed` holatiga o‘tadi.

SQLite jobs, segmentlar, audit va revisions tarixini saqlaydi. API tahririda revision tekshiriladi, eski so‘z vaqtlari o‘chiriladi va audit eskirgan deb belgilanadi. Bunday matnning lug‘at vaqtlari `estimated`; bu qayta majburiy tekislash emas. SRT, VTT va TXT eksport API da mavjud.

## Neyron ASL qatlami

`neural.py` ASR segmentlarini 40 so‘zgacha bo‘lgan gap guruhlariga birlashtiradi. Bitta `madis_runner.py` jarayoni modelni bir marta yuklab, barcha gaplar uchun harakat yaratadi. Umumiy worker lock ASR va neyron hisoblashning bir vaqtda RAM uchun raqobat qilishini cheklaydi; MaDiS yuklanishidan oldin Whisper xotiradan chiqariladi. Asosiy API muhitiga Torch o‘rnatilmaydi.

Vaznlar rasmiy manba revision va SHA-256 bilan tekshiriladi. Runner normalizatsiyani rasmiy mean/std bilan qaytaradi: 30 tana, 45 chap qo‘l, 45 o‘ng qo‘l, 3 jag‘ va 10 yuz parametri. Natijada o‘zgaruvchan va chekli kadrlar bo‘lmasa, muvaffaqiyatli tarjima rejasi chiqarilmaydi. Harakat JSON/NPZ, indeks va jurnal mahalliy `backend/data/neural/<hash>/` ichida saqlanadi. Keshlash kaliti job, revision, matn, model revision va adapter reja versiyasiga bog‘liq.

`neuralMotion.ts` 40 bo‘g‘imning axis-angle aylanishlarini GLB haqiqiy inverse-bind skeletiga ko‘chiradi. Bu anatomik moslashtirish taxminiy: SMPL-X qo‘lning o‘rganilgan bazaviy holati va yuz koeffitsientlarini Galtisga ishonchli ko‘chirish hali yo‘q. Ko‘rinishni yaxshilash uchun taxminiy yuz/qo‘l ishoralari qo‘shilmaydi. Texnik sinov ASL ma’nosi tasdig‘i emas.

Har bir gapning to‘liq harakati ko‘pi bilan 1.25× ijro etiladi. Harakat manba vaqtiga sig‘masa, media to‘xtab turadi; barcha kadrlar saqlanadi. So‘zma-so‘z majburiy alignment yo‘q. Bekor qilish va server yopilishi alohida model jarayonini to‘xtatadi; tugallanmagan indeksdan tayyor reja chop etilmaydi. O‘rnatish: [NEURAL-MODEL.md](NEURAL-MODEL.md).

## Saqlangan lug‘at API va ijro rejasi

`signs.py` matnni tokenlarga normallashtiradi va har segment ichida eng uzun mavjud iborani avval tanlaydi. Harf aktivlari shu lug‘at mosligiga kiritilmaydi. Standart tezkor so‘z rejimida “My name is Alex. Hello” → “my name is” iborasi, “Alex” subtitri, “hello” ishorasi. Faqat ixtiyoriy harflash yoqilganda “Alex” uchun A–L–E–X ijro etiladi. Bu ASL grammatik tartibi yoki kontekstdagi ma’noni aniqlash qatlami emas.

| Endpoint | Vazifa |
|---|---|
| `/sign-plan` | Avvalgi audit rejasi: `matched`, `source_preview`, `missing`, `timing_review`, `unsupported_rig`; 0.5–2 vaqt nisbati tekshiruvi saqlangan. |
| `/playback-plan` | Standart tezkor so‘z rejimi: lug‘at klipi ko‘pi bilan 1.25×; noma’lum so‘z vaqtli subtitr, qo‘shimcha pauzasiz. Ixtiyoriy `fingerspelling=true` to‘liq tabiiy tezlikdagi harflashni yoqadi. |

Ikkalasi faqat `ready` matnni qabul qiladi. Sahifa `include_source=true` bilan manba kliplarini ham qo‘llaydi; bu ekspert tasdig‘i emas. `source → draft → approved / rejected` tekshiruvi va tekshiruvchi izohi API da saqlanadi. Kalibrlash yozuvi ASL sifatida tasdiqlanmaydi. Eski geometrik rig `unsupported_rig`.

`playback-plan` standartida `fingerspelling=false`, `presentation: words`, `fingerspelling_enabled: false`. Interfeysdagi **Harflab ko‘rsatish** dastlab o‘chiq; yoqish `fingerspelling=true`, `presentation: fingerspelling` so‘raydi. Tayyor matnda rejim almashganda ASR qayta bajarilmaydi.

Har element asl matn oralig‘i, ustma-ust bo‘lmagan `media_play_start/end`, `clip_start`, `clip_end`, `playback_rate` va `playback_start/end` qaytaradi. Klipning ijro davomiyligi `(clip_end - clip_start) / playback_rate`; slot media oralig‘i va shu davomiylikning kattasidir. Tezkor rejim lug‘at klipini ko‘pi bilan 1.25× ijro etadi, noma’lum so‘z esa faqat o‘z media oralig‘ini oladi. Shu sabab noma’lum so‘z media vaqtiga hold qo‘shmaydi. Mos klip slotdan uzun bo‘lsa, media ishora tugaguncha so‘z oxirida pauza qiladi. Boshlang‘ich, ichki va oxirgi bo‘shliqlar saqlanadi. `sync_status` avvalgi audit holatini saqlaydi.

Klipni qisqartirish faqat kanonik manifestdagi `playback_window` maydoni `verified: true` va `0 ≤ start < end ≤ source_duration` bo‘lganda qabul qilinadi. Foydalanuvchi importining window ko‘rsatmasiga ishonilmaydi. Amaldagi manifestga bunday trim metama’lumoti qo‘shilmagan: barcha yozilgan harakat saqlanadi. `playback_rate` chegarasi va oynaning to‘g‘riligi tekshiriladi.

Faqat `fingerspelling=true` bo‘lganda lug‘at klipi yo‘q bitta so‘z apostroflari chiqarilgach ASCII A–Z harflariga mos kelsa, manbadagi barmoq alifbosi bilan harflanadi. Barcha kerakli harflar mavjud bo‘lishi shart. Ushbu rejimda kliplar 1.0× va to‘liq davomiylikda ijro etiladi. Birinchi harf so‘zning media oralig‘ini iste’mol qiladi, qolganlari media vaqtini so‘z oxirida ushlab turadi. J va Z ning asl harakat yo‘li ham saqlanadi. Raqam/non-ASCII belgi yoki yetishmagan harf butun so‘zni subtitrga qaytaradi; qisman harflash yo‘q.

| `rendering` | Ma’nosi |
|---|---|
| `sign` | Lug‘atdagi so‘z/ibora klipi. |
| `fingerspelling` | Asl `word_text` uchun `letter`, 0 dan boshlangan `letter_index` va `letter_count` bilan bitta harf klipi. |
| `caption` | Harakat bilan berilmagan matn; subtitr saqlanadi. |
| `gap` | Matnsiz media oralig‘i. |

`signed_words` faqat lug‘at so‘zlarini, `spelled_words` harflangan butun so‘zlarni, `fingerspelling_letters` harf kliplarini va `caption_words` faqat subtitrda qolgan so‘zlarni sanaydi. `dictionary_missing_words` lug‘atda yo‘q so‘zlarni saqlaydi; `missing_words` harflashdan keyin ham faqat subtitrda qolganlarni beradi. Bu hisoblar tarjima aniqligi emas.

Harflash chegaralari: so‘zda ko‘pi bilan 30 harf, rejada 10 000 harf, harflash qo‘shgan pauzalarda jami 3600 soniya. Limitdan oshadigan butun so‘z subtitrda qoladi. `spelling_limits.limited_words` va `limit_reasons` tegishli so‘z hamda sababni qaytaradi. Bu chegaralar uzoq faylda cheksiz reja/ijro yaratilishini cheklaydi.

## Umumiy ijro soati

`playback.ts` — sof vaqt xaritasi; `useInterpreterPlayback.ts` — brauzer boshqaruvchisi. Slayder **umumiy ijro vaqtini** ko‘rsatadi; faqat zarur klip holdlari unga qo‘shiladi. Avatar vaqti `clip_start + elapsed × playback_rate` bilan xaritalanadi. Standart so‘z rejimida noma’lum matn ijroni uzaytirmaydi. Ixtiyoriy to‘liq harflash ancha uzun vaqt berishi mumkin. Media xaritadagi haqiqiy vaqtga qo‘yiladi, ijro qilinadi yoki pauzaga olinadi.

Pauza, boshidan boshlash va oldinga/orqaga seek ikkala panelga ta’sir qiladi. Avatar aktivi tayyor bo‘lmasa yoki media buffering holatida bo‘lsa, umumiy soat kutadi. Brauzer `play()` so‘rovini rad etsa, ijro to‘xtaydi va qayta bosish uchun xabar chiqadi.

## Avatar va korpus

`Avatar3D.tsx` GLB ni klonlaydi va `interpreter.ts` orqali yangi soch, ko‘zoynak, yuz va kiyim beradi. Qo‘l/barmoq skeleti va yuz morph kanallari saqlanadi. `prepareMotions()` zarur kliplarni oldindan yuklab, parse qilingan aktivlarni qayta ishlatadi. Kalibrlash T-pose o‘rniga yozuvning 1/30 soniyalik dam holati ishlatiladi.

`framing.ts` panel tomonlari nisbati va ko‘rish burchagiga qarab kamera masofasini tanlaydi. Qo‘l/barmoq uchlari, yuz va sochning tor panelda kesilmasligi uchun zaxira qo‘yilgan; kamera ishoralar orasida sakramaydi.

Backend va frontend manifestlari aktiv identifikatori, manba URL, Git blob SHA, litsenziya va davomiylikni bog‘laydi. Ixtiyoriy yo‘l `animation_asset` sifatida qabul qilinmaydi. Importer va texnik cheklovlar [AVATAR.md](AVATAR.md) da.

Amaldagi 50 aktivning 24 tasi lug‘at klipi, 26 tasi `kind: fingerspelling`, `letter: A`–`Z` bilan ajratilgan barmoq alifbosidir. Harf metama’lumoti kanonik manifestdan olinadi; faqat klip nomini A deb qo‘yish uni ishonchli harfga aylantirmaydi.

## Brauzerda avatarli video eksporti

`compositeExport.ts` original video kadrini canvasga nisbatini saqlab joylaydi va pastki o‘ng burchakka avatar canvasini qo‘yadi. Audio manba uchun fon yaratiladi. Joriy so‘z subtitri va ishora/harf yorlig‘i ham chiziladi. Chiqishning uzun tomoni 1280 piksel bilan cheklangan; `captureStream(30)` video track beradi. Web Audio `MediaElementAudioSourceNode → MediaStreamAudioDestinationNode` orqali o‘sha media ovozini yozuvga ulaydi. Bitta media element uchun audio source qayta ishlatiladi.

`primeRecordingAudio()` eksport kliki ichida, seek/kadrni kutishdan oldin AudioContextni faollashtiradi. Shu sabab audio faollashtirish brauzerning klik ruxsati saqlangan paytda boshlanadi. Uzoq tayyorlashdan keyin yangi audio context yaratish talab qilinmaydi.

Audio faollashuvi bekor qilish signalini va sakkiz soniyalik kutish chegarasini hisobga oladi. Eksportda manbaning ovozi yozilishi uchun media vaqtincha unmute va to‘liq volume holatiga olinadi; yakun/bekor qilishda avvalgi muted/volume tiklanadi. Subtitrning eksportda borligi foydalanuvchining subtitr tanloviga mos. Tayyor natija sahifada boshqaruvli video preview va yuklab olish havolasi orqali beriladi.

MediaRecorder brauzer qo‘llaydigan WebM/Opus kombinatsiyasini tanlaydi. Yozuv real vaqtda bo‘laklar bilan yig‘iladi; 256 MB ga yetganda bekor qilinadi. Yakuniy `dataavailable` va `stop` dan keyingina Blob/download havolasi yaratiladi. MP4 kodlash yoki serverda video render bu oqimga kirmaydi.

Boshlashdan oldin ijro 0 ga qaytariladi va media seek hamda birinchi mos avatar kadri chizilishi kutiladi. Yozuv davomida fayl, rejim va seek boshqaruvlari bloklanadi. Manba ishorani kutadigan reja holdida avatar soati yuradi va yozuv davom etadi. Umumiy soat 300 ms muzlasa, recorder pauza qiladi; vaqt siljiganda davom etadi. Tab yashirilishi, bekor qilish, media/rasm o‘qish yoki kodlash xatosi yozuvni to‘xtatadi va tracklar tozalanadi. Bunday xatoda tugallangan tarjima fayli berilmaydi.

Rejada birorta ijro qilinadigan ishora/harf bo‘lmasa eksportga ruxsat berilmaydi. Bu tekshiruv bo‘sh avatarni tarjima sifatida taqdim etishni cheklaydi, ammo qisman lug‘at ishorasi mavjudligini to‘liq ASL gap tarjimasiga aylantirmaydi.

Ushbu eksport kodi build va mock hayot sikli sinovidan o‘tgan; haqiqiy brauzerda kodlash, audio/video sinxronligi va yakuniy download alohida tekshiruv talab qiladi. Amaldagi tekshiruv holati [VALIDATION.md](VALIDATION.md) da.

Brauzer API asoslari: [Canvas capture](https://www.w3.org/TR/mediacapture-fromelement/#html-canvas-element-media-capture-extensions), [MediaRecorder](https://www.w3.org/TR/mediastream-recording/), [Web Audio](https://www.w3.org/TR/webaudio/#MediaElementAudioSourceNode).

## Amaliy chegaralar

Bir foydalanuvchilik mahalliy dastur; serverlar `127.0.0.1` bilan cheklangan. Hisoblar, izolyatsiya, bardoshli navbat, ijtimoiy havoladan import va ovozsiz sahna tahlili yo‘q. Nutq aniqligi, lug‘at qamrovi, animatsiya bog‘lanishi va ASL tushunarliligi alohida o‘lchanadi. Umumiy tarjima modeli va ASL foydalanuvchilari tajribasi hali bajarilmagan. Ilmiy mezonlar [RESEARCH_PLAN.md](RESEARCH_PLAN.md) da.
