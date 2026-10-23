# Personal AI Live Voice Translator

ذاتی Windows 11 مترجم کا مرحلہ وار پروجیکٹ۔ صرف اردو ↔ انگریزی؛ ابھی صرف development setup مکمل ہے۔ یہ ابھی قابلِ استعمال translator نہیں ہے۔ مکمل مراحل اور قبولیت کے معیار [PLAN.md](PLAN.md) میں ہیں۔

## مرحلہ 1 — مکمل

2026-10-23 کو اس لیپ ٹاپ پر جانچ:

- Python 3.13.15، 64-bit؛ project-local `.venv`؛ pip 26.2.1۔
- Tcl/Tk 8.6.15؛ Tk window initialize اور بند کرنے کی جانچ کامیاب۔
- sounddevice 0.5.6، numpy 2.5.4؛ متعلقہ dependencies `requirements-lock.txt` میں۔
- `pip check`: No broken requirements found۔
- آڈیو ڈیوائسز دریافت ہوئیں؛ default Realtek microphone اور speakers۔ فہرست میں نام آنے سے اصل recording/playback کی کامیابی ثابت نہیں ہوتی؛ یہ مرحلہ 2 میں آزمائیں گے۔
- کوئی آڈیو record، play یا Gemini کو ارسال نہیں کی گئی۔

## موجودہ environment کی جانچ

پروجیکٹ فولڈر میں PowerShell سے:

```powershell
& '.\.venv\Scripts\python.exe' check_setup.py
& '.\.venv\Scripts\python.exe' -m pip check
```

یہ commands صرف environment اور devices کی معلومات دکھاتی ہیں، recording شروع نہیں کرتیں۔ `.venv` activation یا PowerShell execution policy بدلنا ضروری نہیں۔ Python نصب ہونے سے پہلے کھلا terminal ہو تو عام `python` command استعمال کرنے سے پہلے نیا terminal کھولیں؛ اوپر دیا گیا project interpreter براہِ راست استعمال ہو سکتا ہے۔

## دوسرے کمپیوٹر پر setup

Python 3.13 x64 نصب ہونے کے بعد، project directory میں:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-lock.txt
& '.\.venv\Scripts\python.exe' check_setup.py
```

Dependencies صرف اسی project environment میں نصب کریں۔

## اس لیپ ٹاپ پر ڈاؤن لوڈ کا مسئلہ

`pypi.org` کا DNS جواب ناکام تھا جبکہ سرکاری `www.pypi.org` اور `files.pythonhosted.org` دستیاب تھے۔ صرف installation process میں DNS fallback استعمال کیا گیا؛ HTTPS hostname اور certificate verification برقرار رہی۔ Windows DNS، hosts file، firewall یا مستقل pip configuration تبدیل نہیں کی گئی۔ آئندہ pip download میں DNS error آئے تو network resolution دوبارہ چیک کرنا ہوگا؛ یہ مستقل network repair نہیں ہے۔

## محفوظ فائلیں

API key چیٹ یا source code میں نہ لکھیں۔ آئندہ `.env` میں مقامی طور پر رکھیں گے؛ `.env`، `.venv`، recordings، logs اور key files Git سے خارج ہیں۔ ابھی کسی API key کی ضرورت نہیں۔ کوئی paid service یا virtual audio driver نصب نہیں کیا گیا۔ GitHub remote جوڑا گیا ہے؛ اس repository میں صرف source، منصوبہ اور setup ہدایات محفوظ کریں۔

اگلا مرحلہ صارف کی ہدایت پر مائیک اور playback کا مختصر مقامی تجربہ ہے۔
