# Noutbukdagi kichik ML tajribasi — 2026-10-31

Maqsad: tashqi GPU, katta download yoki yangi kutubxona o‘rnatmasdan, mavjud 2D ma’lumotda haqiqiy o‘rganish va o‘lchov jarayonini sinash. Bu inglizcha matndan ASL yaratish modeli emas.

## Ma’lumot va o‘rganish

`train-features-001` dan 5 klip ishlatildi. PCA o‘rganish to‘plami 3 klip / 582 kadr; parametr tanlash 1 klip / 24 kadr; ichki test 1 klip / 590 kadr. Manba video identifikatorlari bo‘limlar orasida takrorlanmasligi tekshirildi. Bular rasmiy validation/test emas, train arxividan ajratilgan kichik tajriba bo‘limlari.

PCA o‘rtachasi va komponentlari faqat o‘rganish kadrlarida hisoblandi. Yetishmayotgan koordinatalar faqat train o‘rtachasi bilan to‘ldirildi; baholashda maskalandi. Validationda 1/4/8/16/32/64 rank orasidan qo‘l RMSEsi eng kichik bo‘lgan 64 tanlandi; test natijasiga qarab tanlov o‘zgartirilmadi.

Validation/testdagi ishonchli nuqtalarga seed=20261031 bilan sigma=0.03 yelka kengligiga teng sun’iy Gaussian shovqin qo‘shildi. Target — shovqin qo‘shilmagan detector nuqtalari, inson tekshirgan haqiqiy pose emas. Per-clip normallashtirish butun klipdan foydalangan; bu offline rekonstruksiya, real vaqt/streaming baholash emas.

## Haqiqiy natija

| Ko‘rsatkich | Natija |
|---|---:|
| PCA fit | 0.0283 s |
| 590 test kadriga inference | 0.00207 s |
| Yuklash/tanlash/baholash bilan hisoblash | 0.2704 s |
| Jarayon peak working set | 40.71 MiB |
| Saqlangan model | 120 214 bayt |
| O‘zgartirilmagan shovqinli kirish: qo‘l RMSE | 0.03008 |
| PCA chiqishi: qo‘l RMSE | 0.03565 |

Qo‘l xatosi **18.49% yomonlashdi**. Umumiy barcha nuqtalar RMSEsi 0.02994 dan 0.02800 ga kamaygan bo‘lsa ham, buni ishora sifatining yaxshilanishi deb hisoblamaymiz. Yuz nuqtalari umumiy o‘rtachada ko‘proq ulushga ega; qo‘l metrikasi alohida saqlanishi kerak.

**Qaror: model platformaga ulanmaydi.** Qo‘l/barmoq tafsilotlarini buzadigan umumiy smoothing/rekonstruksiya mahsulotga chiqarilmasin. Mavjud MaDiS va avatar ishlash yo‘li o‘zgarmadi.

Bu kichik CPU vazifasi Ryzen 9 5900HX / 24 GB RAM noutbukda bajarildi. Katta transformer o‘qitish muddati yoki RAM talabi bu natijadan chiqarilmaydi. Timings bitta lokal run; universal benchmark emas.

## Fayllar va qayta ishga tushirish

- `backend/app/pose_pca.py`: train/reconstruct va maskalangan qo‘l metrikalari.
- `scripts/benchmark_pose_cpu.py`: train/validation/test ajratish, rank tanlash, Windows RAM o‘lchovi, model va hisobot.
- `storage/experiments/pose-cpu-001/report.json`: o‘lchovlar va manba manifest SHA-256.
- `storage/experiments/pose-cpu-001/pose-pca.npz`: kichik o‘rganilgan model.
- `storage/experiments/pose-cpu-001/test-reconstruction.npz`: observed/noisy/reconstructed va maskalar. `allow_pickle=False` bilan o‘qilsin.

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_pose_cpu.py --source datasets/how2sign/train-features-001 --output storage/experiments/pose-cpu-002
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Yangi output papkasidan foydalaning; oldingi natija ustiga yozilmaydi. 39 backend testi o‘tdi. Rank-one rekonstruksiya, yetishmayotgan nuqtalarni train hisobidan chiqarish va invalid rankni rad etish alohida sinaldi.

## Keyingi amaliy chegara

Hozir katta train arxivlarini ochish yoki og‘ir modelni boshidan o‘qitish boshlanmaydi. Frontal RGB kliplar kelgach, aynan mos kamera va vaqtni tekshirish, keyin kengroq manba videolari bo‘yicha mustaqil baholash kerak. Text→3D avatar vazifasi uchun ushbu 2D baseline yetarli emas; alohida mos 3D ma’lumot/pipeline talab qilinadi.
