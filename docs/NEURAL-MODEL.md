# MaDiS: mahalliy ASL modeli / local ASL model

Bu alohida CPU muhiti inglizcha matndan MaDiS–How2Sign orqali uzluksiz tana, qo‘l, barmoq va yuz parametrlarini yaratadi. Bu tayyor ishoralarni so‘z bo‘yicha qidirish yoki harflab ko‘rsatish rejimidan farq qiladi. Natija tadqiqot modeli chiqishi; uning ASL aniqligi mutaxassis tomonidan baholanishi kerak. Nutq noto‘g‘ri tanilsa, modelga ham noto‘g‘ri matn beriladi.

64-bit Python 3.11 va Git o‘rnatilgan Windows kompyuterida loyiha ichidan:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup-neural-model.ps1
```

`-RuntimeOnly` faqat alohida Python muhitini o‘rnatadi; `-SkipRuntime` mavjud muhit bilan model fayllarini yakunlaydi. Yuklash uzilsa, shu buyruqni qayta ishlating: tugagan qismlar saqlanadi, yakuniy hajm va SHA-256 tekshiriladi. Bu skript mavjud Whisper o‘rnatgichi `scripts/setup-model.ps1` va `backend/.venv` ni o‘zgartirmaydi.

Muhit: `backend/models/MaDiS/runtime/.venv`; Python 3.11.9, Torch **2.5.0+cpu**, Transformers **4.51.0**, NumPy **1.26.4**, Accelerate **1.15.0**. CUDA, Lightning va trening kutubxonalari talab qilinmaydi. CPU tekshiruvi haqiqiy MaDiS modullarini import qiladi, kichik Qwen3 forward natijasini va `from_pretrained(device_map='cpu')` orqali qayta yuklashni tekshiradi; shundan keyingina `runtime/.signa-ready.json` yoziladi. Bu belgi katta modelning ASL sifati tekshirildi degani emas.

Amaldagi runner bo‘sh xom harakat tokenlarini upstream `[0]` bilan almashtirishidan oldin rad etadi. Nutq pauzalari gap chegaralarini ajratadi; model kirishiga yetishmagan yakuniy tinish belgisi qo‘shiladi. Matnning compact Qwen lug‘atida yo‘q tokeni PAD/EOSga jim aylantirilmaydi: original registr saqlanadi, faqat barcha tokenlarni qamrasa kichik harf varianti olinadi. Original transkript va normallashtirish ro‘yxati natijada saqlanadi. Haqiqiy qayta ishlashlar va cheklovlar [VALIDATION.md](VALIDATION.md) da qayd etilgan.

Yuklanadigan zarur fayllar **7,198,549,119 bayt ≈ 7.20 GB**: How2Sign checkpoint, Qwen paketi va mean/std. Noshirning qo‘shimcha tokenizer checkpointi bilan to‘plam taxminan **8.97 GB** bo‘ladi; bu adapter tokenizator/VAE vaznlarini asosiy checkpointdan oladi va ortiqcha 1.77 GB faylni yuklamaydi. Torch CPU paketi yana 205 MB. Yuklash qismlari, yig‘ilgan fayllar, ochilgan Qwen va muhit uchun kamida 25 GB bo‘sh disk ajrating. Mahalliy tekshirilgan qurilma: Ryzen 9 5900HX, 24 GB RAM, CUDA mavjud emas. CPU bajarish tezligi matn uzunligiga bog‘liq.

Manbalar o‘zgarmas versiyaga biriktirilgan:

- [MaDiS rasmiy kod](https://github.com/2000ZRL/MaDiS), commit `071828ea1b94530dc7ff0a6c009c0a7c6d1f0784`.
- [Rasmiy model fayllari](https://huggingface.co/2000zrl/MaDiS), revision `ceaed59c964820f2c13401a0870b2988686956ad`.
- Fayl hajmlari va SHA-256: `scripts/neural-model-manifest.json`. O‘rnatgich faqat tekshirilgan fayllarni faollashtiradi.

MaDiS manbasidagi `license.txt`: **CC BY-NC-ND 4.0**. Upstream kod alohida va o‘zgartirilmagan holda saqlanadi. Adapter SMPL-X tana modeli yoki uning ro‘yxatdan o‘tishni talab qiladigan mesh fayllarini yuklamaydi. Tijoriy foydalanish yoki qayta tarqatishdan oldin model, kod va tegishli ma’lumot litsenziyalarini alohida tekshirish kerak.

**English:** This isolated, CPU-only research integration generates continuous ASL motion parameters from English text with the official How2Sign checkpoint. It does not establish expert-verified translation accuracy. The installer pins source/model revisions, resumes exact download ranges, verifies every asset’s size and SHA-256, safely extracts Qwen, and leaves Whisper untouched. Required inference assets are 7.20 GB; the publisher’s larger 8.97 GB set includes an unused tokenizer checkpoint. No SMPL-X mesh assets are downloaded. Respect the upstream CC BY-NC-ND 4.0 license and evaluate the generated signing with ASL users.
