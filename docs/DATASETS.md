# Ma’lumot va litsenziyalar

2026-10-24 da birlamchi manbalar tekshirildi. Katta dataset yuklanmadi.

| Manba | Til / foydalanish | Qaror |
|---|---|---|
| [How2Sign](https://how2sign.github.io/) | ASL, 80+ soat, tadqiqot uchun | O‘zbek tarjimasiga ulanmagan; yuklanmagan |
| [WLASL](https://github.com/dxli94/WLASL) | ASL, C-UDA, akademik/hisoblash, tijoriy foydalanish taqiqlangan | Startup tarjima bazasiga kiritilmadi |
| [MMS Player](https://github.com/DFKI-SignLanguage/MMS-Player) | GPL-3.0, Blender orqali MMS animatsiya sintezi | Mumkin bo‘lgan offline konverter; hozir runtime dependency emas |
| [Studio Galt](https://github.com/StudioGalt/Sign-Language-Mocap-Archive) | CC0-1.0, Galtis rig va ASL harakat yozuvi | Lokal oldingi loyihadagi GLB va bitta Hello klipi qayta ishlatildi |

Galtis manbasi tarjima xizmati emasligini o‘zi aytadi. Hello faqat ochiq ASL texnik namuna tugmasida ishlaydi. Rest pose harakatsiz holat uchun olinadi. Bular o‘zbek ishorasi emas.

O‘zbek ishoralari bazasi boshlang‘ich holatda bo‘sh. Hech bir yozuv avtomatik tasdiqlanmagan. `datasets/rig-targets.json` bu rig texnik tugunlari, lingvistik dataset emas.

Yozuv maydonlari: id, language, label, gloss, animation_path, duration_ms, source, license, verified, reviewer, notes, keypoint_reference. Oxirgi maydon hozir bo‘sh; keypoint formatini tekshirish hali yo‘q.

Qo‘shish: rozilik va foydalanish huquqini oling → O‘zbekiston karlar hamjamiyati mutaxassisi bilan to‘liq iborani aniqlang → rigga mos animatsiyani tayyorlang → kutubxonada metadata va JSON ni import qiling → tasvir, barmoqlar, yuz va ma’noni tekshiring → tekshiruvchi va asoslangan izoh bilan tasdiqlang. Faqat `uz_sign`, `verified=true` va animatsiyali to‘liq iboralar tarjimada ishlatiladi. Tarjima API tilni avtomatik o‘zgartirmaydi.
