# Validation va test fayllari — 2026-11-01

Manzil: `D:\SignBridge-UZ\datasets\how2sign`.

D diskdagi 5 ta yangi arxiv shu papkaga bir disk ichida ko‘chirildi. Avvalgi validation frontal ZIP Downloads papkasidan nusxalandi; originali saqlangan. Tugallanmagan `Unconfirmed *.crdownload` fayllariga tegilmadi. D disk ildizidagi 6 ta CSV bilan loyiha CSVlarining SHA-256 qiymatlari bir xil.

| Split | CSV iboralar | Frontal MP4 | Yon MP4 | Frontal ZIPda yo‘q CSV klipi |
|---|---:|---:|---:|---:|
| Validation | 1741 | 1739 | 1741 | 2 |
| Test | 2357 | 2343 | 2357 | 14 |

Frontal/yon ZIP markaziy kataloglari CSV bilan solishtirildi. Yon nomdagi `-rgb_side` mos CSVning `-rgb_front` identifikatoriga bog‘landi. Hech bir videoga boshqa ibora matni taxminan biriktirilmadi. To‘liq nom ro‘yxatlari `datasets/how2sign/metadata-audit-003.json` ichida. Arxivda yo‘qligi faylning yuklashda buzilganini o‘z-o‘zidan isbotlamaydi.

## Namuna tekshiruvi

- Har splitdan 3 ta frontal va 3 ta yon klip — jami 12 video ZIP CRC va barcha kadrlarining dekodlanishidan o‘tdi.
- `val_2D_keypoints.tar.gz` dan 3 ibora / 1885 kadr; `test_2D_keypoints.tar.gz` dan 3 ibora / 554 kadr o‘qildi. JSON/koordinata parse xatosi 0. Tana, ikki qo‘l, barmoqlar va yuz nuqtalari NPZ hamda contact-sheet sifatida saqlandi.
- Shu 6 frontal klipda 2D kadrlar soni video dekodlangan kadrlar soni bilan mos. 24/30/60 FPS bor.
- Validationdagi bitta yon klip 1319 kadr, frontal 1761; testdagi bitta yon klip 115, frontal 153. Yon ko‘rinishga frontal nuqtalar va vaqtni jim ko‘chirish mumkin emas. Bir xil kadr soni ham lingvistik yoki kadrma-kadr alignment tasdig‘i emas.
- 2D tar boshida ichki MP4lar bor; JSONga yetish uchun chegaralangan oqim o‘qish kerak bo‘ldi. Scan 4 GiB, o‘qilgan JSON 64 MiB va 12000 member bilan cheklangan. Butun tar ochilmadi.

Hisobot: `datasets/how2sign/evaluation-inspection-002/report.json`. Namuna fayllari uning `val`/`test` papkalarida. `evaluation-inspection-001` oldingi kichik prefix tekshiruvi bo‘lib, JSONga yetmagan; yakuniy xulosa uchun 002 ishlatiladi.

## Foydalanish

Test to‘plami model fit yoki platformaning ibora qidiruviga qo‘shilmadi. U mustaqil baholash uchun saqlanadi. Validation manba katalogi avval ham ijro uchun ishlatilgani sabab o‘sha katalogni avtomatik ravishda mustaqil sifat bahosi deb olish mumkin emas. Yangi model o‘qitilmadi; video/JSONning ochilishi ASL tarjima aniqligini bildirmaydi.

Qayta tekshirish (yangi output nomi kerak):

```powershell
Set-Location D:\SignBridge-UZ
.\.venv\Scripts\python.exe scripts\inspect_evaluation_data.py --output datasets/how2sign/evaluation-inspection-003 --clips 3
.\.venv\Scripts\python.exe scripts\audit_how2sign_metadata.py --output datasets/how2sign/metadata-audit-004.json
```

Keyingi to‘liq yaxlitlik tekshiruvida barcha 6 arxiv o‘tdi: 4 ZIPning barcha fayllari CRC va 2 TAR.GZning to‘liq gzip oqimi CRC tekshirildi. Dalil: `datasets/how2sign/evaluation-integrity-001.json`, `all_complete: true`. Barcha videolarni dekodlash, barcha JSON schemalarini tekshirish va ASL mutaxassisi tasdig‘i bajarilmadi. Bu fayllar How2Sign / ASL ma’lumotlari, O‘zbekiston imo-ishora tili emas. Manba: https://how2sign.github.io/ . Metadata litsenziyasi CC BY-NC 4.0.
