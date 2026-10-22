# DAVA Space Studio 1.0

ASCII kosmik sahnalar uchun desktop dastur. Terminaldagi ko'z animatsiyasi alohida terminal papkasida.
Har bir kadr kod bilan hisoblanadi; bu oldindan tayyorlangan video emas.

## Linuxda tez boshlash

Repozitoriyni klonlagach desktop papkasida ishga tushiring:

```bash
bash run_linux.sh
```

Python 3.10–3.13 va venv kerak. Tavsiya: Python 3.12.
Birinchi ochilishda pygame-ce va NumPy internetdan .venv ichiga o'rnatiladi.
Keyingi ochilishlar internet talab qilmaydi.

Debian / Kali / Ubuntu'da Python yoki venv yetishmasa:

```bash
sudo apt update
sudo apt install python3 python3-venv
bash run_linux.sh
```

Boshqa distributivlarda Python va venv'ni o'z paket menejeringizdan o'rnating.
Tayyor faylni o'z tizimingizda chiqarish: bash build_linux.sh.
GitHub Actions ham Linux va Windows fayllarini yig'adi.

## Windowsda tez boshlash

1. Repozitoriyni klonlab, desktop papkasini oching.
2. Python 3.12 o'rnating: https://www.python.org/downloads/windows/
3. O'rnatishda **Add python.exe to PATH** ni belgilang.
4. `run_windows.bat` faylini ikki marta bosing.

Birinchi ochilish paketlarni o'rnatadi. Keyin dastur offline ishlaydi.
Tayyor bajariladigan fayllar GitHub Actions → Artifacts bo'limida yig'iladi. Git ichida asosiy manba kod saqlanadi.

`.exe` chiqarish uchun `build_windows.bat`ni oching.
Natija: `dist/DAVA_Space_Studio.exe`.
Shu faylni mos Windows x64 kompyuterga ko'chirish mumkin; u yerda Python kerak emas.

## Imkoniyatlar

- Qora tuynuk va aylanuvchi akkresiya diski.
- Halqali sayyora va uning aylanuvchi yuzasi.
- Harakatlanuvchi spiral galaktika.
- ASCII belgilar yoki nuqtalar; to'rtta rang palitrasi.
- Tezlik, masshtab, qiyalik va detal boshqaruvi.
- Yorug'lik, yulduzlar, pauza, toza va to'liq ekran.
- Sichqoncha bilan aylantirish.
- 1600 × 1000 PNG va TXT eksporti.
- Keyingi ochilish uchun sozlamalarni saqlash.

Interfeys o'zbekcha. Tasvirlar badiiy talqin; ilmiy modellashtirish emas.

| Tugma | Amal |
|---|---|
| Space | Pauza / davom |
| 1 / 2 / 3 | Sahna |
| Sichqoncha bilan sudrash | Burish va qiyalik |
| Sichqoncha g'ildiragi | Masshtab |
| C / G | Keyingi rang / yorug'lik |
| S / T | PNG / TXT saqlash |
| Tab | Toza ekran / panel |
| R | Sozlamalarni tiklash |
| F11 | To'liq ekran |
| H / F1 | Yordam |
| Esc | Orqaga qaytish; oddiy oynada yopish |

Eksportlar odatda `Pictures/DAVA Space Studio` ichiga saqlanadi.
Linuxda tizimning XDG Pictures yo'li ishlatiladi. Yordam oynasida aniq yo'l
va papkani ochish tugmasi bor.

Sozlamalar: Linuxda `~/.config/DavaSpaceStudio/settings.json`;
Windowsda `%LOCALAPPDATA%\DavaSpaceStudio\settings.json`.
Yangidan boshlash: `--fresh` argumenti.

## Bitta koddan ikkita dastur

Ilovaning hisoblash, tasvirlash va interfeys kodi **main.py** ichida.
Python + pygame-ce + NumPy ishlatilgan. OpenGL va maxsus videokarta talab qilinmaydi.
Ilova kodi qayta yozilmaydi; bajariladigan fayllar har bir tizimda alohida yig'iladi.

Linuxda `bash build_linux.sh` → `dist/DAVA_Space_Studio.run`.

Windowsda `build_windows.bat` → `dist/DAVA_Space_Studio.exe`.

Avtomatik yig'ish repozitoriy ildizidagi `.github/workflows/build.yml` ichida.
Workflow terminal va desktop papkalaridan yig'adi.
GitHub → Actions → Build applications → Run workflow.
Bitta ishga tushirish ikkita tizimda alohida yig'adi; Artifacts'dan natijalarni oling.
`v*` teglar ham yig'ishni boshlaydi.
Joriy yig'ish holatini Actions sahifasidan tekshiring.

PyInstaller qo'llanmasi: https://pyinstaller.org/en/stable/

## Moslik va tekshiruv holati

| Variant | Holati |
|---|---|
| Python kodi, Linux x86_64 | Offscreen ishlashi, 7 ta funksional test va rasm tekshiruvi o'tkazildi |
| Mahalliy Linux x64 yig'ilishi | Offscreen ochilishi va eksporti tekshirildi; yangi yig'ishlar GitHub Actions'da |
| Windows Python / .exe | Umumiy kod va yig'ish skriptlari berilgan; Windowsda hali tekshirilmagan |
| Barcha Linux / ARM | Universal kafolat yo'q; mos Python muhitidan yoki o'z tizimingizda yig'ishdan foydalaning |

`.run` kengaytmasi barcha Linuxlarda moslik yaratmaydi. Bajariladigan fayl yig'ilgan GNU/Linux muhitiga bog'liq. Eski glibc, Alpine/musl, boshqa protsessor
yoki grafik ish stolisiz muhitda binary ishlamasligi mumkin.
`GLIBC_x.y not found` bo'lsa, koddan ishga tushiring yoki o'z tizimingizda yig'ing.
GitHub workflow Linux yig'ishi Ubuntu 22.04 bazasidan foydalanadi.

## Muammo bo'lsa

- Oyna ochilmasa, terminaldan ochib xabarni ko'ring.
- GLIBC xatosi: `bash run_linux.sh`.
- venv yetishmasa, distributivingizdan `python3-venv` o'rnating.
- Paketlar o'rnatilmasa, internetni tekshirib yana oching.
- Qotish bo'lsa, **Yengil** detalni tanlang va yorug'likni o'chiring.
- `noexec` diskda: faylni foydalanuvchining oddiy papkasiga ko'chiring.
- Windowsda noto'g'ri Python tanlansa: `py -3.12 run.py`;
  yig'ish uchun `py -3.12 run.py --build`.

## Dasturchi uchun

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py --headless --fresh --frames 3 --screenshot preview.png
python main.py --scene 2
python main.py --output-dir /tanlangan/papka
python main.py --version
```

Testlar sahnalar harakati, sonli chegaralar, boshqaruv, sozlamalar va buzilgan
fayl bilan ishlash hamda haqiqiy PNG/TXT eksportini qamrab oladi.
Shrift va boshqa paketlar litsenziyalari: `THIRD_PARTY.md`,
`third_party_licenses/`, `assets/FONT-LICENSE.txt`.
