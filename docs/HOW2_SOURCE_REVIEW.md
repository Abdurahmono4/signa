# How2 manbasi: foydalanish qarori

Manba https://github.com/srvk/how2-dataset ; tekshirilgan commit `59c8a7523660514a1a55349c2e4f54ffa9ca3953`.

README, baseline README va uning LICENSE nusxalari docs/research/upstream/how2 ichida saqlandi. Manba kodi runtimega ko‘chirilmadi, dataset yuklanmadi. How2 English instructional media/transkript datasetidir; How2Sign ASL yozuvlari bilan bir xil narsa emas.

## Foydali qism

`eval/asr` da etalon nutq matni va baseline gipoteza matni bor. Biz shu baholash tamoyiliga muvofiq, mustaqil WER hisoblagich yozdik: backend/app/asr_metrics.py. scripts/score_transcript.py mavjud lokal ishni mustaqil tayyorlangan reference TXT bilan solishtiradi. Substitution/deletion/insertion alohida sanaladi, tahrirlangan transkript ekanligi hisobotda ko‘rsatiladi. Bu upstream scorer nusxasi yoki aynan uning tokenizatsiyasini takrorlash emas. Sclite bilan aynan teng natija deb da’vo qilinmaydi.

```powershell
.\.venv\Scripts\python.exe scripts/score_transcript.py --job JOB_ID --reference reference.txt --output score-new.json
```

Reference gipotezadan ko‘chirib olinmasin: asl nutqdan tekshirilgan matn bo‘lishi kerak. Hisoblagich WERni to‘g‘ri o‘lchashi etalonning to‘g‘riligini kafolatlamaydi. Punctuation/case e’tiborsiz, apostrofli so‘zlar loyiha tokenizeriga muvofiq saqlanadi; WER 100% dan katta bo‘lishi mumkin. Bo‘sh reference qabul qilinmaydi.

Mavjud sintetik 6 so‘zli inglizcha nutq namunasining ma’lum matni reference sifatida yozildi. Saqlangan original ASR natijasi bilan WER=0, 0 deletion, 0 substitution, 0 insertion. Natija examples/asr-reference-score-001.json. Bu tabiiy nutq, turli talaffuzlar yoki uzun videolarda umumiy aniqlik ko‘rsatkichi emas; ASL sifati umuman baholanmagan.

## Nega eski model olinmadi

Upstream baselines/README PyTorch 0.3.1 va maxsus nmtpytorch 1.5.0 kerakligini yozadi. Eski CUDA environment fayllari mavjud. Bu tayyor ASL/3D avatar modeli emas, hozirgi CPU/Windows 3.11 muhitiga drop-in adapter emas. Mavjud faster-whisper/MaDiS yo‘li saqlanadi.

Repo root README data-like content uchun CC BY-SA va software uchun BSD-2 shartlarini aytadi; ichki baselines/code/LICENSE.md esa MIT va ayrim komponentlarning boshqa litsenziyalarini ko‘rsatadi. Litsenziya butun repoga bir xil deb taxmin qilinmadi. Hozir undan runtime kodi yoki reference corpus tarqatilmaydi; faqat manba tekshiruvi hujjatlari saqlangan.

Original How2 videolarining ko‘pi YouTube’dan o‘chirilgani haqida mualliflar README’da ogohlantiradi; katta download jarayoni ishga tushirilmadi. Bu manba saytning ishlashi uchun majburiy bog‘liqlik qilinmadi.
