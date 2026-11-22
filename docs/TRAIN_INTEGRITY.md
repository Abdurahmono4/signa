# Train arxivlarining to‘liq tekshiruvi — 2026-11-01

Avvalgi namuna va katalog tekshiruvlari butun train arxivlari sog‘lomligini isbotlamagan. To‘liq o‘qishda yangi xatolar topildi. Asl arxivlar o‘chirilmagan va qayta yozilmagan.

| Arxiv | Natija |
|---|---|
| train_rgb_front_clips.zip | Barcha 31048 fayl entrysi o‘qildi; 5 MP4da qayta o‘qishda ham CRC xatosi |
| train_rgb_side_clips.zip | Barcha 31165 fayl o‘qildi; 1 MP4da CRC xatosi |
| train_2D_keypoints.tar.gz | 7457472512 bayt ochilgan oqimdan keyin zlib: invalid stored block lengths; to‘liq gzip tekshiruvi o‘tmadi |

Frontal arxivni dastlabki tekshirishda boshqa bitta klip ham CRC xatosi bergan, keyingi ikki o‘qishda o‘tgan. Sabab bu sinov bilan aniqlanmagan. U ham ehtiyot chorasi sifatida vaqtincha chiqarilgan. Jami 6 frontal klip istisno ro‘yxatida; 31047 katalog yozuvidan 31041 tasi qidiruvda qolgan. CSVda bo‘lib ZIPda yo‘q 118 klip bu sonlardan alohida masala.

## Dalillar

- `datasets/how2sign/train-integrity-final-001.json` — birlashtirilgan xulosa.
- `datasets/how2sign/train-integrity-003.progress.json` — ikkala ZIPning to‘liq CRC natijalari; keypoint bosqichida tekshiruvchi zlib xatosi bilan to‘xtagani uchun progress alohida saqlangan.
- `datasets/how2sign/train-keypoint-integrity-001.json` — zlib xatosini alohida qayta tekshirish.
- `datasets/how2sign/train-exclusions.json` — nomlar, ZIP hajmi/mtime va takroriy o‘qish natijalari.

Qidiruv va resolver faqat shu arxiv imzosiga mos istisnolarni qo‘llaydi; bloklangan klip tayyor keshdan ham olinmaydi. Istisno fayli o‘zgarsa indeks yangilanadi. ZIP fayli almashtirilsa, eski imzoga tegishli istisnolar yangi ZIPga avtomatik tatbiq qilinmaydi; yangi arxivni yana tekshirish kerak.

## Keyingi ma’lumot amallari

1. Buzilgan train 2D arxivini qayta olish/ta’mirlashdan so‘ng alohida yangi nusxa sifatida tekshirish zarur. Ushbu bosqichda 21 GB fayl avtomatik qayta yuklanmagan.
2. Buzilgan RGB kliplarini sog‘lom manbadan tiklash yoki arxivning boshqa nusxasini tekshirish mumkin. Yon videoni frontal ishora deb jim almashtirish mumkin emas.
3. Sog‘lomligi tasdiqlangan train namunalari bilan ishlash mumkin; butun train to‘plami o‘qitishga tayyor deb belgilanmaydi. Oldingi beshta namunaning o‘tganligi ushbu yangi xulosani inkor etmaydi.
4. Validation/testdagi 6 arxiv oldingi to‘liq CRC/gzip tekshiruvidan o‘tgan; ularning hisobotlari alohida saqlangan. Test qidiruv yoki model fitga qo‘shilmagan.

## Model kirishini oldindan tekshirish

`backend/app/neural_preflight.py` lokal tokenizer va compact lug‘atni o‘qiydi; model vaznlari yuklanmaydi. Python object qurish taqiqlangan data-only unpickler ishlatiladi. Asl matn va runnerdagi lowercase/oxirgi tinish belgisi qoidasi tekshiriladi; so‘zlar tashlab ketilmaydi yoki boshqa gapga almashtirilmaydi.

Asl Transformers AutoTokenizer va yengil tokenizers natijalari 4 matnda aynan tengligi lokal CPU runtime orqali tekshirildi. Oldin model o‘rtasida to‘xtagan 7 chunkli ishda nomuvofiq chunk oldindan topildi. HTTP POST `/api/jobs/{id}/neural` 422 javobini 0.334 soniyada qaytardi; yangi worker ochilmadi. Avval ishlagan ibora esa cached plan bilan HTTP 200 qaytardi.

Bu tekshiruv faqat kirish lug‘atiga moslikdir. Mos matnda model albatta yaxshi ishora yaratishini yoki ASL to‘g‘riligini kafolatlamaydi. Harakat, qo‘l/yuz aniqligi va tushunarlilik uchun mutaxassis bahosi hali kerak.
